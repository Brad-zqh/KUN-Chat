"""Incremental local RAG index for the public KUN transcript archive.

The store deliberately indexes completed transcript/text files only. Audio and
temporary downloads are never opened, so it can run beside the downloader and
Whisper worker without interfering with them.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sqlite3
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = PROJECT_ROOT / "data" / "kunkun-rag.sqlite3"
TRAINING_PERMISSION = "unverified"
PERSONA_DB_DEFAULTS = {
    "kunkun": DEFAULT_DB,
    "fengge": Path(r"D:\OneDrive\LLMs\persona-material\fengge\production\fengge-rag.sqlite3"),
    "linqingxia": Path(r"D:\OneDrive\LLMs\persona-material\linqingxia\production\linqingxia-rag.sqlite3"),
    "tulei": Path(r"D:\OneDrive\LLMs\persona-material\tulei\production\tulei-rag.sqlite3"),
    "laocan": Path(r"D:\OneDrive\LLMs\persona-material\Laocan\production\laocan-rag.sqlite3"),
}
_FORBIDDEN_SOURCE_PARTS = {
    "raw_segments_unreviewed",
    "rag_documents_unreviewed",
    "candidate_queue",
}
_INDEX_LOCK = threading.Lock()
_LAST_SCAN = 0.0

_TIMESTAMP = re.compile(
    r"^\s*(?:\d{1,2}:)?\d{1,2}:\d{2}[,.]\d{2,3}\s*-->\s*"
    r"(?:\d{1,2}:)?\d{1,2}:\d{2}[,.]\d{2,3}"
)
_TAG = re.compile(r"<[^>]+>|\{\\[^}]+\}")
_SPACE = re.compile(r"\s+")
_CJK = re.compile(r"[\u3400-\u9fff]+")
_ASCII_WORD = re.compile(r"[a-z0-9]{2,}")


@dataclass
class RagHit:
    content: str
    title: str
    url: str
    path: str
    score: float


@dataclass
class StyleHit:
    text: str
    title: str
    source_id: str
    content_type: str
    tags: list[str]
    score: float


def material_root() -> Path:
    return Path(os.getenv("KUN_MATERIAL_DIR", r"D:\OneDrive\LLMs\kun-material"))


def db_path(persona: str = "kunkun") -> Path:
    persona = persona.strip().lower()
    if persona not in PERSONA_DB_DEFAULTS:
        raise ValueError(f"unsupported RAG persona: {persona}")
    env_name = f"{persona.upper()}_RAG_DB"
    return Path(os.getenv(env_name, str(PERSONA_DB_DEFAULTS[persona])))


def _connect_reviewed_persona(persona: str) -> sqlite3.Connection:
    """Open a prebuilt, reviewed persona database without mutating it."""

    target = db_path(persona)
    if not target.is_file():
        raise FileNotFoundError(f"reviewed persona RAG database not found: {target}")
    conn = sqlite3.connect(f"file:{target.as_posix()}?mode=ro", uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def approved_transcript_dir(root: Path | None = None) -> Path:
    """Return the sole production transcript directory.

    Production indexing is intentionally fail-closed: an override is accepted
    only when it still points at a directory named ``approved_rag``. Review
    queues and unreviewed exports must never become retrieval context.
    """

    material = root or material_root()
    target = Path(
        os.getenv(
            "KUN_APPROVED_TRANSCRIPT_DIR",
            str(material / "transcripts" / "approved_rag"),
        )
    )
    lowered_parts = {part.lower() for part in target.parts}
    forbidden = sorted(lowered_parts & _FORBIDDEN_SOURCE_PARTS)
    if forbidden or target.name.lower() != "approved_rag":
        detail = ", ".join(forbidden) if forbidden else target.name
        raise RuntimeError(
            "KUN_APPROVED_TRANSCRIPT_DIR must point to a directory named "
            f"approved_rag; rejected production RAG source: {detail}"
        )
    return target


def style_examples_path(root: Path | None = None) -> Path:
    """Return the reviewed-only short-form style export.

    The fixed filename is intentional: a caller cannot redirect production to
    the unreviewed candidate JSONL by changing an environment variable.
    """

    material = root or material_root()
    target = Path(
        os.getenv(
            "KUN_STYLE_EXAMPLES_FILE",
            str(material / "training" / "style_examples.jsonl"),
        )
    )
    lowered_parts = {part.lower() for part in target.parts}
    forbidden = sorted(lowered_parts & _FORBIDDEN_SOURCE_PARTS)
    if forbidden or target.name.lower() != "style_examples.jsonl":
        detail = ", ".join(forbidden) if forbidden else target.name
        raise RuntimeError(
            "KUN_STYLE_EXAMPLES_FILE must point to style_examples.jsonl; "
            f"rejected style source: {detail}"
        )
    return target


def _connect(path: Path | None = None) -> sqlite3.Connection:
    target = path or db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            fingerprint TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            indexed_at REAL NOT NULL
        );
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY,
            source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            tokens, tokenize='unicode61'
        );
        CREATE TABLE IF NOT EXISTS style_examples (
            id INTEGER PRIMARY KEY,
            example_key TEXT NOT NULL UNIQUE,
            fingerprint TEXT NOT NULL,
            source_id TEXT NOT NULL,
            source_part_id TEXT NOT NULL,
            title TEXT NOT NULL,
            content_type TEXT NOT NULL,
            upload_date TEXT NOT NULL,
            text TEXT NOT NULL,
            tags_json TEXT NOT NULL,
            style_score REAL NOT NULL
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS style_fts USING fts5(
            tokens, tokenize='unicode61'
        );
        """
    )
    return conn


def _clean_lines(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    rows: list[str] = []
    for raw_line in raw.splitlines():
        line = html.unescape(_TAG.sub("", raw_line)).strip()
        if not line or line.isdigit() or _TIMESTAMP.match(line) or line.startswith("WEBVTT"):
            continue
        line = _SPACE.sub(" ", line)
        if line and line not in rows[-1:]:
            rows.append(line)
    return rows


def _chunks(lines: list[str], max_chars: int = 420, overlap_lines: int = 2) -> list[str]:
    output: list[str] = []
    buffer: list[str] = []
    length = 0
    for line in lines:
        if buffer and length + len(line) > max_chars:
            output.append(" ".join(buffer))
            buffer = buffer[-overlap_lines:]
            length = sum(map(len, buffer))
        buffer.append(line)
        length += len(line)
    if buffer:
        output.append(" ".join(buffer))
    return [item for item in output if len(item) >= 12]


def _tokens(text: str) -> list[str]:
    lowered = text.lower()
    result: list[str] = []
    for block in _CJK.findall(lowered):
        chars = list(block)
        result.extend(chars[i] + chars[i + 1] for i in range(len(chars) - 1))
        if len(chars) >= 3:
            result.extend("".join(chars[i : i + 3]) for i in range(len(chars) - 2))
    result.extend(_ASCII_WORD.findall(lowered))
    return list(dict.fromkeys(result))


def _metadata_map(root: Path) -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    meta_root = root / "metadata" / "infojson"
    if not meta_root.exists():
        return result
    for path in meta_root.rglob("*.info.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        stem = path.name.removesuffix(".info.json")
        title = str(data.get("title") or data.get("fulltitle") or stem).strip()
        url = str(data.get("webpage_url") or data.get("original_url") or "").strip()
        result[stem] = (title, url)
    return result


def _transcript_files(root: Path) -> list[Path]:
    transcript_root = approved_transcript_dir(root)
    if not transcript_root.exists():
        return []
    allowed = {".srt", ".vtt", ".txt", ".md"}
    now = time.time()
    files: list[Path] = []
    for path in transcript_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in allowed:
            continue
        if ".part" in path.name.lower():
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        if stat.st_size < 20 or stat.st_size > 10 * 1024 * 1024:
            continue
        if now - stat.st_mtime < 3:
            continue
        files.append(path)
    return sorted(files)


def _index_style_examples(
    conn: sqlite3.Connection, root: Path, *, force: bool = False
) -> tuple[int, int]:
    """Incrementally index the reviewed short-utterance style export."""

    path = style_examples_path(root)
    rows: list[dict] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (
                row.get("speaker_scope") != "cai_xukun_approved"
                or row.get("semantic_scope") != "cai_xukun_own_speech_approved"
                or row.get("usage") != "style_reference_only"
            ):
                continue
            if len(str(row.get("text") or "").strip()) < 10:
                continue
            rows.append(row)

    changed = 0
    added = 0
    seen: set[str] = set()
    for row in rows:
        key = str(row.get("example_id") or "").strip()
        text = _SPACE.sub(" ", str(row.get("text") or "")).strip()
        if not key or not text:
            continue
        seen.add(key)
        fingerprint = hashlib.sha256(
            json.dumps(row, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        current = conn.execute(
            "SELECT id,fingerprint FROM style_examples WHERE example_key=?", (key,)
        ).fetchone()
        if current and current["fingerprint"] == fingerprint and not force:
            continue
        tags = row.get("style_tags") if isinstance(row.get("style_tags"), list) else []
        values = (
            fingerprint,
            str(row.get("source_id") or ""),
            str(row.get("source_part_id") or row.get("source_id") or ""),
            str(row.get("title") or row.get("source_id") or key),
            str(row.get("content_type") or "unknown"),
            str(row.get("upload_date") or ""),
            text,
            json.dumps(tags, ensure_ascii=False),
            float(row.get("style_score") or 0.0),
        )
        if current:
            style_id = int(current["id"])
            conn.execute("DELETE FROM style_fts WHERE rowid=?", (style_id,))
            conn.execute(
                """
                UPDATE style_examples
                SET fingerprint=?,source_id=?,source_part_id=?,title=?,content_type=?,
                    upload_date=?,text=?,tags_json=?,style_score=?
                WHERE id=?
                """,
                (*values, style_id),
            )
        else:
            cursor = conn.execute(
                """
                INSERT INTO style_examples(
                    example_key,fingerprint,source_id,source_part_id,title,content_type,
                    upload_date,text,tags_json,style_score
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (key, *values),
            )
            style_id = int(cursor.lastrowid)
        conn.execute(
            "INSERT INTO style_fts(rowid,tokens) VALUES(?,?)",
            (style_id, " ".join(_tokens(text + " " + " ".join(tags)))),
        )
        changed += 1
        added += 1

    for current in conn.execute("SELECT id,example_key FROM style_examples").fetchall():
        if current["example_key"] in seen:
            continue
        conn.execute("DELETE FROM style_fts WHERE rowid=?", (current["id"],))
        conn.execute("DELETE FROM style_examples WHERE id=?", (current["id"],))
        changed += 1
    return changed, added


def build_index(*, force: bool = False) -> dict[str, int]:
    root = material_root()
    metadata = _metadata_map(root)
    files = _transcript_files(root)
    conn = _connect()
    changed = 0
    chunks_added = 0
    seen_paths: set[str] = set()
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        for path in files:
            stat = path.stat()
            key = str(path.resolve())
            seen_paths.add(key)
            fingerprint = f"{stat.st_size}:{stat.st_mtime_ns}"
            current = conn.execute(
                "SELECT id, fingerprint FROM sources WHERE path=?", (key,)
            ).fetchone()
            if current and current["fingerprint"] == fingerprint and not force:
                continue

            stem = path.stem
            title, url = metadata.get(stem, (stem, ""))
            lines = _clean_lines(path)
            text_chunks = _chunks(lines)
            if not text_chunks:
                continue

            if current:
                old_ids = [row[0] for row in conn.execute("SELECT id FROM chunks WHERE source_id=?", (current["id"],))]
                conn.executemany("DELETE FROM chunks_fts WHERE rowid=?", ((item,) for item in old_ids))
                conn.execute("DELETE FROM chunks WHERE source_id=?", (current["id"],))
                conn.execute(
                    "UPDATE sources SET fingerprint=?, title=?, url=?, indexed_at=? WHERE id=?",
                    (fingerprint, title, url, time.time(), current["id"]),
                )
                source_id = int(current["id"])
            else:
                cursor = conn.execute(
                    "INSERT INTO sources(path,fingerprint,title,url,indexed_at) VALUES(?,?,?,?,?)",
                    (key, fingerprint, title, url, time.time()),
                )
                source_id = int(cursor.lastrowid)

            for index, content in enumerate(text_chunks):
                cursor = conn.execute(
                    "INSERT INTO chunks(source_id,chunk_index,content) VALUES(?,?,?)",
                    (source_id, index, content),
                )
                chunk_id = int(cursor.lastrowid)
                conn.execute(
                    "INSERT INTO chunks_fts(rowid,tokens) VALUES(?,?)",
                    (chunk_id, " ".join(_tokens(content))),
                )
                chunks_added += 1
            changed += 1

        style_changed, style_added = _index_style_examples(conn, root, force=force)

        # Remove disappeared files and files that are no longer eligible after
        # the approved-target speaker gate changes.
        for row in conn.execute("SELECT id,path FROM sources").fetchall():
            if row["path"] in seen_paths:
                continue
            old_ids = [item[0] for item in conn.execute("SELECT id FROM chunks WHERE source_id=?", (row["id"],))]
            conn.executemany("DELETE FROM chunks_fts WHERE rowid=?", ((item,) for item in old_ids))
            conn.execute("DELETE FROM chunks WHERE source_id=?", (row["id"],))
            conn.execute("DELETE FROM sources WHERE id=?", (row["id"],))
        conn.commit()
        counts = conn.execute(
            """
            SELECT (SELECT count(*) FROM sources) AS sources,
                   (SELECT count(*) FROM chunks) AS chunks,
                   (SELECT count(*) FROM style_examples) AS style_examples
            """
        ).fetchone()
        return {
            "files_seen": len(files),
            "files_changed": changed,
            "chunks_added": chunks_added,
            "sources": int(counts["sources"]),
            "chunks": int(counts["chunks"]),
            "style_examples_changed": style_changed,
            "style_examples_added": style_added,
            "style_examples": int(counts["style_examples"]),
        }
    finally:
        conn.close()


def ensure_index(max_age_seconds: float = 15.0) -> dict[str, int] | None:
    global _LAST_SCAN
    if time.monotonic() - _LAST_SCAN < max_age_seconds:
        return None
    with _INDEX_LOCK:
        if time.monotonic() - _LAST_SCAN < max_age_seconds:
            return None
        stats = build_index()
        _LAST_SCAN = time.monotonic()
        return stats


def search(query: str, limit: int = 5, persona: str = "kunkun") -> list[RagHit]:
    persona = persona.strip().lower()
    if persona != "kunkun" and not db_path(persona).is_file():
        return []
    if persona != "kunkun":
        return _search_reviewed_persona(query, limit=limit, persona=persona)
    ensure_index()
    tokens = _tokens(query)
    if not tokens:
        return []
    # Limit query breadth; longer grams are more specific and appear last.
    fts_query = " OR ".join(f'"{token.replace(chr(34), "")}"' for token in tokens[-24:])
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT c.content, s.title, s.url, s.path, bm25(chunks_fts) AS rank
            FROM chunks_fts
            JOIN chunks c ON c.id=chunks_fts.rowid
            JOIN sources s ON s.id=c.source_id
            WHERE chunks_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (fts_query, max(1, min(limit, 12))),
        ).fetchall()
        return [
            RagHit(
                content=row["content"],
                title=row["title"],
                url=row["url"],
                path=row["path"],
                score=round(-float(row["rank"]), 6),
            )
            for row in rows
        ]
    finally:
        conn.close()


def style_search(query: str, limit: int = 4, persona: str = "kunkun") -> list[StyleHit]:
    """Retrieve short public utterances for rhythm, not factual grounding.

    Style retrieval is intentionally *anti-semantic*: examples with lexical
    overlap with the current question are penalized.  Otherwise a model tends
    to copy the example's first-person event into its answer.  Source-part
    diversity also prevents one long livestream from dominating.
    """

    persona = persona.strip().lower()
    if persona != "kunkun" and not db_path(persona).is_file():
        return []
    if persona != "kunkun":
        return _style_search_reviewed_persona(query, limit=limit, persona=persona)
    ensure_index()
    capped = max(1, min(limit, 8))
    conn = _connect()
    try:
        fallback = conn.execute(
            """
            SELECT e.*, 0.0 AS rank
            FROM style_examples e
            ORDER BY e.style_score DESC, e.upload_date DESC
            LIMIT 500
            """,
        ).fetchall()
        query_tokens = set(_tokens(query))

        def order(rows: list[sqlite3.Row], salt: str) -> list[tuple[sqlite3.Row, float]]:
            ranked: list[tuple[sqlite3.Row, float, int]] = []
            for row in rows:
                overlap = len(query_tokens & set(_tokens(row["text"])))
                quality = float(row["style_score"]) - overlap * 3.0
                ranked.append((row, quality, overlap))
            ranked.sort(key=lambda item: (item[2], -item[1], -len(item[0]["text"])))
            # Rotate a high-quality window deterministically so different user
            # turns do not repeatedly prime the model with one catchphrase.
            window_size = min(16, len(ranked))
            if window_size:
                offset = int(hashlib.sha256(f"{salt}\0{query}".encode("utf-8")).hexdigest()[:8], 16) % window_size
                ranked = ranked[offset:window_size] + ranked[:offset] + ranked[window_size:]
            return [(row, score * 0.01) for row, score, _ in ranked]

        spontaneous = order(
            [
                row
                for row in fallback
                if row["content_type"] in {"livestream", "social_or_program_clip"}
            ],
            "informal",
        )
        formal = order([row for row in fallback if row["content_type"] == "interview"], "formal")
        fallback_scored = order(list(fallback), "all")

        # At least half of the prompt comes from informal/live delivery.  The
        # old corpus was 90%+ formal interviews, which made every answer sound
        # like a polished press response even when the user was just chatting.
        informal_target = min(len(spontaneous), max(1, capped // 2))
        candidate_groups = [spontaneous, formal, fallback_scored]

        hits: list[StyleHit] = []
        seen_ids: set[int] = set()
        per_part: dict[str, int] = {}
        for group_index, candidates in enumerate(candidate_groups):
            group_limit = informal_target if group_index == 0 else capped
            added_from_group = 0
            for row, score in candidates:
                row_id = int(row["id"])
                part = str(row["source_part_id"])
                if row_id in seen_ids or per_part.get(part, 0) >= 2 or not 18 <= len(row["text"]) <= 140:
                    continue
                try:
                    tags = json.loads(row["tags_json"])
                except json.JSONDecodeError:
                    tags = []
                if tags == ["neutral_spoken"]:
                    continue
                seen_ids.add(row_id)
                per_part[part] = per_part.get(part, 0) + 1
                hits.append(
                    StyleHit(
                        text=row["text"],
                        title=row["title"],
                        source_id=row["source_id"],
                        content_type=row["content_type"],
                        tags=tags,
                        score=round(score, 6),
                    )
                )
                added_from_group += 1
                if len(hits) >= capped or added_from_group >= group_limit:
                    break
            if len(hits) >= capped:
                break
        return hits
    finally:
        conn.close()


def style_context_for(
    query: str, limit: int = 4, max_chars: int = 1100, persona: str = "kunkun"
) -> str:
    blocks: list[str] = []
    used = 0
    for index, hit in enumerate(style_search(query, limit=limit, persona=persona), 1):
        labels = "、".join(hit.tags[:4]) if hit.tags else "自然口语"
        block = f"[STYLE-{index}｜{hit.content_type}｜{labels}]\n{hit.text}"
        if blocks and used + len(block) > max_chars:
            break
        blocks.append(block)
        used += len(block)
    return "\n\n".join(blocks)


def context_for(
    query: str, limit: int = 5, max_chars: int = 3600, persona: str = "kunkun"
) -> tuple[str, list[dict]]:
    hits = search(query, limit=limit, persona=persona)
    blocks: list[str] = []
    sources: list[dict] = []
    used = 0
    for index, hit in enumerate(hits, 1):
        header = f"[RAG-{index}] {hit.title}"
        if hit.url:
            header += f"\n来源：{hit.url}"
        block = f"{header}\n自动转写片段：{hit.content}"
        if blocks and used + len(block) > max_chars:
            break
        blocks.append(block)
        used += len(block)
        sources.append({
            "id": index,
            "title": hit.title,
            "url": hit.url,
            "score": hit.score,
        })
    return "\n\n".join(blocks), sources


def status(persona: str = "kunkun") -> dict:
    persona = persona.strip().lower()
    if persona != "kunkun" and not db_path(persona).is_file():
        return {
            "persona": persona,
            "database": str(db_path(persona)),
            "sources": 0,
            "chunks": 0,
            "facts": 0,
            "style_documents": 0,
            "style_examples": 0,
            "source_policy": "reviewed_production_pending",
            "training_permission": TRAINING_PERMISSION,
        }
    if persona != "kunkun":
        conn = _connect_reviewed_persona(persona)
        try:
            counts = conn.execute(
                """
                SELECT (SELECT count(*) FROM documents) AS documents,
                       (SELECT count(*) FROM documents WHERE kind = 'fact') AS facts,
                       (SELECT count(*) FROM documents WHERE kind = 'style') AS style_documents,
                       (SELECT count(*) FROM style_examples) AS style_examples
                """
            ).fetchone()
            return {
                "persona": persona,
                "database": str(db_path(persona)),
                "sources": int(counts["documents"]),
                "chunks": int(counts["documents"]),
                "facts": int(counts["facts"]),
                "style_documents": int(counts["style_documents"]),
                "style_examples": int(counts["style_examples"]),
                "source_policy": "reviewed_production_only",
                "training_permission": TRAINING_PERMISSION,
            }
        finally:
            conn.close()
    ensure_index()
    conn = _connect()
    try:
        counts = conn.execute(
            """
            SELECT (SELECT count(*) FROM sources) AS sources,
                   (SELECT count(*) FROM chunks) AS chunks,
                   (SELECT count(*) FROM style_examples) AS style_examples
            """
        ).fetchone()
        return {
            "material_dir": str(material_root()),
            "approved_transcript_dir": str(approved_transcript_dir()),
            "database": str(db_path("kunkun")),
            "sources": int(counts["sources"]),
            "chunks": int(counts["chunks"]),
            "style_examples": int(counts["style_examples"]),
            "source_policy": "approved_only",
            "training_permission": TRAINING_PERMISSION,
        }
    finally:
        conn.close()


def _lexical_score(query: str, text: str) -> float:
    query_tokens = set(_tokens(query))
    if not query_tokens:
        return 0.0
    text_tokens = set(_tokens(text))
    return len(query_tokens & text_tokens) / max(1, len(query_tokens))


def _search_reviewed_persona(query: str, *, limit: int, persona: str) -> list[RagHit]:
    conn = _connect_reviewed_persona(persona)
    try:
        rows = conn.execute(
            """
            SELECT record_id, text, source_title, source_url, kind
            FROM documents
            WHERE kind = 'fact'
              AND semantic_gate IN ('attributed_fact', 'own_speech')
              AND lower(speaker_gate) NOT LIKE '%pending%'
              AND lower(speaker_gate) NOT LIKE '%reject%'
            """
        ).fetchall()
        ranked = sorted(
            rows,
            key=lambda row: (_lexical_score(query, row["text"]), row["kind"] == "facts"),
            reverse=True,
        )[: max(1, min(limit, 12))]
        return [
            RagHit(
                content=str(row["text"]),
                title=str(row["source_title"]),
                url=str(row["source_url"]),
                path=f"{persona}:{row['record_id']}",
                score=round(_lexical_score(query, row["text"]), 6),
            )
            for row in ranked
        ]
    finally:
        conn.close()


def _style_search_reviewed_persona(
    query: str, *, limit: int, persona: str
) -> list[StyleHit]:
    conn = _connect_reviewed_persona(persona)
    try:
        rows = conn.execute(
            """
            SELECT record_id, text, source_url, style_tags_json
            FROM style_examples
            ORDER BY record_id
            """
        ).fetchall()
        ranked = sorted(
            rows,
            key=lambda row: _lexical_score(query, row["text"]),
            reverse=True,
        )
        hits: list[StyleHit] = []
        for row in ranked[: max(1, min(limit, 8))]:
            try:
                tags = json.loads(row["style_tags_json"] or "[]")
            except json.JSONDecodeError:
                tags = []
            hits.append(
                StyleHit(
                    text=str(row["text"]),
                    title=persona,
                    source_id=str(row["record_id"]),
                    content_type="reviewed_public_expression",
                    tags=tags if isinstance(tags, list) else [],
                    score=round(_lexical_score(query, row["text"]), 6),
                )
            )
        return hits
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build/search the incremental KUN transcript RAG index")
    parser.add_argument("--reindex", action="store_true")
    parser.add_argument("--query")
    args = parser.parse_args()
    print(json.dumps(build_index(force=args.reindex), ensure_ascii=False, indent=2))
    if args.query:
        print(json.dumps([asdict(hit) for hit in search(args.query)], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

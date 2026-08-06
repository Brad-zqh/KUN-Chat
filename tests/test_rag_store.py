import json
import os
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from worker import rag_store


class RagStoreTest(unittest.TestCase):
    def test_zouyuxin_private_database_is_isolated_and_searchable(self):
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "zouyuxin.sqlite3"
            conn = sqlite3.connect(database)
            conn.executescript(
                """
                CREATE TABLE documents (
                    record_id TEXT, persona_id TEXT, kind TEXT, text TEXT,
                    source_title TEXT, source_url TEXT, publisher TEXT,
                    published_date TEXT, speaker_gate TEXT, semantic_gate TEXT,
                    locator_json TEXT, training_permission TEXT,
                    audio_training_eligible INTEGER
                );
                CREATE TABLE style_examples (
                    record_id TEXT, persona_id TEXT, text TEXT, source_url TEXT,
                    style_tags_json TEXT, locator_json TEXT,
                    training_permission TEXT
                );
                INSERT INTO documents VALUES (
                    'zyx-f1','zouyuxin','fact','每个人感兴趣的东西不一样',
                    '授权聊天','private://zouyuxin','authorized','2026',
                    'authorized_private_chat_self_only','attributed_fact','{}',
                    'user_authorized_private',0
                );
                INSERT INTO style_examples VALUES (
                    'zyx-s1','zouyuxin','哇，听起来就很安逸。',
                    'private://zouyuxin','["川渝口语"]','{}',
                    'user_authorized_private'
                );
                """
            )
            conn.commit()
            conn.close()
            with patch.dict(os.environ, {"ZOUYUXIN_RAG_DB": str(database)}, clear=False):
                reviewed_status = rag_store.status("zouyuxin")
                self.assertEqual(reviewed_status["facts"], 1)
                self.assertEqual(len(rag_store.search("兴趣", persona="zouyuxin")), 1)
                self.assertEqual(
                    rag_store.style_search("安逸", persona="zouyuxin")[0].source_id,
                    "zyx-s1",
                )

    def test_reviewed_persona_database_is_read_without_reindexing(self):
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "fengge.sqlite3"
            conn = sqlite3.connect(database)
            conn.executescript(
                """
                CREATE TABLE documents (
                    record_id TEXT, persona_id TEXT, kind TEXT, text TEXT,
                    source_title TEXT, source_url TEXT, publisher TEXT,
                    published_date TEXT, speaker_gate TEXT, semantic_gate TEXT,
                    locator_json TEXT, training_permission TEXT,
                    audio_training_eligible INTEGER
                );
                CREATE TABLE style_examples (
                    record_id TEXT, persona_id TEXT, text TEXT, source_url TEXT,
                    style_tags_json TEXT, locator_json TEXT,
                    training_permission TEXT
                );
                INSERT INTO documents VALUES (
                    'f1','fengge','fact','公开表达中的程序员经历','公开访谈',
                    'https://example.com','publisher','2026','approved_publisher',
                    'attributed_fact','{}','unverified',0
                );
                INSERT INTO documents VALUES (
                    'f2','fengge','fact','本人公开说自己重视无障碍出行','公开独白',
                    'https://example.com/monologue','publisher','2026','approved_single_speaker',
                    'own_speech','{}','unverified',0
                );
                INSERT INTO documents VALUES (
                    'sdoc','fengge','style','直播里提到的个人口语片段','公开直播',
                    'https://example.com/live','publisher','2026','approved_clip',
                    'own_speech','{}','unverified',0
                );
                INSERT INTO style_examples VALUES (
                    's0','fengge','今天先随便聊点别的。','https://example.com',
                    '["casual"]','{}','unverified'
                );
                INSERT INTO style_examples VALUES (
                    's1','fengge','先把问题讲清楚，再谈结论。','https://example.com',
                    '["direct"]','{}','unverified'
                );
                """
            )
            conn.commit()
            conn.close()
            with patch.dict(os.environ, {"FENGGE_RAG_DB": str(database)}, clear=False):
                reviewed_status = rag_store.status("fengge")
                self.assertEqual(reviewed_status["sources"], 3)
                self.assertEqual(reviewed_status["facts"], 2)
                self.assertEqual(reviewed_status["style_documents"], 1)
                self.assertEqual(len(rag_store.search("程序员", limit=1, persona="fengge")), 1)
                fact_hits = rag_store.search("个人口语片段", limit=1, persona="fengge")
                self.assertEqual(fact_hits, [])
                own_speech_fact_hits = rag_store.search("无障碍出行", persona="fengge")
                self.assertEqual(own_speech_fact_hits[0].path, "fengge:f2")
                self.assertEqual(rag_store.search("完全无关的量子海豹", persona="fengge"), [])
                style_hits = rag_store.style_search("问题", limit=1, persona="fengge")
                self.assertEqual(len(style_hits), 1)
                self.assertEqual(style_hits[0].source_id, "s1")

    def test_incremental_index_and_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "kun-material"
            transcript = root / "transcripts" / "approved_rag" / "BiliBili" / "demo.srt"
            metadata = root / "metadata" / "infojson" / "BiliBili" / "demo.info.json"
            transcript.parent.mkdir(parents=True)
            metadata.parent.mkdir(parents=True)
            transcript.write_text(
                "1\n00:00:00,000 --> 00:00:04,000\n其实上台紧张很正常\n\n"
                "2\n00:00:04,000 --> 00:00:09,000\n把注意力放回练习和作品\n",
                encoding="utf-8",
            )
            metadata.write_text(
                json.dumps({"title": "公开采访测试", "webpage_url": "https://example.com/demo"}),
                encoding="utf-8",
            )
            old = time.time() - 10
            os.utime(transcript, (old, old))
            database = Path(tmp) / "rag.sqlite3"
            env = {"KUN_MATERIAL_DIR": str(root), "KUN_RAG_DB": str(database)}
            with patch.dict(os.environ, env):
                stats = rag_store.build_index()
                self.assertEqual(stats["sources"], 1)
                self.assertGreaterEqual(stats["chunks"], 1)
                hits = rag_store.search("上台紧张", limit=3)
                self.assertTrue(hits)
                self.assertIn("练习和作品", hits[0].content)
                second = rag_store.build_index()
                self.assertEqual(second["files_changed"], 0)

    def test_unreviewed_environment_switch_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "kun-material"
            approved = root / "transcripts" / "approved_rag" / "approved.txt"
            unreviewed = root / "transcripts" / "raw_segments_unreviewed" / "raw.txt"
            approved.parent.mkdir(parents=True)
            unreviewed.parent.mkdir(parents=True)
            approved.write_text("这是已经审核通过的本人表达内容，允许进入生产检索。", encoding="utf-8")
            unreviewed.write_text("这是未经审核的候选内容，唯一暗号是禁入紫海豹。", encoding="utf-8")
            old = time.time() - 10
            os.utime(approved, (old, old))
            os.utime(unreviewed, (old, old))
            database = Path(tmp) / "rag.sqlite3"
            env = {
                "KUN_MATERIAL_DIR": str(root),
                "KUN_RAG_DB": str(database),
                "KUN_RAG_INCLUDE_UNREVIEWED": "true",
            }
            with patch.dict(os.environ, env, clear=False):
                stats = rag_store.build_index()
                self.assertEqual(stats["files_seen"], 1)
                self.assertEqual(stats["sources"], 1)
                self.assertFalse(rag_store.search("禁入紫海豹"))

    def test_rejects_unreviewed_source_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            forbidden = Path(tmp) / "raw_segments_unreviewed"
            env = {"KUN_APPROVED_TRANSCRIPT_DIR": str(forbidden)}
            with patch.dict(os.environ, env, clear=False):
                with self.assertRaises(RuntimeError):
                    rag_store.approved_transcript_dir()

    def test_style_index_requires_both_review_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "kun-material"
            approved = root / "transcripts" / "approved_rag" / "approved.txt"
            styles = root / "training" / "style_examples.jsonl"
            approved.parent.mkdir(parents=True)
            styles.parent.mkdir(parents=True)
            approved.write_text("这是已经审核通过、可用于事实检索的公开表达。", encoding="utf-8")
            rows = [
                {
                    "example_id": "good:1",
                    "source_id": "good",
                    "source_part_id": "good_p0",
                    "title": "公开直播",
                    "content_type": "livestream",
                    "upload_date": "20260208",
                    "text": "其实我就是想先跟大家聊一会儿，然后再听听你们怎么想",
                    "style_tags": ["spontaneous", "audience_interaction"],
                    "style_score": 8.5,
                    "speaker_scope": "cai_xukun_approved",
                    "semantic_scope": "cai_xukun_own_speech_approved",
                    "usage": "style_reference_only",
                },
                {
                    "example_id": "bad:1",
                    "source_id": "bad",
                    "text": "未经语义审核的内容绝对不能进入风格检索",
                    "speaker_scope": "cai_xukun_approved",
                    "semantic_scope": "pending",
                    "usage": "style_reference_only",
                },
            ]
            styles.write_text(
                "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                encoding="utf-8",
            )
            old = time.time() - 10
            os.utime(approved, (old, old))
            database = Path(tmp) / "rag.sqlite3"
            env = {"KUN_MATERIAL_DIR": str(root), "KUN_RAG_DB": str(database)}
            with patch.dict(os.environ, env, clear=False):
                stats = rag_store.build_index()
                self.assertEqual(stats["style_examples"], 1)
                hits = rag_store.style_search("跟大家聊", limit=3)
                self.assertEqual(len(hits), 1)
                self.assertIn("大家聊一会儿", hits[0].text)
                self.assertNotIn("未经语义审核", rag_store.style_context_for("内容"))


if __name__ == "__main__":
    unittest.main()

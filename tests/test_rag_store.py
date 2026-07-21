import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from worker import rag_store


class RagStoreTest(unittest.TestCase):
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

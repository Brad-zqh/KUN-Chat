import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from worker import local_stt


class LocalSttTest(unittest.TestCase):
    def test_empty_audio_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "没有收到录音"):
            local_stt.transcribe(b"", "audio/webm")

    def test_unsupported_content_type_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "不支持的录音格式"):
            local_stt.transcribe(b"not-audio", "text/plain")

    def test_oversized_audio_is_rejected_before_ffmpeg(self):
        with patch.object(local_stt, "MAX_AUDIO_BYTES", 4):
            with self.assertRaisesRegex(ValueError, "录音过大"):
                local_stt.transcribe(b"12345", "audio/webm")

    def test_incomplete_model_snapshot_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            snapshot = Path(temp_dir)
            (snapshot / "model.bin").touch()
            self.assertFalse(local_stt._valid_snapshot(snapshot))
            (snapshot / "config.json").touch()
            (snapshot / "tokenizer.json").touch()
            self.assertTrue(local_stt._valid_snapshot(snapshot))

    def test_persona_context_corrects_known_name_homophones(self):
        self.assertEqual(
            local_stt._apply_context_corrections("周玉琴你是谁", "zouyuxin"),
            "邹雨芯你是谁",
        )
        self.assertEqual(
            local_stt._apply_context_corrections("清凉善人你好", "qingliangshanren"),
            "清凉山人你好",
        )

    def test_persona_context_does_not_change_other_roles(self):
        self.assertEqual(
            local_stt._apply_context_corrections("周玉琴你是谁", "kunkun"),
            "周玉琴你是谁",
        )


if __name__ == "__main__":
    unittest.main()

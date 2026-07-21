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


if __name__ == "__main__":
    unittest.main()

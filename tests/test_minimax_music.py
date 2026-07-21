import json
import os
import unittest
from unittest.mock import patch

from worker import minimax_music


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(
            {
                "data": {"audio": "https://example.com/generated.mp3", "status": 2},
                "extra_info": {"music_duration": 12345},
                "base_resp": {"status_code": 0, "status_msg": "success"},
            }
        ).encode()


class MiniMaxMusicTest(unittest.TestCase):
    def _env(self, model="music-3.0-free"):
        return patch.dict(
            os.environ,
            {
                "KUN_MUSIC_ENABLED": "true",
                "MINIMAX_API_KEY": "test-key",
                "MINIMAX_MUSIC_MODEL": model,
                "MINIMAX_MUSIC_API_BASE": "https://api.minimax.io",
            },
            clear=False,
        )

    def test_original_generation_never_sends_reference_audio_or_voice_id(self):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return _Response()

        with self._env(), patch("urllib.request.urlopen", fake_urlopen):
            result = minimax_music.generate_original_song(
                "蓝色舞台与夜风",
                "[Verse]\n沿着灯光向前走\n[Chorus]\n把今天唱给你听",
            )

        payload = captured["payload"]
        self.assertEqual(payload["model"], "music-3.0-free")
        self.assertNotIn("audio_url", payload)
        self.assertNotIn("audio_base64", payload)
        self.assertNotIn("cover_feature_id", payload)
        self.assertNotIn("voice_id", payload)
        self.assertIn("do not imitate or identify any real singer", payload["prompt"])
        self.assertEqual(result["audio_url"], "https://example.com/generated.mp3")
        self.assertEqual(result["duration_ms"], 12345)

    def test_cover_model_is_rejected(self):
        with self._env(model="music-cover"):
            with self.assertRaisesRegex(RuntimeError, "仅允许"):
                minimax_music.generate_original_song("原创主题", "这是一段完全原创的测试歌词内容")

    def test_short_lyrics_are_rejected_before_network(self):
        with self._env():
            with self.assertRaisesRegex(ValueError, "10–800"):
                minimax_music.generate_original_song("原创主题", "太短")


if __name__ == "__main__":
    unittest.main()

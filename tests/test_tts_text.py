import unittest

from worker.web_server import _normalize_tts_text


class TtsTextNormalizationTest(unittest.TestCase):
    def test_ikun_is_pronounced_ai_kun(self):
        self.assertEqual(_normalize_tts_text("我是你的IKUN"), "我是你的爱坤")
        self.assertEqual(_normalize_tts_text("i kun一直都在"), "爱坤一直都在")

    def test_unrelated_english_is_unchanged(self):
        self.assertEqual(_normalize_tts_text("KUN Chat"), "KUN Chat")

    def test_emotion_stage_directions_are_not_spoken(self):
        self.assertEqual(
            _normalize_tts_text("（语气平静）打球的话，就是练习时候偶尔放松一下。"),
            "打球的话，就是练习时候偶尔放松一下。",
        )
        self.assertEqual(
            _normalize_tts_text("[轻笑]我知道，还是慢慢来。"),
            "我知道，还是慢慢来。",
        )

    def test_normal_parenthetical_content_is_preserved(self):
        self.assertEqual(
            _normalize_tts_text("这次演出（2026年巡演）会认真准备。"),
            "这次演出（2026年巡演）会认真准备。",
        )


if __name__ == "__main__":
    unittest.main()

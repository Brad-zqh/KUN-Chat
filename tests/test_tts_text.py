import unittest

from worker.web_server import (
    _normalize_tts_text,
    _strip_repetitive_sentence_openers,
    _strip_stage_directions,
)


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
        self.assertEqual(
            _normalize_tts_text("（笑了一下）我也挺想你们的。"),
            "我也挺想你们的。",
        )

    def test_normal_parenthetical_content_is_preserved(self):
        self.assertEqual(
            _normalize_tts_text("这次演出（2026年巡演）会认真准备。"),
            "这次演出（2026年巡演）会认真准备。",
        )

    def test_stage_directions_are_hidden_from_visible_reply(self):
        self.assertEqual(
            _strip_stage_directions("（语气平和）Deadman 那个副歌确实有跨度。"),
            "Deadman 那个副歌确实有跨度。",
        )
        self.assertEqual(
            _strip_stage_directions("我会去看（2026年巡演）。"),
            "我会去看（2026年巡演）。",
        )

    def test_laocan_mechanical_sentence_opening_a_is_removed(self):
        self.assertEqual(
            _strip_repetitive_sentence_openers(
                "啊，这件事可以慢慢说。啊，我先讲个具体例子。结尾自然啊。",
                "laocan",
            ),
            "这件事可以慢慢说。我先讲个具体例子。结尾自然啊。",
        )

    def test_other_personas_keep_their_original_text(self):
        text = "啊，这件事可以慢慢说。"
        self.assertEqual(_strip_repetitive_sentence_openers(text, "fengge"), text)


if __name__ == "__main__":
    unittest.main()

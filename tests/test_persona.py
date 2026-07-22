import os
import unittest
from unittest.mock import patch

from worker.persona import build_system_prompt


class PersonaTest(unittest.TestCase):
    def test_fengge_prompt_is_available(self):
        prompt = build_system_prompt("fengge")
        self.assertIn("峰哥", prompt)
        self.assertIn("AI 同人角色", prompt)
        self.assertIn("不是峰哥（峰哥亡命天涯）本人", prompt)
        self.assertNotIn("你就是峰哥本人", prompt)

    def test_new_public_personas_are_available_and_disclosed(self):
        for persona, display in (("linqingxia", "林青霞"), ("tulei", "涂磊")):
            with self.subTest(persona=persona):
                prompt = build_system_prompt(persona)
                self.assertIn(display, prompt)
                self.assertIn("AI 同人角色", prompt)
                self.assertIn("facts/style RAG", prompt)
                self.assertIn("未审核候选不得使用", prompt)

    def test_kunkun_prompt_discloses_ai_identity(self):
        prompt = build_system_prompt("kunkun")
        self.assertIn("AI 同人", prompt)
        self.assertIn("不是蔡徐坤本人", prompt)
        self.assertIn("原创对话示例", prompt)
        self.assertIn("不是真人原话", prompt)

    def test_kunkun_does_not_repeat_intro_during_normal_chat(self):
        prompt = build_system_prompt("kunkun")
        self.assertIn("普通对话中不要重复", prompt)
        self.assertIn("每次回答必须先接住用户这一轮", prompt)
        self.assertIn("用户：我是你的 IKUN", prompt)

    def test_kunkun_avoids_formulaic_ai_tone_and_fake_schedules(self):
        prompt = build_system_prompt("kunkun")
        self.assertIn("不强行升华", prompt)
        self.assertIn("不以第一人称编造计划", prompt)
        self.assertIn("心理咨询腔", prompt)
        self.assertIn("轻微重复、自我修正", prompt)
        self.assertIn("不要自动把每个话题改造成成长建议", prompt)

    def test_environment_selects_kunkun(self):
        with patch.dict(os.environ, {"PERSONA_NAME": "kunkun"}):
            self.assertIn("坤坤", build_system_prompt())

    def test_unknown_persona_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Unknown persona"):
            build_system_prompt("not-a-persona")


if __name__ == "__main__":
    unittest.main()

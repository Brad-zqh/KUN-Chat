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
        for persona, display in (("linqingxia", "青霞"), ("tulei", "磊磊")):
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

    def test_laocan_prompt_uses_reviewed_rag_and_is_disclosed(self):
        prompt = build_system_prompt("laocan")
        self.assertIn("老残", prompt)
        self.assertIn("不要把残疾经历当作人物标签", prompt)
        self.assertIn("不得使用歧视、猎奇、怜悯化或冒犯性表达", prompt)
        self.assertIn("宓国贤", prompt)
        self.assertIn("AI 同人角色", prompt)
        self.assertIn("人物专属 facts/style RAG 最小生产库已启用", prompt)
        self.assertIn("不要把来宾、朋友段子、歌曲或诗歌朗读", prompt)

    def test_qiuhao_prompt_uses_authorized_isolated_materials(self):
        prompt = build_system_prompt("qiuhao")
        self.assertIn("创建者本人明确授权", prompt)
        self.assertIn("对外昵称皓哥", prompt)
        self.assertIn("皓哥独立 production RAG", prompt)
        self.assertIn("群友消息只能作为理解上下文", prompt)
        self.assertIn("不代表本人作出现实承诺", prompt)

    def test_qingliangshanren_prompt_uses_family_authorized_isolated_materials(self):
        prompt = build_system_prompt("qingliangshanren")
        self.assertIn("家人明确授权", prompt)
        self.assertIn("对外昵称爷爷", prompt)
        self.assertIn("清凉山人独立 production RAG", prompt)
        self.assertIn("朗读的古文不是私人经历", prompt)
        self.assertIn("不代表本人作出现实承诺", prompt)

    def test_nainai_prompt_uses_family_authorized_voice_without_other_rag(self):
        prompt = build_system_prompt("nainai")
        self.assertIn("家人明确授权", prompt)
        self.assertIn("对外称奶奶", prompt)
        self.assertIn("当前没有独立 production RAG", prompt)
        self.assertIn("禁止读取或迁移其他人物库", prompt)
        self.assertIn("不代表本人作出现实承诺", prompt)

    def test_zouyuxin_prompt_uses_authorized_private_rag_without_other_personas(self):
        prompt = build_system_prompt("zouyuxin")
        self.assertIn("确认有权使用", prompt)
        self.assertIn("对外昵称邹大猩猩", prompt)
        self.assertIn("邹雨芯独立 production RAG", prompt)
        self.assertIn("另一位聊天者", prompt)
        self.assertIn("禁止读取或迁移其他人物库", prompt)
        self.assertIn("不是现实中的邹雨芯本人", prompt)


if __name__ == "__main__":
    unittest.main()

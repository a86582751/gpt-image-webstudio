import unittest

import app


class ReasoningSettingsTest(unittest.TestCase):
    def test_glm_52_uses_native_reasoning_effort(self):
        self.assertEqual(
            app.apply_reasoning_settings({}, "openai_chat", "最高", "glm-5.2"),
            {"reasoning_effort": "max"},
        )
        self.assertEqual(
            app.apply_reasoning_settings({}, "openai_chat", "关闭", "glm-5.2"),
            {"reasoning_effort": "none"},
        )

    def test_non_glm_chat_mapping_is_unchanged(self):
        self.assertEqual(
            app.apply_reasoning_settings({}, "openai_chat", "最高", "gpt-5"),
            {"reasoning_effort": "high"},
        )
        self.assertEqual(app.apply_reasoning_settings({}, "openai_chat", "关闭", "gpt-5"), {})


class RandomEnhancePromptTest(unittest.TestCase):
    def test_used_scenes_are_injected_without_template_variables(self):
        old_prompt = app.CONFIG["random_user_prompt"]
        try:
            app.CONFIG["random_user_prompt"] = "请创建一段随机图像生成提示词。"
            prompt = app.build_random_user_prompt("夜间室内", used_scenes=["书店", "洗衣房"])
            self.assertIn("本次创作方向：夜间室内", prompt)
            self.assertIn("已经用过场景：书店、洗衣房", prompt)
            self.assertIn("请避开这些地点和场景", prompt)
        finally:
            app.CONFIG["random_user_prompt"] = old_prompt

    def test_used_scenes_template_variable(self):
        old_prompt = app.CONFIG["random_user_prompt"]
        try:
            app.CONFIG["random_user_prompt"] = "方向：{{preference}}\n已经用过场景：{{used_scenes}}"
            prompt = app.build_random_user_prompt("雨夜", used_scenes=["浴室", "卧室"])
            self.assertEqual(prompt, "方向：雨夜\n已经用过场景：浴室、卧室")
        finally:
            app.CONFIG["random_user_prompt"] = old_prompt

    def test_scene_summary_is_sanitized(self):
        self.assertEqual(app.sanitize_scene_summary("场景概述：雨夜车站。\n说明文字"), "雨夜车站")


if __name__ == "__main__":
    unittest.main()

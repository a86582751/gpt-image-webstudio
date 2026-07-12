import unittest
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

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


class SeedreamInterfaceFormatTest(unittest.TestCase):
    def test_official_seedream_url_is_unchanged(self):
        self.assertEqual(
            app.resolve_seedream_api_url("https://ark.cn-beijing.volces.com/api/v3"),
            "https://ark.cn-beijing.volces.com/api/v3/images/generations",
        )

    def test_relay_root_uses_openai_compatible_paths(self):
        self.assertEqual(
            app.resolve_api_url("https://api.example.com"),
            "https://api.example.com/v1/images/generations",
        )
        self.assertEqual(
            app.resolve_edit_api_url("https://api.example.com"),
            "https://api.example.com/v1/images/edits",
        )

    def test_interface_format_switch(self):
        old_value = app.CONFIG.get("seedream_interface_format")
        try:
            app.CONFIG["seedream_interface_format"] = "官方方舟"
            self.assertTrue(app.seedream_uses_official_interface())
            app.CONFIG["seedream_interface_format"] = "OpenAI 兼容中转"
            self.assertFalse(app.seedream_uses_official_interface())
        finally:
            app.CONFIG["seedream_interface_format"] = old_value


class SharedPromptJobTest(unittest.TestCase):
    def test_prompt_job_generates_prompt_and_scene_with_shared_context(self):
        with patch.object(app, "generate_random_prompt", return_value="测试提示词") as generate_prompt:
            with patch.object(app, "summarize_prompt_scene", return_value="书店") as summarize_scene:
                result = app.generate_random_prompt_job(
                    2,
                    "组",
                    "初始提示词",
                    "https://example.com/v1",
                    "text-model",
                    "key",
                    "夜景",
                    "自动识别",
                    1,
                    2,
                    "高",
                    used_scenes=["洗衣房"],
                    summarize_scene=True,
                )

        self.assertEqual(result[:3], (2, "测试提示词", "书店"))
        self.assertEqual(generate_prompt.call_args.kwargs["used_scenes"], ["洗衣房"])
        summarize_scene.assert_called_once()


class BatchConcurrencyTest(unittest.TestCase):
    def test_bounded_runner_replenishes_without_exceeding_limit(self):
        lock = threading.Lock()
        active = 0
        max_active = 0

        def worker(job_index):
            nonlocal active, max_active
            with lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.01)
            with lock:
                active -= 1
            return job_index

        completed = []
        for job_index, future, stopped in app.run_bounded_concurrent_jobs(
            range(1, 7),
            2,
            worker,
            lambda index: index,
        ):
            self.assertFalse(stopped)
            completed.append(future.result())

        self.assertEqual(sorted(completed), list(range(1, 7)))
        self.assertEqual(max_active, 2)

    def test_bounded_runner_refills_after_first_completion(self):
        started = []
        first_wave_release = threading.Event()

        def worker(job_index):
            started.append(job_index)
            if job_index == 1:
                time.sleep(0.01)
            elif job_index == 2:
                first_wave_release.wait(timeout=1)
            return job_index

        iterator = app.run_bounded_concurrent_jobs(
            range(1, 4),
            2,
            worker,
            lambda index: index,
        )
        _job_index, first_future, stopped = next(iterator)
        self.assertFalse(stopped)
        self.assertEqual(first_future.result(), 1)

        deadline = time.perf_counter() + 0.5
        while 3 not in started and time.perf_counter() < deadline:
            time.sleep(0.005)
        self.assertIn(3, started)
        first_wave_release.set()
        list(iterator)

    def test_launch_gate_spaces_dynamic_requests(self):
        gate = app.ImageRequestLaunchGate(0.02)
        launch_times = []
        lock = threading.Lock()

        def worker():
            gate.wait()
            with lock:
                launch_times.append(time.perf_counter())

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(worker) for _ in range(3)]
            for future in futures:
                future.result()

        launch_times.sort()
        gaps = [later - earlier for earlier, later in zip(launch_times, launch_times[1:])]
        self.assertTrue(all(gap >= 0.012 for gap in gaps), gaps)


if __name__ == "__main__":
    unittest.main()

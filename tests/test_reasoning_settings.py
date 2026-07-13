import builtins
import dis
import inspect
import tempfile
import unittest
import threading
import time
import types
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import app
from webstudio import config, core, image_tasks, logging_utils, prompt_history, runtime, settings, text_tasks, ui
from webstudio.workflows import creative, edit, iterative, manual, random, reverse


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

    def test_official_payload_builder_is_available_in_image_task_layer(self):
        payload = image_tasks.build_seedream_payload(
            "测试提示词",
            "2560x1440",
            "doubao-seedream-5-0-pro-260628",
            "16:9 宽屏",
            output_format="png",
            watermark="开启",
        )
        self.assertEqual(payload["size"], "2560x1440")
        self.assertEqual(payload["output_format"], "png")
        self.assertTrue(payload["watermark"])

    def test_seedream_relay_edit_builds_multipart_files(self):
        old_value = app.CONFIG.get("seedream_interface_format")
        captured = {}

        def fake_post(*_args, **kwargs):
            captured.update(kwargs)
            return object()

        def fake_save(_items, saved_paths, *_args, **_kwargs):
            saved_paths.append("result.png")

        try:
            app.CONFIG["seedream_interface_format"] = "OpenAI 兼容中转"
            with patch.object(
                image_tasks,
                "prepare_seedream_input_image",
                return_value={
                    "filename": "input.png",
                    "bytes": b"image-bytes",
                    "mime_type": "image/png",
                    "data_url": "data:image/png;base64,aW1hZ2UtYnl0ZXM=",
                },
            ), patch.object(image_tasks.requests, "post", side_effect=fake_post), patch.object(
                image_tasks, "parse_image_items", return_value=[{"b64_json": "ignored"}]
            ), patch.object(image_tasks, "save_images_from_items", side_effect=fake_save):
                result, _prepared = image_tasks.generate_one_image_edit(
                    "测试编辑",
                    ["input.png"],
                    ".",
                    "1:1 正方形",
                    "高清",
                    "豆包 Seedream",
                    "https://gpt.example.com",
                    "gpt-image-2",
                    "high",
                    "gpt-key",
                    "https://relay.example.com",
                    "doubao-seedream-5-0-pro-260628",
                    "seedream-key",
                    "url",
                    "自动",
                    "关闭",
                    "high",
                    "test",
                    retry_count=0,
                )
        finally:
            app.CONFIG["seedream_interface_format"] = old_value

        self.assertEqual(result, "result.png")
        self.assertEqual(captured["data"]["model"], "doubao-seedream-5-0-pro-260628")
        self.assertEqual(captured["files"][0][0], "image[]")
        self.assertEqual(captured["files"][0][1][1].getvalue(), b"image-bytes")


class SharedPromptJobTest(unittest.TestCase):
    def test_prompt_job_generates_prompt_and_scene_with_shared_context(self):
        with patch.object(text_tasks, "generate_random_prompt", return_value="测试提示词") as generate_prompt:
            with patch.object(text_tasks, "summarize_prompt_scene", return_value="书店") as summarize_scene:
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

    def test_streamed_gallery_includes_current_completion_and_preserves_job_index(self):
        second_future = Future()
        second_future.set_result((2, "提示词二", "second.png", 2.0, []))
        first_future = Future()
        first_future.set_result((1, "提示词一", "first.png", 1.0, []))

        def fake_runner(*_args, **_kwargs):
            yield 2, second_future, False
            yield 1, first_future, False

        with patch.object(image_tasks, "run_bounded_concurrent_jobs", side_effect=fake_runner):
            updates = list(
                image_tasks.generate_images_concurrently(
                    [(1, "提示词一"), (2, "提示词二")],
                    ".",
                    "1:1 正方形",
                    "高清",
                    "GPT Image",
                    "https://example.com",
                    "gpt-image-2",
                    "high",
                    "key",
                    "https://seedream.example.com",
                    "doubao-seedream-5-0-pro-260628",
                    "seedream-key",
                    "url",
                    "自动",
                    "关闭",
                    2,
                )
            )

        self.assertEqual(updates[1][0], [("second.png", "第 2 张")])
        self.assertEqual(
            updates[2][0],
            [("first.png", "第 1 张"), ("second.png", "第 2 张")],
        )
        self.assertIn("刚完成第 2 张", updates[1][1])

    def test_creative_gallery_uses_prompt_segment_labels(self):
        gallery = core.build_indexed_gallery_items(
            [(3, "third.png", 1.0), (1, "first.png", 1.0)],
            item_label="段",
        )
        self.assertEqual(gallery, [("first.png", "第 1 段"), ("third.png", "第 3 段")])

    def test_creative_stream_reports_and_displays_same_prompt_segment(self):
        release_first = threading.Event()

        def fake_prompt_job(index, *_args, **_kwargs):
            return index, f"提示词{index}", "", []

        def fake_image(prompt, *_args, **_kwargs):
            index = int(prompt[-1])
            if index == 1:
                release_first.wait(timeout=1)
                time.sleep(0.01)
            else:
                release_first.set()
            return f"image-{index}.png"

        with tempfile.TemporaryDirectory() as temp_dir, patch.object(
            creative, "generate_random_prompt_job", side_effect=fake_prompt_job
        ), patch.object(creative, "generate_one_image", side_effect=fake_image), patch.object(
            creative, "persist_config"
        ), patch.object(creative, "save_prompt_batch"):
            updates = list(
                creative.generate_creative_images(
                    temp_dir,
                    2,
                    False,
                    2,
                    2,
                    0,
                    0,
                    0,
                    "GPT Image",
                    "1:1 正方形",
                    "高清",
                    "https://image.example.com",
                    "gpt-image-2",
                    "high",
                    "image-key",
                    "https://seedream.example.com",
                    "doubao-seedream-5-0-pro-260628",
                    "seedream-key",
                    "url",
                    "自动",
                    "关闭",
                    "https://text.example.com",
                    "text-model",
                    "text-key",
                    "自动识别",
                    "关闭",
                    "测试方向",
                )
            )

        second_completion = next(update for update in updates if "刚完成第 2 段对应图片" in update[2])
        self.assertEqual(second_completion[1], [("image-2.png", "第 2 段")])


class RefactorSmokeTest(unittest.TestCase):
    def test_generation_stats_can_format_durations(self):
        summary = core.format_generation_stats([], 2, 65, "1024x1024")
        self.assertIn("总耗时 1 分 5.0 秒", summary)

    def test_iteration_source_ui_callback_has_gradio_dependency(self):
        preference_update, prompt_update = ui.update_iteration_source_ui("自定义提示词")
        self.assertEqual(preference_update["label"], "创作主题")
        self.assertTrue(prompt_update["interactive"])

    def test_module_functions_have_no_unbound_global_dependencies(self):
        modules = [
            config,
            core,
            image_tasks,
            logging_utils,
            prompt_history,
            runtime,
            settings,
            text_tasks,
            ui,
            creative,
            edit,
            iterative,
            manual,
            random,
            reverse,
        ]
        missing = []

        def walk_code(code):
            yield code
            for value in code.co_consts:
                if isinstance(value, types.CodeType):
                    yield from walk_code(value)

        for module in modules:
            available = set(vars(module)) | set(dir(builtins))
            for function_name, function in vars(module).items():
                if not inspect.isfunction(function) or function.__module__ != module.__name__:
                    continue
                for code in walk_code(function.__code__):
                    for instruction in dis.get_instructions(code):
                        if instruction.opname in ("LOAD_GLOBAL", "LOAD_NAME") and instruction.argval not in available:
                            missing.append(
                                f"{module.__name__}.{function_name}/{code.co_name}: {instruction.argval}"
                            )

        self.assertEqual(missing, [])

    def test_console_log_fields_redact_secrets(self):
        self.assertEqual(logging_utils._format_field("api_key", "secret-value"), "***")
        self.assertEqual(logging_utils._format_field("Authorization", "Bearer secret"), "***")
        self.assertEqual(logging_utils._format_field("model", "test-model"), "test-model")


class PromptHistoryTest(unittest.TestCase):
    def test_default_image_and_prompt_history_directories_match(self):
        self.assertEqual(
            prompt_history.resolve_prompt_history_path("").parent,
            Path(core.get_save_dir("")),
        )

    def test_disabled_history_does_not_create_file(self):
        old_value = app.CONFIG.get("save_prompt_history")
        try:
            app.CONFIG["save_prompt_history"] = False
            with tempfile.TemporaryDirectory() as temp_dir:
                result = prompt_history.save_prompt_batch(temp_dir, "随机模式", "雨夜", ["提示词一"])
                self.assertIsNone(result)
                self.assertFalse(prompt_history.resolve_prompt_history_path(temp_dir).exists())
        finally:
            app.CONFIG["save_prompt_history"] = old_value

    def test_creative_batch_is_saved_as_one_markdown_record(self):
        old_value = app.CONFIG.get("save_prompt_history")
        try:
            app.CONFIG["save_prompt_history"] = True
            with tempfile.TemporaryDirectory() as temp_dir:
                result = prompt_history.save_prompt_batch(
                    temp_dir,
                    "创意模式",
                    "雨夜校园",
                    ["第一段完整提示词", "第二段完整提示词", "第三段完整提示词"],
                )
                content = prompt_history.resolve_prompt_history_path(temp_dir).read_text(encoding="utf-8")
        finally:
            app.CONFIG["save_prompt_history"] = old_value

        self.assertEqual(result, str(prompt_history.resolve_prompt_history_path(temp_dir)))
        self.assertEqual(sum(line.startswith("## ") for line in content.splitlines()), 1)
        self.assertIn("｜创意模式", content)
        self.assertIn("**创作方向：** 雨夜校园", content)
        self.assertIn("### 提示词 1", content)
        self.assertIn("### 提示词 3", content)
        self.assertNotIn("模型：", content)
        self.assertNotIn("任务编号", content)


if __name__ == "__main__":
    unittest.main()

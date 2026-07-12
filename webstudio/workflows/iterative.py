import os
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from ..config import normalize_seedream_model_id, persist_config, reset_stop_flag, should_stop
from ..core import (
    build_iterative_gallery_items,
    format_bytes,
    format_failed_jobs_summary,
    format_generation_stats,
    format_protocol_label,
    get_image_dimensions,
    get_save_dir,
    normalize_image_request_delay,
    normalize_iteration_prompt_source,
    normalize_protocol,
    normalize_quality,
    normalize_reasoning_effort,
    normalize_retry_settings,
    normalize_seedream_output_format,
    normalize_seedream_response_format,
    normalize_seedream_watermark,
    prepare_vision_image,
    resolve_image_request_size,
    resolve_vision_protocol,
)
from ..image_tasks import generate_one_image, resolve_selected_image_config, validate_selected_image_config
from ..runtime import ImageRequestLaunchGate, format_duration
from ..text_tasks import (
    format_used_scenes,
    generate_random_prompt_job,
    optimize_prompt_with_image,
    submit_sequential_prompt_job,
)

def generate_iterative_image(
    save_dir,
    iteration_prompt_source,
    iteration_custom_prompt,
    iteration_count,
    iteration_batch_count,
    iteration_random_enhance,
    iteration_text_concurrency,
    iteration_image_concurrency,
    retry_count,
    retry_delay,
    image_request_delay,
    image_model_provider,
    aspect_ratio,
    resolution,
    image_base_url,
    image_model_id,
    quality,
    image_api_key,
    seedream_base_url,
    seedream_model_id,
    seedream_api_key,
    seedream_response_format,
    seedream_output_format,
    seedream_watermark,
    random_base_url,
    random_model_id,
    random_api_key,
    random_protocol,
    random_reasoning_effort,
    random_preference,
    iteration_base_url,
    iteration_model_id,
    iteration_api_key,
    iteration_protocol,
    iteration_reasoning_effort,
):
    reset_stop_flag("iterative")
    image_model_provider, _selected_base_url, selected_model_id, selected_api_key = resolve_selected_image_config(
        image_model_provider,
        image_base_url,
        image_model_id,
        image_api_key,
        seedream_base_url,
        seedream_model_id,
        seedream_api_key,
    )
    validation_error = validate_selected_image_config(image_model_provider, selected_model_id, selected_api_key)
    if validation_error:
        yield iteration_custom_prompt, "", [], [], validation_error
        return

    iteration_prompt_source = normalize_iteration_prompt_source(iteration_prompt_source)
    iteration_custom_prompt = (iteration_custom_prompt or "").strip()
    iteration_count = int(iteration_count)
    iteration_batch_count = min(10, max(1, int(iteration_batch_count)))
    iteration_random_enhance = (
        bool(iteration_random_enhance)
        and iteration_prompt_source == "随机提示词"
        and iteration_batch_count > 1
    )
    iteration_text_concurrency = 1 if iteration_random_enhance else max(1, int(iteration_text_concurrency))
    iteration_image_concurrency = max(1, int(iteration_image_concurrency))
    retry_count, retry_delay = normalize_retry_settings(retry_count, retry_delay)
    image_request_delay = normalize_image_request_delay(image_request_delay)
    quality = normalize_quality(quality)
    seedream_model_id = normalize_seedream_model_id(seedream_model_id)
    seedream_response_format = normalize_seedream_response_format(seedream_response_format)
    seedream_output_format = normalize_seedream_output_format(seedream_output_format)
    seedream_watermark = normalize_seedream_watermark(seedream_watermark)
    random_protocol = normalize_protocol(random_protocol)
    iteration_protocol = normalize_protocol(iteration_protocol)
    random_reasoning_effort = normalize_reasoning_effort(random_reasoning_effort)
    iteration_reasoning_effort = normalize_reasoning_effort(iteration_reasoning_effort)
    raw_save_dir = save_dir
    save_dir = get_save_dir(save_dir)
    os.makedirs(save_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    total_started_at = time.perf_counter()
    final_records = []
    process_records = []
    image_records = []
    prompt_histories = {}
    initial_prompt_records = {}
    initial_prompt_plan = {}
    used_scenes = []
    task_statuses = {}
    failed_tasks = []
    request_size = resolve_image_request_size(image_model_provider, aspect_ratio, resolution, selected_model_id)
    image_gate = threading.Semaphore(min(iteration_image_concurrency, iteration_batch_count))
    text_gate = threading.Semaphore(min(iteration_text_concurrency, iteration_batch_count))
    launch_gate = ImageRequestLaunchGate(image_request_delay)

    persist_config(
        {
            "save_dir": raw_save_dir,
            "iteration_count": iteration_count,
            "iteration_batch_count": iteration_batch_count,
            "iteration_random_enhance": iteration_random_enhance,
            "iteration_text_concurrency": iteration_text_concurrency,
            "iteration_image_concurrency": iteration_image_concurrency,
            "retry_count": retry_count,
            "retry_delay": retry_delay,
            "image_request_delay": image_request_delay,
            "image_model_provider": image_model_provider,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "base_url": image_base_url,
            "model_id": image_model_id,
            "quality": quality,
            "api_key": image_api_key,
            "seedream_base_url": seedream_base_url,
            "seedream_model_id": seedream_model_id,
            "seedream_api_key": seedream_api_key,
            "seedream_response_format": seedream_response_format,
            "seedream_output_format": seedream_output_format,
            "seedream_watermark": seedream_watermark,
            "random_base_url": random_base_url,
            "random_model_id": random_model_id,
            "random_api_key": random_api_key,
            "random_protocol": random_protocol,
            "random_reasoning_effort": random_reasoning_effort,
            "random_preference": random_preference,
            "iteration_prompt_source": iteration_prompt_source,
            "iteration_custom_prompt": iteration_custom_prompt,
            "iteration_base_url": iteration_base_url,
            "iteration_model_id": iteration_model_id,
            "iteration_api_key": iteration_api_key,
            "iteration_protocol": iteration_protocol,
            "iteration_reasoning_effort": iteration_reasoning_effort,
        },
    )

    if iteration_prompt_source == "自定义提示词":
        if not iteration_custom_prompt:
            yield iteration_custom_prompt, "", [], [], "请填写自定义初始提示词。"
            return
        initial_prompt_records.update(
            {task_index: iteration_custom_prompt for task_index in range(1, iteration_batch_count + 1)}
        )
    else:
        # Random mode must show the actual prompts returned by the text model,
        # not stale values that may still be sitting in the input box.
        initial_prompt_records.clear()

    def initial_prompts_text_for_ui():
        if not initial_prompt_records:
            return ""
        parts = ["本次任务各组第一轮："]
        for task_index in sorted(initial_prompt_records):
            parts.append(f"第 {task_index} 组：\n{initial_prompt_records[task_index]}")
        return "\n\n".join(parts)

    def prompt_text_for_ui():
        parts = []
        for task_index in sorted(prompt_histories):
            parts.append(f"第 {task_index} 组：\n" + "\n\n".join(prompt_histories[task_index]))
        return "\n\n".join(parts)

    def status_text(prefix=""):
        running = sum(1 for status in task_statuses.values() if status not in ("完成", "失败", "已停止"))
        lines = [
            f"自我迭代批量运行：生成数量 {iteration_batch_count}，迭代 {iteration_count} 轮；初始提示词并发 {iteration_text_concurrency}，图片并发 {iteration_image_concurrency}，生图并发间隔 {image_request_delay:g} 秒。",
            f"最终成品 {len(final_records)}/{iteration_batch_count} 张；过程图 {len(process_records)} 张；运行中 {running} 组；失败 {len(failed_tasks)} 组。",
        ]
        if iteration_random_enhance:
            lines.append(f"随机增强：已禁用文本并行；已经用过场景：{format_used_scenes(used_scenes) or '暂无'}。")
        if prefix:
            lines.insert(0, prefix)
        if task_statuses:
            latest = "；".join(f"第 {index} 组 {task_statuses[index]}" for index in sorted(task_statuses)[-6:])
            lines.append(latest)
        if failed_tasks:
            samples = "；".join(f"第 {index} 组：{message[:180]}" for index, message in failed_tasks[-3:])
            lines.append(f"失败详情：{samples}")
        return "\n".join(lines)

    def yield_state(prefix="", prompt_value=None):
        return (
            prompt_value if prompt_value is not None else initial_prompts_text_for_ui(),
            prompt_text_for_ui(),
            build_iterative_gallery_items(final_records, final_only=True),
            build_iterative_gallery_items(process_records),
            status_text(prefix),
        )

    event_queue = queue.Queue()

    def put_event(kind, task_index, **payload):
        event_queue.put({"kind": kind, "task_index": task_index, **payload})

    def run_image_generation(task_index, round_index, prompt):
        with image_gate:
            if should_stop("iterative"):
                raise RuntimeError("任务已停止。")
            launch_gate.wait("iterative")
            started_at = time.perf_counter()
            image_path = generate_one_image(
                prompt,
                save_dir,
                aspect_ratio,
                resolution,
                image_model_provider,
                image_base_url,
                image_model_id,
                quality,
                image_api_key,
                seedream_base_url,
                seedream_model_id,
                seedream_api_key,
                seedream_response_format,
                seedream_output_format,
                seedream_watermark,
                f"{timestamp}_task{task_index:02d}_round{round_index:02d}",
                retry_count,
                retry_delay,
            )
            return image_path, time.perf_counter() - started_at

    def generate_initial_prompt_for_task(task_index):
        if iteration_prompt_source == "自定义提示词":
            return iteration_custom_prompt
        if task_index in initial_prompt_plan:
            return initial_prompt_plan[task_index]
        with text_gate:
            if should_stop("iterative"):
                raise RuntimeError("任务已停止。")
            put_event("status", task_index, status="正在生成初始随机提示词")
            _index, prompt, _scene, events = generate_random_prompt_job(
                task_index,
                "组",
                "初始提示词",
                random_base_url,
                random_model_id,
                random_api_key,
                random_preference,
                random_protocol,
                retry_count,
                retry_delay,
                random_reasoning_effort,
            )
            for event in events:
                put_event("status", task_index, status=event)
            return prompt

    def generate_enhanced_initial_prompt_for_task(task_index, scenes_snapshot):
        _index, prompt, scene, events = generate_random_prompt_job(
            task_index,
            "组",
            "初始提示词",
            random_base_url,
            random_model_id,
            random_api_key,
            random_preference,
            random_protocol,
            retry_count,
            retry_delay,
            random_reasoning_effort,
            used_scenes=scenes_snapshot,
            summarize_scene=True,
        )
        return prompt, scene, events

    def optimize_prompt_for_task(task_index, round_index, current_prompt, image_path):
        if should_stop("iterative"):
            raise RuntimeError("任务已停止。")
        vision_protocol, vision_url = resolve_vision_protocol(
            iteration_base_url,
            iteration_model_id,
            iteration_protocol,
        )
        preview_image = prepare_vision_image(image_path)
        upload_size_label = f"{format_bytes(preview_image['original_size'])} -> {format_bytes(preview_image['compressed_size'])}"
        put_event(
            "status",
            task_index,
            status=f"正在评估第 {round_index} 轮；协议 {format_protocol_label(vision_protocol)}；上传 {upload_size_label}，{preview_image['dimensions']}",
        )
        return optimize_prompt_with_image(
            current_prompt,
            image_path,
            iteration_base_url,
            iteration_model_id,
            iteration_api_key,
            iteration_protocol,
            retry_count,
            retry_delay,
            reasoning_effort=iteration_reasoning_effort,
            creation_theme=random_preference if iteration_prompt_source == "自定义提示词" else "",
            user_initial_direction=random_preference if iteration_prompt_source == "随机提示词" else "",
            prepared_vision_image=preview_image,
        )

    def iteration_worker(task_index):
        current_prompt = generate_initial_prompt_for_task(task_index)
        put_event("prompt", task_index, round_index=1, prompt=current_prompt)
        for round_index in range(1, iteration_count + 1):
            if should_stop("iterative"):
                raise RuntimeError("任务已停止。")
            put_event("status", task_index, status=f"正在生成第 {round_index}/{iteration_count} 轮图片")
            image_path, elapsed = run_image_generation(task_index, round_index, current_prompt)
            is_final = round_index == iteration_count
            put_event(
                "image",
                task_index,
                round_index=round_index,
                path=image_path,
                elapsed=elapsed,
                is_final=is_final,
            )
            if is_final:
                put_event("done", task_index, final_prompt=current_prompt)
                return current_prompt
            current_prompt = optimize_prompt_for_task(task_index, round_index, current_prompt, image_path)
            put_event("prompt", task_index, round_index=round_index + 1, prompt=current_prompt)
        return current_prompt

    def apply_iteration_event(event):
        task_index = event["task_index"]
        kind = event["kind"]
        if kind == "status":
            task_statuses[task_index] = event["status"]
        elif kind == "prompt":
            prompt_histories.setdefault(task_index, []).append(
                f"第 {event['round_index']} 轮提示词：\n{event['prompt']}"
            )
            task_statuses[task_index] = f"第 {event['round_index']} 轮提示词已就绪"
            if event["round_index"] == 1:
                initial_prompt_records[task_index] = event["prompt"]
        elif kind == "image":
            dimensions = get_image_dimensions(event["path"]) or request_size
            record = {
                "task_index": task_index,
                "round_index": event["round_index"],
                "path": event["path"],
                "elapsed": event["elapsed"],
                "is_final": event["is_final"],
            }
            process_records.append(record)
            image_records.append((len(image_records) + 1, event["path"], event["elapsed"]))
            if event["is_final"]:
                final_records.append(record)
            task_statuses[task_index] = f"第 {event['round_index']}/{iteration_count} 轮图片完成，{dimensions}，耗时 {format_duration(event['elapsed'])}"
        elif kind == "done":
            task_statuses[task_index] = "完成"
            persist_config({"prompt": event["final_prompt"]})

    def finish_iteration_futures(done_futures, futures, remaining):
        for future in done_futures:
            remaining.remove(future)
            task_index = futures[future]
            try:
                final_prompt = future.result()
                task_statuses[task_index] = "完成"
                persist_config({"prompt": final_prompt})
            except Exception as e:
                message = str(e)
                task_statuses[task_index] = "已停止" if should_stop("iterative") else "失败"
                failed_tasks.append((task_index, message))

    yield yield_state(
        f"开始并行自我迭代：生成数量 {iteration_batch_count}，每组完整运行 {iteration_count} 轮。",
    )

    with ThreadPoolExecutor(max_workers=1) as prompt_executor, ThreadPoolExecutor(max_workers=iteration_batch_count) as executor:
        prompt_futures = {}
        futures = {}
        remaining = set()
        next_prompt_index = iteration_batch_count + 1

        if iteration_random_enhance:
            next_prompt_index = submit_sequential_prompt_job(
                prompt_executor,
                prompt_futures,
                1,
                iteration_batch_count,
                generate_enhanced_initial_prompt_for_task,
                used_scenes,
            )
        else:
            futures.update(
                {
                    executor.submit(iteration_worker, task_index): task_index
                    for task_index in range(1, iteration_batch_count + 1)
                }
            )
            remaining.update(futures)

        while prompt_futures or remaining:
            if should_stop("iterative"):
                for future in set(prompt_futures) | remaining:
                    future.cancel()
                yield yield_state("已停止：正在等待已进入接口请求的任务返回。")
                return

            did_update = False
            while True:
                try:
                    event = event_queue.get_nowait()
                except queue.Empty:
                    break
                apply_iteration_event(event)
                did_update = True

            done_prompt_futures = {future for future in prompt_futures if future.done()}
            for future in done_prompt_futures:
                task_index = prompt_futures.pop(future)
                try:
                    prompt, scene, events = future.result()
                    initial_prompt_plan[task_index] = prompt
                    initial_prompt_records[task_index] = prompt
                    if scene:
                        used_scenes.append(scene)
                    task_statuses[task_index] = "初始提示词已就绪"
                    retry_line = f"\n{events[-1]}" if events else ""
                    yield yield_state(
                        f"随机增强：第 {task_index}/{iteration_batch_count} 组初始提示词已生成，已立即启动该组迭代；已经用过场景：{format_used_scenes(used_scenes) or '暂无'}。{retry_line}"
                    )
                except Exception as e:
                    task_statuses[task_index] = "失败"
                    failed_tasks.append((task_index, f"初始提示词生成失败：{e}"))
                    yield yield_state(f"第 {task_index} 组初始提示词生成失败并已跳过：{e}")
                else:
                    future_task = executor.submit(iteration_worker, task_index)
                    futures[future_task] = task_index
                    remaining.add(future_task)

                if next_prompt_index <= iteration_batch_count:
                    task_statuses[next_prompt_index] = "正在串行生成增强初始提示词"
                next_prompt_index = submit_sequential_prompt_job(
                    prompt_executor,
                    prompt_futures,
                    next_prompt_index,
                    iteration_batch_count,
                    generate_enhanced_initial_prompt_for_task,
                    used_scenes,
                )
                did_update = True

            done_iteration_futures = {future for future in remaining if future.done()}
            if done_iteration_futures:
                finish_iteration_futures(done_iteration_futures, futures, remaining)
                did_update = True

            if did_update:
                yield yield_state()
            else:
                try:
                    event = event_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                apply_iteration_event(event)
                yield yield_state()

    failed_task_summary = format_failed_jobs_summary(failed_tasks, item_label="组")
    yield (
        initial_prompts_text_for_ui(),
        prompt_text_for_ui(),
        build_iterative_gallery_items(final_records, final_only=True),
        build_iterative_gallery_items(process_records),
        f"自我迭代完成：图片模型 {image_model_provider}；最终成品 {len(final_records)}/{iteration_batch_count} 张；过程图 {len(process_records)} 张；失败 {len(failed_tasks)} 组；{format_generation_stats(image_records, iteration_batch_count * iteration_count, time.perf_counter() - total_started_at, request_size)}；品质 {quality}；目录 {save_dir}{failed_task_summary}",
    )

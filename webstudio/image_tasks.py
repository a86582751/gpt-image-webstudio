import base64
import os
import time
from io import BytesIO

import requests

from .config import IMAGE_READ_TIMEOUT, INPUT_FIDELITY_PRESETS, should_stop
from .core import (
    build_indexed_gallery_items,
    build_seedream_prompt,
    display_endpoint,
    format_bytes,
    format_failed_jobs_summary,
    format_generation_stats,
    get_image_dimensions,
    get_save_dir,
    normalize_image_model_provider,
    normalize_image_request_delay,
    normalize_quality,
    normalize_seedream_output_format,
    normalize_seedream_response_format,
    parse_image_items,
    post_json,
    prepare_edit_input_image,
    prepare_seedream_input_image,
    request_timeout,
    resolve_api_url,
    resolve_edit_api_url,
    resolve_image_request_size,
    resolve_seedream_api_url,
    seedream_uses_official_interface,
    seedream_watermark_enabled,
)
from .runtime import ImageRequestLaunchGate, format_duration, run_bounded_concurrent_jobs, run_with_retry
from .logging_utils import log_error, log_event


def build_seedream_payload(
    prompt,
    size,
    model_id,
    aspect_ratio,
    response_format="url",
    output_format="自动",
    watermark="关闭",
    input_images=None,
):
    payload = {
        "model": model_id.strip(),
        "prompt": build_seedream_prompt(prompt, aspect_ratio),
        "size": size,
        "response_format": normalize_seedream_response_format(response_format),
        "watermark": seedream_watermark_enabled(watermark),
    }
    output_format = normalize_seedream_output_format(output_format)
    if output_format != "自动":
        payload["output_format"] = output_format
    if input_images:
        image_values = [image["data_url"] for image in input_images]
        payload["image"] = image_values[0] if len(image_values) == 1 else image_values
    return payload

def is_http_url(value):
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def save_image_bytes(image_bytes, saved_paths, save_dir, timestamp):
    image_index = len(saved_paths) + 1
    filename = f"img_{timestamp}_{image_index:02d}.png"
    save_path = os.path.join(save_dir, filename)

    with open(save_path, "wb") as f:
        f.write(image_bytes)
    saved_paths.append(save_path)


def save_image_url(image_url, saved_paths, save_dir, timestamp, retry_count=1, retry_delay=2, on_retry=None):
    def download_image():
        image_response = requests.get(image_url, timeout=request_timeout(IMAGE_READ_TIMEOUT))
        image_response.raise_for_status()
        return image_response.content

    image_bytes = run_with_retry(
        download_image,
        "图片下载",
        retries=int(retry_count),
        delay_seconds=float(retry_delay),
        on_retry=on_retry,
    )
    save_image_bytes(image_bytes, saved_paths, save_dir, timestamp)


def save_image_value(image_value, saved_paths, save_dir, timestamp, retry_count=1, retry_delay=2, on_retry=None):
    if not image_value:
        return

    if is_http_url(image_value):
        save_image_url(image_value, saved_paths, save_dir, timestamp, retry_count, retry_delay, on_retry)
        return

    image_bytes = base64.b64decode(image_value)
    save_image_bytes(image_bytes, saved_paths, save_dir, timestamp)


def save_images_from_items(image_items, saved_paths, save_dir, timestamp, retry_count=1, retry_delay=2, on_retry=None):
    for item in image_items:
        if isinstance(item, str):
            save_image_value(item, saved_paths, save_dir, timestamp, retry_count, retry_delay, on_retry)
            continue

        image_values = item.get("b64_json")
        if isinstance(image_values, str):
            image_values = [image_values]

        for image_base64 in image_values or []:
            save_image_value(image_base64, saved_paths, save_dir, timestamp, retry_count, retry_delay, on_retry)

    for item in image_items:
        if not isinstance(item, dict):
            continue

        image_url = item.get("url")
        if not image_url:
            continue

        save_image_url(image_url, saved_paths, save_dir, timestamp, retry_count, retry_delay, on_retry)


def generate_one_image(
    prompt,
    save_dir,
    aspect_ratio,
    resolution,
    image_model_provider,
    base_url,
    model_id,
    quality,
    api_key,
    seedream_base_url,
    seedream_model_id,
    seedream_api_key,
    seedream_response_format,
    seedream_output_format,
    seedream_watermark,
    timestamp,
    retry_count=1,
    retry_delay=2,
    on_retry=None,
):
    image_model_provider = normalize_image_model_provider(image_model_provider)
    active_base_url = seedream_base_url if image_model_provider == "豆包 Seedream" else base_url
    active_model_id = seedream_model_id if image_model_provider == "豆包 Seedream" else model_id
    active_api_key = seedream_api_key if image_model_provider == "豆包 Seedream" else api_key
    size = resolve_image_request_size(image_model_provider, aspect_ratio, resolution, active_model_id)
    quality = normalize_quality(quality)
    saved_paths = []
    log_event(
        "图片生成",
        "准备请求",
        provider=image_model_provider,
        model=active_model_id,
        size=size,
        endpoint=display_endpoint(active_base_url),
        task=timestamp,
    )

    def request_image():
        if image_model_provider == "豆包 Seedream" and seedream_uses_official_interface():
            return parse_image_items(
                post_json(
                    resolve_seedream_api_url(active_base_url),
                    headers={
                        "Authorization": f"Bearer {active_api_key.strip()}",
                    },
                    payload=build_seedream_payload(
                        prompt,
                        size,
                        active_model_id,
                        aspect_ratio,
                        seedream_response_format,
                        seedream_output_format,
                        seedream_watermark,
                    ),
                    timeout=request_timeout(IMAGE_READ_TIMEOUT),
                )
            )
        if image_model_provider == "豆包 Seedream":
            payload = {
                "model": active_model_id.strip(),
                "size": size,
                "n": 1,
                "prompt": prompt.strip(),
                "watermark": seedream_watermark_enabled(seedream_watermark),
                "response_format": normalize_seedream_response_format(seedream_response_format),
            }
            output_format = normalize_seedream_output_format(seedream_output_format)
            if output_format != "自动":
                payload["output_format"] = output_format
            return parse_image_items(
                post_json(
                    resolve_api_url(active_base_url),
                    headers={"Authorization": f"Bearer {active_api_key.strip()}"},
                    payload=payload,
                    timeout=request_timeout(IMAGE_READ_TIMEOUT),
                )
            )
        return parse_image_items(
            post_json(
                resolve_api_url(active_base_url),
                headers={
                    "Authorization": f"Bearer {active_api_key.strip()}",
                },
                payload={
                    "model": active_model_id.strip(),
                    "size": size,
                    "n": 1,
                    "quality": quality,
                    "moderation": "low",
                    "prompt": prompt.strip(),
                },
                timeout=request_timeout(IMAGE_READ_TIMEOUT),
            )
        )

    image_items = run_with_retry(
        request_image,
        "图片生成",
        retries=int(retry_count),
        delay_seconds=float(retry_delay),
        on_retry=on_retry,
    )
    save_images_from_items(image_items, saved_paths, save_dir, timestamp, retry_count, retry_delay, on_retry)
    if not saved_paths:
        log_error("图片生成", "接口成功但没有图片数据", provider=image_model_provider, model=active_model_id, task=timestamp)
        raise RuntimeError("接口返回成功，但没有收到图片数据。")
    log_event("图片生成", "图片已保存", provider=image_model_provider, model=active_model_id, path=saved_paths[0], task=timestamp)
    return saved_paths[0]


def generate_one_image_edit(
    prompt,
    input_images,
    save_dir,
    aspect_ratio,
    resolution,
    image_model_provider,
    base_url,
    model_id,
    quality,
    api_key,
    seedream_base_url,
    seedream_model_id,
    seedream_api_key,
    seedream_response_format,
    seedream_output_format,
    seedream_watermark,
    input_fidelity,
    timestamp,
    retry_count=1,
    retry_delay=2,
    on_retry=None,
):
    image_model_provider = normalize_image_model_provider(image_model_provider)
    active_base_url = seedream_base_url if image_model_provider == "豆包 Seedream" else base_url
    active_model_id = seedream_model_id if image_model_provider == "豆包 Seedream" else model_id
    active_api_key = seedream_api_key if image_model_provider == "豆包 Seedream" else api_key
    size = resolve_image_request_size(image_model_provider, aspect_ratio, resolution, active_model_id)
    quality = normalize_quality(quality)
    input_fidelity = input_fidelity if input_fidelity in INPUT_FIDELITY_PRESETS else "high"
    prepared_images = [
        prepare_seedream_input_image(path) if image_model_provider == "豆包 Seedream" else prepare_edit_input_image(path)
        for path in input_images
    ]
    saved_paths = []
    log_event(
        "图片编辑",
        "准备请求",
        provider=image_model_provider,
        model=active_model_id,
        size=size,
        inputs=len(prepared_images),
        endpoint=display_endpoint(active_base_url),
        task=timestamp,
    )

    def request_edit():
        if image_model_provider == "豆包 Seedream" and seedream_uses_official_interface():
            # Seedream does not support OpenAI's input_fidelity edit parameter.
            return parse_image_items(
                post_json(
                    resolve_seedream_api_url(active_base_url),
                    headers={"Authorization": f"Bearer {active_api_key.strip()}"},
                    payload=build_seedream_payload(
                        prompt,
                        size,
                        active_model_id,
                        aspect_ratio,
                        seedream_response_format,
                        seedream_output_format,
                        seedream_watermark,
                        prepared_images,
                    ),
                    timeout=request_timeout(IMAGE_READ_TIMEOUT),
                )
            )

        files = []
        for image in prepared_images:
            files.append(("image[]", (image["filename"], BytesIO(image["bytes"]), image["mime_type"])))
        data = {
            "model": active_model_id.strip(),
            "prompt": prompt.strip(),
            "size": size,
            "n": "1",
        }
        if image_model_provider == "豆包 Seedream":
            data["watermark"] = str(seedream_watermark_enabled(seedream_watermark)).lower()
            data["response_format"] = normalize_seedream_response_format(seedream_response_format)
            output_format = normalize_seedream_output_format(seedream_output_format)
            if output_format != "自动":
                data["output_format"] = output_format
        else:
            data["quality"] = quality
            data["input_fidelity"] = input_fidelity
        response = requests.post(
            resolve_edit_api_url(active_base_url),
            headers={"Authorization": f"Bearer {active_api_key.strip()}"},
            data=data,
            files=files,
            timeout=request_timeout(IMAGE_READ_TIMEOUT),
        )
        return parse_image_items(response)

    image_items = run_with_retry(
        request_edit,
        "图片编辑",
        retries=int(retry_count),
        delay_seconds=float(retry_delay),
        on_retry=on_retry,
    )
    save_images_from_items(image_items, saved_paths, save_dir, timestamp, retry_count, retry_delay, on_retry)
    if not saved_paths:
        log_error("图片编辑", "接口成功但没有图片数据", provider=image_model_provider, model=active_model_id, task=timestamp)
        raise RuntimeError("接口返回成功，但没有收到图片数据。")
    log_event("图片编辑", "图片已保存", provider=image_model_provider, model=active_model_id, path=saved_paths[0], task=timestamp)
    return saved_paths[0], prepared_images

def generate_images_concurrently(
    prompt_jobs,
    save_dir,
    aspect_ratio,
    resolution,
    image_model_provider,
    base_url,
    model_id,
    quality,
    api_key,
    seedream_base_url,
    seedream_model_id,
    seedream_api_key,
    seedream_response_format,
    seedream_output_format,
    seedream_watermark,
    concurrency,
    retry_count=1,
    retry_delay=2,
    image_request_delay=0,
    stop_mode=None,
):
    save_dir = get_save_dir(save_dir)
    os.makedirs(save_dir, exist_ok=True)

    prompt_jobs = list(prompt_jobs)
    total_count = len(prompt_jobs)
    concurrency = max(1, min(int(concurrency), total_count or 1))
    saved_paths = []
    image_records = []
    failed_jobs = []
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    total_started_at = time.perf_counter()
    image_model_provider = normalize_image_model_provider(image_model_provider)
    active_model_id = seedream_model_id if image_model_provider == "豆包 Seedream" else model_id
    request_size = resolve_image_request_size(image_model_provider, aspect_ratio, resolution, active_model_id)
    quality = normalize_quality(quality)
    image_request_delay = normalize_image_request_delay(image_request_delay)
    launch_gate = ImageRequestLaunchGate(image_request_delay)

    if not prompt_jobs:
        yield [], "没有可生成的提示词。"
        return

    yield (
        build_indexed_gallery_items(image_records),
        f"开始生成 {total_count} 张；图片模型 {image_model_provider}；最大并发 {concurrency}；生图并发间隔 {image_request_delay:g} 秒；请求尺寸 {request_size}；品质 {quality}",
    )

    def worker(job):
        job_index, job_prompt = job
        if stop_mode and should_stop(stop_mode):
            raise RuntimeError("任务已停止。")
        launch_gate.wait(stop_mode)
        started_at = time.perf_counter()
        events = []
        image_path = generate_one_image(
            job_prompt,
            save_dir,
            aspect_ratio,
            resolution,
            image_model_provider,
            base_url,
            model_id,
            quality,
            api_key,
            seedream_base_url,
            seedream_model_id,
            seedream_api_key,
            seedream_response_format,
            seedream_output_format,
            seedream_watermark,
            f"{timestamp}_job{job_index:02d}",
            retry_count,
            retry_delay,
            lambda label, attempt, retries, error: events.append(
                f"第 {job_index} 张{label}触发重试 {attempt}/{retries}：{error}"
            ),
        )
        return job_index, job_prompt, image_path, time.perf_counter() - started_at, events

    try:
        for job_index, future, stopped in run_bounded_concurrent_jobs(
            prompt_jobs,
            concurrency,
            worker,
            lambda job: job[0],
            stop_mode,
        ):
            if stopped:
                yield (
                    build_indexed_gallery_items(image_records),
                    f"已停止：保存 {len(saved_paths)}/{total_count} 张。",
                )
                return
            try:
                job_index, _job_prompt, image_path, elapsed, events = future.result()
                saved_paths.append(image_path)
                image_records.append((job_index, image_path, elapsed))
                dimensions = get_image_dimensions(image_path) or request_size
                status_extra = f"\n{events[-1]}" if events else ""
                yield (
                    build_indexed_gallery_items(image_records),
                    f"已完成 {len(saved_paths)}/{total_count} 张；刚完成第 {job_index} 张，分辨率 {dimensions}，耗时 {format_duration(elapsed)}；累计耗时 {format_duration(time.perf_counter() - total_started_at)}{status_extra}",
                )
            except Exception as e:
                failed_jobs.append((job_index, str(e)))
                yield (
                    build_indexed_gallery_items(image_records),
                    f"第 {job_index} 张失败并已跳过：{e}；已保存 {len(saved_paths)}/{total_count} 张，失败 {len(failed_jobs)} 张。",
                )
    except Exception as e:
        failed_count = len(failed_jobs) or total_count - len(saved_paths)
        yield (
            build_indexed_gallery_items(image_records),
            f"生成中断：{e}；已保存 {len(saved_paths)}/{total_count} 张，失败 {failed_count} 张；{format_generation_stats(image_records, total_count, time.perf_counter() - total_started_at, request_size)}。",
        )
        return

    failed_summary = f"；失败 {len(failed_jobs)} 张" if failed_jobs else ""
    yield (
        build_indexed_gallery_items(image_records),
        f"生成完成：图片模型 {image_model_provider}；共保存 {len(saved_paths)} 张{failed_summary}；{format_generation_stats(image_records, total_count, time.perf_counter() - total_started_at, request_size)}；品质 {quality}；目录 {save_dir}{format_failed_jobs_summary(failed_jobs)}",
    )


def normalize_uploaded_file_paths(uploaded_files):
    if not uploaded_files:
        return []
    if isinstance(uploaded_files, str):
        return [uploaded_files]
    paths = []
    for item in uploaded_files:
        if isinstance(item, str):
            paths.append(item)
        elif hasattr(item, "name"):
            paths.append(item.name)
    return paths


def format_edit_input_summary(prepared_images):
    parts = []
    for index, image in enumerate(prepared_images, start=1):
        marker = "压缩" if image["compressed"] else "原图"
        size_text = f"{format_bytes(image['original_size'])} -> {format_bytes(image['compressed_size'])}" if image["compressed"] else format_bytes(image["original_size"])
        dimensions = f"，{image['dimensions']}" if image["dimensions"] else ""
        parts.append(f"参考图 {index}：{marker}，{size_text}{dimensions}")
    return "；".join(parts)


def generate_image_edits_concurrently(
    prompt,
    input_images,
    save_dir,
    image_count,
    aspect_ratio,
    resolution,
    image_model_provider,
    base_url,
    model_id,
    quality,
    api_key,
    seedream_base_url,
    seedream_model_id,
    seedream_api_key,
    seedream_response_format,
    seedream_output_format,
    seedream_watermark,
    input_fidelity,
    concurrency,
    retry_count=1,
    retry_delay=2,
    image_request_delay=0,
):
    save_dir = get_save_dir(save_dir)
    os.makedirs(save_dir, exist_ok=True)
    image_count = int(image_count)
    concurrency = max(1, min(int(concurrency), image_count or 1))
    saved_paths = []
    image_records = []
    failed_jobs = []
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    total_started_at = time.perf_counter()
    image_model_provider = normalize_image_model_provider(image_model_provider)
    active_model_id = seedream_model_id if image_model_provider == "豆包 Seedream" else model_id
    request_size = resolve_image_request_size(image_model_provider, aspect_ratio, resolution, active_model_id)
    quality = normalize_quality(quality)
    image_request_delay = normalize_image_request_delay(image_request_delay)
    launch_gate = ImageRequestLaunchGate(image_request_delay)
    try:
        prepared_preview = [
            prepare_seedream_input_image(path) if image_model_provider == "豆包 Seedream" else prepare_edit_input_image(path)
            for path in input_images
        ]
    except Exception as e:
        yield build_indexed_gallery_items(image_records), f"参考图读取或压缩失败：{e}"
        return

    yield (
        build_indexed_gallery_items(image_records),
        f"开始图片编辑 {image_count} 张；图片模型 {image_model_provider}；最大并发 {concurrency}；生图并发间隔 {image_request_delay:g} 秒；请求尺寸 {request_size}；品质 {quality}；输入保真度 {input_fidelity}；{format_edit_input_summary(prepared_preview)}",
    )

    def worker(job_index):
        if should_stop("edit"):
            raise RuntimeError("任务已停止。")
        launch_gate.wait("edit")
        started_at = time.perf_counter()
        events = []
        image_path, prepared_images = generate_one_image_edit(
            prompt,
            input_images,
            save_dir,
            aspect_ratio,
            resolution,
            image_model_provider,
            base_url,
            model_id,
            quality,
            api_key,
            seedream_base_url,
            seedream_model_id,
            seedream_api_key,
            seedream_response_format,
            seedream_output_format,
            seedream_watermark,
            input_fidelity,
            f"{timestamp}_edit{job_index:02d}",
            retry_count,
            retry_delay,
            lambda label, attempt, retries, error: events.append(
                f"第 {job_index} 张{label}触发重试 {attempt}/{retries}：{error}"
            ),
        )
        return job_index, image_path, time.perf_counter() - started_at, events, prepared_images

    try:
        for job_index, future, stopped in run_bounded_concurrent_jobs(
            range(1, image_count + 1),
            concurrency,
            worker,
            lambda index: index,
            "edit",
        ):
            if stopped:
                yield build_indexed_gallery_items(image_records), f"已停止：已保存 {len(saved_paths)}/{image_count} 张。"
                return
            try:
                index, image_path, elapsed, events, prepared_images = future.result()
                saved_paths.append(image_path)
                image_records.append((index, image_path, elapsed))
                dimensions = get_image_dimensions(image_path) or request_size
                status_extra = f"\n{events[-1]}" if events else ""
                yield (
                    build_indexed_gallery_items(image_records),
                    f"已完成 {len(saved_paths)}/{image_count} 张；刚完成第 {index} 张，分辨率 {dimensions}，耗时 {format_duration(elapsed)}；{format_edit_input_summary(prepared_images)}；累计耗时 {format_duration(time.perf_counter() - total_started_at)}{status_extra}",
                )
            except Exception as e:
                failed_jobs.append((job_index, str(e)))
                yield (
                    build_indexed_gallery_items(image_records),
                    f"第 {job_index} 张图片编辑失败并已跳过：{e}；已保存 {len(saved_paths)}/{image_count} 张，失败 {len(failed_jobs)} 张。",
                )

    except Exception as e:
        yield build_indexed_gallery_items(image_records), f"图片编辑调度中断：{e}；已保存 {len(saved_paths)}/{image_count} 张。"
        return

    yield (
        build_indexed_gallery_items(image_records),
        f"图片编辑完成：图片模型 {image_model_provider}；共保存 {len(saved_paths)} 张；失败 {len(failed_jobs)} 张；{format_generation_stats(image_records, image_count, time.perf_counter() - total_started_at, request_size)}；品质 {quality}；输入保真度 {input_fidelity}；目录 {save_dir}{format_failed_jobs_summary(failed_jobs)}",
    )


def generate_images_from_prompt(
    prompt,
    save_dir,
    image_count,
    aspect_ratio,
    resolution,
    image_model_provider,
    base_url,
    model_id,
    quality,
    api_key,
    seedream_base_url,
    seedream_model_id,
    seedream_api_key,
    seedream_response_format,
    seedream_output_format,
    seedream_watermark,
    concurrency=1,
    retry_count=1,
    retry_delay=2,
    image_request_delay=0,
    stop_mode=None,
):
    prompt_jobs = [(index, prompt) for index in range(1, int(image_count) + 1)]
    yield from generate_images_concurrently(
        prompt_jobs=prompt_jobs,
        save_dir=save_dir,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        image_model_provider=image_model_provider,
        base_url=base_url,
        model_id=model_id,
        quality=quality,
        api_key=api_key,
        seedream_base_url=seedream_base_url,
        seedream_model_id=seedream_model_id,
        seedream_api_key=seedream_api_key,
        seedream_response_format=seedream_response_format,
        seedream_output_format=seedream_output_format,
        seedream_watermark=seedream_watermark,
        concurrency=concurrency,
        retry_count=retry_count,
        retry_delay=retry_delay,
        image_request_delay=image_request_delay,
        stop_mode=stop_mode,
    )


def resolve_selected_image_config(
    image_model_provider,
    base_url,
    model_id,
    api_key,
    seedream_base_url,
    seedream_model_id,
    seedream_api_key,
):
    image_model_provider = normalize_image_model_provider(image_model_provider)
    if image_model_provider == "豆包 Seedream":
        return image_model_provider, seedream_base_url, seedream_model_id, seedream_api_key
    return image_model_provider, base_url, model_id, api_key


def validate_selected_image_config(image_model_provider, selected_model_id, selected_api_key):
    if not selected_api_key or not selected_api_key.strip():
        yield_message = "请填写 Seedream API Key。" if image_model_provider == "豆包 Seedream" else "请填写图片生成 API Key。"
        return yield_message
    if not selected_model_id or not selected_model_id.strip():
        yield_message = "请填写 Seedream 模型 ID。" if image_model_provider == "豆包 Seedream" else "请填写图片生成模型 ID。"
        return yield_message
    return ""

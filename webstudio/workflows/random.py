import time

from ..config import normalize_seedream_model_id, persist_config, reset_stop_flag, should_stop
from ..core import (
    format_failed_jobs_summary,
    normalize_image_request_delay,
    normalize_protocol,
    normalize_quality,
    normalize_reasoning_effort,
    normalize_retry_settings,
    normalize_seedream_output_format,
    normalize_seedream_response_format,
    normalize_seedream_watermark,
)
from ..image_tasks import generate_images_from_prompt, resolve_selected_image_config, validate_selected_image_config
from ..runtime import format_duration
from ..text_tasks import generate_random_prompt_job

def generate_random_image(
    save_dir,
    image_count,
    concurrency,
    retry_count,
    retry_delay,
    image_request_delay,
    image_model_provider,
    aspect_ratio,
    resolution,
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
    random_base_url,
    random_model_id,
    random_api_key,
    random_protocol,
    random_reasoning_effort,
    random_preference,
):
    reset_stop_flag("random")
    image_model_provider, _selected_base_url, selected_model_id, selected_api_key = resolve_selected_image_config(
        image_model_provider,
        base_url,
        model_id,
        api_key,
        seedream_base_url,
        seedream_model_id,
        seedream_api_key,
    )
    validation_error = validate_selected_image_config(image_model_provider, selected_model_id, selected_api_key)
    if validation_error:
        yield "", [], validation_error
        return

    retry_count, retry_delay = normalize_retry_settings(retry_count, retry_delay)
    image_request_delay = normalize_image_request_delay(image_request_delay)
    quality = normalize_quality(quality)
    seedream_model_id = normalize_seedream_model_id(seedream_model_id)
    seedream_response_format = normalize_seedream_response_format(seedream_response_format)
    seedream_output_format = normalize_seedream_output_format(seedream_output_format)
    seedream_watermark = normalize_seedream_watermark(seedream_watermark)
    random_protocol = normalize_protocol(random_protocol)
    random_reasoning_effort = normalize_reasoning_effort(random_reasoning_effort)
    prompt_started_at = time.perf_counter()
    persist_config(
        {
            "save_dir": save_dir,
            "image_count": int(image_count),
            "concurrency": int(concurrency),
            "retry_count": int(retry_count),
            "retry_delay": float(retry_delay),
            "image_request_delay": image_request_delay,
            "image_model_provider": image_model_provider,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "base_url": base_url,
            "model_id": model_id,
            "quality": quality,
            "api_key": api_key,
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
        },
    )
    yield "", [], "正在生成随机提示词..."
    if should_stop("random"):
        yield "", [], "已停止。"
        return

    try:
        _index, random_prompt, _scene, prompt_events = generate_random_prompt_job(
            1,
            "段",
            "提示词",
            random_base_url,
            random_model_id,
            random_api_key,
            random_preference,
            random_protocol,
            retry_count,
            retry_delay,
            random_reasoning_effort,
        )
    except Exception as e:
        yield "", [], f"随机提示词生成失败：{e}{format_failed_jobs_summary([(1, str(e))], item_label='段')}"
        return

    persist_config({"prompt": random_prompt})
    prompt_status_extra = f"\n{prompt_events[-1]}" if prompt_events else ""

    yield (
        random_prompt,
        [],
        f"随机提示词已生成；耗时 {format_duration(time.perf_counter() - prompt_started_at)}。开始生成图片...{prompt_status_extra}",
    )

    for gallery_items, status in generate_images_from_prompt(
        prompt=random_prompt,
        save_dir=save_dir,
        image_count=image_count,
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
        stop_mode="random",
    ):
        yield random_prompt, gallery_items, status

from ..config import normalize_seedream_model_id, persist_config, reset_stop_flag
from ..core import (
    normalize_image_request_delay,
    normalize_quality,
    normalize_retry_settings,
    normalize_seedream_output_format,
    normalize_seedream_response_format,
    normalize_seedream_watermark,
)
from ..image_tasks import generate_images_from_prompt, resolve_selected_image_config, validate_selected_image_config
from ..logging_utils import log_event

def generate_image(
    prompt,
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
):
    reset_stop_flag("manual")
    log_event("手动模式", "任务启动", images=int(image_count), concurrency=int(concurrency), provider=image_model_provider)
    if not prompt or not prompt.strip():
        yield [], "请先输入提示词。"
        return
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
        yield [], validation_error
        return

    retry_count, retry_delay = normalize_retry_settings(retry_count, retry_delay)
    image_request_delay = normalize_image_request_delay(image_request_delay)
    quality = normalize_quality(quality)
    seedream_model_id = normalize_seedream_model_id(seedream_model_id)
    seedream_response_format = normalize_seedream_response_format(seedream_response_format)
    seedream_output_format = normalize_seedream_output_format(seedream_output_format)
    seedream_watermark = normalize_seedream_watermark(seedream_watermark)

    persist_config(
        {
            "prompt": prompt,
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
        },
    )

    yield from generate_images_from_prompt(
        prompt=prompt,
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
        stop_mode="manual",
    )
    log_event("手动模式", "任务结束", images=int(image_count), provider=image_model_provider)

from ..config import *
from ..core import *
from ..image_tasks import *
from ..runtime import ImageRequestLaunchGate, format_duration
from ..text_tasks import *

def generate_image_edit(
    uploaded_files,
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
    input_fidelity,
):
    reset_stop_flag("edit")
    input_images = normalize_uploaded_file_paths(uploaded_files)
    if not input_images:
        yield [], "请先上传至少一张参考图。"
        return
    if len(input_images) > 4:
        yield [], "当前先支持最多 4 张参考图，请减少后再试。"
        return
    if not prompt or not prompt.strip():
        yield [], "请先输入编辑提示词。"
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
    input_fidelity = input_fidelity if input_fidelity in INPUT_FIDELITY_PRESETS else "high"

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
            "edit_input_fidelity": input_fidelity,
        },
    )

    yield from generate_image_edits_concurrently(
        prompt=prompt,
        input_images=input_images,
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
        input_fidelity=input_fidelity,
        concurrency=concurrency,
        retry_count=retry_count,
        retry_delay=retry_delay,
        image_request_delay=image_request_delay,
    )

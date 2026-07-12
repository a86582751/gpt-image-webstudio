import time

from ..config import CONFIG, REVERSE_PROMPT, reset_stop_flag
from ..core import (
    display_endpoint,
    format_bytes,
    format_protocol_label,
    normalize_protocol,
    normalize_reasoning_effort,
    normalize_retry_settings,
)
from ..runtime import format_duration
from ..text_tasks import request_multimodal_text, resolve_reverse_image_path


def reverse_prompt_from_image(
    uploaded_image,
    local_image_path,
    iteration_base_url,
    iteration_model_id,
    iteration_api_key,
    iteration_protocol,
    iteration_reasoning_effort,
    retry_count,
    retry_delay,
):
    reset_stop_flag("reverse")
    retry_count, retry_delay = normalize_retry_settings(retry_count, retry_delay)
    iteration_protocol = normalize_protocol(iteration_protocol)
    iteration_reasoning_effort = normalize_reasoning_effort(iteration_reasoning_effort)
    image_path = resolve_reverse_image_path(uploaded_image, local_image_path)
    reverse_prompt = CONFIG.get("reverse_prompt", REVERSE_PROMPT)
    started_at = time.perf_counter()
    retry_events = []

    try:
        result, vision_image, protocol, request_url = request_multimodal_text(
            reverse_prompt,
            image_path,
            iteration_base_url,
            iteration_model_id,
            iteration_api_key,
            iteration_protocol,
            retry_count,
            retry_delay,
            iteration_reasoning_effort,
            lambda label, attempt, retries, error: retry_events.append(
                f"{label}触发重试 {attempt}/{retries}：{error}"
            ),
            "提示词反推",
        )
    except Exception as error:
        return "", f"提示词反推失败：{error}"

    status_extra = f"\n{retry_events[-1]}" if retry_events else ""
    return (
        result,
        f"反推完成；协议：{format_protocol_label(protocol)}；地址：{display_endpoint(request_url)}；上传图片 {format_bytes(vision_image['original_size'])} -> {format_bytes(vision_image['compressed_size'])}，{vision_image['dimensions']}；耗时 {format_duration(time.perf_counter() - started_at)}{status_extra}",
    )

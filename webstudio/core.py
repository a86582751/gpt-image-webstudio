import base64
import json
import os
import re
import time
from io import BytesIO
from urllib.parse import urlparse

import requests
from PIL import Image

from .config import (
    ASPECT_RATIOS,
    CONFIG,
    CONNECT_TIMEOUT,
    EDIT_INPUT_COMPRESS_THRESHOLD,
    EDIT_INPUT_JPEG_QUALITY,
    EDIT_INPUT_MAX_SIDE,
    IMAGE_MODEL_PRESETS,
    ITERATION_PROMPT_SOURCE_PRESETS,
    MODEL_PROTOCOL_PRESETS,
    QUALITY_PRESETS,
    REASONING_EFFORT_PRESETS,
    RESOLUTION_PRESETS,
    SEEDREAM_INTERFACE_FORMAT_PRESETS,
    SEEDREAM_OUTPUT_FORMAT_PRESETS,
    SEEDREAM_RESPONSE_FORMAT_PRESETS,
    SEEDREAM_WATERMARK_PRESETS,
    VISION_IMAGE_JPEG_QUALITY,
    VISION_IMAGE_MAX_SIDE,
    seedream_model_family,
)

def resolve_size(aspect_ratio, resolution):
    ratio_sizes = ASPECT_RATIOS.get(aspect_ratio, ASPECT_RATIOS["4:3 横图"])
    resolution_key = RESOLUTION_PRESETS.get(resolution, "高清")
    return ratio_sizes[resolution_key]

SEEDREAM_PRO_SIZE_TABLES = {
    "1K": {
        "1:1 正方形": "1024x1024",
        "4:3 横图": "1152x864",
        "3:4 竖图": "864x1152",
        "16:9 宽屏": "1312x736",
        "9:16 竖屏": "736x1312",
    },
    "2K": {
        "1:1 正方形": "2048x2048",
        "4:3 横图": "2304x1728",
        "3:4 竖图": "1728x2304",
        "16:9 宽屏": "2560x1440",
        "9:16 竖屏": "1440x2560",
    },
}

SEEDREAM_LITE_SIZE_TABLES = {
    "2K": {
        "1:1 正方形": "2048x2048",
        "4:3 横图": "2304x1728",
        "3:4 竖图": "1728x2304",
        "16:9 宽屏": "2848x1600",
        "9:16 竖屏": "1600x2848",
    },
    "3K": {
        "1:1 正方形": "3072x3072",
        "4:3 横图": "3456x2592",
        "3:4 竖图": "2592x3456",
        "16:9 宽屏": "4096x2304",
        "9:16 竖屏": "2304x4096",
    },
    "4K": {
        "1:1 正方形": "4096x4096",
        "4:3 横图": "4704x3520",
        "3:4 竖图": "3520x4704",
        "16:9 宽屏": "5504x3040",
        "9:16 竖屏": "3040x5504",
    },
}


def resolve_seedream_size(aspect_ratio, resolution, model_id=""):
    resolution_key = RESOLUTION_PRESETS.get(resolution, "高清")
    if seedream_model_family(model_id) == "lite":
        size_tier = {
            "标准": "2K",
            "高清": "3K",
            "超清": "4K",
        }.get(resolution_key, "3K")
        size_table = SEEDREAM_LITE_SIZE_TABLES
    else:
        size_tier = {
            "标准": "1K",
            "高清": "2K",
            "超清": "2K",
        }.get(resolution_key, "2K")
        size_table = SEEDREAM_PRO_SIZE_TABLES
    return size_table[size_tier].get(aspect_ratio, size_table[size_tier]["4:3 横图"])


def resolve_image_request_size(provider, aspect_ratio, resolution, model_id=""):
    if normalize_image_model_provider(provider) == "豆包 Seedream":
        return resolve_seedream_size(aspect_ratio, resolution, model_id)
    return resolve_size(aspect_ratio, resolution)


def normalize_quality(quality):
    quality = (quality or "auto").strip()
    return quality if quality in QUALITY_PRESETS else "auto"


def normalize_image_model_provider(provider):
    provider = (provider or "GPT Image").strip()
    return provider if provider in IMAGE_MODEL_PRESETS else "GPT Image"


def normalize_seedream_response_format(response_format):
    response_format = (response_format or "url").strip()
    return response_format if response_format in SEEDREAM_RESPONSE_FORMAT_PRESETS else "url"


def normalize_seedream_output_format(output_format):
    output_format = (output_format or "自动").strip()
    return output_format if output_format in SEEDREAM_OUTPUT_FORMAT_PRESETS else "自动"


def normalize_seedream_watermark(watermark):
    watermark = (watermark or "关闭").strip()
    return watermark if watermark in SEEDREAM_WATERMARK_PRESETS else "关闭"


def normalize_seedream_interface_format(interface_format):
    interface_format = (interface_format or "官方方舟").strip()
    return interface_format if interface_format in SEEDREAM_INTERFACE_FORMAT_PRESETS else "官方方舟"


def seedream_uses_official_interface():
    return normalize_seedream_interface_format(CONFIG.get("seedream_interface_format")) == "官方方舟"


def seedream_watermark_enabled(watermark):
    return normalize_seedream_watermark(watermark) == "开启"


def seedream_aspect_ratio_text(aspect_ratio):
    return {
        "1:1 正方形": "1:1 正方形",
        "4:3 横图": "4:3 横图",
        "3:4 竖图": "3:4 竖图",
        "16:9 宽屏": "16:9 宽屏横图",
        "9:16 竖屏": "9:16 竖屏图",
    }.get(aspect_ratio, aspect_ratio or "4:3 横图")


def build_seedream_prompt(prompt, aspect_ratio):
    prompt = (prompt or "").strip()
    ratio_text = seedream_aspect_ratio_text(aspect_ratio)
    return f"{prompt}\n\n图片比例：{ratio_text}。"


def normalize_protocol(protocol):
    protocol = (protocol or "自动识别").strip()
    return protocol if protocol in MODEL_PROTOCOL_PRESETS else "自动识别"


def normalize_iteration_prompt_source(source):
    source = (source or "随机提示词").strip()
    return source if source in ITERATION_PROMPT_SOURCE_PRESETS else "随机提示词"


def normalize_reasoning_effort(effort):
    effort = (effort or "关闭").strip()
    return effort if effort in REASONING_EFFORT_PRESETS else "关闭"


def normalize_retry_settings(retry_count, retry_delay):
    return max(0, int(retry_count)), max(0, float(retry_delay))


def normalize_image_request_delay(image_request_delay):
    return max(0, min(30, float(image_request_delay or 0)))


def request_timeout(read_timeout):
    return (CONNECT_TIMEOUT, read_timeout)


def format_protocol_label(protocol):
    return {
        "openai_chat": "OpenAI Chat",
        "openai_responses": "OpenAI Responses",
        "gemini": "Gemini 原生",
        "anthropic_messages": "Claude Messages",
    }.get(protocol, protocol)


def display_endpoint(url):
    return (url or "").split("?", 1)[0]


def format_bytes(byte_count):
    byte_count = int(byte_count or 0)
    if byte_count < 1024 * 1024:
        return f"{byte_count / 1024:.1f} KB"
    return f"{byte_count / (1024 * 1024):.1f} MB"


def gemini_headers(api_key, request_url):
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key.strip()}
    if "generativelanguage.googleapis.com" not in request_url:
        headers["Authorization"] = f"Bearer {api_key.strip()}"
    return headers


def apply_reasoning_settings(payload, protocol, effort, model_id=""):
    """Apply vendor-specific thinking/reasoning parameters only when the user enables them."""
    effort = normalize_reasoning_effort(effort)

    effort_map = {
        "低": "low",
        "中": "medium",
        "高": "high",
        "最高": "high",
    }
    max_compatible_effort = {
        "低": "low",
        "中": "medium",
        "高": "high",
        "最高": "max",
    }
    gemini_budget = {
        "低": 1024,
        "中": 4096,
        "高": 8192,
        "最高": 24576,
    }
    claude_budget = {
        "低": 1024,
        "中": 4096,
        "高": 8192,
        "最高": 16000,
    }
    claude_effort = {
        "低": "low",
        "中": "medium",
        "高": "high",
        "最高": "max",
    }
    glm_reasoning_effort = {
        "关闭": "none",
        "低": "low",
        "中": "medium",
        "高": "high",
        "最高": "max",
    }

    model_lower = (model_id or "").lower()
    if protocol == "openai_chat" and "glm-5.2" in model_lower:
        payload["reasoning_effort"] = glm_reasoning_effort[effort]
        return payload

    if effort == "关闭":
        return payload

    if protocol == "openai_responses":
        payload["reasoning"] = {"effort": effort_map[effort]}
        return payload
    if protocol == "openai_chat":
        if "deepseek" in model_lower:
            payload["reasoning_effort"] = max_compatible_effort[effort]
            payload["extra_body"] = {"thinking": {"type": "enabled"}}
        else:
            payload["reasoning_effort"] = effort_map[effort]
        return payload
    if protocol == "gemini":
        thinking_config = {"thinkingBudget": gemini_budget[effort]}
        if model_lower.startswith("gemini-3"):
            thinking_config = {"thinkingLevel": effort_map[effort]}
        payload["generationConfig"] = {**payload.get("generationConfig", {}), "thinkingConfig": thinking_config}
        return payload
    if protocol == "anthropic_messages":
        if any(model_name in model_lower for model_name in ("claude-opus-4-7", "claude-opus-4-6", "claude-sonnet-4-6")):
            payload["thinking"] = {"type": "adaptive"}
            payload["output_config"] = {"effort": claude_effort[effort]}
            payload["max_tokens"] = max(int(payload.get("max_tokens", 2000)), 4096)
            return payload
        payload["thinking"] = {"type": "enabled", "budget_tokens": claude_budget[effort]}
        payload["max_tokens"] = max(int(payload.get("max_tokens", 2000)), claude_budget[effort] + 1024)
        return payload
    return payload


def resolve_api_url(base_url):
    base_url = (base_url or "").strip().rstrip("/")
    if not base_url:
        raise ValueError("请填写 API 地址。")
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"

    parsed_url = urlparse(base_url)
    if not parsed_url.scheme or not parsed_url.netloc:
        raise ValueError("API 地址格式不正确，请填写类似 https://example.com 的地址。")

    if base_url.endswith("/images/generations"):
        return base_url
    if base_url.endswith("/v1"):
        return f"{base_url}/images/generations"
    return f"{base_url}/v1/images/generations"


def resolve_seedream_api_url(base_url):
    base_url = (base_url or "").strip().rstrip("/")
    if not base_url:
        raise ValueError("请填写 Seedream API 地址。")
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"

    parsed_url = urlparse(base_url)
    if not parsed_url.scheme or not parsed_url.netloc:
        raise ValueError("Seedream API 地址格式不正确，请填写类似 https://ark.cn-beijing.volces.com/api/v3 的地址。")

    if base_url.endswith("/images/generations"):
        return base_url
    return f"{base_url}/images/generations"


def resolve_edit_api_url(base_url):
    base_url = (base_url or "").strip().rstrip("/")
    if not base_url:
        raise ValueError("请填写 API 地址。")
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"

    parsed_url = urlparse(base_url)
    if not parsed_url.scheme or not parsed_url.netloc:
        raise ValueError("API 地址格式不正确，请填写类似 https://example.com 的地址。")

    if base_url.endswith("/images/edits"):
        return base_url
    if base_url.endswith("/images/generations"):
        return base_url[: -len("/images/generations")] + "/images/edits"
    if base_url.endswith("/v1"):
        return f"{base_url}/images/edits"
    return f"{base_url}/v1/images/edits"


def normalize_base_url(base_url, empty_message, invalid_message):
    base_url = (base_url or "").strip().rstrip("/")
    if not base_url:
        raise ValueError(empty_message)
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"

    parsed_url = urlparse(base_url)
    if not parsed_url.scheme or not parsed_url.netloc:
        raise ValueError(invalid_message)
    return base_url


def detect_text_protocol(base_url, model_id):
    base_url = normalize_base_url(base_url, "请填写文本模型 API 地址。", "文本模型 API 地址格式不正确。")
    model_id = (model_id or "").strip()
    if not model_id:
        raise ValueError("请填写文本模型 ID。")

    model_lower = model_id.lower()
    if base_url.endswith("/chat/completions"):
        return "openai_chat", base_url
    if base_url.endswith("/responses"):
        return "openai_responses", base_url
    if base_url.endswith("/messages"):
        return "anthropic_messages", base_url
    if "/v1beta/models" in base_url:
        if base_url.endswith(":generateContent"):
            return "gemini", base_url
        if "/v1beta/models/" in base_url:
            return "gemini", f"{base_url}:generateContent"
        return "gemini", f"{base_url.rstrip('/')}/{model_id}:generateContent"
    if base_url.endswith("/v1beta"):
        return "gemini", f"{base_url}/models/{model_id}:generateContent"
    if model_lower.startswith(("gemini", "models/gemini")):
        return "gemini", f"{base_url}/v1beta/models/{model_id}:generateContent"
    if model_lower.startswith(("claude", "anthropic")):
        if base_url.endswith("/v1"):
            return "anthropic_messages", f"{base_url}/messages"
        return "anthropic_messages", f"{base_url}/v1/messages"
    if base_url.endswith("/v1"):
        return "openai_chat", f"{base_url}/chat/completions"
    return "openai_chat", f"{base_url}/v1/chat/completions"


def protocol_choice_to_code(choice):
    return {
        "OpenAI Chat": "openai_chat",
        "OpenAI Responses": "openai_responses",
        "Gemini 原生": "gemini",
        "Claude Messages": "anthropic_messages",
    }.get(choice)


def resolve_protocol_url(base_url, model_id, protocol_code, empty_message, invalid_message):
    """Build a concrete endpoint from root URLs, version URLs, or full endpoints."""
    base_url = normalize_base_url(base_url, empty_message, invalid_message)
    model_id = (model_id or "").strip()
    if not model_id:
        raise ValueError("请填写模型 ID。")

    if protocol_code == "openai_chat":
        if base_url.endswith("/chat/completions"):
            return protocol_code, base_url
        if base_url.endswith("/v1"):
            return protocol_code, f"{base_url}/chat/completions"
        return protocol_code, f"{base_url}/v1/chat/completions"
    if protocol_code == "openai_responses":
        if base_url.endswith("/responses"):
            return protocol_code, base_url
        if base_url.endswith("/v1"):
            return protocol_code, f"{base_url}/responses"
        return protocol_code, f"{base_url}/v1/responses"
    if protocol_code == "anthropic_messages":
        if base_url.endswith("/messages"):
            return protocol_code, base_url
        if base_url.endswith("/v1"):
            return protocol_code, f"{base_url}/messages"
        return protocol_code, f"{base_url}/v1/messages"
    if protocol_code == "gemini":
        if base_url.endswith(":generateContent"):
            return protocol_code, base_url
        if "/v1beta/models/" in base_url:
            return protocol_code, f"{base_url}:generateContent"
        if "/v1beta/models" in base_url:
            return protocol_code, f"{base_url.rstrip('/')}/{model_id}:generateContent"
        if base_url.endswith("/v1beta"):
            return protocol_code, f"{base_url}/models/{model_id}:generateContent"
        return protocol_code, f"{base_url}/v1beta/models/{model_id}:generateContent"
    raise ValueError("不支持的协议选择。")


def resolve_text_protocol(base_url, model_id, protocol_choice):
    protocol_code = protocol_choice_to_code(protocol_choice)
    if protocol_code:
        return resolve_protocol_url(
            base_url,
            model_id,
            protocol_code,
            "请填写文本模型 API 地址。",
            "文本模型 API 地址格式不正确。",
        )
    return detect_text_protocol(base_url, model_id)


def detect_vision_protocol(base_url, model_id):
    base_url = normalize_base_url(base_url, "请填写多模态模型 API 地址。", "多模态模型 API 地址格式不正确。")
    model_id = (model_id or "").strip()
    if not model_id:
        raise ValueError("请填写多模态模型 ID。")

    model_lower = model_id.lower()
    if base_url.endswith("/chat/completions"):
        return "openai_chat", base_url
    if base_url.endswith("/responses"):
        return "openai_responses", base_url
    if base_url.endswith("/messages"):
        return "anthropic_messages", base_url
    if "/v1beta/models" in base_url:
        if base_url.endswith(":generateContent"):
            return "gemini", base_url
        if "/v1beta/models/" in base_url:
            return "gemini", f"{base_url}:generateContent"
        return "gemini", f"{base_url.rstrip('/')}/{model_id}:generateContent"
    if base_url.endswith("/v1beta"):
        return "gemini", f"{base_url}/models/{model_id}:generateContent"
    if model_lower.startswith(("claude", "anthropic")):
        if base_url.endswith("/v1"):
            return "anthropic_messages", f"{base_url}/messages"
        return "anthropic_messages", f"{base_url}/v1/messages"
    if model_lower.startswith(("gpt", "o1", "o3", "o4")):
        return "openai_chat", f"{base_url}/v1/chat/completions"
    if base_url.endswith("/v1"):
        return "openai_chat", f"{base_url}/chat/completions"
    return "gemini", f"{base_url}/v1beta/models/{model_id}:generateContent"


def resolve_vision_protocol(base_url, model_id, protocol_choice):
    protocol_code = protocol_choice_to_code(protocol_choice)
    if protocol_code:
        return resolve_protocol_url(
            base_url,
            model_id,
            protocol_code,
            "请填写多模态模型 API 地址。",
            "多模态模型 API 地址格式不正确。",
        )
    return detect_vision_protocol(base_url, model_id)


def get_save_dir(save_dir):
    save_dir = (save_dir or "").strip()
    if not save_dir:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(script_dir, "AI_Cards")
    return save_dir


def build_gallery_items(saved_paths):
    return [(path, f"第 {index} 张") for index, path in enumerate(saved_paths, start=1)]


def build_iterative_gallery_items(records, final_only=False):
    items = []
    for record in sorted(records, key=lambda item: (item["task_index"], item["round_index"])):
        if final_only and not record.get("is_final"):
            continue
        label = f"第 {record['task_index']} 组"
        if not final_only:
            label += f" / 第 {record['round_index']} 轮"
        items.append((record["path"], label))
    return items


def get_image_dimensions(image_path):
    """Read PNG/JPEG dimensions without pulling in another imaging dependency."""
    try:
        with open(image_path, "rb") as image_file:
            header = image_file.read(32)
            if header.startswith(b"\x89PNG\r\n\x1a\n") and len(header) >= 24:
                width = int.from_bytes(header[16:20], "big")
                height = int.from_bytes(header[20:24], "big")
                return f"{width}x{height}"
            if header[:3] == b"\xff\xd8\xff":
                image_file.seek(2)
                while True:
                    marker_prefix = image_file.read(1)
                    if marker_prefix != b"\xff":
                        return ""
                    marker = image_file.read(1)
                    while marker == b"\xff":
                        marker = image_file.read(1)
                    if marker in (b"\xc0", b"\xc1", b"\xc2", b"\xc3", b"\xc5", b"\xc6", b"\xc7", b"\xc9", b"\xca", b"\xcb", b"\xcd", b"\xce", b"\xcf"):
                        segment_length = int.from_bytes(image_file.read(2), "big")
                        segment = image_file.read(segment_length - 2)
                        if len(segment) >= 5:
                            height = int.from_bytes(segment[1:3], "big")
                            width = int.from_bytes(segment[3:5], "big")
                            return f"{width}x{height}"
                    else:
                        segment_length_data = image_file.read(2)
                        if len(segment_length_data) != 2:
                            return ""
                        segment_length = int.from_bytes(segment_length_data, "big")
                        image_file.seek(segment_length - 2, os.SEEK_CUR)
    except Exception:
        return ""
    return ""


def format_resolution_summary(image_records, fallback_size):
    if not image_records:
        return f"图片分辨率：未保存图片；请求尺寸 {fallback_size}"

    dimensions_by_index = []
    for job_index, image_path, _elapsed in sorted(image_records, key=lambda item: item[0]):
        dimensions_by_index.append((job_index, get_image_dimensions(image_path) or fallback_size))

    unique_dimensions = {dimensions for _index, dimensions in dimensions_by_index}
    if len(unique_dimensions) == 1 and len(dimensions_by_index) > 12:
        only_dimensions = next(iter(unique_dimensions))
        return f"图片分辨率：第 {dimensions_by_index[0][0]}-{dimensions_by_index[-1][0]} 张均为 {only_dimensions}"

    details = "，".join(f"第 {index} 张 {dimensions}" for index, dimensions in dimensions_by_index)
    return f"图片分辨率：{details}"


def format_duration(seconds):
    if seconds < 60:
        return f"{seconds:.1f} 秒"
    minutes = int(seconds // 60)
    rest_seconds = seconds % 60
    return f"{minutes} 分 {rest_seconds:.1f} 秒"


def format_generation_stats(image_records, requested_count, total_elapsed, fallback_size):
    success_count = len(image_records)
    success_rate = success_count / requested_count * 100 if requested_count else 0
    average_elapsed = sum(record[2] for record in image_records) / success_count if success_count else 0
    return (
        f"{format_resolution_summary(image_records, fallback_size)}；"
        f"单张平均耗时 {format_duration(average_elapsed)}；"
        f"成功率 {success_count}/{requested_count} ({success_rate:.1f}%)；"
        f"总耗时 {format_duration(total_elapsed)}"
    )


def format_failed_jobs_summary(failed_jobs, max_items=3, item_label="张"):
    if not failed_jobs:
        return ""
    samples = "；".join(
        f"第 {job_index} {item_label}：{message[:260]}"
        for job_index, message in failed_jobs[-max_items:]
    )
    extra_count = len(failed_jobs) - max_items
    suffix = f"；另有 {extra_count} 个失败未展开" if extra_count > 0 else ""
    reconnect_hint = ""
    if any(is_remote_disconnected_error(message) for _job_index, message in failed_jobs):
        reconnect_hint = "\n提示：远端在返回结果前断开连接，API可能已生成并计费，但本地应用没有拿到图片 URL/base64，无法自动保存。可能是提示词被上游审核拦截或者上游服务异常。"
    return f"\n失败详情：{samples}{suffix}{reconnect_hint}"


def is_remote_disconnected_error(error):
    error_text = f"{type(error).__name__}: {error!r} {error}"
    return (
        "RemoteDisconnected" in error_text
        or "Remote end closed connection without response" in error_text
        or "Connection aborted" in error_text
    )


def extract_error_message(payload):
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            return error.get("message") or error.get("code") or str(error)
        if isinstance(error, str):
            return error
        for key in ("message", "msg", "detail"):
            if payload.get(key):
                return str(payload[key])
    return ""


def format_response_error(response):
    try:
        payload = response.json()
        detail = extract_error_message(payload) or str(payload)
    except ValueError:
        detail = response.text.strip()

    if response.status_code in (401, 403):
        prefix = "认证失败，请检查 API Key 是否正确"
    elif response.status_code == 404:
        prefix = "接口地址不可用，请检查 API 地址或模型是否正确"
    elif response.status_code == 429:
        prefix = "请求过于频繁或额度不足"
    else:
        prefix = "中转站返回错误"

    detail = detail[:500] if detail else "没有返回错误详情"
    return f"{prefix}；HTTP {response.status_code}；{detail}"


def parse_image_items(response):
    if not response.ok:
        raise RuntimeError(format_response_error(response))

    try:
        payload = response.json()
    except ValueError as error:
        raise RuntimeError("中转站返回的不是有效 JSON。") from error

    error_message = extract_error_message(payload)
    if error_message:
        raise RuntimeError(f"中转站返回错误：{error_message}")

    if not isinstance(payload, dict):
        raise RuntimeError("中转站返回格式不正确：顶层不是 JSON 对象。")

    image_items = payload.get("data", [])
    if not isinstance(image_items, list):
        raise RuntimeError("中转站返回格式不正确：data 不是列表。")

    return image_items


def post_json(url, headers, payload, timeout):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request_headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
        **headers,
    }
    return requests.post(url, headers=request_headers, data=body, timeout=timeout)


def parse_text_model_content(protocol, response):
    if protocol == "gemini":
        return parse_google_content(response)

    if not response.ok:
        raise RuntimeError(format_response_error(response))

    try:
        payload = response.json()
    except ValueError as error:
        raise RuntimeError("文本模型接口返回的不是有效 JSON。") from error

    error_message = extract_error_message(payload)
    if error_message:
        raise RuntimeError(f"文本模型接口返回错误：{error_message}")

    if protocol == "openai_responses":
        output_text = payload.get("output_text")
        if output_text:
            return output_text.strip()
        texts = []
        for item in payload.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in ("output_text", "text") and content.get("text"):
                    texts.append(content["text"])
        content = "\n".join(texts).strip()
        if content:
            return content

    if protocol == "anthropic_messages":
        texts = [part.get("text", "") for part in payload.get("content", []) if isinstance(part, dict)]
        content = "\n".join(text.strip() for text in texts if text.strip()).strip()
        if content:
            return content

    choices = payload.get("choices", [])
    if choices:
        message = choices[0].get("message", {})
        content = message.get("content")
        if content:
            return content.strip()

    raise RuntimeError("文本模型接口返回内容为空。")


def parse_google_content(response):
    if not response.ok:
        raise RuntimeError(format_response_error(response))

    try:
        payload = response.json()
    except ValueError as error:
        raise RuntimeError("视觉评估接口返回的不是有效 JSON。") from error

    error_message = extract_error_message(payload)
    if error_message:
        raise RuntimeError(f"视觉评估接口返回错误：{error_message}")

    candidates = payload.get("candidates", [])
    if not candidates:
        raise RuntimeError("视觉评估接口没有返回候选结果。")

    parts = candidates[0].get("content", {}).get("parts", [])
    texts = [part.get("text", "") for part in parts if isinstance(part, dict)]
    content = "\n".join(text.strip() for text in texts if text.strip()).strip()
    if not content:
        raise RuntimeError("视觉评估接口返回内容为空。")
    return content


def prepare_vision_image(image_path):
    """Create a compact JPEG copy in memory for multimodal evaluation."""
    original_size = os.path.getsize(image_path)
    with Image.open(image_path) as image:
        image = image.convert("RGBA")
        if max(image.size) > VISION_IMAGE_MAX_SIDE:
            image.thumbnail((VISION_IMAGE_MAX_SIDE, VISION_IMAGE_MAX_SIDE), Image.Resampling.LANCZOS)

        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.getchannel("A"))
            image = background
        else:
            image = image.convert("RGB")

        buffer = BytesIO()
        image.save(
            buffer,
            format="JPEG",
            quality=VISION_IMAGE_JPEG_QUALITY,
            optimize=True,
            progressive=True,
        )

    data = buffer.getvalue()
    return {
        "base64": base64.b64encode(data).decode("utf-8"),
        "mime_type": "image/jpeg",
        "original_size": original_size,
        "compressed_size": len(data),
        "dimensions": f"{image.width}x{image.height}",
    }


def prepare_edit_input_image(image_path):
    original_size = os.path.getsize(image_path)
    suffix = os.path.splitext(image_path)[1].lower()
    if original_size <= EDIT_INPUT_COMPRESS_THRESHOLD and suffix in (".png", ".jpg", ".jpeg", ".webp"):
        with open(image_path, "rb") as image_file:
            data = image_file.read()
        mime_type = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }[suffix]
        return {
            "filename": os.path.basename(image_path),
            "bytes": data,
            "mime_type": mime_type,
            "original_size": original_size,
            "compressed_size": len(data),
            "dimensions": get_image_dimensions(image_path) or "",
            "compressed": False,
        }

    with Image.open(image_path) as image:
        image = image.convert("RGBA")
        if max(image.size) > EDIT_INPUT_MAX_SIDE:
            image.thumbnail((EDIT_INPUT_MAX_SIDE, EDIT_INPUT_MAX_SIDE), Image.Resampling.LANCZOS)
        background = Image.new("RGB", image.size, (255, 255, 255))
        background.paste(image, mask=image.getchannel("A"))
        buffer = BytesIO()
        background.save(
            buffer,
            format="JPEG",
            quality=EDIT_INPUT_JPEG_QUALITY,
            optimize=True,
            progressive=True,
        )
        dimensions = f"{background.width}x{background.height}"

    data = buffer.getvalue()
    return {
        "filename": f"{os.path.splitext(os.path.basename(image_path))[0]}_compressed.jpg",
        "bytes": data,
        "mime_type": "image/jpeg",
        "original_size": original_size,
        "compressed_size": len(data),
        "dimensions": dimensions,
        "compressed": True,
    }


def prepare_seedream_input_image(image_path):
    image = prepare_edit_input_image(image_path)
    image["data_url"] = f"data:{image['mime_type']};base64,{base64.b64encode(image['bytes']).decode('utf-8')}"
    return image

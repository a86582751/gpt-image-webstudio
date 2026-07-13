import os
import re

import requests

from .config import (
    CONFIG,
    ITERATION_OPTIMIZER_PROMPT,
    RANDOM_SCENE_SUMMARY_PROMPT,
    RANDOM_SYSTEM_PROMPT,
    RANDOM_USER_PROMPT,
    TEXT_READ_TIMEOUT,
    VISION_READ_TIMEOUT,
    render_prompt_template,
    template_has_variables,
)
from .core import (
    apply_reasoning_settings,
    gemini_headers,
    parse_text_model_content,
    prepare_vision_image,
    request_timeout,
    resolve_text_protocol,
    resolve_vision_protocol,
)
from .runtime import run_with_retry
from .logging_utils import log_event

def optimize_prompt_with_image(
    prompt,
    image_path,
    base_url,
    model_id,
    api_key,
    protocol_choice="自动识别",
    retry_count=1,
    retry_delay=2,
    on_retry=None,
    reasoning_effort="关闭",
    creation_theme="",
    user_initial_direction="",
    prepared_vision_image=None,
):
    log_event("多模态", "开始评估图片", model=model_id, protocol=protocol_choice)
    if not api_key or not api_key.strip():
        raise ValueError("请填写视觉评估 API Key。")

    vision_image = prepared_vision_image or prepare_vision_image(image_path)
    image_base64 = vision_image["base64"]
    image_mime_type = vision_image["mime_type"]
    optimizer_prompt = CONFIG.get("iteration_optimizer_prompt", ITERATION_OPTIMIZER_PROMPT)
    template_variables = {
        "current_prompt": prompt.strip(),
        "prompt": prompt.strip(),
        "creation_theme": (creation_theme or "").strip(),
        "theme": (creation_theme or "").strip(),
        "user_initial_direction": (user_initial_direction or "").strip(),
        "initial_direction": (user_initial_direction or "").strip(),
        "image": "见随附图片。",
    }
    if template_has_variables(optimizer_prompt):
        request_text = render_prompt_template(optimizer_prompt, template_variables)
    else:
        context_parts = [
            f"【多模态模型的系统提示词】\n{optimizer_prompt.strip()}",
        ]
        if creation_theme and creation_theme.strip():
            context_parts.append(f"【创作主题】\n{creation_theme.strip()}")
        if user_initial_direction and user_initial_direction.strip():
            context_parts.append(f"【用户初始创作方向】\n{user_initial_direction.strip()}")
        context_parts.append(f"【本轮图片使用的提示词】\n{prompt.strip()}")
        context_parts.append("【本轮图片】\n见随附图片。")
        request_text = "\n\n".join(context_parts)
    protocol, request_url = resolve_vision_protocol(base_url, model_id, protocol_choice)

    def request_vision():
        if protocol == "openai_chat":
            payload = apply_reasoning_settings(
                {
                    "model": model_id.strip(),
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": request_text},
                                {"type": "image_url", "image_url": {"url": f"data:{image_mime_type};base64,{image_base64}"}},
                            ],
                        }
                    ],
                },
                protocol,
                reasoning_effort,
                model_id,
            )
            response = requests.post(
                request_url,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key.strip()}"},
                json=payload,
                timeout=request_timeout(VISION_READ_TIMEOUT),
            )
        elif protocol == "openai_responses":
            payload = apply_reasoning_settings(
                {
                    "model": model_id.strip(),
                    "input": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": request_text},
                                {"type": "input_image", "image_url": f"data:{image_mime_type};base64,{image_base64}"},
                            ],
                        }
                    ],
                },
                protocol,
                reasoning_effort,
                model_id,
            )
            response = requests.post(
                request_url,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key.strip()}"},
                json=payload,
                timeout=request_timeout(VISION_READ_TIMEOUT),
            )
        elif protocol == "anthropic_messages":
            payload = apply_reasoning_settings(
                {
                    "model": model_id.strip(),
                    "max_tokens": 2000,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": request_text},
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": image_mime_type,
                                        "data": image_base64,
                                    },
                                },
                            ],
                        }
                    ],
                },
                protocol,
                reasoning_effort,
                model_id,
            )
            response = requests.post(
                request_url,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key.strip(),
                    "anthropic-version": "2023-06-01",
                },
                json=payload,
                timeout=request_timeout(VISION_READ_TIMEOUT),
            )
        else:
            payload = apply_reasoning_settings(
                {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {"text": request_text},
                                {
                                    "inline_data": {
                                        "mime_type": image_mime_type,
                                        "data": image_base64,
                                    }
                                },
                            ],
                        }
                    ],
                },
                protocol,
                reasoning_effort,
                model_id,
            )
            response = requests.post(
                request_url,
                headers=gemini_headers(api_key, request_url),
                json=payload,
                timeout=request_timeout(VISION_READ_TIMEOUT),
            )
        return parse_text_model_content(protocol, response)

    return run_with_retry(
        request_vision,
        "视觉评估优化",
        retries=int(retry_count),
        delay_seconds=float(retry_delay),
        on_retry=on_retry,
    )


def request_multimodal_text(
    text_prompt,
    image_path,
    base_url,
    model_id,
    api_key,
    protocol_choice="自动识别",
    retry_count=1,
    retry_delay=2,
    reasoning_effort="关闭",
    on_retry=None,
    label="多模态请求",
):
    log_event("多模态", "开始读取图片", model=model_id, protocol=protocol_choice, operation=label)
    if not api_key or not api_key.strip():
        raise ValueError("请填写多模态模型 API Key。")
    if not model_id or not model_id.strip():
        raise ValueError("请填写多模态模型 ID。")

    vision_image = prepare_vision_image(image_path)
    image_base64 = vision_image["base64"]
    image_mime_type = vision_image["mime_type"]
    protocol, request_url = resolve_vision_protocol(base_url, model_id, protocol_choice)

    def request_vision_text():
        if protocol == "openai_chat":
            payload = apply_reasoning_settings(
                {
                    "model": model_id.strip(),
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": text_prompt},
                                {"type": "image_url", "image_url": {"url": f"data:{image_mime_type};base64,{image_base64}"}},
                            ],
                        }
                    ],
                },
                protocol,
                reasoning_effort,
                model_id,
            )
            response = requests.post(
                request_url,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key.strip()}"},
                json=payload,
                timeout=request_timeout(VISION_READ_TIMEOUT),
            )
        elif protocol == "openai_responses":
            payload = apply_reasoning_settings(
                {
                    "model": model_id.strip(),
                    "input": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": text_prompt},
                                {"type": "input_image", "image_url": f"data:{image_mime_type};base64,{image_base64}"},
                            ],
                        }
                    ],
                },
                protocol,
                reasoning_effort,
                model_id,
            )
            response = requests.post(
                request_url,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key.strip()}"},
                json=payload,
                timeout=request_timeout(VISION_READ_TIMEOUT),
            )
        elif protocol == "anthropic_messages":
            payload = apply_reasoning_settings(
                {
                    "model": model_id.strip(),
                    "max_tokens": 2000,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": text_prompt},
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": image_mime_type,
                                        "data": image_base64,
                                    },
                                },
                            ],
                        }
                    ],
                },
                protocol,
                reasoning_effort,
                model_id,
            )
            response = requests.post(
                request_url,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key.strip(),
                    "anthropic-version": "2023-06-01",
                },
                json=payload,
                timeout=request_timeout(VISION_READ_TIMEOUT),
            )
        else:
            payload = apply_reasoning_settings(
                {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {"text": text_prompt},
                                {
                                    "inline_data": {
                                        "mime_type": image_mime_type,
                                        "data": image_base64,
                                    }
                                },
                            ],
                        }
                    ],
                },
                protocol,
                reasoning_effort,
                model_id,
            )
            response = requests.post(
                request_url,
                headers=gemini_headers(api_key, request_url),
                json=payload,
                timeout=request_timeout(VISION_READ_TIMEOUT),
            )
        return parse_text_model_content(protocol, response)

    content = run_with_retry(
        request_vision_text,
        label,
        retries=int(retry_count),
        delay_seconds=float(retry_delay),
        on_retry=on_retry,
    )
    return content, vision_image, protocol, request_url


def format_used_scenes(used_scenes):
    scenes = [str(scene).strip() for scene in (used_scenes or []) if str(scene).strip()]
    return "、".join(scenes)


def build_random_user_prompt(preference, used_scenes=None):
    preference = (preference or "").strip()
    used_scenes_text = format_used_scenes(used_scenes)
    user_prompt = CONFIG.get("random_user_prompt", RANDOM_USER_PROMPT)
    variables = {
        "preference": preference,
        "creative_direction": preference,
        "creation_direction": preference,
        "used_scenes": used_scenes_text,
    }
    if template_has_variables(user_prompt):
        return render_prompt_template(user_prompt, variables)
    if used_scenes_text:
        scene_instruction = f"已经用过场景：{used_scenes_text}\n请避开这些地点和场景，生成一个新的具体场景。"
        if preference:
            return f"{user_prompt}\n\n本次创作方向：{preference}\n\n{scene_instruction}"
        return f"{user_prompt}\n\n{scene_instruction}"
    if not preference:
        return user_prompt
    return f"{user_prompt}\n\n本次创作方向：{preference}"


def resolve_reverse_image_path(uploaded_image, local_image_path):
    if uploaded_image:
        return uploaded_image
    local_image_path = (local_image_path or "").strip().strip('"')
    if not local_image_path:
        raise ValueError("请上传图片，或填写本地图片路径。")
    if not os.path.exists(local_image_path):
        raise ValueError("本地图片路径不存在。")
    return local_image_path


def generate_random_prompt(
    base_url,
    model_id,
    api_key,
    preference,
    protocol_choice="自动识别",
    retry_count=1,
    retry_delay=2,
    on_retry=None,
    reasoning_effort="关闭",
    used_scenes=None,
):
    if not api_key or not api_key.strip():
        raise ValueError("请填写随机提示词 API Key。")
    if not model_id or not model_id.strip():
        raise ValueError("请填写随机提示词模型 ID。")

    protocol, request_url = resolve_text_protocol(base_url, model_id, protocol_choice)
    system_prompt = CONFIG.get("random_system_prompt", RANDOM_SYSTEM_PROMPT)
    user_prompt = build_random_user_prompt(preference, used_scenes=used_scenes)

    def request_text():
        if protocol == "openai_chat":
            payload = apply_reasoning_settings(
                {
                    "model": model_id.strip(),
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "stream": False,
                },
                protocol,
                reasoning_effort,
                model_id,
            )
            response = requests.post(
                request_url,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key.strip()}"},
                json=payload,
                timeout=request_timeout(TEXT_READ_TIMEOUT),
            )
        elif protocol == "openai_responses":
            payload = apply_reasoning_settings(
                {
                    "model": model_id.strip(),
                    "input": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
                protocol,
                reasoning_effort,
                model_id,
            )
            response = requests.post(
                request_url,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key.strip()}"},
                json=payload,
                timeout=request_timeout(TEXT_READ_TIMEOUT),
            )
        elif protocol == "anthropic_messages":
            payload = apply_reasoning_settings(
                {
                    "model": model_id.strip(),
                    "system": system_prompt,
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
                protocol,
                reasoning_effort,
                model_id,
            )
            response = requests.post(
                request_url,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key.strip(),
                    "anthropic-version": "2023-06-01",
                },
                json=payload,
                timeout=request_timeout(TEXT_READ_TIMEOUT),
            )
        else:
            payload = apply_reasoning_settings(
                {
                    "system_instruction": {"parts": [{"text": system_prompt}]},
                    "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                },
                protocol,
                reasoning_effort,
                model_id,
            )
            response = requests.post(
                request_url,
                headers=gemini_headers(api_key, request_url),
                json=payload,
                timeout=request_timeout(TEXT_READ_TIMEOUT),
            )
        return parse_text_model_content(protocol, response)

    return run_with_retry(
        request_text,
        "随机提示词生成",
        retries=int(retry_count),
        delay_seconds=float(retry_delay),
        on_retry=on_retry,
    )


def sanitize_scene_summary(scene):
    scene = (scene or "").strip()
    scene = re.sub(r"^[`\"'“”‘’\s]+|[`\"'“”‘’\s]+$", "", scene)
    scene = re.sub(r"^(地点和场景概述|场景概述|地点|场景)\s*[:：]\s*", "", scene)
    scene = re.split(r"[\n\r。；;，,]", scene, maxsplit=1)[0].strip()
    return scene[:40]


def summarize_prompt_scene(
    prompt,
    base_url,
    model_id,
    api_key,
    protocol_choice="自动识别",
    retry_count=1,
    retry_delay=2,
    on_retry=None,
):
    summary_template = CONFIG.get("random_scene_summary_prompt", RANDOM_SCENE_SUMMARY_PROMPT)
    variables = {"prompt": prompt}
    user_prompt = render_prompt_template(summary_template, variables) if template_has_variables(summary_template) else f"{summary_template}\n\n提示词：\n{prompt}"
    protocol, request_url = resolve_text_protocol(base_url, model_id, protocol_choice)

    def request_summary():
        if protocol == "openai_chat":
            payload = apply_reasoning_settings(
                {
                    "model": model_id.strip(),
                    "messages": [{"role": "user", "content": user_prompt}],
                    "stream": False,
                },
                protocol,
                "低",
                model_id,
            )
            response = requests.post(
                request_url,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key.strip()}"},
                json=payload,
                timeout=request_timeout(TEXT_READ_TIMEOUT),
            )
        elif protocol == "openai_responses":
            payload = apply_reasoning_settings(
                {
                    "model": model_id.strip(),
                    "input": [{"role": "user", "content": user_prompt}],
                },
                protocol,
                "低",
                model_id,
            )
            response = requests.post(
                request_url,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key.strip()}"},
                json=payload,
                timeout=request_timeout(TEXT_READ_TIMEOUT),
            )
        elif protocol == "anthropic_messages":
            payload = apply_reasoning_settings(
                {
                    "model": model_id.strip(),
                    "max_tokens": 200,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
                protocol,
                "低",
                model_id,
            )
            response = requests.post(
                request_url,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key.strip(),
                    "anthropic-version": "2023-06-01",
                },
                json=payload,
                timeout=request_timeout(TEXT_READ_TIMEOUT),
            )
        else:
            payload = apply_reasoning_settings(
                {
                    "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                },
                protocol,
                "低",
                model_id,
            )
            response = requests.post(
                request_url,
                headers=gemini_headers(api_key, request_url),
                json=payload,
                timeout=request_timeout(TEXT_READ_TIMEOUT),
            )
        return sanitize_scene_summary(parse_text_model_content(protocol, response))

    return run_with_retry(
        request_summary,
        "场景概述提取",
        retries=int(retry_count),
        delay_seconds=float(retry_delay),
        on_retry=on_retry,
    )


def generate_random_prompt_job(
    job_index,
    item_label,
    prompt_kind,
    base_url,
    model_id,
    api_key,
    preference,
    protocol,
    retry_count,
    retry_delay,
    reasoning_effort,
    used_scenes=None,
    summarize_scene=False,
):
    log_event(
        "文本任务",
        "开始生成提示词",
        job=job_index,
        item=item_label,
        model=model_id,
        protocol=protocol,
        summarize_scene=summarize_scene,
    )
    events = []
    prompt = generate_random_prompt(
        base_url,
        model_id,
        api_key,
        preference,
        protocol,
        retry_count,
        retry_delay,
        lambda label, attempt, retries, error: events.append(
            f"第 {job_index} {item_label}{prompt_kind}触发重试 {attempt}/{retries}：{error}"
        ),
        reasoning_effort=reasoning_effort,
        used_scenes=used_scenes,
    )
    scene = ""
    if summarize_scene:
        scene = summarize_prompt_scene(
            prompt,
            base_url,
            model_id,
            api_key,
            protocol,
            retry_count,
            retry_delay,
            lambda label, attempt, retries, error: events.append(
                f"第 {job_index} {item_label}场景概述触发重试 {attempt}/{retries}：{error}"
            ),
        )
    log_event("文本任务", "提示词已生成", job=job_index, item=item_label, scene=scene or "未提取")
    return job_index, prompt, scene, events


def submit_sequential_prompt_job(executor, futures, job_index, total_count, worker, used_scenes):
    if job_index > total_count:
        return job_index
    futures[executor.submit(worker, job_index, list(used_scenes))] = job_index
    return job_index + 1

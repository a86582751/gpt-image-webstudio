from .config import (
    CONFIG,
    DEFAULT_CONFIG,
    env_config_values,
    load_config,
    normalize_config,
    normalize_seedream_model_id,
    persist_config,
    prompt_config_values,
    save_env_config,
    save_prompt_templates,
)
from .core import (
    normalize_image_request_delay,
    normalize_protocol,
    normalize_quality,
    normalize_reasoning_effort,
    normalize_retry_settings,
    normalize_seedream_interface_format,
    normalize_seedream_output_format,
    normalize_seedream_response_format,
    normalize_seedream_watermark,
)

def save_settings(
    save_dir,
    base_url,
    model_id,
    quality,
    api_key,
    seedream_base_url,
    seedream_model_id,
    seedream_api_key,
    seedream_interface_format,
    seedream_response_format,
    seedream_output_format,
    seedream_watermark,
    random_base_url,
    random_model_id,
    random_api_key,
    random_protocol,
    random_reasoning_effort,
    iteration_base_url,
    iteration_model_id,
    iteration_api_key,
    iteration_protocol,
    iteration_reasoning_effort,
    retry_count,
    retry_delay,
    image_request_delay,
    random_system_prompt,
    random_user_prompt,
    random_scene_summary_prompt,
    iteration_optimizer_prompt,
    reverse_prompt,
):
    retry_count, retry_delay = normalize_retry_settings(retry_count, retry_delay)
    image_request_delay = normalize_image_request_delay(image_request_delay)
    quality = normalize_quality(quality)
    seedream_model_id = normalize_seedream_model_id(seedream_model_id)
    seedream_interface_format = normalize_seedream_interface_format(seedream_interface_format)
    seedream_response_format = normalize_seedream_response_format(seedream_response_format)
    seedream_output_format = normalize_seedream_output_format(seedream_output_format)
    seedream_watermark = normalize_seedream_watermark(seedream_watermark)
    random_protocol = normalize_protocol(random_protocol)
    iteration_protocol = normalize_protocol(iteration_protocol)
    random_reasoning_effort = normalize_reasoning_effort(random_reasoning_effort)
    iteration_reasoning_effort = normalize_reasoning_effort(iteration_reasoning_effort)

    save_env_config(
        {
            "base_url": base_url,
            "model_id": model_id,
            "api_key": api_key,
            "seedream_base_url": seedream_base_url,
            "seedream_model_id": seedream_model_id,
            "seedream_api_key": seedream_api_key,
            "random_base_url": random_base_url,
            "random_model_id": random_model_id,
            "random_api_key": random_api_key,
            "iteration_base_url": iteration_base_url,
            "iteration_model_id": iteration_model_id,
            "iteration_api_key": iteration_api_key,
        }
    )
    save_prompt_templates(
        {
            "random_system_prompt": random_system_prompt,
            "random_user_prompt": random_user_prompt,
            "random_scene_summary_prompt": random_scene_summary_prompt,
            "iteration_optimizer_prompt": iteration_optimizer_prompt,
            "reverse_prompt": reverse_prompt,
        }
    )

    persist_config(
        {
            "save_dir": save_dir,
            "base_url": base_url,
            "model_id": model_id,
            "quality": quality,
            "api_key": api_key,
            "seedream_base_url": seedream_base_url,
            "seedream_model_id": seedream_model_id,
            "seedream_api_key": seedream_api_key,
            "seedream_interface_format": seedream_interface_format,
            "seedream_response_format": seedream_response_format,
            "seedream_output_format": seedream_output_format,
            "seedream_watermark": seedream_watermark,
            "random_base_url": random_base_url,
            "random_model_id": random_model_id,
            "random_api_key": random_api_key,
            "random_protocol": random_protocol,
            "random_reasoning_effort": random_reasoning_effort,
            "iteration_base_url": iteration_base_url,
            "iteration_model_id": iteration_model_id,
            "iteration_api_key": iteration_api_key,
            "iteration_protocol": iteration_protocol,
            "iteration_reasoning_effort": iteration_reasoning_effort,
            "retry_count": retry_count,
            "retry_delay": retry_delay,
            "image_request_delay": image_request_delay,
        },
    )
    CONFIG.update(prompt_config_values())
    return "设置已保存。"


def load_ui_state():
    latest_config = normalize_config(load_config(DEFAULT_CONFIG))
    latest_config.update(env_config_values())
    latest_config.update(prompt_config_values())
    CONFIG.clear()
    CONFIG.update(latest_config)
    return [
        latest_config["prompt"],
        latest_config["image_count"],
        latest_config["concurrency"],
        latest_config["image_model_provider"],
        latest_config["aspect_ratio"],
        latest_config["resolution"],
        latest_config["prompt"],
        latest_config["image_count"],
        latest_config["concurrency"],
        latest_config["image_model_provider"],
        latest_config["aspect_ratio"],
        latest_config["resolution"],
        latest_config["edit_input_fidelity"],
        latest_config["random_preference"],
        latest_config["prompt"],
        latest_config["image_count"],
        latest_config["concurrency"],
        latest_config["image_model_provider"],
        latest_config["aspect_ratio"],
        latest_config["resolution"],
        latest_config["random_preference"],
        latest_config["creative_count"],
        latest_config["creative_random_enhance"],
        latest_config["text_concurrency"],
        latest_config["image_concurrency"],
        latest_config["image_model_provider"],
        latest_config["aspect_ratio"],
        latest_config["resolution"],
        latest_config["random_preference"],
        latest_config["iteration_prompt_source"],
        latest_config["iteration_custom_prompt"],
        latest_config["prompt"],
        latest_config["iteration_count"],
        latest_config["iteration_batch_count"],
        latest_config["iteration_random_enhance"],
        latest_config["iteration_text_concurrency"],
        latest_config["iteration_image_concurrency"],
        latest_config["image_model_provider"],
        latest_config["aspect_ratio"],
        latest_config["resolution"],
        latest_config["save_dir"],
        latest_config["base_url"],
        latest_config["model_id"],
        latest_config["quality"],
        latest_config["api_key"],
        latest_config["seedream_base_url"],
        latest_config["seedream_model_id"],
        latest_config["seedream_interface_format"],
        latest_config["seedream_response_format"],
        latest_config["seedream_output_format"],
        latest_config["seedream_watermark"],
        latest_config["seedream_api_key"],
        latest_config["random_base_url"],
        latest_config["random_model_id"],
        latest_config["random_protocol"],
        latest_config["random_reasoning_effort"],
        latest_config["random_api_key"],
        latest_config["iteration_base_url"],
        latest_config["iteration_model_id"],
        latest_config["iteration_protocol"],
        latest_config["iteration_reasoning_effort"],
        latest_config["iteration_api_key"],
        latest_config["retry_count"],
        latest_config["retry_delay"],
        latest_config["image_request_delay"],
        latest_config["random_system_prompt"],
        latest_config["random_user_prompt"],
        latest_config["random_scene_summary_prompt"],
        latest_config["iteration_optimizer_prompt"],
        latest_config["reverse_prompt"],
        "已加载保存的设置。",
    ]

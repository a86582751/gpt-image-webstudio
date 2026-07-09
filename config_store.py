import json
from pathlib import Path


CONFIG_PATH = Path(__file__).with_name("app_config.json")
ENV_MANAGED_KEYS = {
    "base_url",
    "api_key",
    "model_id",
    "seedream_base_url",
    "seedream_api_key",
    "seedream_model_id",
    "random_base_url",
    "random_api_key",
    "random_model_id",
    "iteration_base_url",
    "iteration_api_key",
    "iteration_model_id",
}
PROMPT_TEMPLATE_KEYS = {
    "random_system_prompt",
    "random_user_prompt",
    "random_scene_summary_prompt",
    "iteration_optimizer_prompt",
    "reverse_prompt",
}
LOCAL_ONLY_KEYS = ENV_MANAGED_KEYS | PROMPT_TEMPLATE_KEYS | {"seedream_model_version"}


def local_config(default_config):
    return {key: value for key, value in default_config.items() if key not in LOCAL_ONLY_KEYS}


def load_config(default_config):
    if not CONFIG_PATH.exists():
        save_config(local_config(default_config))
        return default_config.copy()

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
            saved_config = json.load(config_file)
    except (OSError, json.JSONDecodeError):
        return default_config.copy()

    config = default_config.copy()
    if isinstance(saved_config, dict):
        config.update({key: value for key, value in saved_config.items() if key in config})
        if any(key in LOCAL_ONLY_KEYS for key in saved_config):
            save_config(config)
    return config


def save_config(config):
    config = {key: value for key, value in config.items() if key not in LOCAL_ONLY_KEYS}
    temp_path = CONFIG_PATH.with_suffix(".tmp")
    with temp_path.open("w", encoding="utf-8") as config_file:
        json.dump(config, config_file, ensure_ascii=False, indent=2)
    temp_path.replace(CONFIG_PATH)


def update_config(default_config, updates):
    config = load_config(default_config)
    config.update(updates)
    save_config(config)

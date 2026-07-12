import ast
import os
import re
import time
from pathlib import Path

from config_store import load_config, save_config
from env_loader import load_local_env, update_local_env


ROOT_DIR = Path(__file__).resolve().parent.parent

load_local_env()

from prompt_templates import (
    ITERATION_OPTIMIZER_PROMPT,
    RANDOM_SYSTEM_PROMPT,
    RANDOM_USER_PROMPT,
    REVERSE_PROMPT,
)
try:
    from prompt_templates import RANDOM_SCENE_SUMMARY_PROMPT
except ImportError:
    from prompt_templates_Default import RANDOM_SCENE_SUMMARY_PROMPT

BASE_URL = os.getenv("OPENAI_BASE_URL", "").rstrip("/")
API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_ID = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2")
RANDOM_BASE_URL = os.getenv("RANDOM_PROMPT_BASE_URL", "").rstrip("/")
RANDOM_API_KEY = os.getenv("RANDOM_PROMPT_API_KEY", "")
RANDOM_MODEL_ID = os.getenv("RANDOM_PROMPT_MODEL", "")
ITERATION_BASE_URL = os.getenv("ITERATION_BASE_URL", "").rstrip("/")
ITERATION_API_KEY = os.getenv("ITERATION_API_KEY", "")
ITERATION_MODEL_ID = os.getenv("ITERATION_MODEL", "")
SEEDREAM_BASE_URL = os.getenv("SEEDREAM_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")
SEEDREAM_API_KEY = os.getenv("SEEDREAM_API_KEY", "")
DEFAULT_SEEDREAM_MODEL_ID = "doubao-seedream-5-0-pro-260628"
SEEDREAM_MODEL_ID = os.getenv("SEEDREAM_MODEL", DEFAULT_SEEDREAM_MODEL_ID).strip() or DEFAULT_SEEDREAM_MODEL_ID
QUALITY_PRESETS = ["auto", "medium", "high", "low"]
IMAGE_MODEL_PRESETS = ["GPT Image", "豆包 Seedream"]
SEEDREAM_PRO_MODEL_IDS = {"doubao-seedream-5-0-pro-260628"}
SEEDREAM_LITE_MODEL_IDS = {"doubao-seedream-5-0-260128", "doubao-seedream-5-0-lite-260128"}
SEEDREAM_MODEL_ID_PRESETS = [
    "doubao-seedream-5-0-pro-260628",
    "doubao-seedream-5-0-lite-260128",
    "doubao-seedream-5-0-260128",
]
SEEDREAM_RESPONSE_FORMAT_PRESETS = ["url", "b64_json"]
SEEDREAM_OUTPUT_FORMAT_PRESETS = ["自动", "jpeg", "png"]
SEEDREAM_WATERMARK_PRESETS = ["关闭", "开启"]
SEEDREAM_INTERFACE_FORMAT_PRESETS = ["官方方舟", "OpenAI 兼容中转"]
MODEL_PROTOCOL_PRESETS = ["自动识别", "OpenAI Chat", "OpenAI Responses", "Gemini 原生", "Claude Messages"]
ITERATION_PROMPT_SOURCE_PRESETS = ["随机提示词", "自定义提示词"]
REASONING_EFFORT_PRESETS = ["关闭", "低", "中", "高", "最高"]
INPUT_FIDELITY_PRESETS = ["low", "high"]
STOP_FLAGS = {
    "manual": False,
    "edit": False,
    "random": False,
    "creative": False,
    "iterative": False,
    "reverse": False,
}

TEMPLATE_TOKEN_PATTERN = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")


def template_has_variables(template):
    return bool(TEMPLATE_TOKEN_PATTERN.search(template or ""))


def render_prompt_template(template, variables):
    now = time.localtime()
    values = {
        "date": time.strftime("%Y-%m-%d", now),
        "time": time.strftime("%H:%M:%S", now),
        "datetime": time.strftime("%Y-%m-%d %H:%M:%S", now),
    }
    values.update({key: "" if value is None else str(value) for key, value in variables.items()})

    def replace_token(match):
        return values.get(match.group(1), match.group(0))

    return TEMPLATE_TOKEN_PATTERN.sub(replace_token, template or "")

ASPECT_RATIOS = {
    "1:1 正方形": {
        "标准": "1248x1248",
        "高清": "2048x2048",
        "超清": "2880x2880",
    },
    "4:3 横图": {
        "标准": "1440x1072",
        "高清": "2048x1536",
        "超清": "3264x2448",
    },
    "3:4 竖图": {
        "标准": "1072x1440",
        "高清": "1536x2048",
        "超清": "2448x3264",
    },
    "16:9 宽屏": {
        "标准": "1664x928",
        "高清": "2560x1440",
        "超清": "3840x2160",
    },
    "9:16 竖屏": {
        "标准": "928x1664",
        "高清": "1440x2560",
        "超清": "2160x3840",
    },
}

RESOLUTION_PRESETS = {
    "标准": "标准",
    "高清": "高清",
    "超清": "超清",
}

DEFAULT_CONFIG = {
    "prompt": "",
    "save_dir": "",
    "image_count": 1,
    "concurrency": 1,
    "text_concurrency": 10,
    "image_concurrency": 3,
    "creative_count": 5,
    "creative_random_enhance": False,
    "retry_count": 1,
    "retry_delay": 2,
    "image_request_delay": 0,
    "aspect_ratio": "4:3 横图",
    "resolution": "高清",
    "image_model_provider": "GPT Image",
    "base_url": BASE_URL,
    "model_id": MODEL_ID,
    "quality": "auto",
    "api_key": API_KEY,
    "seedream_base_url": SEEDREAM_BASE_URL,
    "seedream_model_id": SEEDREAM_MODEL_ID,
    "seedream_api_key": SEEDREAM_API_KEY,
    "seedream_interface_format": "官方方舟",
    "seedream_response_format": "url",
    "seedream_output_format": "自动",
    "seedream_watermark": "关闭",
    "edit_input_fidelity": "high",
    "random_base_url": RANDOM_BASE_URL,
    "random_model_id": RANDOM_MODEL_ID,
    "random_api_key": RANDOM_API_KEY,
    "random_protocol": "自动识别",
    "random_reasoning_effort": "最高",
    "random_preference": "",
    "iteration_count": 3,
    "iteration_batch_count": 1,
    "iteration_text_concurrency": 3,
    "iteration_image_concurrency": 3,
    "iteration_random_enhance": False,
    "iteration_prompt_source": "随机提示词",
    "iteration_custom_prompt": "",
    "iteration_base_url": ITERATION_BASE_URL,
    "iteration_model_id": ITERATION_MODEL_ID,
    "iteration_api_key": ITERATION_API_KEY,
    "iteration_protocol": "自动识别",
    "iteration_reasoning_effort": "关闭",
    "random_system_prompt": RANDOM_SYSTEM_PROMPT,
    "random_user_prompt": RANDOM_USER_PROMPT,
    "random_scene_summary_prompt": RANDOM_SCENE_SUMMARY_PROMPT,
    "iteration_optimizer_prompt": ITERATION_OPTIMIZER_PROMPT,
    "reverse_prompt": REVERSE_PROMPT,
}


def normalize_seedream_model_id(model_id):
    model_id = (model_id or "").strip()
    return model_id or DEFAULT_SEEDREAM_MODEL_ID


def seedream_model_family(model_id):
    model_id = normalize_seedream_model_id(model_id)
    if model_id in SEEDREAM_LITE_MODEL_IDS:
        return "lite"
    if model_id in SEEDREAM_PRO_MODEL_IDS:
        return "pro"
    lowered = model_id.lower()
    if "lite" in lowered:
        return "lite"
    return "pro"


ENV_CONFIG_FIELDS = {
    "base_url": "OPENAI_BASE_URL",
    "api_key": "OPENAI_API_KEY",
    "model_id": "OPENAI_IMAGE_MODEL",
    "seedream_base_url": "SEEDREAM_BASE_URL",
    "seedream_api_key": "SEEDREAM_API_KEY",
    "seedream_model_id": "SEEDREAM_MODEL",
    "random_base_url": "RANDOM_PROMPT_BASE_URL",
    "random_api_key": "RANDOM_PROMPT_API_KEY",
    "random_model_id": "RANDOM_PROMPT_MODEL",
    "iteration_base_url": "ITERATION_BASE_URL",
    "iteration_api_key": "ITERATION_API_KEY",
    "iteration_model_id": "ITERATION_MODEL",
}
PROMPT_TEMPLATE_FIELDS = {
    "random_system_prompt": "RANDOM_SYSTEM_PROMPT",
    "random_user_prompt": "RANDOM_USER_PROMPT",
    "random_scene_summary_prompt": "RANDOM_SCENE_SUMMARY_PROMPT",
    "iteration_optimizer_prompt": "ITERATION_OPTIMIZER_PROMPT",
    "reverse_prompt": "REVERSE_PROMPT",
}


def prompt_config_values():
    values = {
        "random_system_prompt": RANDOM_SYSTEM_PROMPT,
        "random_user_prompt": RANDOM_USER_PROMPT,
        "random_scene_summary_prompt": RANDOM_SCENE_SUMMARY_PROMPT,
        "iteration_optimizer_prompt": ITERATION_OPTIMIZER_PROMPT,
        "reverse_prompt": REVERSE_PROMPT,
    }
    prompt_path = ROOT_DIR / "prompt_templates.py"
    try:
        tree = ast.parse(prompt_path.read_text(encoding="utf-8"))
        constant_to_config = {constant_name: config_key for config_key, constant_name in PROMPT_TEMPLATE_FIELDS.items()}
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in constant_to_config:
                    value = ast.literal_eval(node.value)
                    if isinstance(value, str):
                        values[constant_to_config[target.id]] = value
    except (OSError, SyntaxError, ValueError):
        pass
    return values


def save_prompt_templates(updates):
    prompt_path = ROOT_DIR / "prompt_templates.py"
    lines = ["# Local prompt templates. This file is intentionally ignored by Git.", ""]
    for config_key, constant_name in PROMPT_TEMPLATE_FIELDS.items():
        lines.append(f"{constant_name} = {updates[config_key]!r}")
        lines.append("")
    prompt_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def env_config_values():
    values = {}
    for config_key, env_key in ENV_CONFIG_FIELDS.items():
        if env_key in os.environ:
            value = os.getenv(env_key, "")
            values[config_key] = value.rstrip("/") if config_key.endswith("base_url") else value
    values["seedream_model_id"] = normalize_seedream_model_id(values.get("seedream_model_id", CONFIG.get("seedream_model_id", DEFAULT_SEEDREAM_MODEL_ID) if "CONFIG" in globals() else SEEDREAM_MODEL_ID))
    return values


def save_env_config(updates):
    env_updates = {
        env_key: updates[config_key]
        for config_key, env_key in ENV_CONFIG_FIELDS.items()
        if config_key in updates
    }
    update_local_env(env_updates)


def normalize_config(config):
    config = config.copy()
    if config["aspect_ratio"] not in ASPECT_RATIOS:
        config["aspect_ratio"] = DEFAULT_CONFIG["aspect_ratio"]
    if config["resolution"] not in RESOLUTION_PRESETS:
        config["resolution"] = DEFAULT_CONFIG["resolution"]
    if config["image_model_provider"] not in IMAGE_MODEL_PRESETS:
        config["image_model_provider"] = DEFAULT_CONFIG["image_model_provider"]
    if config["quality"] not in QUALITY_PRESETS:
        config["quality"] = DEFAULT_CONFIG["quality"]
    if config["seedream_response_format"] not in SEEDREAM_RESPONSE_FORMAT_PRESETS:
        config["seedream_response_format"] = DEFAULT_CONFIG["seedream_response_format"]
    if config["seedream_output_format"] not in SEEDREAM_OUTPUT_FORMAT_PRESETS:
        config["seedream_output_format"] = DEFAULT_CONFIG["seedream_output_format"]
    if config["seedream_watermark"] not in SEEDREAM_WATERMARK_PRESETS:
        config["seedream_watermark"] = DEFAULT_CONFIG["seedream_watermark"]
    if config.get("seedream_interface_format") not in SEEDREAM_INTERFACE_FORMAT_PRESETS:
        config["seedream_interface_format"] = DEFAULT_CONFIG["seedream_interface_format"]
    config["seedream_model_id"] = normalize_seedream_model_id(config.get("seedream_model_id"))
    if config["edit_input_fidelity"] not in INPUT_FIDELITY_PRESETS:
        config["edit_input_fidelity"] = DEFAULT_CONFIG["edit_input_fidelity"]
    if config["random_protocol"] not in MODEL_PROTOCOL_PRESETS:
        config["random_protocol"] = DEFAULT_CONFIG["random_protocol"]
    if config["iteration_protocol"] not in MODEL_PROTOCOL_PRESETS:
        config["iteration_protocol"] = DEFAULT_CONFIG["iteration_protocol"]
    if config["iteration_prompt_source"] not in ITERATION_PROMPT_SOURCE_PRESETS:
        config["iteration_prompt_source"] = DEFAULT_CONFIG["iteration_prompt_source"]
    if config["random_reasoning_effort"] not in REASONING_EFFORT_PRESETS:
        config["random_reasoning_effort"] = DEFAULT_CONFIG["random_reasoning_effort"]
    if config["iteration_reasoning_effort"] not in REASONING_EFFORT_PRESETS:
        config["iteration_reasoning_effort"] = DEFAULT_CONFIG["iteration_reasoning_effort"]
    config["iteration_batch_count"] = min(10, max(1, int(config.get("iteration_batch_count") or DEFAULT_CONFIG["iteration_batch_count"])))
    config["iteration_text_concurrency"] = min(10, max(1, int(config.get("iteration_text_concurrency") or DEFAULT_CONFIG["iteration_text_concurrency"])))
    config["iteration_image_concurrency"] = min(10, max(1, int(config.get("iteration_image_concurrency") or DEFAULT_CONFIG["iteration_image_concurrency"])))
    return config


CONFIG = normalize_config(load_config(DEFAULT_CONFIG))
CONFIG.update(env_config_values())
CONFIG.update(prompt_config_values())

CONNECT_TIMEOUT = 30
TEXT_READ_TIMEOUT = 300
VISION_READ_TIMEOUT = 600
IMAGE_READ_TIMEOUT = 1200
VISION_IMAGE_MAX_SIDE = 1536
VISION_IMAGE_JPEG_QUALITY = 90
EDIT_INPUT_COMPRESS_THRESHOLD = int(2.5 * 1024 * 1024)
EDIT_INPUT_MAX_SIDE = 2048
EDIT_INPUT_JPEG_QUALITY = 92


def persist_config(updates):
    """Persist UI state and keep the in-memory config aligned for later callbacks."""
    persisted_updates = {key: value for key, value in updates.items() if key not in ENV_CONFIG_FIELDS}
    if persisted_updates:
        config = load_config(DEFAULT_CONFIG)
        config.update(persisted_updates)
        for env_key in ENV_CONFIG_FIELDS:
            config.pop(env_key, None)
        config.pop("seedream_model_version", None)
        save_config(config)
    CONFIG.update(updates)


def reset_stop_flag(mode):
    STOP_FLAGS[mode] = False


def request_stop(mode):
    STOP_FLAGS[mode] = True
    return "已请求停止：正在取消排队任务，已开始的网络请求会在当前请求返回后停止继续。"


def should_stop(mode):
    return STOP_FLAGS.get(mode, False)

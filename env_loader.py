import os
import shutil
from pathlib import Path


ENV_TEMPLATE = """OPENAI_BASE_URL=
OPENAI_API_KEY=
OPENAI_IMAGE_MODEL=gpt-image-2

SEEDREAM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
SEEDREAM_API_KEY=
SEEDREAM_MODEL=doubao-seedream-5-0-pro-260628

RANDOM_PROMPT_BASE_URL=
RANDOM_PROMPT_API_KEY=
RANDOM_PROMPT_MODEL=

ITERATION_BASE_URL=
ITERATION_API_KEY=
ITERATION_MODEL=

# Console logging: DEBUG / INFO / WARNING / ERROR
WEBSTUDIO_LOG_LEVEL=INFO
"""


def ensure_local_runtime_files():
    base_dir = Path(__file__).resolve().parent
    env_path = base_dir / ".env"
    if not env_path.exists():
        env_path.write_text(ENV_TEMPLATE, encoding="utf-8")

    prompt_path = base_dir / "prompt_templates.py"
    default_prompt_path = base_dir / "prompt_templates_Default.py"
    if not prompt_path.exists() and default_prompt_path.exists():
        shutil.copyfile(default_prompt_path, prompt_path)


def load_local_env(filename=".env"):
    ensure_local_runtime_files()
    env_path = Path(__file__).with_name(filename)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


def _format_env_value(value):
    value = "" if value is None else str(value)
    if not value:
        return ""
    special_chars = " #" + "\t" + "\r" + "\n" + "\"'"
    if any(char in value for char in special_chars):
        return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return value


def update_local_env(updates, filename=".env"):
    env_path = Path(__file__).with_name(filename)
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    pending = {key: "" if value is None else str(value) for key, value in updates.items()}
    written = set()
    output = []
    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or "=" not in raw_line:
            output.append(raw_line)
            continue
        key = raw_line.split("=", 1)[0].strip()
        if key in pending:
            output.append(f"{key}={_format_env_value(pending[key])}")
            os.environ[key] = pending[key]
            written.add(key)
        else:
            output.append(raw_line)
    for key, value in pending.items():
        if key not in written:
            output.append(f"{key}={_format_env_value(value)}")
            os.environ[key] = value
    env_path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")

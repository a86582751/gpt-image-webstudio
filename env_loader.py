import os
from pathlib import Path


def load_local_env(filename=".env"):
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

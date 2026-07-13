import threading
import time
from pathlib import Path

from .config import CONFIG, ROOT_DIR
from .logging_utils import log_event


PROMPT_HISTORY_FILENAME = "prompt_history.md"
PROMPT_HISTORY_LOCK = threading.Lock()


def resolve_prompt_history_path(save_dir):
    raw_dir = (save_dir or "").strip().strip('"')
    output_dir = Path(raw_dir).expanduser() if raw_dir else ROOT_DIR / "AI_Cards"
    return output_dir / PROMPT_HISTORY_FILENAME


def save_prompt_batch(save_dir, mode, creation_direction, prompts):
    if not CONFIG.get("save_prompt_history", False):
        return None

    prompts = [str(prompt).strip() for prompt in prompts if prompt is not None and str(prompt).strip()]
    if not prompts:
        return None

    history_path = resolve_prompt_history_path(save_dir)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    direction = (creation_direction or "").replace("\r", " ").replace("\n", " ").strip() or "未指定"
    sections = [f"## {timestamp}｜{mode}", "", f"**创作方向：** {direction}", ""]
    for index, prompt in enumerate(prompts, start=1):
        sections.extend([f"### 提示词 {index}", "", prompt, ""])
    sections.extend(["---", ""])

    with PROMPT_HISTORY_LOCK:
        history_path.parent.mkdir(parents=True, exist_ok=True)
        is_new_file = not history_path.exists()
        with history_path.open("a", encoding="utf-8", newline="\n") as history_file:
            if is_new_file:
                history_file.write("# 文生图提示词历史\n\n")
            history_file.write("\n".join(sections))

    log_event("提示词记录", "已保存 Markdown", mode=mode, prompts=len(prompts), path=history_path)
    return str(history_path)

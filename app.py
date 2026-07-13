"""Compatibility entry point for GPT Image WebStudio."""

from webstudio.config import *
from webstudio.core import *
from webstudio.runtime import *
from webstudio.text_tasks import *
from webstudio.image_tasks import *
from webstudio.workflows import *
from webstudio.settings import *
from webstudio.ui import app, css, js, theme, update_iteration_source_ui
from webstudio.logging_utils import log_event


if __name__ == "__main__":
    log_event("应用", "GPT Image WebStudio 正在启动")
    app.launch(theme=theme, css=css, js=js, inbrowser=True)

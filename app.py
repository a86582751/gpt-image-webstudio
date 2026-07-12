"""Compatibility entry point for GPT Image WebStudio."""

from webstudio.config import *
from webstudio.core import *
from webstudio.runtime import *
from webstudio.text_tasks import *
from webstudio.image_tasks import *
from webstudio.workflows import *
from webstudio.settings import *
from webstudio.ui import app, css, js, theme


if __name__ == "__main__":
    app.launch(theme=theme, css=css, js=js, inbrowser=True)

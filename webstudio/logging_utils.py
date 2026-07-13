import logging
import os
import sys


LOGGER_NAME = "webstudio"
DEFAULT_LOG_LEVEL = "INFO"
SENSITIVE_FIELD_MARKERS = ("key", "token", "secret", "authorization", "password")


def _resolve_log_level():
    level_name = os.getenv("WEBSTUDIO_LOG_LEVEL", DEFAULT_LOG_LEVEL).strip().upper()
    return getattr(logging, level_name, logging.INFO)


def configure_logging():
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(_resolve_log_level())
    logger.propagate = False
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-7s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
    return logger


LOGGER = configure_logging()


def _format_field(key, value):
    lowered = key.lower()
    if any(marker in lowered for marker in SENSITIVE_FIELD_MARKERS):
        return "***"
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    return text if len(text) <= 300 else f"{text[:297]}..."


def log_event(category, message, *, level=logging.INFO, **fields):
    details = " | ".join(
        f"{key}={_format_field(key, value)}"
        for key, value in fields.items()
        if value is not None and value != ""
    )
    text = f"[{category}] {message}"
    if details:
        text = f"{text} | {details}"
    LOGGER.log(level, text)


def log_debug(category, message, **fields):
    log_event(category, message, level=logging.DEBUG, **fields)


def log_warning(category, message, **fields):
    log_event(category, message, level=logging.WARNING, **fields)


def log_error(category, message, **fields):
    log_event(category, message, level=logging.ERROR, **fields)

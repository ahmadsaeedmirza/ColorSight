"""Rotating app log in user_data_dir + global exception hook."""

from __future__ import annotations

import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

from kivy.app import App

_LOG_NAME = "colorsight"
_configured = False


def _log_dir() -> Path:
    app = App.get_running_app()
    if app is not None:
        base = Path(app.user_data_dir)
    else:
        base = Path.home() / ".colorsight"
    base.mkdir(parents=True, exist_ok=True)
    return base


def log_path() -> Path:
    return _log_dir() / "colorsight.log"


def setup_logging() -> Path:
    global _configured
    path = log_path()
    if _configured:
        return path

    root = logging.getLogger(_LOG_NAME)
    root.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    fh = RotatingFileHandler(path, maxBytes=512_000, backupCount=2, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # Also attach to common module loggers
    for name in (
        "colorsight",
        "colorsight.theme",
        "colorsight.camera",
        "colorsight.photos",
    ):
        logging.getLogger(name).setLevel(logging.INFO)
        if not any(isinstance(h, RotatingFileHandler) for h in logging.getLogger(name).handlers):
            logging.getLogger(name).addHandler(fh)
            logging.getLogger(name).propagate = True

    def _hook(exc_type, exc, tb):
        logging.getLogger(_LOG_NAME).error(
            "Unhandled exception\n%s",
            "".join(traceback.format_exception(exc_type, exc, tb)),
        )
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _hook
    _configured = True
    root.info("logging started path=%s", path.name)  # never show full path in UI
    return path


def read_recent_lines(n: int = 300) -> str:
    path = log_path()
    if not path.is_file():
        return "(no log yet)"
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-n:])
    except Exception as exc:
        return f"(could not read log: {exc})"


def log_event(msg: str, *args, level: int = logging.INFO):
    logging.getLogger(_LOG_NAME).log(level, msg, *args)

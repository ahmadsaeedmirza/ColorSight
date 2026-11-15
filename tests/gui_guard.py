"""Helpers so GUI tests skip cleanly when no display / OpenGL window is available.

Never aborts the process — callers raise ``unittest.SkipTest`` instead.
"""

from __future__ import annotations

import os
import unittest


def headless_requested() -> bool:
    return os.environ.get("COLORSIGHT_HEADLESS", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def ensure_kivy_window(*, reason: str = "GUI test needs a Kivy Window") -> None:
    """Ensure a Kivy Window exists, or skip when headless / display is missing.

    Raises ``unittest.SkipTest`` on failure when ``COLORSIGHT_HEADLESS=1``.
    Re-raises when not headless so local developers still see real errors.
    """
    os.environ.setdefault("KIVY_NO_ARGS", "1")
    try:
        from kivy.base import EventLoop
        from kivy.core.window import Window

        EventLoop.ensure_window()
        # Touch size so a dead/null window is obvious
        _ = Window.size
    except Exception as exc:  # noqa: BLE001
        msg = f"{reason}: {exc}"
        if headless_requested():
            raise unittest.SkipTest(msg) from exc
        raise RuntimeError(msg) from exc

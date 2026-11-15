"""Global Kivy ExceptionHandler — log + friendly status, never kill the app."""

from __future__ import annotations

import logging
import traceback

from kivy.app import App
from kivy.base import ExceptionHandler, ExceptionManager

log = logging.getLogger("colorsight")

_installed = False


class DiagnosticsExceptionHandler(ExceptionHandler):
    """Log uncaught exceptions to the diagnostics log; return PASS so Kivy continues."""

    def handle_exception(self, inst):
        try:
            tb = "".join(traceback.format_exception(type(inst), inst, inst.__traceback__))
            log.error("uncaught exception: %s\n%s", inst, tb)
        except Exception:
            log.error("uncaught exception (logging failed): %s", inst)
        try:
            app = App.get_running_app()
            root = getattr(app, "root", None) if app else None
            sm = getattr(root, "sm", None) if root is not None else None
            if sm is not None:
                scr = sm.get_screen(sm.current)
                if hasattr(scr, "_set_status"):
                    scr._set_status("Something went wrong")
                elif hasattr(scr, "set_status"):
                    scr.set_status("Something went wrong")
        except Exception:
            pass
        return ExceptionManager.PASS


def install_exception_handler() -> None:
    global _installed
    if _installed:
        return
    ExceptionManager.add_handler(DiagnosticsExceptionHandler())
    _installed = True
    log.info("diagnostics ExceptionHandler installed")

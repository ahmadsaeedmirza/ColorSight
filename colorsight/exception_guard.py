"""Global Kivy ExceptionHandler — log + status; PASS for non-fatal errors."""

from __future__ import annotations

import logging
import traceback

from kivy.app import App
from kivy.base import ExceptionHandler, ExceptionManager
from kivy.clock import Clock

log = logging.getLogger("colorsight")

_installed = False
_fallback_scheduled = False


class DiagnosticsExceptionHandler(ExceptionHandler):
    """Log uncaught exceptions; show status; count early faults; return PASS."""

    def handle_exception(self, inst):
        try:
            tb = "".join(traceback.format_exception(type(inst), inst, inst.__traceback__))
            log.error("uncaught exception: %s\n%s", inst, tb)
            try:
                for h in logging.getLogger("colorsight").handlers:
                    h.flush()
            except Exception:
                pass
        except Exception:
            log.error("uncaught exception (logging failed): %s", inst)

        count = 0
        try:
            from colorsight.startup import note_startup_exception

            count = note_startup_exception()
        except Exception:
            pass

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

        # Early storm or empty UI → fallback error screen
        try:
            if count >= 3:
                _schedule_fallback(f"startup exception storm (n={count}): {inst}")
            else:
                from colorsight.startup import first_frame_drawn, layout_looks_broken

                app = App.get_running_app()
                root = getattr(app, "root", None) if app else None
                broken, reason = layout_looks_broken(root)
                if broken or (root is not None and not first_frame_drawn() and count >= 1):
                    _schedule_fallback(reason or str(inst))
        except Exception:
            pass

        return ExceptionManager.PASS


def _schedule_fallback(reason: str) -> None:
    global _fallback_scheduled
    if _fallback_scheduled:
        return
    _fallback_scheduled = True

    def _go(_dt=None):
        try:
            from colorsight.app import show_fallback_error

            show_fallback_error(None, detail=reason)
        except Exception:
            log.exception("fallback schedule failed")

    try:
        Clock.schedule_once(_go, 0)
    except Exception:
        _go()


def install_exception_handler() -> None:
    global _installed
    if _installed:
        return
    ExceptionManager.add_handler(DiagnosticsExceptionHandler())
    _installed = True
    log.info("diagnostics ExceptionHandler installed")


def reset_fallback_gate() -> None:
    global _fallback_scheduled
    _fallback_scheduled = False

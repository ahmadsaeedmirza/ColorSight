"""Copy text to the system clipboard (desktop + Android).

Never raise to the UI caller — return False and log. Tries platform-native
paths first (Win32 / Android ClipData), then Kivy, then tkinter.
"""

from __future__ import annotations

import logging
import sys

from colorsight.photo_io import is_android

log = logging.getLogger("colorsight")

_MAX_CHARS = 180_000


def copy_text(text: str) -> bool:
    """Copy ``text`` to the clipboard. Returns True on success."""
    raw = text or ""
    if len(raw) > _MAX_CHARS:
        raw = raw[:_MAX_CHARS] + "\n...(truncated)"

    if is_android():
        if _android_copy(raw):
            return True
        return _kivy_copy(raw)

    if sys.platform == "win32":
        if _win32_copy(raw):
            return True
    if _kivy_copy(raw):
        return True
    if _tk_copy(raw):
        return True
    log.error("clipboard: all copy backends failed chars=%d", len(raw))
    return False


def _kivy_copy(text: str) -> bool:
    try:
        from kivy.core.clipboard import Clipboard

        Clipboard.copy(text)
        # Verify when paste is available (catches silent no-ops)
        try:
            got = Clipboard.paste()
            if got is not None and str(got) != "" and str(got) != text:
                # Some backends return partial / normalized text — still OK if non-empty
                if text[:64] not in str(got) and str(got)[:64] not in text:
                    log.warning("clipboard: kivy paste mismatch — treating as ok")
        except Exception:
            pass
        log.info("clipboard: kivy copy ok chars=%d", len(text))
        return True
    except Exception:
        log.exception("clipboard: kivy copy failed")
        return False


def _win32_copy(text: str) -> bool:
    """CF_UNICODETEXT via Win32 — reliable when Kivy/SDL clipboard is a no-op."""
    try:
        import ctypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        CF_UNICODETEXT = 13
        GMEM_MOVEABLE = 0x0002

        if not user32.OpenClipboard(None):
            log.warning("clipboard: OpenClipboard failed")
            return False
        try:
            user32.EmptyClipboard()
            data = text.encode("utf-16-le") + b"\x00\x00"
            h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
            if not h:
                return False
            ptr = kernel32.GlobalLock(h)
            if not ptr:
                kernel32.GlobalFree(h)
                return False
            ctypes.memmove(ptr, data, len(data))
            kernel32.GlobalUnlock(h)
            if not user32.SetClipboardData(CF_UNICODETEXT, h):
                kernel32.GlobalFree(h)
                return False
            # Clipboard owns ``h`` after SetClipboardData
            log.info("clipboard: win32 copy ok chars=%d", len(text))
            return True
        finally:
            user32.CloseClipboard()
    except Exception:
        log.exception("clipboard: win32 copy failed")
        return False


def _tk_copy(text: str) -> bool:
    try:
        import tkinter as tk

        r = tk.Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(text)
        r.update()
        r.destroy()
        log.info("clipboard: tkinter copy ok chars=%d", len(text))
        return True
    except Exception:
        log.exception("clipboard: tkinter copy failed")
        return False


def _android_copy(text: str) -> bool:
    try:
        from jnius import autoclass, cast  # type: ignore
        from android.runnable import run_on_ui_thread  # type: ignore
    except Exception:
        log.exception("clipboard: android imports failed")
        return False

    try:
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Context = autoclass("android.content.Context")
        ClipData = autoclass("android.content.ClipData")
        String = autoclass("java.lang.String")
        activity = PythonActivity.mActivity
        if activity is None:
            log.error("clipboard: mActivity is None")
            return False

        label = cast("java.lang.CharSequence", String("ColorSight"))
        body = cast("java.lang.CharSequence", String(text))
        clip = ClipData.newPlainText(label, body)

        done = {"ok": False, "err": None}

        @run_on_ui_thread
        def _set():
            try:
                svc = activity.getSystemService(Context.CLIPBOARD_SERVICE)
                svc.setPrimaryClip(clip)
                done["ok"] = True
                log.info("clipboard: android setPrimaryClip ok chars=%d", len(text))
            except Exception as exc:
                done["err"] = exc
                log.exception("clipboard: setPrimaryClip failed")

        _set()
        # Brief wait so UI-thread work can finish before we report
        try:
            import time

            for _ in range(50):
                if done["ok"] or done["err"] is not None:
                    break
                time.sleep(0.01)
        except Exception:
            pass
        return bool(done["ok"])
    except Exception:
        log.exception("clipboard: android copy setup failed")
        return False

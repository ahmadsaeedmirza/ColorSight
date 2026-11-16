"""Copy text to the system clipboard (desktop + Android).

Kivy's ``Clipboard.copy`` can hang or fail silently on Android when the
ClipboardManager init races the UI thread. Prefer a direct pyjnius path there.
Never raise to the UI caller — return False and log.
"""

from __future__ import annotations

import logging

from colorsight.photo_io import is_android

log = logging.getLogger("colorsight")

# Android ClipData can choke on huge blobs; keep a sane cap for log paste.
_MAX_CHARS = 180_000


def copy_text(text: str) -> bool:
    """Copy ``text`` to the clipboard. Returns True if a copy was attempted OK."""
    raw = text or ""
    if len(raw) > _MAX_CHARS:
        raw = raw[:_MAX_CHARS] + "\n…(truncated)"
    if is_android():
        if _android_copy(raw):
            return True
        # Fall through to Kivy as a last resort
    try:
        from kivy.core.clipboard import Clipboard

        Clipboard.copy(raw)
        return True
    except Exception:
        log.exception("clipboard: Clipboard.copy failed")
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

        ok_holder = {"ok": False}

        @run_on_ui_thread
        def _set():
            try:
                svc = activity.getSystemService(Context.CLIPBOARD_SERVICE)
                svc.setPrimaryClip(clip)
                ok_holder["ok"] = True
                log.info("clipboard: android setPrimaryClip ok chars=%d", len(text))
            except Exception:
                log.exception("clipboard: setPrimaryClip failed")

        _set()
        # run_on_ui_thread posts async — treat schedule success as OK when no raise
        return True
    except Exception:
        log.exception("clipboard: android copy setup failed")
        return False

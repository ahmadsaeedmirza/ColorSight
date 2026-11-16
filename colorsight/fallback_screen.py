"""Theme-independent startup failure UI — must work even if the rest of the app failed."""

from __future__ import annotations

import traceback
from pathlib import Path


def build_fallback_root(exc: BaseException | None = None, detail: str = "") -> object:
    """Return a plain BoxLayout root (white bg, black text) with diagnostics + actions.

    Uses only stock Kivy widgets — no theme, fonts, safe_area, or GPU code.
    """
    from kivy.app import App
    from kivy.core.clipboard import Clipboard
    from kivy.graphics import Color, Rectangle
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.button import Button
    from kivy.uix.label import Label
    from kivy.uix.scrollview import ScrollView

    lines: list[str] = []
    if exc is not None:
        lines.append(f"{type(exc).__name__}: {exc}")
        try:
            lines.append(
                "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-1500:]
            )
        except Exception:
            pass
    if detail:
        lines.append(detail)
    log_tail = _safe_log_tail(15)
    if log_tail:
        lines.append("--- last log lines ---")
        lines.append(log_tail)
    body = "\n".join(lines) if lines else "(no details)"

    root = BoxLayout(orientation="vertical", padding=16, spacing=8, size_hint=(1, 1))
    with root.canvas.before:
        Color(1, 1, 1, 1)
        bg = Rectangle(pos=root.pos, size=root.size)

    def _sync(*_a):
        bg.pos = root.pos
        bg.size = root.size

    root.bind(pos=_sync, size=_sync)

    title = Label(
        text="ColorSight could not start",
        color=(0, 0, 0, 1),
        bold=True,
        size_hint_y=None,
        height=36,
        halign="left",
        valign="middle",
    )
    title.bind(size=lambda *_: setattr(title, "text_size", title.size))
    root.add_widget(title)

    scroll = ScrollView(size_hint=(1, 1))
    detail_lbl = Label(
        text=body,
        color=(0, 0, 0, 1),
        size_hint_y=None,
        halign="left",
        valign="top",
    )
    detail_lbl.bind(
        width=lambda *_: setattr(detail_lbl, "text_size", (detail_lbl.width, None)),
        texture_size=lambda *_: setattr(detail_lbl, "height", detail_lbl.texture_size[1]),
    )
    scroll.add_widget(detail_lbl)
    root.add_widget(scroll)

    row = BoxLayout(orientation="horizontal", size_hint_y=None, height=48, spacing=8)

    def _copy(_btn):
        try:
            Clipboard.copy(body)
            title.text = "ColorSight could not start — copied"
        except Exception:
            title.text = "ColorSight could not start — copy failed"

    def _reset(_btn):
        try:
            _reset_prefs_only()
            title.text = "Prefs reset — tap Try again"
        except Exception as e:
            title.text = f"Reset failed: {e}"

    def _retry(_btn):
        app = App.get_running_app()
        if app is None:
            return
        try:
            if hasattr(app, "rebuild_ui"):
                app.rebuild_ui(return_to="home")
            elif hasattr(app, "build"):
                new_root = app.build()
                app.root = new_root
        except Exception as e:
            title.text = f"Retry failed: {type(e).__name__}: {e}"
            detail_lbl.text = f"{type(e).__name__}: {e}\n\n{_safe_log_tail(15)}"

    for text, cb in (
        ("Copy details", _copy),
        ("Reset app data", _reset),
        ("Try again", _retry),
    ):
        btn = Button(text=text, size_hint_x=1)
        btn.bind(on_release=cb)
        row.add_widget(btn)
    root.add_widget(row)
    return root


def _safe_log_tail(n: int = 15) -> str:
    try:
        from colorsight.logging_setup import read_recent_lines

        return read_recent_lines(n)
    except Exception:
        pass
    for base in (Path.home() / ".colorsight",):
        path = base / "colorsight.log"
        try:
            if path.is_file():
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                return "\n".join(lines[-n:])
        except Exception:
            continue
    return "(no log yet)"


def _reset_prefs_only() -> None:
    """Delete prefs / saved theme only — keep correction profile."""
    from kivy.app import App

    app = App.get_running_app()
    if app is not None:
        base = Path(app.user_data_dir)
    else:
        base = Path.home() / ".colorsight"
    prefs = base / "prefs.json"
    if prefs.is_file():
        prefs.unlink()

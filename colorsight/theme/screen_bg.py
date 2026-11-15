"""Opaque full-size screen backgrounds (prevents black flash on transitions)."""

from __future__ import annotations

from kivy.graphics import Color, Rectangle
from kivy.uix.screenmanager import Screen

from colorsight.theme.tokens import Colors, NEUTRAL_BG


def install_opaque_bg(widget, *, neutral: bool = False):
    """Draw an opaque bg in canvas.before that tracks pos/size.

    neutral=True forces the accuracy-safe light cream (Vision Test / preview hosts).
    """
    with widget.canvas.before:
        widget._bg_color = Color(*(NEUTRAL_BG if neutral else Colors.bg))
        widget._bg_rect = Rectangle(pos=widget.pos, size=widget.size)

    def _sync(*_a):
        widget._bg_rect.pos = widget.pos
        widget._bg_rect.size = widget.size

    widget.bind(pos=_sync, size=_sync)
    _sync()

    def apply_theme():
        widget._bg_color.rgba = NEUTRAL_BG if neutral else Colors.bg

    widget.apply_theme = apply_theme  # type: ignore[attr-defined]
    return widget


class ThemedScreen(Screen):
    """Screen with opaque themed background (default)."""

    use_neutral_bg = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        install_opaque_bg(self, neutral=bool(self.use_neutral_bg))

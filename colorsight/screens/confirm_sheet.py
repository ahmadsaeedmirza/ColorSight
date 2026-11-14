"""Modal confirmation sheet — not named after Kivy Popup."""

from __future__ import annotations

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, RoundedRectangle

from colorsight.screens.photo_widgets import _invoke
from colorsight.theme.geometry import clamped_radii
from colorsight.theme.tokens import Colors, Fonts, Radii, Spacing
from colorsight.widgets import PrimaryButton


class ConfirmSheet(FloatLayout):
    """Dimmed overlay with title, message, Cancel / Confirm."""

    def __init__(
        self,
        title: str,
        message: str,
        *,
        confirm_text: str = "Confirm",
        cancel_text: str = "Cancel",
        confirm_cb=None,
        cancel_cb=None,
        danger: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.size_hint = (1, 1)
        self._confirm_cb = confirm_cb
        self._cancel_cb = cancel_cb

        with self.canvas.before:
            Color(0, 0, 0, 0.45)
            self._dim = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync, size=self._sync)

        card = BoxLayout(
            orientation="vertical",
            size_hint=(0.88, None),
            height=dp(220),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            padding=[dp(20), dp(18)],
            spacing=dp(12),
        )
        with card.canvas.before:
            Color(*Colors.surface)
            self._card_bg = RoundedRectangle(
                pos=card.pos,
                size=card.size,
                radius=clamped_radii(dp(Radii.card), 200, 200),
            )
        card.bind(
            pos=lambda *_: setattr(self._card_bg, "pos", card.pos)
            or setattr(
                self._card_bg,
                "radius",
                clamped_radii(dp(Radii.card), card.width, card.height),
            ),
            size=lambda *_: setattr(self._card_bg, "size", card.size)
            or setattr(
                self._card_bg,
                "radius",
                clamped_radii(dp(Radii.card), card.width, card.height),
            ),
        )

        t = Label(
            text=title,
            font_name=Fonts.bold,
            font_size=dp(18),
            color=Colors.text,
            size_hint_y=None,
            height=dp(28),
            halign="left",
        )
        t.bind(size=lambda *_: setattr(t, "text_size", t.size))
        card.add_widget(t)

        m = Label(
            text=message,
            font_name=Fonts.regular,
            font_size=dp(14),
            color=Colors.text_muted,
            size_hint_y=None,
            height=dp(72),
            halign="left",
            valign="top",
        )
        m.bind(size=lambda *_: setattr(m, "text_size", m.size))
        card.add_widget(m)

        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48), spacing=dp(10))
        cancel = PrimaryButton(text=cancel_text)
        cancel.bg_color = (1, 1, 1, 1)
        cancel.text_color = Colors.text
        cancel.on_press_cb = lambda *_: self._cancel()
        confirm = PrimaryButton(text=confirm_text)
        if danger:
            confirm.bg_color = (0.85, 0.25, 0.35, 1)
        confirm.on_press_cb = lambda *_: self._confirm()
        row.add_widget(cancel)
        row.add_widget(confirm)
        card.add_widget(row)
        self.add_widget(card)

    def _sync(self, *_a):
        self._dim.pos = self.pos
        self._dim.size = self.size

    def _confirm(self):
        parent = self.parent
        if parent is not None:
            parent.remove_widget(self)
        _invoke(self._confirm_cb)

    def _cancel(self):
        parent = self.parent
        if parent is not None:
            parent.remove_widget(self)
        _invoke(self._cancel_cb)

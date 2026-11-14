"""Pastel note-style feature card with accent dot."""

from kivy.metrics import dp
from kivy.properties import BooleanProperty, ObjectProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse

from colorsight.theme.tokens import Colors, Fonts, PASTEL_PALETTE, Radii, Spacing
from colorsight.widgets.rounded_card import RoundedCard


class _AccentDot(Widget):
    def __init__(self, rgba, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(10), dp(10))
        self._rgba = rgba
        self.bind(pos=self._draw, size=self._draw)
        self._draw()

    def _draw(self, *_args):
        self.canvas.clear()
        with self.canvas:
            Color(*self._rgba)
            Ellipse(pos=self.pos, size=self.size)


class PastelCard(ButtonBehavior, RoundedCard):
    title = StringProperty("")
    subtitle = StringProperty("")
    palette = StringProperty("yellow")
    show_dot = BooleanProperty(True)
    on_select = ObjectProperty(None, allownone=True)

    def __init__(self, title="", subtitle="", palette="yellow", **kwargs):
        fill, accent = PASTEL_PALETTE.get(palette, PASTEL_PALETTE["yellow"])
        kwargs.setdefault("card_color", fill)
        kwargs.setdefault("radius", Radii.card)
        kwargs.setdefault("padding", [dp(18), dp(18), dp(18), dp(18)])
        kwargs.setdefault("spacing", dp(Spacing.sm))
        super().__init__(**kwargs)
        self.title = title
        self.subtitle = subtitle
        self.palette = palette
        self._accent = accent

        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(18),
            spacing=dp(8),
        )
        if self.show_dot:
            header.add_widget(_AccentDot(accent))
            header.add_widget(Widget())  # spacer
        self.add_widget(header)

        self._title_lbl = Label(
            text=self.title,
            font_name=Fonts.bold,
            font_size=dp(17),
            color=Colors.text,
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(28),
            shorten=True,
            shorten_from="right",
        )
        self._title_lbl.bind(size=lambda *_: setattr(self._title_lbl, "text_size", self._title_lbl.size))
        self.add_widget(self._title_lbl)

        self._sub_lbl = Label(
            text=self.subtitle,
            font_name=Fonts.regular,
            font_size=dp(13),
            color=Colors.text_muted,
            halign="left",
            valign="top",
            size_hint_y=None,
            height=dp(36) if subtitle else 0,
            opacity=1 if subtitle else 0,
        )
        self._sub_lbl.bind(size=lambda *_: setattr(self._sub_lbl, "text_size", self._sub_lbl.size))
        self.add_widget(self._sub_lbl)

        self.bind(title=self._sync_text, subtitle=self._sync_text, palette=self._sync_palette)

    def _sync_text(self, *_args):
        self._title_lbl.text = self.title
        self._sub_lbl.text = self.subtitle
        self._sub_lbl.height = dp(36) if self.subtitle else 0
        self._sub_lbl.opacity = 1 if self.subtitle else 0

    def _sync_palette(self, *_args):
        fill, accent = PASTEL_PALETTE.get(self.palette, PASTEL_PALETTE["yellow"])
        self.card_color = fill
        self._accent = accent

    def on_release(self):
        if callable(self.on_select):
            self.on_select(self)

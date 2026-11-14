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
    auto_height = BooleanProperty(False)
    on_select = ObjectProperty(None, allownone=True)

    def __init__(self, title="", subtitle="", palette="yellow", auto_height=False, **kwargs):
        fill, accent = PASTEL_PALETTE.get(palette, PASTEL_PALETTE["yellow"])
        kwargs.setdefault("card_color", fill)
        kwargs.setdefault("radius", Radii.card)
        kwargs.setdefault("padding", [dp(18), dp(18), dp(18), dp(18)])
        kwargs.setdefault("spacing", dp(Spacing.sm))
        super().__init__(**kwargs)
        self.title = title
        self.subtitle = subtitle
        self.palette = palette
        self.auto_height = auto_height
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
        # Wrap to width; height follows texture (no clipping)
        self._sub_lbl.bind(
            width=self._reflow_subtitle,
            texture_size=self._reflow_subtitle,
        )
        self.add_widget(self._sub_lbl)

        self.bind(
            title=self._sync_text,
            subtitle=self._sync_text,
            palette=self._sync_palette,
            width=self._reflow_subtitle,
            auto_height=self._reflow_subtitle,
        )
        self._reflow_subtitle()

    def _reflow_subtitle(self, *_args):
        pad_x = (self.padding[0] + self.padding[2]) if self.padding else 0
        wrap_w = max(1, self.width - pad_x) if self.width > pad_x else max(1, self._sub_lbl.width)
        self._sub_lbl.text_size = (wrap_w, None)
        self._sub_lbl.texture_update()
        if self.subtitle:
            self._sub_lbl.height = max(dp(20), self._sub_lbl.texture_size[1] + dp(2))
            self._sub_lbl.opacity = 1
        else:
            self._sub_lbl.height = 0
            self._sub_lbl.opacity = 0
        if self.auto_height and self.size_hint_y is None:
            pad_y = (self.padding[1] + self.padding[3]) if self.padding else 0
            gaps = self.spacing * 2  # header–title, title–subtitle
            self.height = (
                pad_y
                + dp(18)
                + dp(28)
                + self._sub_lbl.height
                + gaps
            )

    def _sync_text(self, *_args):
        self._title_lbl.text = self.title
        self._sub_lbl.text = self.subtitle
        self._reflow_subtitle()

    def _sync_palette(self, *_args):
        fill, accent = PASTEL_PALETTE.get(self.palette, PASTEL_PALETTE["yellow"])
        self.card_color = fill
        self._accent = accent

    def on_release(self):
        if callable(self.on_select):
            self.on_select(self)

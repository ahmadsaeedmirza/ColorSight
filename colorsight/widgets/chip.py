"""Pill filter chips and a horizontally scrollable chip row."""

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import BooleanProperty, ListProperty, ObjectProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Line, RoundedRectangle

from colorsight.theme.geometry import clamped_radii
from colorsight.theme.tokens import Colors, Fonts, Radii, Spacing

# Horizontal padding inside each chip (each side)
_CHIP_PAD_X = 18


class Chip(ButtonBehavior, BoxLayout):
    """Single-line pill that grows to fit its label (no wrap / clip)."""

    text = StringProperty("")
    selected = BooleanProperty(False)
    select_cb = ObjectProperty(None, allownone=True)

    def __init__(self, text="", selected=False, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.selected = selected
        self.size_hint = (None, None)
        self.height = dp(36)
        self.padding = [dp(_CHIP_PAD_X), 0, dp(_CHIP_PAD_X), 0]
        self.spacing = 0

        # Do NOT bind text_size to widget size — that forces wrapping.
        self._label = Label(
            text=text,
            font_name=Fonts.medium,
            font_size=dp(13),
            color=Colors.chip_text,
            halign="center",
            valign="middle",
            size_hint=(None, None),
            shorten=False,
        )
        self.add_widget(self._label)

        self.bind(
            pos=self._redraw,
            size=self._redraw,
            selected=self._on_selected,
            text=self._on_text,
        )
        self._on_selected()
        Clock.schedule_once(lambda dt: self._fit_width(), 0)
        self._redraw()

    def _on_text(self, *_args):
        self._label.text = self.text
        self._fit_width()

    def _fit_width(self, *_args):
        self._label.text_size = (None, None)
        self._label.texture_update()
        tw, th = self._label.texture_size
        if tw <= 0:
            tw = max(dp(24), len(self.text) * dp(7))
        if th <= 0:
            th = dp(18)
        self._label.size = (tw, th)
        self.width = max(dp(52), tw + dp(_CHIP_PAD_X) * 2)
        # Vertically center the label inside the chip
        self._label.center_y = self.center_y
        self._label.x = self.x + dp(_CHIP_PAD_X)
        self._redraw()

    def _on_selected(self, *_args):
        if self.selected:
            self._label.color = list(Colors.chip_selected_text)
            self._label.font_name = Fonts.semibold
        else:
            self._label.color = list(Colors.chip_text)
            self._label.font_name = Fonts.medium
        self._fit_width()

    def _redraw(self, *_args):
        self.canvas.before.clear()
        radii = clamped_radii(dp(Radii.chip), self.width, self.height)
        with self.canvas.before:
            if self.selected:
                Color(*Colors.chip_selected_bg)
            else:
                Color(*Colors.chip_bg)
            RoundedRectangle(pos=self.pos, size=self.size, radius=radii)
            if not self.selected:
                Color(*Colors.chip_border)
                Line(
                    rounded_rectangle=(
                        self.x + 0.5,
                        self.y + 0.5,
                        self.width - 1,
                        self.height - 1,
                        radii[0],
                    ),
                    width=1,
                )
        # Keep label centered after layout moves
        if self._label.texture_size[0] > 0:
            self._label.size = self._label.texture_size
        self._label.center_y = self.center_y
        self._label.x = self.x + dp(_CHIP_PAD_X)
        self._label.color = (
            list(Colors.chip_selected_text)
            if self.selected
            else list(Colors.chip_text)
        )

    def on_release(self):
        if callable(self.select_cb):
            self.select_cb(self)


class ChipRow(BoxLayout):
    """Horizontal chip strip inside a scrollbar-free ScrollView for narrow screens."""

    options = ListProperty([])
    selected = StringProperty("")
    change_cb = ObjectProperty(None, allownone=True)

    def __init__(self, options=None, selected="", **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(40)
        self.padding = 0
        self.spacing = 0
        self.options = options or []
        self.selected = selected or (self.options[0] if self.options else "")

        self._scroll = ScrollView(
            do_scroll_x=True,
            do_scroll_y=False,
            bar_width=0,
            size_hint=(1, 1),
            scroll_type=["content"],
        )
        self._row = BoxLayout(
            orientation="horizontal",
            size_hint=(None, 1),
            spacing=dp(Spacing.sm),
            padding=[0, 0, 0, 0],
        )
        self._row.bind(minimum_width=self._row.setter("width"))
        self._scroll.add_widget(self._row)
        self.add_widget(self._scroll)

        self.bind(options=self._rebuild)
        self._rebuild()

    def _rebuild(self, *_args):
        self._row.clear_widgets()
        for opt in self.options:
            chip = Chip(text=opt, selected=(opt == self.selected))
            chip.select_cb = self._pick
            self._row.add_widget(chip)
        Clock.schedule_once(lambda dt: self._row.width, 0)

    def _pick(self, chip: Chip):
        self.selected = chip.text
        for child in self._row.children:
            if isinstance(child, Chip):
                child.selected = child.text == self.selected
        if callable(self.change_cb):
            self.change_cb(self.selected)

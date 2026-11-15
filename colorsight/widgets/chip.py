"""Pill filter chips and a horizontally scrollable chip row."""

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import BooleanProperty, ListProperty, ObjectProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, Line, RoundedRectangle

from colorsight.theme.geometry import clamped_radii
from colorsight.theme.tokens import Colors, Fonts, Radii, Spacing

_CHIP_PAD_X = 18  # → width = label + 36 dp
_CHIP_H = 40


class Chip(ButtonBehavior, FloatLayout):
    """Fixed-height single-line pill; label centered both ways."""

    text = StringProperty("")
    selected = BooleanProperty(False)
    select_cb = ObjectProperty(None, allownone=True)

    def __init__(self, text="", selected=False, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.selected = selected
        self.size_hint = (None, None)
        self.height = dp(_CHIP_H)

        self._label = Label(
            text=text,
            font_name=Fonts.medium,
            font_size=dp(13),
            color=Colors.chip_text,
            halign="center",
            valign="middle",
            size_hint=(None, None),
            shorten=False,
            max_lines=1,
        )
        self.add_widget(self._label)

        self.bind(
            pos=self._layout,
            size=self._layout,
            selected=self._on_selected,
            text=self._on_text,
        )
        self._on_selected()
        Clock.schedule_once(lambda dt: self._fit(), 0)

    def _on_text(self, *_args):
        self._label.text = self.text
        self._fit()

    def _fit(self, *_args):
        self._label.text_size = (None, None)
        self._label.texture_update()
        tw = self._label.texture_size[0] or max(dp(24), len(self.text) * dp(7))
        self.width = max(dp(52), tw + dp(_CHIP_PAD_X) * 2)
        self.height = dp(_CHIP_H)
        self._layout()

    def _on_selected(self, *_args):
        self._label.font_name = Fonts.semibold if self.selected else Fonts.medium
        self._fit()

    def _layout(self, *_args):
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
        # Center via text_size = chip size (halign/valign middle)
        self._label.size = self.size
        self._label.pos = self.pos
        self._label.text_size = self.size
        self._label.halign = "center"
        self._label.valign = "middle"
        self._label.color = (
            list(Colors.chip_selected_text)
            if self.selected
            else list(Colors.chip_text)
        )

    def apply_theme(self):
        self._layout()

    def on_release(self):
        if callable(self.select_cb):
            self.select_cb(self)


class ChipRow(BoxLayout):
    """Horizontal chip strip in a scrollbar-free ScrollView (scrolls to the edge)."""

    options = ListProperty([])
    selected = StringProperty("")
    change_cb = ObjectProperty(None, allownone=True)

    def __init__(self, options=None, selected="", **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(_CHIP_H)
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
            effect_cls="ScrollEffect",
        )
        self._row = BoxLayout(
            orientation="horizontal",
            size_hint=(None, 1),
            spacing=dp(Spacing.sm),
            padding=[0, 0, dp(Spacing.screen_x), 0],  # room past the right margin
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

    def _pick(self, chip: Chip):
        self.selected = chip.text
        for child in self._row.children:
            if isinstance(child, Chip):
                child.selected = child.text == self.selected
        if callable(self.change_cb):
            self.change_cb(self.selected)

    def reset_scroll(self):
        """Show the first chips (All / Test) — call on Home enter / theme rebuild."""
        self._scroll.scroll_x = 0

    def apply_theme(self):
        for child in self._row.children:
            if isinstance(child, Chip):
                child.apply_theme()
        self.reset_scroll()

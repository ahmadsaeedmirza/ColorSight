"""Pill filter chips and a horizontal chip row."""

from kivy.metrics import dp
from kivy.properties import BooleanProperty, ListProperty, ObjectProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Line, RoundedRectangle

from colorsight.theme.geometry import clamped_radii
from colorsight.theme.tokens import Colors, Fonts, Radii, Spacing


class Chip(ButtonBehavior, BoxLayout):
    text = StringProperty("")
    selected = BooleanProperty(False)
    on_select = ObjectProperty(None, allownone=True)

    def __init__(self, text="", selected=False, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.selected = selected
        self.size_hint = (None, None)
        self.height = dp(36)
        self.padding = [dp(14), 0, dp(14), 0]
        self.spacing = 0

        self._label = Label(
            text=text,
            font_name=Fonts.medium,
            font_size=dp(13),
            color=Colors.chip_text,
            halign="center",
            valign="middle",
            size_hint=(1, 1),
        )
        self._label.bind(
            size=lambda *_: setattr(self._label, "text_size", self._label.size),
            texture_size=self._fit_width,
        )
        self.add_widget(self._label)

        self.bind(
            pos=self._redraw,
            size=self._redraw,
            selected=self._on_selected,
            text=self._on_text,
        )
        self._on_selected()
        self._fit_width()
        self._redraw()

    def _on_text(self, *_args):
        self._label.text = self.text
        self._fit_width()

    def _fit_width(self, *_args):
        # Measure with the active font so selected/unselected widths stay honest.
        tw = self._label.texture_size[0]
        if tw <= 0:
            tw = len(self.text) * dp(8)
        self.width = max(dp(52), tw + dp(28))

    def _on_selected(self, *_args):
        if self.selected:
            self._label.color = list(Colors.chip_selected_text)
            self._label.font_name = Fonts.semibold
        else:
            self._label.color = list(Colors.chip_text)
            self._label.font_name = Fonts.medium
        self._label.halign = "center"
        self._label.valign = "middle"
        self._label.text_size = self._label.size
        self._fit_width()
        self._redraw()

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
        # Keep label text_size in sync for vertical centering
        self._label.text_size = self._label.size
        self._label.color = (
            list(Colors.chip_selected_text)
            if self.selected
            else list(Colors.chip_text)
        )

    def on_release(self):
        if callable(self.on_select):
            self.on_select(self)


class ChipRow(BoxLayout):
    options = ListProperty([])
    selected = StringProperty("")
    on_change = ObjectProperty(None, allownone=True)

    def __init__(self, options=None, selected="", **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(40)
        self.spacing = dp(Spacing.sm)
        self.options = options or []
        self.selected = selected or (self.options[0] if self.options else "")
        self.bind(options=self._rebuild)
        self._rebuild()

    def _rebuild(self, *_args):
        self.clear_widgets()
        for opt in self.options:
            chip = Chip(text=opt, selected=(opt == self.selected))
            chip.on_select = self._pick
            self.add_widget(chip)

    def _pick(self, chip: Chip):
        self.selected = chip.text
        for child in self.children:
            if isinstance(child, Chip):
                child.selected = child.text == self.selected
        if callable(self.on_change):
            self.on_change(self.selected)

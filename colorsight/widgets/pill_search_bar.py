"""Pill-shaped search bar."""

from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, RoundedRectangle

from colorsight.theme.geometry import clamped_radii
from colorsight.theme.tokens import Colors, Fonts, Icons, Radii, Spacing
from colorsight.widgets.icon import Icon


class PillSearchBar(BoxLayout):
    hint = StringProperty("Search")
    text = StringProperty("")

    def __init__(self, hint="Search", **kwargs):
        super().__init__(**kwargs)
        self.hint = hint
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(48)
        self.padding = [dp(14), dp(6)]
        self.spacing = dp(Spacing.sm)

        self._icon = Icon(
            icon=Icons.search,
            icon_size=20,
            color=Colors.text_muted,
            size_hint=(None, None),
            size=(dp(24), dp(24)),
        )
        self._icon.pos_hint = {"center_y": 0.5}
        self.add_widget(self._icon)

        self._input = TextInput(
            text="",
            hint_text=self.hint,
            font_name=Fonts.regular,
            font_size=dp(15),
            foreground_color=Colors.text,
            hint_text_color=Colors.text_muted,
            background_color=(0, 0, 0, 0),
            cursor_color=Colors.accent_blue,
            multiline=False,
            padding=[0, dp(10), 0, 0],
        )
        self._input.bind(text=lambda *_: setattr(self, "text", self._input.text))
        self.add_widget(self._input)

        self.bind(pos=self._redraw, size=self._redraw, hint=self._on_hint)
        self._redraw()

    def _on_hint(self, *_args):
        self._input.hint_text = self.hint

    def _redraw(self, *_args):
        self.canvas.before.clear()
        radii = clamped_radii(dp(Radii.search), self.width, self.height)
        with self.canvas.before:
            Color(*Colors.shadow)
            RoundedRectangle(
                pos=(self.x, self.y - dp(2)),
                size=self.size,
                radius=radii,
            )
            Color(*Colors.surface)
            RoundedRectangle(pos=self.pos, size=self.size, radius=radii)

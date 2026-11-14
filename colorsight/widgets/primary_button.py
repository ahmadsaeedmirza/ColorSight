"""Primary CTA and round icon buttons."""

from kivy.animation import Animation
from kivy.metrics import dp
from kivy.properties import ColorProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Ellipse, RoundedRectangle

from colorsight.theme.tokens import Colors, Fonts, Radii


class PrimaryButton(ButtonBehavior, BoxLayout):
    text = StringProperty("Continue")
    bg_color = ColorProperty(Colors.accent_dark)
    text_color = ColorProperty((1, 1, 1, 1))
    radius = NumericProperty(Radii.button)
    on_press_cb = ObjectProperty(None, allownone=True)

    def __init__(self, text="Continue", **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.size_hint_y = None
        self.height = dp(52)
        self.padding = [dp(20), dp(12)]

        self._label = Label(
            text=self.text,
            font_name=Fonts.semibold,
            font_size=dp(16),
            color=self.text_color,
        )
        self.add_widget(self._label)
        self.bind(
            pos=self._redraw,
            size=self._redraw,
            bg_color=self._redraw,
            text=lambda *_: setattr(self._label, "text", self.text),
            text_color=lambda *_: setattr(self._label, "color", self.text_color),
        )
        self._redraw()

    def _redraw(self, *_args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*Colors.shadow)
            RoundedRectangle(
                pos=(self.x, self.y - dp(2)),
                size=self.size,
                radius=[dp(self.radius)],
            )
            Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(self.radius)])

    def on_press(self):
        Animation.cancel_all(self)
        Animation(opacity=0.85, d=0.08).start(self)

    def on_release(self):
        Animation.cancel_all(self)
        Animation(opacity=1, d=0.12).start(self)
        if callable(self.on_press_cb):
            self.on_press_cb(self)


class RoundIconButton(ButtonBehavior, BoxLayout):
    icon = StringProperty("→")
    bg_color = ColorProperty(Colors.accent_dark)
    icon_color = ColorProperty((1, 1, 1, 1))
    diameter = NumericProperty(56)
    on_press_cb = ObjectProperty(None, allownone=True)

    def __init__(self, icon="→", **kwargs):
        super().__init__(**kwargs)
        self.icon = icon
        self.size_hint = (None, None)
        d = dp(self.diameter)
        self.size = (d, d)

        self._label = Label(
            text=self.icon,
            font_name=Fonts.bold,
            font_size=dp(22),
            color=self.icon_color,
        )
        self.add_widget(self._label)
        self.bind(
            pos=self._redraw,
            size=self._redraw,
            bg_color=self._redraw,
            diameter=self._on_diameter,
            icon=lambda *_: setattr(self._label, "text", self.icon),
        )
        self._redraw()

    def _on_diameter(self, *_args):
        d = dp(self.diameter)
        self.size = (d, d)
        self._redraw()

    def _redraw(self, *_args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*Colors.shadow)
            Ellipse(pos=(self.x, self.y - dp(2)), size=self.size)
            Color(*self.bg_color)
            Ellipse(pos=self.pos, size=self.size)

    def on_press(self):
        Animation.cancel_all(self)
        Animation(opacity=0.85, d=0.08).start(self)

    def on_release(self):
        Animation.cancel_all(self)
        Animation(opacity=1, d=0.12).start(self)
        if callable(self.on_press_cb):
            self.on_press_cb(self)

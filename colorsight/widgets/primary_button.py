"""Primary CTA and round icon buttons."""

from kivy.animation import Animation
from kivy.metrics import dp
from kivy.properties import ColorProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, Ellipse, RoundedRectangle

from colorsight.theme.geometry import clamped_radii
from colorsight.theme.tokens import Colors, Fonts, Icons, Radii
from colorsight.widgets.icon import Icon


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
        self.padding = [dp(16), dp(12), dp(16), dp(12)]

        self._label = Label(
            text=self.text,
            font_name=Fonts.semibold,
            font_size=dp(15),
            color=self.text_color,
            halign="center",
            valign="middle",
            size_hint=(1, 1),
        )
        self.add_widget(self._label)
        self.bind(
            pos=self._redraw,
            size=self._fit_and_redraw,
            bg_color=self._redraw,
            text=self._on_text,
            text_color=lambda *_: setattr(self._label, "color", self.text_color),
        )
        self._fit_and_redraw()

    def _on_text(self, *_args):
        self._label.text = self.text
        self._fit_and_redraw()

    def _fit_and_redraw(self, *_args):
        """Keep label inside the button: wrap to width; grow height if needed."""
        pad_x = (self.padding[0] + self.padding[2]) if self.padding else 0
        pad_y = (self.padding[1] + self.padding[3]) if self.padding else 0
        wrap_w = max(1, self.width - pad_x) if self.width > pad_x else 1
        self._label.text_size = (wrap_w, None)
        self._label.texture_update()
        th = max(dp(18), self._label.texture_size[1])
        # Prefer single-line look; if wrap needs more room, grow the button
        self.height = max(dp(52), th + pad_y)
        self._redraw()

    def _redraw(self, *_args):
        self.canvas.before.clear()
        radii = clamped_radii(dp(self.radius), self.width, self.height)
        with self.canvas.before:
            Color(*Colors.shadow)
            RoundedRectangle(
                pos=(self.x, self.y - dp(2)),
                size=self.size,
                radius=radii,
            )
            Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=radii)
        # Keep label vertically centered in the button
        self._label.halign = "center"
        self._label.valign = "middle"
        self._label.color = self.text_color

    def apply_theme(self):
        self._fit_and_redraw()

    def on_press(self):
        Animation.cancel_all(self)
        Animation(opacity=0.85, d=0.08).start(self)

    def on_release(self):
        Animation.cancel_all(self)
        Animation(opacity=1, d=0.12).start(self)
        if callable(self.on_press_cb):
            self.on_press_cb(self)


class RoundIconButton(ButtonBehavior, BoxLayout):
    """Circular button that shows a Material Icon ligature."""

    icon = StringProperty(Icons.arrow_forward)
    bg_color = ColorProperty(Colors.accent_dark)
    icon_color = ColorProperty((1, 1, 1, 1))
    diameter = NumericProperty(56)
    on_press_cb = ObjectProperty(None, allownone=True)

    def __init__(self, icon=Icons.arrow_forward, **kwargs):
        super().__init__(**kwargs)
        self.icon = icon
        self.size_hint = (None, None)
        d = dp(self.diameter)
        self.size = (d, d)
        self.padding = 0

        self._icon = Icon(
            icon=self.icon,
            icon_size=max(18, int(self.diameter * 0.42)),
            color=self.icon_color,
            size_hint=(1, 1),
        )
        self.add_widget(self._icon)
        self.bind(
            pos=self._redraw,
            size=self._redraw,
            bg_color=self._redraw,
            diameter=self._on_diameter,
            icon=self._on_icon,
            icon_color=self._on_icon_color,
        )
        self._redraw()

    def _on_icon(self, *_args):
        self._icon.icon = self.icon

    def _on_icon_color(self, *_args):
        self._icon.color = self.icon_color

    def _on_diameter(self, *_args):
        d = dp(self.diameter)
        self.size = (d, d)
        self._icon.icon_size = max(18, int(self.diameter * 0.42))
        self._redraw()

    def _redraw(self, *_args):
        self.canvas.before.clear()
        # Equal width/height keeps Ellipse circular; clamp for consistency if stretched
        side = min(self.width, self.height)
        with self.canvas.before:
            Color(*Colors.shadow)
            Ellipse(
                pos=(self.center_x - side / 2, self.center_y - side / 2 - dp(2)),
                size=(side, side),
            )
            Color(*self.bg_color)
            Ellipse(
                pos=(self.center_x - side / 2, self.center_y - side / 2),
                size=(side, side),
            )

    def on_press(self):
        Animation.cancel_all(self)
        Animation(opacity=0.85, d=0.08).start(self)

    def on_release(self):
        Animation.cancel_all(self)
        Animation(opacity=1, d=0.12).start(self)
        if callable(self.on_press_cb):
            self.on_press_cb(self)

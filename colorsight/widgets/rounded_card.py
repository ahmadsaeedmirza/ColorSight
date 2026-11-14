"""Base rounded card with soft shadow."""

from kivy.animation import Animation
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import BooleanProperty, ColorProperty, ListProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout

from colorsight.theme.geometry import clamped_radii
from colorsight.theme.tokens import Colors, Radii


class RoundedCard(BoxLayout):
    card_color = ColorProperty(Colors.surface)
    shadow_color = ColorProperty(Colors.shadow)
    radius = NumericProperty(Radii.card)
    shadow_offset = ListProperty([0, -2])
    interactive = BooleanProperty(True)
    press_scale = NumericProperty(0.97)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = kwargs.get("orientation", "vertical")
        self.padding = kwargs.get("padding", [dp(16), dp(16), dp(16), dp(16)])
        self.spacing = kwargs.get("spacing", dp(8))
        self.size_hint_y = kwargs.get("size_hint_y", None)
        self.bind(
            pos=self._redraw,
            size=self._redraw,
            card_color=self._redraw,
            radius=self._redraw,
        )
        self._redraw()

    def _redraw(self, *_args):
        self.canvas.before.clear()
        radii = clamped_radii(dp(self.radius), self.width, self.height)
        with self.canvas.before:
            Color(*self.shadow_color)
            RoundedRectangle(
                pos=(
                    self.x + dp(self.shadow_offset[0]),
                    self.y + dp(self.shadow_offset[1]) - dp(2),
                ),
                size=(self.width, self.height),
                radius=radii,
            )
            Color(*self.card_color)
            RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=radii,
            )

    def on_touch_down(self, touch):
        if self.interactive and self.collide_point(*touch.pos):
            Animation.cancel_all(self)
            Animation(opacity=0.92, d=0.08, t="out_quad").start(self)
            touch.ud["rounded_card"] = self
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if touch.ud.get("rounded_card") is self:
            Animation.cancel_all(self)
            Animation(opacity=1, d=0.12, t="out_quad").start(self)
        return super().on_touch_up(touch)

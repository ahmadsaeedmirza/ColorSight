"""Widgets for the Photos (image correction) screen — avoid Kivy builtin names."""

from __future__ import annotations

import numpy as np
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, RoundedRectangle
from kivy.graphics.texture import Texture
from kivy.metrics import dp
from kivy.properties import NumericProperty, ObjectProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.scatter import Scatter
from kivy.uix.widget import Widget
from kivy.uix.image import Image as KivyImage

from colorsight.image_pipeline import before_after_split
from colorsight.theme.geometry import clamped_radii
from colorsight.theme.tokens import Colors, Fonts, Icons, Radii
from colorsight.widgets import Icon


def rgb_to_texture(rgb: np.ndarray, existing: Texture | None = None) -> Texture:
    """HxWx3 RGB uint8 → Kivy texture (reuses ``existing`` when size matches)."""
    arr = np.ascontiguousarray(rgb[::-1], dtype=np.uint8)
    h, w = arr.shape[:2]
    if existing is not None and tuple(existing.size) == (w, h):
        tex = existing
    else:
        tex = Texture.create(size=(w, h), colorfmt="rgb")
        tex.mag_filter = "linear"
        tex.min_filter = "linear"
    tex.blit_buffer(arr.tobytes(), colorfmt="rgb", bufferfmt="ubyte")
    return tex


class LoadingShimmer(Widget):
    """Small animated shimmer bar while previews process."""

    phase = NumericProperty(0.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(6)
        self._anim = None
        self.opacity = 0
        self.bind(pos=self._draw, size=self._draw, phase=self._draw)

    def start(self):
        self.opacity = 1
        Animation.cancel_all(self)
        self._anim = Animation(phase=1.0, d=0.9) + Animation(phase=0.0, d=0.9)
        self._anim.repeat = True
        self._anim.start(self)
        self._draw()

    def stop(self):
        Animation.cancel_all(self)
        self.opacity = 0
        self._draw()

    def _draw(self, *_a):
        self.canvas.clear()
        if self.opacity <= 0:
            return
        with self.canvas:
            Color(0.90, 0.88, 0.86, 1)
            RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=clamped_radii(dp(4), self.width, self.height),
            )
            Color(0.75, 0.78, 0.90, 0.85)
            w = max(dp(40), self.width * 0.35)
            x = self.x + (self.width - w) * float(self.phase)
            RoundedRectangle(
                pos=(x, self.y),
                size=(w, self.height),
                radius=clamped_radii(dp(4), w, self.height),
            )


class PreviewSeverityBar(Widget):
    """Preview-only severity control (not a Kivy Slider; does not persist profile)."""

    value = NumericProperty(0.5)
    on_change = ObjectProperty(None, allownone=True)

    def __init__(self, value=0.5, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(44)
        self.value = float(np.clip(value, 0.0, 1.0))
        self._dragging = False
        self.bind(pos=self._draw, size=self._draw, value=self._draw)
        self._draw()

    def _track_y(self):
        return self.center_y

    def _knob_x(self):
        pad = dp(12)
        usable = max(1.0, self.width - pad * 2)
        return self.x + pad + self.value * usable

    def _draw(self, *_a):
        self.canvas.clear()
        pad = dp(12)
        track_h = dp(6)
        y = self.center_y - track_h / 2
        with self.canvas:
            Color(0.88, 0.86, 0.84, 1)
            RoundedRectangle(
                pos=(self.x + pad, y),
                size=(max(0, self.width - pad * 2), track_h),
                radius=clamped_radii(dp(3), self.width, track_h),
            )
            fill_w = max(0.0, self._knob_x() - (self.x + pad))
            Color(*Colors.accent_blue)
            RoundedRectangle(
                pos=(self.x + pad, y),
                size=(fill_w, track_h),
                radius=clamped_radii(dp(3), fill_w, track_h),
            )
            kx = self._knob_x()
            r = dp(11)
            Color(*Colors.shadow)
            Ellipse(pos=(kx - r, self.center_y - r - dp(1)), size=(r * 2, r * 2))
            Color(1, 1, 1, 1)
            Ellipse(pos=(kx - r, self.center_y - r), size=(r * 2, r * 2))
            Color(*Colors.accent_blue)
            Ellipse(pos=(kx - dp(5), self.center_y - dp(5)), size=(dp(10), dp(10)))

    def _set_from_x(self, x):
        pad = dp(12)
        usable = max(1.0, self.width - pad * 2)
        v = float(np.clip((x - self.x - pad) / usable, 0.0, 1.0))
        if abs(v - self.value) > 1e-4:
            self.value = v
            if callable(self.on_change):
                self.on_change(v)

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos):
            return False
        touch.grab(self)
        self._dragging = True
        self._set_from_x(touch.x)
        return True

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return False
        self._set_from_x(touch.x)
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return False
        touch.ungrab(self)
        self._dragging = False
        return True


class _ModeChip(ButtonBehavior, Label):
    def __init__(self, key: str, text: str, active: bool, on_tap, **kwargs):
        super().__init__(**kwargs)
        self.key = key
        self._on_tap = on_tap
        self.text = text
        self.font_name = Fonts.semibold if active else Fonts.medium
        self.font_size = dp(12)
        self.color = (1, 1, 1, 1) if active else (0.72, 0.72, 0.72, 1)
        self.halign = "center"
        self.valign = "middle"
        self.size_hint = (1, 1)
        self._active = active
        self.bind(size=lambda *_: setattr(self, "text_size", self.size))

    def set_active(self, active: bool):
        self._active = active
        self.font_name = Fonts.semibold if active else Fonts.medium
        self.color = (1, 1, 1, 1) if active else (0.72, 0.72, 0.72, 1)

    def on_release(self):
        if callable(self._on_tap):
            self._on_tap(self.key)


class PhotoModeToolbar(BoxLayout):
    """Floating dark pill: Original | Corrected | Simulation + Save."""

    mode = StringProperty("corrected")
    on_mode = ObjectProperty(None, allownone=True)
    on_save = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(52)
        self.padding = [dp(8), dp(6), dp(8), dp(6)]
        self.spacing = dp(4)
        self._chips = {}
        for key, label in (
            ("original", "Original"),
            ("corrected", "Corrected"),
            ("simulation", "Simulation"),
        ):
            chip = _ModeChip(key, label, active=(key == self.mode), on_tap=self._tap_mode)
            self._chips[key] = chip
            self.add_widget(chip)

        class _SaveHit(ButtonBehavior, BoxLayout):
            pass

        hit = _SaveHit(size_hint=(None, 1), width=dp(44), padding=[dp(4), dp(4)])
        hit.add_widget(
            Icon(icon=Icons.save, icon_size=22, color=(1, 1, 1, 1), size_hint=(1, 1))
        )
        hit.bind(on_release=lambda *_: self._do_save())
        self.add_widget(hit)
        self.bind(pos=self._draw, size=self._draw, mode=self._sync_mode)
        self._draw()

    def _do_save(self):
        if callable(self.on_save):
            self.on_save()

    def _tap_mode(self, key: str):
        self.mode = key
        if callable(self.on_mode):
            self.on_mode(key)

    def _sync_mode(self, *_a):
        for k, chip in self._chips.items():
            chip.set_active(k == self.mode)

    def _draw(self, *_a):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*Colors.shadow)
            RoundedRectangle(
                pos=(self.x, self.y - dp(2)),
                size=self.size,
                radius=clamped_radii(dp(Radii.chip), self.width, self.height),
            )
            Color(*Colors.nav_bg)
            RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=clamped_radii(dp(Radii.chip), self.width, self.height),
            )


class BeforeAfterViewer(FloatLayout):
    """Pinch-zoom / pan photo stage with optional before/after divider."""

    split = NumericProperty(0.5)
    on_split = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._orig = None
        self._right = None
        self._mode = "corrected"
        self._tex = None
        self._dragging_handle = False

        self._scatter = Scatter(
            do_rotation=False,
            do_translation=True,
            do_scale=True,
            scale_min=1.0,
            scale_max=4.0,
            size_hint=(None, None),
        )
        self._photo = KivyImage(fit_mode="contain", size_hint=(None, None))
        self._scatter.add_widget(self._photo)
        self.add_widget(self._scatter)

        self._handle = Widget(size_hint=(None, None), size=(dp(36), dp(36)))
        self._handle_icon = Icon(
            icon=Icons.drag_handle,
            icon_size=18,
            color=Colors.text_muted,
            size_hint=(None, None),
            size=(dp(36), dp(36)),
        )
        self._handle.add_widget(self._handle_icon)
        self.add_widget(self._handle)
        self._handle.opacity = 0

        self.bind(pos=self._layout, size=self._layout, split=self._on_split_prop)
        Clock.schedule_once(lambda dt: self._layout(), 0)

    def set_images(self, original: np.ndarray | None, right: np.ndarray | None, mode: str):
        self._orig = original
        self._right = right
        self._mode = mode
        self._handle.opacity = 1 if mode == "corrected" and original is not None and right is not None else 0
        self._refresh_display()
        self._layout()

    def clear(self):
        self._orig = None
        self._right = None
        self._photo.texture = None
        self._handle.opacity = 0

    def _on_split_prop(self, *_a):
        self._refresh_display()
        self._place_handle()
        if callable(self.on_split):
            self.on_split(self.split)

    def _compose(self) -> np.ndarray | None:
        if self._orig is None:
            return None
        if self._mode == "original" or self._right is None:
            return self._orig
        if self._mode == "simulation":
            return self._right
        # corrected → before/after split
        return before_after_split(self._orig, self._right, self.split)

    def _refresh_display(self):
        rgb = self._compose()
        if rgb is None:
            return
        self._tex = rgb_to_texture(rgb, existing=self._tex)
        self._photo.texture = self._tex
        h, w = rgb.shape[:2]
        self._photo.size = (w, h)
        self._scatter.size = (w, h)

    def _fit_scatter(self):
        if self._photo.texture is None or self.width <= 1 or self.height <= 1:
            return
        tw, th = self._photo.texture.size
        if tw <= 0 or th <= 0:
            return
        scale = min(self.width / tw, self.height / th)
        self._scatter.scale = max(scale, 0.05)
        self._scatter.scale_min = self._scatter.scale
        bw, bh = tw * self._scatter.scale, th * self._scatter.scale
        self._scatter.pos = (
            self.x + (self.width - bw) / 2,
            self.y + (self.height - bh) / 2,
        )

    def _layout(self, *_a):
        self._fit_scatter()
        self._place_handle()

    def _place_handle(self):
        if self._handle.opacity <= 0 or self._photo.texture is None:
            return
        # Handle along viewer vertical center at split fraction of scatter width
        sx, sy = self._scatter.pos
        sw = self._photo.width * self._scatter.scale
        sh = self._photo.height * self._scatter.scale
        hx = sx + self.split * sw
        hy = sy + sh / 2
        self._handle.center = (hx, hy)
        self._handle_icon.pos = self._handle.pos
        self._draw_divider(sx, sy, sw, sh)

    def _draw_divider(self, sx, sy, sw, sh):
        self.canvas.after.clear()
        if self._handle.opacity <= 0:
            return
        x = sx + self.split * sw
        with self.canvas.after:
            Color(1, 1, 1, 0.85)
            Line(points=[x, sy, x, sy + sh], width=1.2)
            Color(*Colors.shadow)
            Ellipse(
                pos=(self._handle.center_x - dp(18), self._handle.center_y - dp(18) - dp(1)),
                size=(dp(36), dp(36)),
            )
            Color(1, 1, 1, 1)
            Ellipse(
                pos=(self._handle.center_x - dp(17), self._handle.center_y - dp(17)),
                size=(dp(34), dp(34)),
            )

    def on_touch_down(self, touch):
        if self._handle.opacity > 0 and self._handle.collide_point(*touch.pos):
            touch.grab(self)
            self._dragging_handle = True
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self and self._dragging_handle:
            sw = max(1.0, self._photo.width * self._scatter.scale)
            sx = self._scatter.x
            self.split = float(np.clip((touch.x - sx) / sw, 0.02, 0.98))
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            touch.ungrab(self)
            self._dragging_handle = False
            return True
        return super().on_touch_up(touch)

"""Shared Camera / Lens widgets — avoid Kivy builtin names; use *_cb callbacks."""

from __future__ import annotations

import logging
import time

import numpy as np
from kivy.graphics import (
    Color,
    Ellipse,
    Line,
    Rectangle,
    RoundedRectangle,
    StencilPop,
    StencilPush,
    StencilUnUse,
    StencilUse,
)
from kivy.graphics.texture import Texture
from kivy.metrics import dp
from kivy.properties import BooleanProperty, NumericProperty, ObjectProperty, StringProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.image import Image as KivyImage

from colorsight.camera_gpu import identity_matrix
from colorsight.camera_pipeline import DEFAULT_ZOOM, LOUPE_DIAMETER_DP
from colorsight.screens.photo_widgets import _invoke, rgb_to_texture
from colorsight.theme.geometry import clamped_radii
from colorsight.theme.tokens import Colors, Fonts, Icons, NEUTRAL_SURFACE, NEUTRAL_TEXT, Radii
from colorsight.widgets import Icon

log = logging.getLogger("colorsight")


class LivePreviewStage(FloatLayout):
    """Full-bleed preview: letterboxed RGB texture + color matrix (≡ core).

    Uses the same ``rgb_to_texture`` path as Photos (proven on desktop/Android).
    The previous nested ``RenderContext`` FS path uploaded frames but drew black
    on common GL drivers — matrix is applied on CPU via
    ``apply_matrix_shader_emulation`` (same math as ``core._apply_matrix``).
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._tex: Texture | None = None
        self._rgb: np.ndarray | None = None
        self._matrix = identity_matrix()
        self._upload_ms = 0.0
        self._draw_ms = 0.0
        # Kept for CameraScreen status probes (GPU path retired for reliability)
        self._gpu_ready = False
        self._gpu_failed = False
        self._cpu_fallback = True
        self._rc = None
        self._rect = None
        with self.canvas.before:
            self._bg_c = Color(*NEUTRAL_SURFACE)
            self._bg_r = RoundedRectangle(pos=self.pos, size=self.size, radius=[0])
        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._layout, size=self._layout)

    def ensure_gpu(self) -> bool:
        """GPU FS path disabled — always use CPU matrix + RGB texture (visible)."""
        self._cpu_fallback = True
        self._gpu_ready = False
        return False

    def set_color_matrix(self, matrix: np.ndarray) -> None:
        """Update the 3×3 color matrix; re-blit current frame if present."""
        self._matrix = np.asarray(matrix, dtype=np.float64).reshape(3, 3)
        if self._rgb is not None:
            self.set_rgb(self._rgb)

    def set_rgb(self, rgb: np.ndarray | None) -> None:
        """Apply color matrix (≡ core) and blit via Photos-proven RGB texture."""
        if rgb is None:
            return
        t0 = time.perf_counter()
        arr = np.asarray(rgb)
        if arr.ndim != 3 or arr.shape[2] < 3:
            return
        rgb3 = np.ascontiguousarray(arr[..., :3], dtype=np.uint8)
        self._rgb = rgb3

        try:
            from colorsight.camera_gpu import apply_matrix_shader_emulation

            display = apply_matrix_shader_emulation(rgb3, self._matrix)
        except Exception:
            log.exception("camera_preview: matrix apply failed — showing raw")
            display = rgb3

        try:
            self._blit_rgb(display)
        except Exception:
            log.exception("camera_preview: texture blit failed")
            return

        self._layout()
        self._upload_ms = (time.perf_counter() - t0) * 1000.0

    def _blit_rgb(self, rgb: np.ndarray) -> None:
        existing = None
        if self._tex is not None and getattr(self._tex, "colorfmt", "") == "rgb":
            existing = self._tex
        self._tex = rgb_to_texture(rgb, existing=existing)
        self._rect.texture = self._tex

    def current_rgb(self) -> np.ndarray | None:
        return self._rgb

    def last_upload_ms(self) -> float:
        return float(self._upload_ms)

    def _layout(self, *_a):
        self._bg_r.pos = self.pos
        self._bg_r.size = self.size
        if self._rect is None:
            return
        rgb = self._rgb
        if rgb is None:
            self._rect.pos = self.pos
            self._rect.size = self.size
            return
        th, tw = rgb.shape[0], rgb.shape[1]
        if tw <= 0 or th <= 0 or self.width <= 0 or self.height <= 0:
            return
        scale = min(self.width / tw, self.height / th)
        bw, bh = tw * scale, th * scale
        ox = self.x + (self.width - bw) / 2
        oy = self.y + (self.height - bh) / 2
        self._rect.pos = (ox, oy)
        self._rect.size = (bw, bh)

    def image_to_pixel(self, x: float, y: float) -> tuple[float, float] | None:
        if self._rgb is None:
            return None
        th, tw = self._rgb.shape[0], self._rgb.shape[1]
        if tw <= 0 or th <= 0 or self.width <= 0 or self.height <= 0:
            return None
        scale = min(self.width / tw, self.height / th)
        bw, bh = tw * scale, th * scale
        ox = self.x + (self.width - bw) / 2
        oy = self.y + (self.height - bh) / 2
        if x < ox or y < oy or x > ox + bw or y > oy + bh:
            return None
        px = (x - ox) / scale
        py = th - (y - oy) / scale
        return float(np.clip(px, 0, tw - 1)), float(np.clip(py, 0, th - 1))


class LoupeOverlay(FloatLayout):
    """Draggable circular loupe; zoom content clipped to the circle; name pill above chrome."""

    locked = BooleanProperty(False)
    zoom = NumericProperty(DEFAULT_ZOOM)
    move_cb = ObjectProperty(None, allownone=True)
    lock_cb = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        d = dp(LOUPE_DIAMETER_DP)
        self.size_hint = (None, None)
        # Glass only; pill is positioned separately but still a child for hit-testing
        self.size = (d, d)
        self._dragging = False
        self._hold_ev = None
        self._glass = Widget(size_hint=(None, None), size=(d, d))
        self._zoom_img = KivyImage(fit_mode="fill", size_hint=(None, None), size=(d, d))
        self._glass.add_widget(self._zoom_img)
        self.add_widget(self._glass)

        self._lock_icon = Icon(
            icon=Icons.lock_open,
            icon_size=16,
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=(dp(24), dp(24)),
        )
        self.add_widget(self._lock_icon)

        self._pill = BoxLayout(
            orientation="horizontal",
            size_hint=(None, None),
            size=(d + dp(24), dp(28)),
            spacing=dp(6),
            padding=[dp(6), dp(2)],
        )
        self._swatch = Widget(size_hint=(None, None), size=(dp(16), dp(16)))
        self._swatch2 = Widget(size_hint=(None, None), size=(dp(16), dp(16)))
        self._swatch2.opacity = 0
        # Pill is always near-white — never use Colors.text (light in dark theme).
        self._name_lbl = Label(
            text="",
            font_name=Fonts.semibold,
            font_size=dp(11),
            color=NEUTRAL_TEXT,
            size_hint=(1, 1),
            halign="left",
            valign="middle",
            shorten=True,
            max_lines=1,
        )
        self._name_lbl.bind(size=lambda *_: setattr(self._name_lbl, "text_size", self._name_lbl.size))
        self._pill.add_widget(self._swatch)
        self._pill.add_widget(self._swatch2)
        self._pill.add_widget(self._name_lbl)
        self.add_widget(self._pill)

        self._zoom_tex = None
        self.bind(pos=self._layout, size=self._layout, locked=self._on_locked)
        self._layout()

    def _on_locked(self, *_a):
        self._lock_icon.icon = Icons.lock if self.locked else Icons.lock_open
        self._draw_chrome()

    def set_zoom_rgb(self, rgb: np.ndarray | None):
        if rgb is None:
            return
        self._zoom_tex = rgb_to_texture(rgb, existing=self._zoom_tex)
        self._zoom_img.texture = self._zoom_tex

    def set_label(self, name: str, swatch_rgb: np.ndarray, corrected_rgb: np.ndarray | None = None):
        self._name_lbl.text = name
        self._paint_swatch(self._swatch, swatch_rgb)
        if corrected_rgb is not None:
            self._swatch2.opacity = 1
            self._paint_swatch(self._swatch2, corrected_rgb)
        else:
            self._swatch2.opacity = 0

    def _paint_swatch(self, w: Widget, rgb: np.ndarray):
        w.canvas.clear()
        r, g, b = [float(c) / 255.0 for c in rgb.tolist()]
        with w.canvas:
            Color(r, g, b, 1)
            Ellipse(pos=w.pos, size=w.size)

    def _layout(self, *_a):
        d = dp(LOUPE_DIAMETER_DP)
        self.size = (d, d)
        self._glass.pos = self.pos
        self._glass.size = (d, d)
        self._zoom_img.pos = self._glass.pos
        self._zoom_img.size = self._glass.size
        self._lock_icon.pos = (self.x + d - dp(28), self.y + d - dp(28))
        # Name pill directly below the loupe (caller may reposition above controls)
        self._pill.size = (d + dp(24), dp(28))
        self._pill.pos = (self.x - dp(12), self.y - dp(34))
        self._swatch.pos = (self._pill.x + dp(6), self._pill.y + dp(6))
        self._swatch2.pos = (self._swatch.x + dp(20), self._swatch.y)
        self._draw_chrome()

    def place_pill_inside(self, bounds: Widget, prefer_below: bool = True):
        """Keep the name pill inside ``bounds`` (preview rect), below or above the glass."""
        d = dp(LOUPE_DIAMETER_DP)
        pill_h = self._pill.height
        if prefer_below:
            py = self.y - pill_h - dp(6)
            if py < bounds.y:
                py = self.y + d + dp(6)
        else:
            py = self.y + d + dp(6)
            if py + pill_h > bounds.top:
                py = self.y - pill_h - dp(6)
        px = float(np.clip(self.x - dp(12), bounds.x, bounds.right - self._pill.width))
        py = float(np.clip(py, bounds.y, bounds.top - pill_h))
        self._pill.pos = (px, py)
        self._swatch.pos = (self._pill.x + dp(6), self._pill.y + dp(6))
        self._swatch2.pos = (self._swatch.x + dp(20), self._swatch.y)
        self._draw_chrome()

    def _draw_chrome(self):
        # Circular stencil so zoom never sticks out of the loupe
        self._glass.canvas.before.clear()
        self._glass.canvas.after.clear()
        d = dp(LOUPE_DIAMETER_DP)
        gx, gy = self._glass.pos
        with self._glass.canvas.before:
            StencilPush()
            Color(1, 1, 1, 1)
            Ellipse(pos=(gx, gy), size=(d, d))
            StencilUse()
        with self._glass.canvas.after:
            StencilUnUse()
            StencilPop()
            Color(*Colors.shadow)
            Ellipse(pos=(gx, gy - dp(2)), size=(d, d))
            Color(1, 1, 1, 0.95)
            Line(circle=(gx + d / 2, gy + d / 2, d / 2 - dp(2)), width=1.6)
            Color(1, 1, 1, 0.85)
            cx, cy = gx + d / 2, gy + d / 2
            Line(points=[cx - dp(12), cy, cx + dp(12), cy], width=1.1)
            Line(points=[cx, cy - dp(12), cx, cy + dp(12)], width=1.1)

        self.canvas.after.clear()
        with self.canvas.after:
            Color(1, 1, 1, 0.94)
            RoundedRectangle(
                pos=self._pill.pos,
                size=self._pill.size,
                radius=clamped_radii(dp(14), self._pill.width, self._pill.height),
            )

    def on_touch_down(self, touch):
        if self._pill.collide_point(*touch.pos):
            return True
        if not self.collide_point(*touch.pos) and not self._glass.collide_point(*touch.pos):
            return False
        if self.locked:
            if self._lock_icon.collide_point(*touch.pos):
                self.locked = False
                _invoke(self.lock_cb, False)
                return True
            return True
        touch.grab(self)
        self._dragging = True
        from kivy.clock import Clock

        self._hold_ev = Clock.schedule_once(self._do_lock, 0.45)
        return True

    def _do_lock(self, *_a):
        self.locked = True
        self._dragging = False
        _invoke(self.lock_cb, True)

    def on_touch_move(self, touch):
        if touch.grab_current is not self or self.locked:
            return False
        if self._hold_ev is not None:
            self._hold_ev.cancel()
            self._hold_ev = None
        parent = self.parent
        if parent is None:
            return True
        d = dp(LOUPE_DIAMETER_DP)
        nx = float(np.clip(touch.x - d / 2, parent.x, parent.x + parent.width - d))
        ny = float(np.clip(touch.y - d / 2, parent.y, parent.y + parent.height - d))
        self.pos = (nx, ny)
        _invoke(self.move_cb, self.center_x, self.center_y)
        return True

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return False
        touch.ungrab(self)
        if self._hold_ev is not None:
            self._hold_ev.cancel()
            self._hold_ev = None
        self._dragging = False
        return True

    def glass_center(self) -> tuple[float, float]:
        return self._glass.center_x, self._glass.center_y


class _CamChip(ButtonBehavior, Label):
    def __init__(self, key: str, text: str, active: bool, on_tap, **kwargs):
        super().__init__(**kwargs)
        self.key = key
        self._on_tap = on_tap
        self.text = text
        self.font_name = Fonts.semibold if active else Fonts.medium
        self.font_size = dp(11)
        self.color = Colors.toolbar_text_active if active else Colors.toolbar_text
        self.halign = "center"
        self.valign = "middle"
        self.size_hint = (1, 1)
        self._active = active
        self.shorten = True
        self.shorten_from = "right"
        self.max_lines = 1
        self.bind(size=lambda *_: setattr(self, "text_size", self.size))

    def set_active(self, active: bool):
        self._active = active
        self.font_name = Fonts.semibold if active else Fonts.medium
        self.color = Colors.toolbar_text_active if active else Colors.toolbar_text

    def on_release(self):
        _invoke(self._on_tap, self.key)

    def apply_theme(self):
        self.set_active(self._active)


class _CamIconHit(ButtonBehavior, BoxLayout):
    def __init__(self, icon_name: str, on_tap, **kwargs):
        super().__init__(**kwargs)
        self._on_tap = on_tap
        self.size_hint = (None, 1)
        self.width = dp(40)
        self.padding = [dp(4), dp(4)]
        self.add_widget(Icon(icon=icon_name, icon_size=20, color=(1, 1, 1, 1), size_hint=(1, 1)))

    def on_release(self):
        _invoke(self._on_tap)


class CameraModeToolbar(BoxLayout):
    """Dark pill: Original | Corrected | Simulation + freeze/capture + loupe + flip."""

    mode = StringProperty("corrected")
    mode_cb = ObjectProperty(None, allownone=True)
    freeze_cb = ObjectProperty(None, allownone=True)
    capture_cb = ObjectProperty(None, allownone=True)
    loupe_cb = ObjectProperty(None, allownone=True)
    flip_cb = ObjectProperty(None, allownone=True)

    def __init__(self, *, show_flip: bool = False, **kwargs):
        self._chips = {}
        self._show_flip = show_flip
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(52)
        self.padding = [dp(4), dp(6), dp(4), dp(6)]
        self.spacing = dp(2)
        for key, label in (
            ("original", "Original"),
            ("corrected", "Corrected"),
            ("simulation", "Sim"),
        ):
            chip = _CamChip(key, label, active=(key == self.mode), on_tap=self._tap_mode)
            self._chips[key] = chip
            self.add_widget(chip)
        self._freeze_hit = _CamIconHit(Icons.pause, self._do_freeze)
        self.add_widget(self._freeze_hit)
        self.add_widget(_CamIconHit(Icons.camera, lambda: _invoke(self.capture_cb)))
        self.add_widget(_CamIconHit(Icons.loupe_toggle, lambda: _invoke(self.loupe_cb)))
        if show_flip:
            self.add_widget(_CamIconHit(Icons.flip_camera, lambda: _invoke(self.flip_cb)))
        self.bind(pos=self._draw, size=self._draw)
        self._sync_mode()
        self._draw()

    def set_frozen(self, frozen: bool):
        self._freeze_hit.clear_widgets()
        self._freeze_hit.add_widget(
            Icon(
                icon=Icons.play_arrow if frozen else Icons.pause,
                icon_size=20,
                color=(1, 1, 1, 1),
                size_hint=(1, 1),
            )
        )

    def on_mode(self, _instance, _value):
        if self._chips:
            self._sync_mode()
        _invoke(self.mode_cb, self.mode)

    def _tap_mode(self, key: str):
        self.mode = key

    def _do_freeze(self):
        _invoke(self.freeze_cb)

    def _sync_mode(self):
        for key, chip in self._chips.items():
            chip.set_active(key == self.mode)

    def _draw(self, *_a):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*Colors.toolbar_bg)
            RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=clamped_radii(dp(Radii.chip), self.width, self.height),
            )

    def apply_theme(self):
        self._sync_mode()
        self._draw()

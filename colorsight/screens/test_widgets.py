"""Widgets used only by the vision-test flow."""

from __future__ import annotations

import numpy as np
from kivy.graphics import Color, RoundedRectangle
from kivy.graphics.texture import Texture
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget

from colorsight.theme.geometry import clamped_radii
from colorsight.theme.tokens import Colors
from colorsight.widgets import PrimaryButton


def numpy_to_texture(rgb: np.ndarray) -> Texture:
    """HxWx3 RGB uint8 → Kivy texture (flipped for Image)."""
    arr = np.ascontiguousarray(rgb, dtype=np.uint8)
    h, w = arr.shape[:2]
    tex = Texture.create(size=(w, h), colorfmt="rgb")
    tex.blit_buffer(arr.tobytes(), colorfmt="rgb", bufferfmt="ubyte")
    tex.flip_vertical()
    return tex


class PillProgressBar(Widget):
    """Pill-shaped progress indicator (do not name after Kivy ``ProgressBar``)."""

    def __init__(self, progress=0.0, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(8)
        self._progress = float(progress)
        self.bind(pos=self._draw, size=self._draw)

    def set_progress(self, value: float):
        self._progress = float(np.clip(value, 0.0, 1.0))
        self._draw()

    def _draw(self, *_a):
        self.canvas.clear()
        radii = clamped_radii(dp(999), self.width, self.height)
        with self.canvas:
            Color(0.90, 0.88, 0.86, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=radii)
            Color(*Colors.accent_blue)
            w = max(self.height, self.width * self._progress)
            RoundedRectangle(pos=self.pos, size=(w, self.height), radius=radii)


class Numpad(BoxLayout):
    """Large number pad + can't-see + backspace + submit."""

    def __init__(self, on_digit=None, on_clear=None, on_cant_see=None, on_submit=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = dp(8)
        self.size_hint_y = None
        self.height = dp(260)
        self._on_digit = on_digit
        self._on_clear = on_clear
        self._on_cant_see = on_cant_see
        self._on_submit = on_submit

        grid = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None, height=dp(168))
        for row in ((1, 2, 3), (4, 5, 6), (7, 8, 9)):
            r = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(48))
            for d in row:
                r.add_widget(self._key(str(d), lambda _b, n=d: self._tap_digit(n)))
            grid.add_widget(r)
        bottom = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(48))
        bottom.add_widget(self._key("⌫", lambda *_: self._tap_clear(), dark=False))
        bottom.add_widget(self._key("0", lambda *_: self._tap_digit(0)))
        bottom.add_widget(self._key("OK", lambda *_: self._tap_submit(), dark=True))
        grid.add_widget(bottom)
        self.add_widget(grid)

        cant = PrimaryButton(text="Can't see anything")
        cant.bg_color = (0.85, 0.85, 0.85, 1)
        cant.text_color = Colors.text
        cant.height = dp(48)
        cant.on_press_cb = lambda *_: self._tap_cant()
        self.add_widget(cant)

    def _key(self, text, cb, dark=False):
        btn = PrimaryButton(text=text)
        btn.height = dp(48)
        if dark:
            btn.bg_color = Colors.accent_dark
            btn.text_color = (1, 1, 1, 1)
        else:
            btn.bg_color = Colors.surface
            btn.text_color = Colors.text
        btn.on_press_cb = cb
        return btn

    def _tap_digit(self, n):
        if callable(self._on_digit):
            self._on_digit(n)

    def _tap_clear(self):
        if callable(self._on_clear):
            self._on_clear()

    def _tap_cant(self):
        if callable(self._on_cant_see):
            self._on_cant_see()

    def _tap_submit(self):
        if callable(self._on_submit):
            self._on_submit()


class ArrowPad(BoxLayout):
    """Large up/down/left/right arrows + can't-see for Landolt C 4-AFC."""

    def __init__(self, on_orient=None, on_cant_see=None, **kwargs):
        from colorsight.theme.tokens import Icons

        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = dp(8)
        self.size_hint_y = None
        self.height = dp(220)
        self._on_orient = on_orient
        self._on_cant_see = on_cant_see

        mid = BoxLayout(spacing=dp(8), size_hint_y=None, height=dp(56))
        mid.add_widget(self._arrow("left", Icons.arrow_back))
        mid.add_widget(Widget())
        mid.add_widget(self._arrow("right", Icons.arrow_forward))

        self.add_widget(self._arrow("up", Icons.arrow_upward))
        self.add_widget(mid)
        self.add_widget(self._arrow("down", Icons.arrow_downward))

        cant = PrimaryButton(text="I can't see it")
        cant.bg_color = (0.85, 0.85, 0.85, 1)
        cant.text_color = Colors.text
        cant.height = dp(48)
        cant.on_press_cb = lambda *_: self._tap_cant()
        self.add_widget(cant)

    def _arrow(self, orient: str, icon_name: str):
        from colorsight.theme.tokens import Fonts
        from colorsight.widgets import Icon

        btn = PrimaryButton(text="")
        btn.height = dp(56)
        btn.bg_color = Colors.surface
        btn.clear_widgets()
        ic = Icon(icon_name, size=dp(28), color=Colors.text)
        btn.add_widget(ic)
        btn.on_press_cb = lambda *_ , o=orient: self._tap(o)
        return btn

    def _tap(self, orient: str):
        if callable(self._on_orient):
            self._on_orient(orient)

    def _tap_cant(self):
        if callable(self._on_cant_see):
            self._on_cant_see()


class AxisBars(Widget):
    """Pastel per-axis threshold bars (protan / deutan / tritan)."""

    def __init__(self, thresholds: dict | None = None, cutoffs: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(90)
        self._thr = thresholds or {"protan": 0.0, "deutan": 0.0, "tritan": 0.0}
        self._cut = cutoffs or {"protan": 0.01, "deutan": 0.01, "tritan": 0.015}
        self.bind(pos=self._draw, size=self._draw)

    def set_values(self, thresholds: dict, cutoffs: dict | None = None):
        self._thr = dict(thresholds)
        if cutoffs:
            self._cut = dict(cutoffs)
        self._draw()

    def _draw(self, *_a):
        self.canvas.clear()
        if self.width < 4:
            return
        colors = {
            "protan": (1.0, 0.72, 0.78, 1),   # pink
            "deutan": (0.78, 0.94, 0.84, 1),  # mint
            "tritan": (0.72, 0.88, 1.0, 1),   # sky
        }
        labels = ("protan", "deutan", "tritan")
        row_h = self.height / 3.0
        max_v = max(0.08, max(self._thr.values()), max(self._cut.values()) * 2)
        with self.canvas:
            for i, name in enumerate(labels):
                y = self.y + self.height - (i + 1) * row_h + dp(4)
                h = row_h - dp(8)
                Color(0.90, 0.88, 0.86, 1)
                radii = clamped_radii(dp(8), self.width, h)
                RoundedRectangle(pos=(self.x, y), size=(self.width, h), radius=radii)
                frac = float(np.clip(self._thr[name] / max_v, 0.0, 1.0))
                Color(*colors[name])
                RoundedRectangle(
                    pos=(self.x, y),
                    size=(max(h, self.width * frac), h),
                    radius=radii,
                )


class SeverityBar(Widget):
    """0–100 severity capsule."""

    def __init__(self, value: float = 0.0, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(14)
        self._value = float(np.clip(value, 0.0, 1.0))
        self.bind(pos=self._draw, size=self._draw)

    def set_value(self, value: float):
        self._value = float(np.clip(value, 0.0, 1.0))
        self._draw()

    def _draw(self, *_a):
        self.canvas.clear()
        radii = clamped_radii(dp(999), self.width, self.height)
        with self.canvas:
            Color(0.90, 0.88, 0.86, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=radii)
            Color(*Colors.accent_blue)
            w = max(self.height, self.width * self._value)
            RoundedRectangle(pos=self.pos, size=(w, self.height), radius=radii)


class HueTile(ButtonBehavior, Widget):
    def __init__(self, index: int, rgb, **kwargs):
        super().__init__(**kwargs)
        self.index = index
        self.rgb = rgb
        self.size_hint = (1, None)
        self.height = dp(56)
        self.bind(pos=self._draw, size=self._draw)

    def _draw(self, *_a):
        self.canvas.before.clear()
        r, g, b = self.rgb
        radii = clamped_radii(dp(14), self.width, self.height)
        with self.canvas.before:
            Color(*Colors.shadow)
            RoundedRectangle(pos=(self.x, self.y - dp(2)), size=self.size, radius=radii)
            Color(r / 255.0, g / 255.0, b / 255.0, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=radii)


class HueStrip(BoxLayout):
    """Draggable hue tiles — tap a tile then tap a slot to swap, or drag across neighbors."""

    def __init__(self, colors, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.spacing = dp(8)
        self.size_hint_y = None
        self.height = dp(64)
        self._order = list(range(len(colors)))
        self._colors = list(colors)
        self._selected = None
        self._rebuild()

    @property
    def order(self):
        return list(self._order)

    def _rebuild(self):
        self.clear_widgets()
        for pos, idx in enumerate(self._order):
            tile = HueTile(index=idx, rgb=self._colors[idx])
            tile.bind(on_release=lambda _w, p=pos: self._on_tap(p))
            self.add_widget(tile)

    def _on_tap(self, pos: int):
        if self._selected is None:
            self._selected = pos
            return
        if self._selected == pos:
            self._selected = None
            return
        i, j = self._selected, pos
        self._order[i], self._order[j] = self._order[j], self._order[i]
        self._selected = None
        self._rebuild()

    def shuffle(self, rng=None):
        rng = rng or np.random.default_rng()
        self._order = list(rng.permutation(len(self._colors)))
        # Avoid starting already sorted
        if self._order == list(range(len(self._colors))):
            self._order = list(reversed(self._order))
        self._selected = None
        self._rebuild()

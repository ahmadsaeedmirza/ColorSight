"""Widgets used only by the vision-test flow."""

from __future__ import annotations

import numpy as np
from kivy.animation import Animation
from kivy.graphics import Color, Ellipse, Line, RoundedRectangle
from kivy.graphics.texture import Texture
from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from colorsight.theme.geometry import clamped_radii
from colorsight.theme.tokens import Colors, Fonts
from colorsight.widgets import Icon, PrimaryButton
from colorsight.theme.tokens import Icons


def numpy_to_texture(rgb: np.ndarray, existing: Texture | None = None) -> Texture:
    """HxWx3 RGB uint8 → Kivy texture with linear filtering (reuses ``existing`` when size matches)."""
    arr = np.ascontiguousarray(rgb[::-1], dtype=np.uint8)  # flip once in NumPy
    h, w = arr.shape[:2]
    if existing is not None and tuple(existing.size) == (w, h):
        tex = existing
    else:
        tex = Texture.create(size=(w, h), colorfmt="rgb")
        tex.mag_filter = "linear"
        tex.min_filter = "linear"
    tex.blit_buffer(arr.tobytes(), colorfmt="rgb", bufferfmt="ubyte")
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
    """Large number pad + can't-see + backspace + submit (legacy)."""

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


ARROW_KEY_DP = 76


class ArrowKey(ButtonBehavior, FloatLayout):
    """White rounded key with centered Material Icon + soft shadow + press feedback."""

    def __init__(self, orient: str, icon_name: str, on_orient=None, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        side = dp(ARROW_KEY_DP)
        self.size = (side, side)
        self._orient = orient
        self._on_orient = on_orient
        self._pressed = False

        self._icon = Icon(icon=icon_name, icon_size=28, color=Colors.text)
        self._icon.size_hint = (None, None)
        self._icon.size = (dp(32), dp(32))
        self.add_widget(self._icon)

        self.bind(pos=self._layout, size=self._layout)
        self._layout()

    def _layout(self, *_a):
        self.canvas.before.clear()
        radii = clamped_radii(dp(18), self.width, self.height)
        with self.canvas.before:
            Color(*Colors.shadow)
            RoundedRectangle(
                pos=(self.x, self.y - dp(2)),
                size=self.size,
                radius=radii,
            )
            fill = (0.96, 0.96, 0.96, 1) if self._pressed else Colors.surface
            Color(*fill)
            RoundedRectangle(pos=self.pos, size=self.size, radius=radii)
        # Center icon
        self._icon.center = self.center

    def on_press(self):
        self._pressed = True
        self._layout()
        Animation.cancel_all(self)
        Animation(opacity=0.88, d=0.06).start(self)

    def on_release(self):
        self._pressed = False
        self._layout()
        Animation.cancel_all(self)
        Animation(opacity=1.0, d=0.10).start(self)
        if callable(self._on_orient):
            self._on_orient(self._orient)


class ArrowPad(BoxLayout):
    """D-pad cross: Up / Left·Right / Down + full-width “I can't see it”."""

    def __init__(self, on_orient=None, on_cant_see=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = dp(10)
        self.size_hint_y = None
        key = dp(ARROW_KEY_DP)
        gap = dp(10)
        # 3 key rows + can't-see
        self.height = key * 3 + gap * 2 + dp(48) + dp(10)
        self._on_orient = on_orient
        self._on_cant_see = on_cant_see

        grid = GridLayout(
            cols=3,
            rows=3,
            spacing=gap,
            size_hint=(None, None),
            size=(key * 3 + gap * 2, key * 3 + gap * 2),
        )
        # Row 0: empty | Up | empty
        grid.add_widget(Widget(size_hint=(None, None), size=(key, key)))
        grid.add_widget(ArrowKey("up", Icons.arrow_upward, on_orient=self._tap))
        grid.add_widget(Widget(size_hint=(None, None), size=(key, key)))
        # Row 1: Left | empty | Right
        grid.add_widget(ArrowKey("left", Icons.arrow_back, on_orient=self._tap))
        grid.add_widget(Widget(size_hint=(None, None), size=(key, key)))
        grid.add_widget(ArrowKey("right", Icons.arrow_forward, on_orient=self._tap))
        # Row 2: empty | Down | empty
        grid.add_widget(Widget(size_hint=(None, None), size=(key, key)))
        grid.add_widget(ArrowKey("down", Icons.arrow_downward, on_orient=self._tap))
        grid.add_widget(Widget(size_hint=(None, None), size=(key, key)))

        # Center the grid horizontally
        holder = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            size_hint_y=None,
            height=key * 3 + gap * 2,
        )
        holder.add_widget(grid)
        self.add_widget(holder)

        cant = PrimaryButton(text="I can't see it")
        cant.bg_color = (0.85, 0.85, 0.85, 1)
        cant.text_color = Colors.text
        cant.height = dp(48)
        cant.on_press_cb = lambda *_: self._tap_cant()
        self.add_widget(cant)

    def _tap(self, orient: str):
        if callable(self._on_orient):
            self._on_orient(orient)

    def _tap_cant(self):
        if callable(self._on_cant_see):
            self._on_cant_see()


class AxisBars(BoxLayout):
    """Labeled pastel axis bars with ×cutoff value and a 1.0× normal-limit tick."""

    def __init__(self, thresholds: dict | None = None, cutoffs: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = dp(10)
        self.size_hint_y = None
        self._thr = thresholds or {"protan": 0.0, "deutan": 0.0, "tritan": 0.0}
        self._cut = cutoffs or {"protan": 0.01, "deutan": 0.01, "tritan": 0.015}
        self._rows: dict[str, dict] = {}
        self._colors = {
            "protan": (1.0, 0.72, 0.78, 1),
            "deutan": (0.78, 0.94, 0.84, 1),
            "tritan": (0.72, 0.88, 1.0, 1),
        }
        self._titles = {"protan": "Protan", "deutan": "Deutan", "tritan": "Tritan"}
        for name in ("protan", "deutan", "tritan"):
            self.add_widget(self._make_row(name))
        self.height = dp(3 * 44 + 2 * 10)
        self.bind(width=self._redraw_bars)

    def _make_row(self, name: str) -> BoxLayout:
        row = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(44), spacing=dp(4))
        head = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(18))
        # Colored dot
        dot = Widget(size_hint=(None, None), size=(dp(10), dp(10)))
        rgba = self._colors[name]

        def _draw_dot(*_a, w=dot, c=rgba):
            w.canvas.clear()
            with w.canvas:
                Color(*c)
                Ellipse(pos=w.pos, size=w.size)

        dot.bind(pos=_draw_dot, size=_draw_dot)
        head.add_widget(dot)
        head.add_widget(Widget(size_hint_x=None, width=dp(8)))
        title = Label(
            text=self._titles[name],
            font_name=Fonts.semibold,
            font_size=dp(13),
            color=Colors.text,
            halign="left",
            valign="middle",
            size_hint_x=1,
        )
        title.bind(size=lambda *_ , L=title: setattr(L, "text_size", L.size))
        head.add_widget(title)
        val = Label(
            text="0.0×",
            font_name=Fonts.medium,
            font_size=dp(13),
            color=Colors.text_muted,
            halign="right",
            valign="middle",
            size_hint_x=None,
            width=dp(56),
        )
        val.bind(size=lambda *_ , L=val: setattr(L, "text_size", L.size))
        head.add_widget(val)
        row.add_widget(head)

        bar = Widget(size_hint_y=None, height=dp(14))
        row.add_widget(bar)
        self._rows[name] = {"val": val, "bar": bar}
        return row

    def set_values(self, thresholds: dict, cutoffs: dict | None = None):
        self._thr = dict(thresholds)
        if cutoffs:
            self._cut = dict(cutoffs)
        self._redraw_bars()

    def _redraw_bars(self, *_a):
        # Scale so 1.0× cutoff sits at a readable position; extend to max observed
        multiples = []
        for name in ("protan", "deutan", "tritan"):
            cut = max(1e-9, float(self._cut[name]))
            multiples.append(float(self._thr[name]) / cut)
        max_mult = max(2.0, max(multiples) if multiples else 2.0)

        for name in ("protan", "deutan", "tritan"):
            cut = max(1e-9, float(self._cut[name]))
            mult = float(self._thr[name]) / cut
            self._rows[name]["val"].text = f"{mult:.1f}×"
            bar = self._rows[name]["bar"]
            bar.canvas.clear()
            if bar.width < 4:
                continue
            radii = clamped_radii(dp(7), bar.width, bar.height)
            frac = float(np.clip(mult / max_mult, 0.0, 1.0))
            tick_x = bar.x + bar.width * (1.0 / max_mult)
            with bar.canvas:
                Color(0.90, 0.88, 0.86, 1)
                RoundedRectangle(pos=bar.pos, size=bar.size, radius=radii)
                Color(*self._colors[name])
                RoundedRectangle(
                    pos=bar.pos,
                    size=(max(bar.height, bar.width * frac), bar.height),
                    radius=radii,
                )
                # Normal-limit tick at 1.0×
                Color(0.35, 0.35, 0.35, 0.85)
                Line(
                    points=[tick_x, bar.y, tick_x, bar.y + bar.height],
                    width=1.2,
                )


class SeverityBar(BoxLayout):
    """0–100 severity capsule with numeric label (e.g. “91 / 100”)."""

    def __init__(self, value: float = 0.0, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = dp(6)
        self.size_hint_y = None
        self.height = dp(40)
        self._value = float(np.clip(value, 0.0, 1.0))

        head = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(18))
        head.add_widget(Widget())
        self._lbl = Label(
            text=self._fmt(),
            font_name=Fonts.semibold,
            font_size=dp(13),
            color=Colors.text_muted,
            halign="right",
            valign="middle",
            size_hint_x=None,
            width=dp(72),
        )
        self._lbl.bind(size=lambda *_: setattr(self._lbl, "text_size", self._lbl.size))
        head.add_widget(self._lbl)
        self.add_widget(head)

        self._bar = Widget(size_hint_y=None, height=dp(14))
        self._bar.bind(pos=self._draw_bar, size=self._draw_bar)
        self.add_widget(self._bar)
        self._draw_bar()

    def _fmt(self) -> str:
        return f"{int(round(self._value * 100))} / 100"

    def set_value(self, value: float):
        self._value = float(np.clip(value, 0.0, 1.0))
        self._lbl.text = self._fmt()
        self._draw_bar()

    def _draw_bar(self, *_a):
        self._bar.canvas.clear()
        radii = clamped_radii(dp(999), self._bar.width, self._bar.height)
        with self._bar.canvas:
            Color(0.90, 0.88, 0.86, 1)
            RoundedRectangle(pos=self._bar.pos, size=self._bar.size, radius=radii)
            Color(*Colors.accent_blue)
            w = max(self._bar.height, self._bar.width * self._value)
            RoundedRectangle(pos=self._bar.pos, size=(w, self._bar.height), radius=radii)


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
        if self._order == list(range(len(self._colors))):
            self._order = list(reversed(self._order))
        self._selected = None
        self._rebuild()

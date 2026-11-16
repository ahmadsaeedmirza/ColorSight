"""First-time Vision Test tutorial + optional practice (UI layer only).

Never touches TrivectorSession, scoring, or the correction profile.
"""

from __future__ import annotations

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from colorsight.screens.photo_widgets import TextLinkButton
from colorsight.screens.test_widgets import (
    ARROW_GAP_DP,
    ARROW_KEY_DP,
    ArrowKey,
)
from colorsight.theme.tokens import (
    NEUTRAL_BG,
    NEUTRAL_TEXT,
    NEUTRAL_TEXT_MUTED,
    Colors,
    Fonts,
    Icons,
    Spacing,
)
from colorsight.widgets import PrimaryButton
from colorsight.widgets.icon import Icon


class _DemoRing(Widget):
    """High-contrast Landolt-C-like demo (not a real test stimulus)."""

    def __init__(self, gap: str = "right", **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (dp(160), dp(160))
        self._gap = gap  # up/down/left/right
        self.bind(pos=self._draw, size=self._draw)
        Clock.schedule_once(lambda dt: self._draw(), 0)

    def set_gap(self, gap: str):
        self._gap = gap
        self._draw()

    def _draw(self, *_a):
        self.canvas.clear()
        cx = self.center_x
        cy = self.center_y
        r = min(self.width, self.height) * 0.42
        with self.canvas:
            Color(0.15, 0.15, 0.18, 1)
            Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))
            Color(*NEUTRAL_BG)
            inner = r * 0.55
            Ellipse(pos=(cx - inner, cy - inner), size=(inner * 2, inner * 2))
            Color(*NEUTRAL_BG)
            gap = self._gap
            w = r * 0.55
            if gap == "right":
                Ellipse(pos=(cx, cy - w / 2), size=(r + 4, w))
            elif gap == "left":
                Ellipse(pos=(cx - r - 4, cy - w / 2), size=(r + 4, w))
            elif gap == "up":
                Ellipse(pos=(cx - w / 2, cy), size=(w, r + 4))
            else:
                Ellipse(pos=(cx - w / 2, cy - r - 4), size=(w, r + 4))
            Color(0.15, 0.15, 0.18, 1)
            Line(circle=(cx, cy, r), width=dp(2))


class _PulseArrowHint(BoxLayout):
    """Inverted-T Material Icons pad that gently pulses (step 2)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint_y = None
        key = dp(48)
        gap = dp(ARROW_GAP_DP)
        self.height = key * 2 + gap + dp(8)
        self.spacing = gap
        self.opacity = 0.85

        top = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            size_hint_y=None,
            height=key,
        )
        top.add_widget(self._icon(Icons.arrow_upward, key))
        self.add_widget(top)

        bottom = BoxLayout(
            orientation="horizontal",
            size_hint=(None, None),
            size=(key * 3 + gap * 2, key),
            spacing=gap,
            pos_hint={"center_x": 0.5},
        )
        bottom.add_widget(self._icon(Icons.arrow_back, key))
        bottom.add_widget(self._icon(Icons.arrow_downward, key))
        bottom.add_widget(self._icon(Icons.arrow_forward, key))
        holder = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            size_hint_y=None,
            height=key,
        )
        holder.add_widget(bottom)
        self.add_widget(holder)

        self._anim = None
        Clock.schedule_once(lambda dt: self._pulse(), 0.2)

    def _icon(self, name: str, side: float) -> Icon:
        ic = Icon(icon=name, icon_size=28, color=Colors.accent_blue)
        ic.size_hint = (None, None)
        ic.size = (side, side)
        return ic

    def _pulse(self, *_a):
        self._anim = Animation(opacity=0.35, duration=0.7) + Animation(
            opacity=1.0, duration=0.7
        )
        self._anim.repeat = True
        self._anim.start(self)

    def on_parent(self, *_a):
        if self.parent is None and self._anim is not None:
            self._anim.cancel(self)


class _PeachHint(BoxLayout):
    """Peach 'I can't see it' demo chip (step 3)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(52)
        self.padding = [dp(16), dp(10), dp(16), dp(10)]
        self._lbl = Label(
            text="I can't see it",
            font_name=Fonts.semibold,
            font_size=dp(15),
            color=Colors.cant_see_text,
        )
        self.add_widget(self._lbl)
        self.bind(pos=self._draw, size=self._draw)
        self.opacity = 0.9
        Clock.schedule_once(lambda dt: self._pulse(), 0.2)

    def _draw(self, *_a):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*Colors.cant_see_bg)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(16)] * 4)

    def _pulse(self, *_a):
        anim = Animation(opacity=0.45, duration=0.7) + Animation(
            opacity=1.0, duration=0.7
        )
        anim.repeat = True
        anim.start(self)


class VisionTestTutorial(BoxLayout):
    """3 steps + optional practice. finish_cb() / skip_cb() when done."""

    def __init__(self, *, finish_cb=None, skip_cb=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint_y = None
        self.spacing = dp(Spacing.md)
        self.finish_cb = finish_cb
        self.skip_cb = skip_cb
        self._step = 0
        self._practice_gap = "left"
        self.bind(minimum_height=self.setter("height"))
        self._build_step()

    def _paint_neutral(self, widget: Widget):
        widget.canvas.before.clear()
        with widget.canvas.before:
            Color(*NEUTRAL_BG)
            RoundedRectangle(pos=widget.pos, size=widget.size, radius=[0])
        widget.bind(
            pos=lambda *_: self._repaint(widget),
            size=lambda *_: self._repaint(widget),
        )

    def _repaint(self, widget):
        widget.canvas.before.clear()
        with widget.canvas.before:
            Color(*NEUTRAL_BG)
            RoundedRectangle(pos=widget.pos, size=widget.size, radius=[0])

    def _build_step(self):
        self.clear_widgets()
        self._paint_neutral(self)
        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(44),
            spacing=dp(8),
        )
        title = Label(
            text=f"Quick tip {self._step + 1} of 3" if self._step < 3 else "Try one",
            font_name=Fonts.semibold,
            font_size=dp(14),
            color=NEUTRAL_TEXT_MUTED,
            halign="left",
            valign="middle",
            size_hint_y=1,
        )
        title.bind(size=lambda *_: setattr(title, "text_size", title.size))
        header.add_widget(title)
        skip = TextLinkButton(text="Skip")
        skip.color = Colors.accent_blue
        skip.size_hint = (None, 1)
        skip.width = dp(56)
        skip.bind(on_release=lambda *_: self._skip())
        header.add_widget(skip)
        self.add_widget(header)

        body = BoxLayout(
            orientation="vertical",
            spacing=dp(Spacing.md),
            size_hint_y=None,
        )
        body.bind(minimum_height=body.setter("height"))

        if self._step == 0:
            body.add_widget(
                self._copy(
                    "You'll see a circle with a ring. One side of the ring has a small gap."
                )
            )
            ring = _DemoRing(gap="right")
            wrap = FloatLayout(size_hint_y=None, height=dp(180))
            ring.pos_hint = {"center_x": 0.5, "center_y": 0.5}
            wrap.add_widget(ring)
            body.add_widget(wrap)
            body.add_widget(Widget(size_hint_y=None, height=dp(8)))
            body.add_widget(self._next_btn("Next"))
        elif self._step == 1:
            body.add_widget(self._copy("Tap the arrow that points to the gap."))
            body.add_widget(Widget(size_hint_y=None, height=dp(12)))
            body.add_widget(_PulseArrowHint())
            body.add_widget(Widget(size_hint_y=None, height=dp(16)))
            body.add_widget(self._next_btn("Next"))
        elif self._step == 2:
            body.add_widget(
                self._copy(
                    "Can't see the ring or the gap? Tap I can't see it. "
                    "Guessing is not needed."
                )
            )
            body.add_widget(Widget(size_hint_y=None, height=dp(8)))
            body.add_widget(_PeachHint())
            body.add_widget(Widget(size_hint_y=None, height=dp(16)))
            body.add_widget(self._next_btn("Try a practice"))
        else:
            self._build_practice(body)

        self.add_widget(body)

    def _copy(self, text: str) -> Label:
        lbl = Label(
            text=text,
            font_name=Fonts.medium,
            font_size=dp(16),
            color=NEUTRAL_TEXT,
            halign="left",
            valign="top",
            size_hint_y=None,
            text_size=(None, None),
        )

        def _fit(*_a):
            lbl.text_size = (lbl.width, None)
            lbl.height = max(dp(48), lbl.texture_size[1] + dp(4))

        lbl.bind(width=_fit, texture_size=_fit)
        lbl.height = dp(72)
        return lbl

    def _next_btn(self, text: str) -> PrimaryButton:
        btn = PrimaryButton(text=text)
        btn.bg_color = Colors.accent_blue
        btn.on_press_cb = lambda *_: self._advance()
        return btn

    def _advance(self):
        self._step += 1
        if self._step > 3:
            self._finish()
            return
        self._build_step()

    def _skip(self):
        if callable(self.skip_cb):
            self.skip_cb()
        elif callable(self.finish_cb):
            self.finish_cb()

    def _finish(self):
        if callable(self.finish_cb):
            self.finish_cb()

    def _build_practice(self, body: BoxLayout):
        body.add_widget(
            self._copy(
                "Practice only — tap the arrow that matches the gap. "
                "This does not count."
            )
        )
        self._practice_ring = _DemoRing(gap=self._practice_gap)
        wrap = FloatLayout(size_hint_y=None, height=dp(168))
        self._practice_ring.pos_hint = {"center_x": 0.5, "center_y": 0.5}
        wrap.add_widget(self._practice_ring)
        body.add_widget(wrap)

        self._feedback = Label(
            text="",
            font_name=Fonts.semibold,
            font_size=dp(16),
            color=Colors.accent_blue,
            size_hint_y=None,
            height=dp(28),
        )
        body.add_widget(self._feedback)

        key = dp(ARROW_KEY_DP)
        gap = dp(ARROW_GAP_DP)
        pad = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=key * 2 + gap,
            spacing=gap,
        )
        top = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            size_hint_y=None,
            height=key,
        )
        top.add_widget(
            ArrowKey("up", Icons.arrow_upward, on_orient=self._on_practice)
        )
        pad.add_widget(top)

        bottom = BoxLayout(
            orientation="horizontal",
            size_hint=(None, None),
            size=(key * 3 + gap * 2, key),
            spacing=gap,
            pos_hint={"center_x": 0.5},
        )
        bottom.add_widget(
            ArrowKey("left", Icons.arrow_back, on_orient=self._on_practice)
        )
        bottom.add_widget(
            ArrowKey("down", Icons.arrow_downward, on_orient=self._on_practice)
        )
        bottom.add_widget(
            ArrowKey("right", Icons.arrow_forward, on_orient=self._on_practice)
        )
        holder = AnchorLayout(
            anchor_x="center",
            anchor_y="center",
            size_hint_y=None,
            height=key,
        )
        holder.add_widget(bottom)
        pad.add_widget(holder)
        body.add_widget(pad)

        body.add_widget(Widget(size_hint_y=None, height=dp(12)))
        start = PrimaryButton(text="Start the real test")
        start.bg_color = Colors.accent_blue
        start.on_press_cb = lambda *_: self._finish()
        body.add_widget(start)

    def _on_practice(self, orient: str):
        if orient == self._practice_gap:
            self._feedback.text = "Correct!"
            self._feedback.color = (0.2, 0.65, 0.35, 1)
        else:
            pretty = {"left": "left", "right": "right", "up": "up", "down": "down"}
            self._feedback.text = f"The gap was on the {pretty[self._practice_gap]}"
            self._feedback.color = Colors.accent_blue

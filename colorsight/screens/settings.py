"""Settings — debug toggles (FPS) and about copy."""

from __future__ import annotations

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color, RoundedRectangle

from colorsight.theme.geometry import clamped_radii
from colorsight.theme.tokens import Colors, Fonts, Icons, Radii, Spacing
from colorsight.widgets import PastelCard, RoundIconButton


class _FpsToggle(ButtonBehavior, BoxLayout):
    """On/off chip — not named Switch (Kivy builtin)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(52)
        self.padding = [dp(16), dp(8)]
        self._on = False
        app = App.get_running_app()
        if app is not None:
            self._on = bool(getattr(app, "show_camera_fps", False))
        self._lbl = Label(
            text=self._label(),
            font_name=Fonts.semibold,
            font_size=dp(14),
            color=Colors.text,
            halign="left",
            valign="middle",
        )
        self._lbl.bind(size=lambda *_: setattr(self._lbl, "text_size", self._lbl.size))
        self.add_widget(self._lbl)
        self.bind(pos=self._draw, size=self._draw)
        self._draw()

    def _label(self) -> str:
        return f"Show camera FPS: {'On' if self._on else 'Off'}"

    def _draw(self, *_a):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*(0.92, 0.94, 0.98, 1) if self._on else (1, 1, 1, 1))
            RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=clamped_radii(dp(Radii.card), self.width, self.height),
            )

    def on_release(self):
        self._on = not self._on
        self._lbl.text = self._label()
        app = App.get_running_app()
        if app is not None:
            app.show_camera_fps = self._on
        self._draw()


class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="settings", **kwargs)
        root = BoxLayout(
            orientation="vertical",
            padding=[
                dp(Spacing.screen_x),
                dp(Spacing.lg),
                dp(Spacing.screen_x),
                dp(Spacing.nav_clearance),
            ],
            spacing=dp(Spacing.md),
        )
        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(8))
        back = RoundIconButton(icon=Icons.arrow_back, diameter=40)
        back.on_press_cb = lambda *_: self._go("home")
        header.add_widget(back)
        title = Label(
            text="Settings",
            font_name=Fonts.bold,
            font_size=dp(22),
            color=Colors.text,
            halign="left",
            valign="middle",
        )
        title.bind(size=lambda *_: setattr(title, "text_size", title.size))
        header.add_widget(title)
        root.add_widget(header)

        root.add_widget(
            PastelCard(
                title="Debug",
                subtitle="Optional tools for measuring live camera performance.",
                palette="lavender",
                auto_height=True,
                size_hint_y=None,
            )
        )
        root.add_widget(_FpsToggle())
        root.add_widget(
            PastelCard(
                title="About ColorSight",
                subtitle="Assistive color tools. Vision Test results are a screening aid, not a medical diagnosis.",
                palette="mint",
                auto_height=True,
                size_hint_y=None,
            )
        )
        root.add_widget(Widget())
        self.add_widget(root)

    def _go(self, name: str):
        if self.manager:
            self.manager.current = name

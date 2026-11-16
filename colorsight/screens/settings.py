"""Settings — About, Privacy, Theme, Display tips, Debug (+ log viewer)."""

from __future__ import annotations

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle

from colorsight import __version__
from colorsight.clipboard_util import copy_text
from colorsight.logging_setup import read_recent_lines
from colorsight.theme.geometry import clamped_radii
from colorsight.theme.screen_bg import install_opaque_bg
from colorsight.theme.theme import get_theme
from colorsight.theme.tokens import Colors, Fonts, Radii, Spacing
from colorsight.widgets import PastelCard, PrimaryButton, ScreenHeader


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
            Color(*(Colors.accent_blue if self._on else Colors.surface))
            RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=clamped_radii(dp(Radii.card), self.width, self.height),
            )
        self._lbl.color = (1, 1, 1, 1) if self._on else Colors.text

    def on_release(self):
        self._on = not self._on
        self._lbl.text = self._label()
        app = App.get_running_app()
        if app is not None:
            app.show_camera_fps = self._on
        self._draw()

    def apply_theme(self):
        self._draw()


class _ThemeChip(ButtonBehavior, Label):
    def __init__(self, key: str, text: str, active: bool, on_tap, **kwargs):
        super().__init__(**kwargs)
        self.key = key
        self._on_tap = on_tap
        self.text = text
        self.font_name = Fonts.semibold if active else Fonts.medium
        self.font_size = dp(13)
        self.halign = "center"
        self.valign = "middle"
        self.size_hint = (1, None)
        self.height = dp(40)
        self._active = active
        self.shorten = True
        self.max_lines = 1
        self.bind(size=lambda *_: setattr(self, "text_size", self.size))
        self.bind(pos=self._draw, size=self._draw)
        self._draw()

    def set_active(self, active: bool):
        self._active = active
        self.font_name = Fonts.semibold if active else Fonts.medium
        self._draw()

    def _draw(self, *_a):
        self.canvas.before.clear()
        with self.canvas.before:
            if self._active:
                Color(*Colors.chip_selected_bg)
                self.color = Colors.chip_selected_text
            else:
                Color(*Colors.chip_bg)
                self.color = Colors.chip_text
            RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=clamped_radii(dp(Radii.chip), self.width, self.height),
            )

    def on_release(self):
        if callable(self._on_tap):
            self._on_tap(self.key)


class _ThemeRow(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(44)
        self.spacing = dp(8)
        self._chips = {}
        theme = get_theme()
        for key, label in (("system", "System"), ("light", "Light"), ("dark", "Dark")):
            chip = _ThemeChip(
                key, label, active=(theme.preference == key), on_tap=self._pick
            )
            self._chips[key] = chip
            self.add_widget(chip)

    def _pick(self, key: str):
        get_theme().set_preference(key)
        for k, chip in self._chips.items():
            chip.set_active(k == key)

    def apply_theme(self):
        pref = get_theme().preference
        for k, chip in self._chips.items():
            chip.set_active(k == pref)


class LogViewerScreen(Screen):
    """Scrollable recent log + copy — never shows filesystem paths."""

    def __init__(self, **kwargs):
        super().__init__(name="log_viewer", **kwargs)
        install_opaque_bg(self)
        root = BoxLayout(
            orientation="vertical",
            padding=[
                dp(Spacing.screen_x),
                dp(Spacing.sm),
                dp(Spacing.screen_x),
                dp(Spacing.md),
            ],
            spacing=dp(Spacing.sm),
        )
        root.add_widget(
            ScreenHeader(title="Recent log", on_back=lambda: self._go("settings"))
        )
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(4))
        self._body = Label(
            text="",
            font_name=Fonts.regular,
            font_size=dp(11),
            color=Colors.text,
            halign="left",
            valign="top",
            size_hint_y=None,
            text_size=(None, None),
        )
        self._body.bind(
            texture_size=lambda *_: setattr(
                self._body, "height", max(dp(40), self._body.texture_size[1])
            ),
            width=lambda *_: setattr(
                self._body, "text_size", (self._body.width, None)
            ),
        )
        scroll.add_widget(self._body)
        root.add_widget(scroll)
        self._copy_btn = PrimaryButton(text="Copy to clipboard")
        self._copy_btn.on_press_cb = self._copy
        root.add_widget(self._copy_btn)
        self._copy_status = Label(
            text="",
            font_name=Fonts.medium,
            font_size=dp(13),
            color=Colors.accent_blue,
            size_hint_y=None,
            height=dp(22),
            halign="center",
            valign="middle",
        )
        self._copy_status.bind(
            size=lambda *_: setattr(
                self._copy_status, "text_size", self._copy_status.size
            )
        )
        root.add_widget(self._copy_status)
        self.add_widget(root)

    def on_pre_enter(self, *_a):
        self._body.text = read_recent_lines(300)
        self._body.color = Colors.text
        if hasattr(self, "_copy_btn"):
            self._copy_btn.text = "Copy to clipboard"
        if hasattr(self, "_copy_status"):
            self._copy_status.text = ""

    def _copy(self, *_a):
        text = self._body.text or ""
        ok = copy_text(text)
        self._copy_btn.text = "Copied" if ok else "Copy failed"
        self._copy_status.text = (
            "Log copied — paste anywhere"
            if ok
            else "Copy failed — see log for details"
        )
        self._copy_status.color = (
            Colors.accent_blue if ok else (0.85, 0.25, 0.25, 1)
        )
        Clock.unschedule(self._reset_copy_label)
        Clock.schedule_once(self._reset_copy_label, 2.0)

    def _reset_copy_label(self, *_a):
        if hasattr(self, "_copy_btn"):
            self._copy_btn.text = "Copy to clipboard"
        if hasattr(self, "_copy_status"):
            self._copy_status.text = ""

    def _go(self, name: str):
        if self.manager:
            self.manager.current = name


class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="settings", **kwargs)
        install_opaque_bg(self)
        self._build()

    def _build(self):
        self.clear_widgets()
        scroll = ScrollView(do_scroll_x=False, bar_width=0)
        root = BoxLayout(
            orientation="vertical",
            padding=[
                dp(Spacing.screen_x),
                dp(Spacing.sm),
                dp(Spacing.screen_x),
                dp(Spacing.nav_clearance),
            ],
            spacing=dp(Spacing.md),
            size_hint_y=None,
        )
        root.bind(minimum_height=root.setter("height"))

        root.add_widget(
            ScreenHeader(title="Settings", on_back=lambda: self._go("home"))
        )

        root.add_widget(
            PastelCard(
                title="About",
                subtitle=(
                    f"ColorSight v{__version__}\n"
                    "A screening toolkit for color vision — not a medical diagnosis. "
                    "Results can vary with screen brightness and calibration."
                ),
                palette="mint",
                auto_height=True,
                size_hint_y=None,
            )
        )
        root.add_widget(
            PastelCard(
                title="Privacy",
                subtitle="Everything runs on your phone. Photos and camera frames are never uploaded.",
                palette="sky",
                auto_height=True,
                size_hint_y=None,
            )
        )
        root.add_widget(
            PastelCard(
                title="Theme",
                subtitle="System follows the phone. Vision Test and photo/camera previews stay on a neutral light surface so colors stay accurate.",
                palette="lavender",
                auto_height=True,
                size_hint_y=None,
            )
        )
        root.add_widget(_ThemeRow())
        root.add_widget(
            PastelCard(
                title="Display tips",
                subtitle=(
                    "For the Vision Test: raise brightness, turn off night mode / dark theme, "
                    "and disable blue-light filters so colors stay accurate."
                ),
                palette="yellow",
                auto_height=True,
                size_hint_y=None,
            )
        )
        root.add_widget(
            PastelCard(
                title="Debug",
                subtitle="Optional tools for measuring live camera performance and reading the on-device log.",
                palette="peach",
                auto_height=True,
                size_hint_y=None,
            )
        )
        root.add_widget(_FpsToggle())
        view_log = PrimaryButton(text="View recent log")
        view_log.bg_color = Colors.accent_dark
        view_log.on_press_cb = lambda *_: self._go("log_viewer")
        root.add_widget(view_log)
        test_pick = PrimaryButton(text="Test photo picker")
        test_pick.bg_color = Colors.accent_blue
        test_pick.on_press_cb = lambda *_: self._test_photo_picker()
        root.add_widget(test_pick)
        replay = PrimaryButton(text="Replay vision-test tutorial")
        replay.bg_color = Colors.accent_blue
        replay.on_press_cb = lambda *_: self._replay_tutorial()
        root.add_widget(replay)
        root.add_widget(Widget(size_hint_y=None, height=dp(8)))
        scroll.add_widget(root)
        self.add_widget(scroll)

    def apply_theme(self):
        self._build()

    def _test_photo_picker(self):
        import logging

        from colorsight.photo_io import pick_image

        log = logging.getLogger("colorsight")
        log.info("debug: test photo picker tapped")

        def _done(path):
            if path:
                log.info("debug: test photo picker result=ok")
            else:
                log.info("debug: test photo picker result=cancel_or_none")

        def _err(msg):
            log.warning("debug: test photo picker error=%s", msg)

        pick_image(_done, on_error=_err)

    def _replay_tutorial(self):
        from colorsight.prefs import request_tutorial_replay

        request_tutorial_replay()
        if self.manager:
            self.manager.current = "test"

    def _go(self, name: str):
        if self.manager:
            self.manager.current = name

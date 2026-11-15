"""ColorSight application shell."""

from __future__ import annotations

import logging

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import FadeTransition, ScreenManager

from colorsight.logging_setup import setup_logging
from colorsight.prefs import get_theme_pref, is_first_run
from colorsight.safe_area import refresh_safe_insets
from colorsight.theme import register_fonts
from colorsight.theme.screen_bg import install_opaque_bg
from colorsight.theme.theme import get_theme
from colorsight.theme.tokens import Colors, Spacing
from colorsight.widgets import FloatingNavBar
from colorsight.screens import (
    WelcomeScreen,
    HomeScreen,
    TestScreen,
    PhotosScreen,
    CameraScreen,
    LensScreen,
    ProfileScreen,
    SettingsScreen,
    LogViewerScreen,
)

log = logging.getLogger("colorsight")

# Back stack for consistent navigation
_BACK_HOME = {"test", "settings", "photos", "camera", "lens", "profile", "log_viewer"}

# Accuracy-safe neutral surfaces (theme never skews these)
_NEUTRAL_SCREENS = {"test", "photos", "camera", "lens"}


class RootShell(FloatLayout):
    """ScreenManager + floating nav; nav hidden on welcome."""

    NAV_SCREENS = {"home", "photos", "camera", "lens", "profile", "test", "settings"}

    def __init__(self, start_screen: str | None = None, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            self._bg_color = Color(*Colors.bg)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync_bg, size=self._sync_bg)

        self.sm = ScreenManager(transition=FadeTransition(duration=0.22))
        screens = (
            WelcomeScreen(),
            HomeScreen(),
            TestScreen(),
            PhotosScreen(),
            CameraScreen(),
            LensScreen(),
            ProfileScreen(),
            SettingsScreen(),
            LogViewerScreen(),
        )
        for screen in screens:
            if not hasattr(screen, "_bg_rect"):
                install_opaque_bg(
                    screen, neutral=(screen.name in _NEUTRAL_SCREENS)
                )
            self.sm.add_widget(screen)
        self.nav = FloatingNavBar()
        self.nav.navigate_cb = self._navigate
        self.add_widget(self.sm)
        self.add_widget(self.nav)
        self.bind(size=self._place_nav)
        self._place_nav()
        self.sm.bind(current=self._on_screen)

        if start_screen and start_screen in self.sm.screen_names:
            initial = start_screen
        else:
            initial = "welcome" if is_first_run() else "home"
        self.sm.current = initial
        self._on_screen(self.sm, self.sm.current)

        Window.bind(on_keyboard=self._on_key)

    def _sync_bg(self, *_args):
        self._bg.pos = self.pos
        self._bg.size = self.size
        self._bg_color.rgba = Colors.bg

    def _place_nav(self, *_args):
        margin = dp(Spacing.nav_margin)
        bottom = dp(Spacing.safe_bottom)
        self.nav.width = max(0, self.width - margin * 2)
        self.nav.x = self.x + margin
        self.nav.y = self.y + margin + bottom

    def _on_screen(self, _sm, name):
        show_nav = name in self.NAV_SCREENS and name != "welcome"
        self.nav.opacity = 1 if show_nav else 0
        self.nav.disabled = not show_nav
        nav_key = {
            "home": "home",
            "photos": "photos",
            "camera": "camera",
            "lens": "lens",
            "profile": "profile",
            "test": "home",
            "settings": "home",
            "log_viewer": "home",
        }.get(name, "home")
        if show_nav:
            self.nav.active = nav_key

    def _navigate(self, key: str):
        if key in self.sm.screen_names:
            self.sm.transition.direction = "left"
            self.sm.current = key

    def set_nav_active(self, screen_name: str):
        if screen_name in self.sm.screen_names:
            self.sm.current = screen_name

    def go_back(self) -> bool:
        cur = self.sm.current
        if cur == "welcome":
            return False
        if cur == "log_viewer":
            self.sm.transition.direction = "right"
            self.sm.current = "settings"
            return True
        if cur in _BACK_HOME:
            self.sm.transition.direction = "right"
            self.sm.current = "home"
            return True
        if cur == "home":
            return False
        self.sm.transition.direction = "right"
        self.sm.current = "home"
        return True

    def _on_key(self, _window, key, *_args):
        if key in (27, 1000, 1001):
            return self.go_back()
        return False


class ColorSightApp(App):
    title = "ColorSight"
    show_camera_fps = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rebuilding = False
        self._last_system_dark: bool | None = None

    def build(self):
        register_fonts()
        setup_logging()
        refresh_safe_insets()
        theme = get_theme()
        # Tokens only — UI does not exist yet
        theme.preference = get_theme_pref()
        theme.apply(rebuild=False)
        Window.clearcolor = Colors.bg
        Window.bind(on_resize=self._on_window_resize)
        return RootShell()

    def rebuild_ui(self, return_to: str | None = None):
        """Recreate ScreenManager + screens + nav with current tokens/insets."""
        if self._rebuilding:
            return
        self._rebuilding = True
        try:
            refresh_safe_insets()
            Window.clearcolor = Colors.bg
            cur = return_to
            old = self.root
            if cur is None and isinstance(old, RootShell):
                cur = old.sm.current
            if not cur:
                cur = "settings"
            shell = RootShell(start_screen=cur)
            if old is not None:
                try:
                    Window.remove_widget(old)
                except Exception:
                    if getattr(old, "parent", None) is not None:
                        old.parent.remove_widget(old)
            self.root = shell
            if shell.parent is None:
                Window.add_widget(shell)
            log.info("ui rebuilt return_to=%s", cur)
        finally:
            self._rebuilding = False

    def _on_window_resize(self, *_a):
        # Re-read insets (orientation / foldable) and reposition nav
        refresh_safe_insets()
        root = self.root
        if isinstance(root, RootShell):
            root._place_nav()

    def on_pause(self):
        root = self.root
        if root is not None and hasattr(root, "sm"):
            scr = root.sm.get_screen(root.sm.current)
            if hasattr(scr, "on_pause"):
                scr.on_pause()
        return True

    def on_resume(self):
        root = self.root
        if root is not None and hasattr(root, "sm"):
            scr = root.sm.get_screen(root.sm.current)
            if hasattr(scr, "on_resume"):
                scr.on_resume()
        refresh_safe_insets()
        theme = get_theme()
        if theme.preference == "system":
            from colorsight.theme.theme import system_prefers_dark

            dark = system_prefers_dark()
            if self._last_system_dark is None or dark != self._last_system_dark:
                self._last_system_dark = dark
                # Stay on current screen when OS night mode flips
                cur = root.sm.current if isinstance(root, RootShell) else None
                theme.apply(rebuild=True, return_to=cur)
            else:
                if isinstance(root, RootShell):
                    root._place_nav()
        else:
            if isinstance(root, RootShell):
                root._place_nav()

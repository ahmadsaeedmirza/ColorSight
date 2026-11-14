"""ColorSight application shell."""

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import FadeTransition, ScreenManager
from kivy.graphics import Color, Rectangle

from colorsight.prefs import is_first_run
from colorsight.theme import register_fonts
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
)

# Phone-like default for desktop layout checks
Window.size = (390, 844)
Window.clearcolor = Colors.bg

# Back stack for consistent navigation
_BACK_HOME = {"test", "settings", "photos", "camera", "lens", "profile"}


class RootShell(FloatLayout):
    """ScreenManager + floating nav; nav hidden on welcome."""

    NAV_SCREENS = {"home", "photos", "camera", "lens", "profile", "test", "settings"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*Colors.bg)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync_bg, size=self._sync_bg)

        self.sm = ScreenManager(transition=FadeTransition(duration=0.18))
        for screen in (
            WelcomeScreen(),
            HomeScreen(),
            TestScreen(),
            PhotosScreen(),
            CameraScreen(),
            LensScreen(),
            ProfileScreen(),
            SettingsScreen(),
        ):
            self.sm.add_widget(screen)
        self.nav = FloatingNavBar()
        self.nav.navigate_cb = self._navigate
        self.add_widget(self.sm)
        self.add_widget(self.nav)
        self.bind(size=self._place_nav)
        self._place_nav()
        self.sm.bind(current=self._on_screen)
        # First run → Welcome; later launches → Home (after nav exists)
        self.sm.current = "welcome" if is_first_run() else "home"
        self._on_screen(self.sm, self.sm.current)

        Window.bind(on_keyboard=self._on_key)

    def _sync_bg(self, *_args):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def _place_nav(self, *_args):
        margin = dp(Spacing.nav_margin)
        self.nav.width = max(0, self.width - margin * 2)
        self.nav.x = self.x + margin
        self.nav.y = self.y + margin

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
        """Handle Android back / Escape. Returns True if consumed."""
        cur = self.sm.current
        if cur == "welcome":
            return False
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
        # Android back = 27 (Escape) or 1001 on some devices
        if key in (27, 1000, 1001):
            return self.go_back()
        return False


class ColorSightApp(App):
    title = "ColorSight"
    show_camera_fps = False

    def build(self):
        register_fonts()
        return RootShell()

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

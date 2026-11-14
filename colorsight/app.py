"""ColorSight application shell."""

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import FadeTransition, ScreenManager
from kivy.graphics import Color, Rectangle

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
        self.sm.bind(current=self._on_screen)
        self.add_widget(self.sm)

        self.nav = FloatingNavBar()
        self.nav.on_navigate = self._navigate
        self.add_widget(self.nav)
        self.bind(size=self._place_nav)
        self._place_nav()
        self._on_screen(self.sm, self.sm.current)

    def _sync_bg(self, *_args):
        self._bg.pos = self.pos
        self._bg.size = self.size

    def _place_nav(self, *_args):
        margin = dp(Spacing.nav_margin)  # 16–20dp side inset
        self.nav.width = max(0, self.width - margin * 2)
        self.nav.x = self.x + margin
        self.nav.y = self.y + margin
        # Height owned by FloatingNavBar (pill + raised FAB)

    def _on_screen(self, _sm, name):
        show_nav = name in self.NAV_SCREENS and name != "welcome"
        self.nav.opacity = 1 if show_nav else 0
        self.nav.disabled = not show_nav
        # Map feature screens onto closest nav key
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


class ColorSightApp(App):
    title = "ColorSight"

    def build(self):
        register_fonts()
        return RootShell()

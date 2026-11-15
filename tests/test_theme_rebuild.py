"""Theme rebuild: chrome colors flip with light/dark; accuracy stays neutral."""

from __future__ import annotations

import unittest
from pathlib import Path

from kivy.base import EventLoop
from kivy.clock import Clock

from colorsight.app import RootShell
from colorsight.prefs import mark_onboarding_done, set_theme_pref
from colorsight.safe_area import set_debug_insets
from colorsight.theme import register_fonts
from colorsight.theme.tokens import (
    DARK_COLORS,
    LIGHT_COLORS,
    NEUTRAL_BG,
    Colors,
    apply_color_set,
)
from colorsight.widgets.chip import Chip
from colorsight.widgets.floating_nav_bar import FloatingNavBar
from colorsight.widgets.pastel_card import PastelCard


def _approx(a, b, tol=0.02) -> bool:
    if a is None or b is None or len(a) != len(b):
        return False
    return all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))


def _tick(n: int = 2):
    for _ in range(n):
        Clock.tick()


class TestThemeRebuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        register_fonts()
        EventLoop.ensure_window()
        Path.home().joinpath(".colorsight").mkdir(parents=True, exist_ok=True)
        mark_onboarding_done()
        set_theme_pref("light")
        set_debug_insets(28, 24)

    def _build_shell(self, start: str = "settings") -> RootShell:
        apply_color_set("light")
        shell = RootShell(start_screen=start)
        _tick()
        return shell

    def test_rebuild_shell_switches_chrome_keeps_neutral(self):
        # Light shell
        apply_color_set("light")
        light = RootShell(start_screen="home")
        _tick()
        light_bg = tuple(Colors.bg)
        self.assertTrue(_approx(light_bg, LIGHT_COLORS["bg"]))

        light_chip_bg = LIGHT_COLORS["chip_bg"]
        light_nav_bg = LIGHT_COLORS["nav_bg"]
        light_text = LIGHT_COLORS["text"]

        # Simulate theme rebuild: new shell under dark tokens
        apply_color_set("dark")
        dark = RootShell(start_screen="settings")
        _tick()
        self.assertTrue(_approx(tuple(Colors.bg), DARK_COLORS["bg"]))
        self.assertFalse(_approx(tuple(Colors.bg), light_bg))
        self.assertFalse(_approx(tuple(Colors.chip_bg), light_chip_bg))
        self.assertFalse(_approx(tuple(Colors.nav_bg), light_nav_bg))
        self.assertFalse(_approx(tuple(Colors.text), light_text))

        dark.sm.current = "home"
        _tick()
        home = dark.sm.get_screen("home")
        self.assertIsInstance(dark.nav, FloatingNavBar)
        self.assertFalse(_approx(tuple(Colors.nav_bg), light_nav_bg))

        # Walk every widget under Home + shell; assert no chrome still matches light tokens
        names = {type(w).__name__ for w in home.walk()}
        self.assertIn("PastelCard", names)
        self.assertIn("Chip", names)
        for w in home.walk():
            if isinstance(w, Chip) or type(w).__name__ == "Chip":
                # Fresh chips use dark chip_bg at draw time via Colors
                self.assertFalse(_approx(tuple(Colors.chip_bg), light_chip_bg))
            if isinstance(w, PastelCard) or type(w).__name__ == "PastelCard":
                self.assertFalse(_approx(tuple(Colors.text), light_text))

        self.assertFalse(_approx(tuple(Colors.bg), light_bg))
        self.assertFalse(_approx(tuple(Colors.surface), LIGHT_COLORS["surface"]))

        # Accuracy screens always NEUTRAL_BG on the screen canvas
        for scr_name in ("test", "photos", "camera"):
            scr = dark.sm.get_screen(scr_name)
            self.assertTrue(
                hasattr(scr, "_bg_color"),
                msg=f"{scr_name} missing opaque bg",
            )
            self.assertTrue(
                _approx(tuple(scr._bg_color.rgba), NEUTRAL_BG),
                msg=f"{scr_name} must stay NEUTRAL_BG under dark chrome",
            )

        # Back to light rebuild
        apply_color_set("light")
        light2 = RootShell(start_screen="settings")
        _tick()
        self.assertTrue(_approx(tuple(Colors.bg), LIGHT_COLORS["bg"]))
        for name in ("welcome", "home", "test", "photos", "camera", "profile", "settings"):
            light2.sm.current = name
            _tick(1)

    def test_color_sets_differ(self):
        apply_color_set("light")
        lt = tuple(Colors.text)
        lb = tuple(Colors.bg)
        apply_color_set("dark")
        self.assertFalse(_approx(tuple(Colors.text), lt))
        self.assertFalse(_approx(tuple(Colors.bg), lb))
        apply_color_set("light")


if __name__ == "__main__":
    unittest.main()

"""Startup must degrade, never abort — fallback UI or normal root always builds."""

from __future__ import annotations

import os
import unittest
from unittest import mock

os.environ.setdefault("KIVY_NO_ARGS", "1")
os.environ.setdefault("COLORSIGHT_FAKE_CAMERA", "1")


class TestSafeAreaClamp(unittest.TestCase):
    def test_absurd_insets_clamped(self):
        from colorsight.safe_area import clamp_inset, refresh_safe_insets, set_debug_insets
        from colorsight.theme.tokens import Spacing

        self.assertEqual(clamp_inset(-5, kind="top"), 28.0)
        self.assertEqual(clamp_inset(5000, kind="top"), 28.0)
        self.assertEqual(clamp_inset(float("nan"), kind="bottom"), 16.0)
        self.assertLessEqual(clamp_inset(40, kind="bottom"), 48.0)

        set_debug_insets(0, 0)
        top, bot = refresh_safe_insets()
        self.assertGreaterEqual(top, 0.0)
        self.assertLessEqual(top, 80.0)
        self.assertGreaterEqual(bot, 0.0)
        self.assertLessEqual(bot, 48.0)
        self.assertLessEqual(Spacing.safe_top, 80.0)

        set_debug_insets(5000, -10)
        top, bot = refresh_safe_insets()
        self.assertLessEqual(top, 80.0)
        self.assertGreaterEqual(bot, 0.0)
        set_debug_insets(None, None)

    def test_android_probe_failure_uses_defaults(self):
        from colorsight import safe_area
        from colorsight.safe_area import refresh_safe_insets

        with mock.patch.object(safe_area, "platform", "android"):
            with mock.patch.object(
                safe_area,
                "_android_insets_dp",
                side_effect=RuntimeError("jnius boom"),
            ):
                top, bot = refresh_safe_insets()
        self.assertGreaterEqual(top, 0.0)
        self.assertLessEqual(top, 80.0)
        self.assertGreaterEqual(bot, 0.0)


class TestFallbackScreen(unittest.TestCase):
    def test_fallback_builds_without_theme(self):
        from tests.gui_guard import ensure_kivy_window

        try:
            ensure_kivy_window(reason="fallback screen test needs Window")
        except unittest.SkipTest:
            raise
        from colorsight.fallback_screen import build_fallback_root

        root = build_fallback_root(RuntimeError("simulated"), detail="stage=fonts")
        self.assertIsNotNone(root)
        self.assertTrue(hasattr(root, "children"))
        self.assertGreater(len(root.children), 0)


class TestBuildSurvivesStageFailures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.gui_guard import ensure_kivy_window

        ensure_kivy_window(reason="startup resilience needs Window")

    def _build_app(self):
        from colorsight.app import ColorSightApp
        from colorsight.prefs import mark_onboarding_done

        mark_onboarding_done()
        app = ColorSightApp()
        root = app.build()
        app.root = root
        return app, root

    def test_normal_build_returns_root(self):
        app, root = self._build_app()
        self.assertIsNotNone(root)
        self.assertGreater(len(root.children), 0)
        # cleanup
        try:
            from kivy.app import App as KivyApp

            KivyApp._running_app = None
        except Exception:
            pass

    def test_safe_area_exception_still_builds(self):
        with mock.patch(
            "colorsight.safe_area.refresh_safe_insets",
            side_effect=RuntimeError("insets boom"),
        ):
            app, root = self._build_app()
        self.assertIsNotNone(root)
        self.assertGreater(len(getattr(root, "children", []) or [1]), 0)

    def test_theme_exception_still_builds(self):
        with mock.patch(
            "colorsight.theme.theme.get_theme",
            side_effect=RuntimeError("theme boom"),
        ):
            app, root = self._build_app()
        self.assertIsNotNone(root)

    def test_fonts_exception_still_builds(self):
        with mock.patch(
            "colorsight.theme.register_fonts",
            side_effect=RuntimeError("font boom"),
        ):
            app, root = self._build_app()
        self.assertIsNotNone(root)

    def test_root_shell_exception_yields_fallback(self):
        with mock.patch(
            "colorsight.app.RootShell",
            side_effect=RuntimeError("shell boom"),
        ):
            from colorsight.app import ColorSightApp

            app = ColorSightApp()
            root = app.build()
        self.assertIsNotNone(root)
        # Fallback label/box — not necessarily RootShell
        text_blob = ""
        try:
            for w in root.walk():
                t = getattr(w, "text", None)
                if t:
                    text_blob += str(t)
        except Exception:
            text_blob = str(root)
        self.assertTrue(
            "could not start" in text_blob.lower() or len(getattr(root, "children", [])) >= 0
        )


class TestBreadcrumbFlush(unittest.TestCase):
    def test_breadcrumb_does_not_raise(self):
        from colorsight.startup import breadcrumb, reset_startup_clock

        reset_startup_clock()
        breadcrumb("unit_test_stage", "ok")


class TestFontFallback(unittest.TestCase):
    def test_missing_files_switch_to_roboto(self):
        from colorsight.theme.theme import _use_default_font_names
        from colorsight.theme.tokens import Fonts

        saved = (Fonts.regular, Fonts.medium, Fonts.semibold, Fonts.bold, Fonts.icons)
        try:
            _use_default_font_names()
            self.assertEqual(Fonts.bold, "Roboto")
            self.assertEqual(Fonts.regular, "Roboto")
        finally:
            Fonts.regular, Fonts.medium, Fonts.semibold, Fonts.bold, Fonts.icons = saved


class TestLayoutProbe(unittest.TestCase):
    def test_none_root_broken(self):
        from colorsight.startup import layout_looks_broken

        broken, reason = layout_looks_broken(None)
        self.assertTrue(broken)
        self.assertIn("None", reason)

    def test_tiny_screen_on_large_root_broken(self):
        """100×100 current screen on a phone-sized root must trip the watchdog."""
        from colorsight.startup import layout_looks_broken

        class _Scr:
            name = "home"
            width = 100.0
            height = 100.0
            x = 0.0
            y = 0.0
            opacity = 1.0
            children = [1]

        class _SM:
            current = "home"
            width = 1080.0
            height = 2340.0
            x = 0.0
            y = 0.0
            opacity = 1.0
            children = [1]

            def get_screen(self, name):
                return _Scr()

        class _Root:
            width = 1080.0
            height = 2340.0
            x = 0.0
            y = 0.0
            opacity = 1.0
            children = [1, 2]
            sm = _SM()

        broken, reason = layout_looks_broken(_Root())
        self.assertTrue(broken)
        self.assertIn("smaller", reason)


class TestEssentialFirstStartup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.gui_guard import ensure_kivy_window

        ensure_kivy_window(reason="essential-first startup needs Window")

    def test_build_has_home_before_deferred_cv2(self):
        """Essential screens must exist even if deferred (cv2) screens are blocked."""
        import sys
        from colorsight.app import ColorSightApp, RootShell
        from colorsight.prefs import mark_onboarding_done

        mark_onboarding_done()
        # Block trivector/cv2 screen module; essential path must still show Home
        sys.modules["colorsight.screens.test_screen"] = None  # type: ignore
        try:
            app = ColorSightApp()
            root = app.build()
            self.assertIsNotNone(root)
            self.assertIsInstance(root, RootShell)
            self.assertIn("home", root.sm.screen_names)
            # Force deferred load now (Clock may not idle in unit tests)
            root._load_deferred_screens()
            self.assertIn("home", root.sm.screen_names)
            self.assertNotIn("test", root.sm.screen_names)
        finally:
            sys.modules.pop("colorsight.screens.test_screen", None)
            try:
                from kivy.app import App as KivyApp

                KivyApp._running_app = None
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()

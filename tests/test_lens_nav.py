"""Regression: Home → Lens → Camera → Lens → Back must not raise."""

from __future__ import annotations

import os
import unittest

# Fake camera / no-arg Kivy before any Kivy import
os.environ.setdefault("COLORSIGHT_FAKE_CAMERA", "1")
os.environ.setdefault("KIVY_NO_ARGS", "1")


class TestLensNavNoCrash(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Lazy imports so a missing display cannot abort the whole suite at import time
        from tests.gui_guard import ensure_kivy_window

        ensure_kivy_window(reason="Lens nav regression needs a Kivy Window")

        from kivy.config import Config

        Config.set("graphics", "width", "390")
        Config.set("graphics", "height", "844")
        Config.set("graphics", "resizable", "0")

    def test_home_lens_camera_lens_back_loop(self):
        from kivy.clock import Clock

        from colorsight.app import ColorSightApp, RootShell
        from colorsight.prefs import mark_onboarding_done

        mark_onboarding_done()
        app = ColorSightApp()
        root = app.build()
        self.assertIsInstance(root, RootShell)
        app.root = root
        sm = root.sm
        errors: list[BaseException] = []

        def _pump(seconds: float = 0.05):
            # Advance scheduled Clock events without a full App.run()
            Clock.tick()
            for _ in range(max(1, int(seconds * 60))):
                Clock.tick()

        try:
            sm.current = "home"
            _pump()
            for _ in range(4):
                root._navigate("lens")
                _pump(0.08)
                self.assertEqual(sm.current, "camera")
                cam = sm.get_screen("camera")
                self.assertTrue(getattr(cam, "_loupe_on", False))
                self.assertEqual(root.nav.active, "lens")

                root._navigate("camera")
                _pump(0.08)
                self.assertEqual(sm.current, "camera")
                self.assertFalse(getattr(cam, "_loupe_on", False))

                root._navigate("lens")
                _pump(0.08)
                self.assertTrue(getattr(cam, "_loupe_on", False))

                root.go_back()
                _pump(0.08)
                self.assertEqual(sm.current, "home")
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)
            raise
        finally:
            try:
                cam = sm.get_screen("camera")
                cam.on_leave()
            except Exception:
                pass
            try:
                # Do not leave a stale App for later tests' Clock marshaling
                from kivy.app import App as KivyApp

                KivyApp._running_app = None
            except Exception:
                pass

        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()

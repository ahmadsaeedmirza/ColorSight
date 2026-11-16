"""ColorSight application shell — crash-proof startup + layout sanity."""

from __future__ import annotations

import logging

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import FadeTransition, NoTransition, ScreenManager

from colorsight.exception_guard import install_exception_handler, reset_fallback_gate
from colorsight.logging_setup import setup_logging
from colorsight.startup import (
    breadcrumb,
    describe_widget,
    first_frame_drawn,
    layout_looks_broken,
    mark_first_frame,
    reset_startup_clock,
)

log = logging.getLogger("colorsight")

# Back stack for consistent navigation
_BACK_HOME = {"test", "settings", "photos", "camera", "lens", "profile", "log_viewer"}

# Accuracy-safe neutral surfaces (theme never skews these)
_NEUTRAL_SCREENS = {"test", "photos", "camera", "lens"}


def show_fallback_error(exc: BaseException | None = None, detail: str = "") -> None:
    """Replace the app root with the plain fallback error screen."""
    try:
        from colorsight.fallback_screen import build_fallback_root

        app = App.get_running_app()
        if app is None:
            return
        new_root = build_fallback_root(exc, detail=detail)
        old = app.root
        app.root = new_root
        if old is not None:
            try:
                Window.remove_widget(old)
            except Exception:
                try:
                    if getattr(old, "parent", None) is not None:
                        old.parent.remove_widget(old)
                except Exception:
                    pass
        if getattr(new_root, "parent", None) is None:
            Window.add_widget(new_root)
        breadcrumb("fallback_shown", detail[:80] if detail else (type(exc).__name__ if exc else ""))
        log.error("fallback error screen shown: %s", detail or exc)
    except Exception:
        log.exception("show_fallback_error failed")


class RootShell(FloatLayout):
    """ScreenManager + floating nav; nav hidden on welcome."""

    NAV_SCREENS = {"home", "photos", "camera", "lens", "profile", "test", "settings"}

    def __init__(self, start_screen: str | None = None, **kwargs):
        super().__init__(**kwargs)
        # Explicit fill — never rely on a one-shot Window.size at import time
        self.size_hint = (1, 1)
        with self.canvas.before:
            from colorsight.theme.tokens import Colors

            self._bg_color = Color(*Colors.bg)
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._sync_bg, size=self._sync_bg)

        breadcrumb("sm_create")
        self.sm = ScreenManager(
            transition=NoTransition(),
            size_hint=(1, 1),
        )
        self.bind(size=self._sync_sm, pos=self._sync_sm)

        from colorsight.theme.screen_bg import install_opaque_bg

        screen_ctors = self._screen_ctors()
        for name, ctor in screen_ctors:
            breadcrumb("screen_build_begin", name)
            try:
                screen = ctor()
                if not hasattr(screen, "_bg_rect"):
                    install_opaque_bg(
                        screen, neutral=(screen.name in _NEUTRAL_SCREENS)
                    )
                self.sm.add_widget(screen)
                breadcrumb("screen_build_ok", name)
            except Exception as exc:
                log.exception("screen build failed: %s", name)
                breadcrumb("screen_build_fail", f"{name} {type(exc).__name__}")

        breadcrumb("nav_build")
        from colorsight.widgets import FloatingNavBar

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
            try:
                from colorsight.prefs import is_first_run

                initial = "welcome" if is_first_run() else "home"
            except Exception:
                initial = "home"
        if initial not in self.sm.screen_names and self.sm.screen_names:
            initial = self.sm.screen_names[0]
        if self.sm.screen_names:
            self.sm.current = initial
            self._on_screen(self.sm, self.sm.current)
            # Restore soft fade after first paint
            Clock.schedule_once(self._enable_fade, 0)

        Window.bind(on_keyboard=self._on_key)
        if not self.sm.screen_names:
            # Every screen failed (often missing fonts) — raise so build() shows fallback
            raise RuntimeError(
                "No screens could be built (check fonts / startup log). "
                "Labels need registered fonts or Roboto fallback."
            )
        breadcrumb("root_shell_ready", f"current={getattr(self.sm, 'current', None)}")

    def _screen_ctors(self):
        # Import screens lazily so a broken module cannot kill the whole shell
        from colorsight.screens import (
            CameraScreen,
            HomeScreen,
            LensScreen,
            LogViewerScreen,
            PhotosScreen,
            ProfileScreen,
            SettingsScreen,
            TestScreen,
            WelcomeScreen,
        )

        return (
            ("welcome", WelcomeScreen),
            ("home", HomeScreen),
            ("test", TestScreen),
            ("photos", PhotosScreen),
            ("camera", CameraScreen),
            ("lens", LensScreen),
            ("profile", ProfileScreen),
            ("settings", SettingsScreen),
            ("log_viewer", LogViewerScreen),
        )

    def _enable_fade(self, *_a):
        try:
            self.sm.transition = FadeTransition(duration=0.22)
        except Exception:
            pass

    def _sync_sm(self, *_a):
        self.sm.pos = self.pos
        self.sm.size = self.size

    def _sync_bg(self, *_args):
        self._bg.pos = self.pos
        self._bg.size = self.size
        try:
            from colorsight.theme.tokens import Colors

            self._bg_color.rgba = Colors.bg
        except Exception:
            pass

    def _place_nav(self, *_args):
        try:
            from colorsight.theme.tokens import Spacing

            margin = dp(Spacing.nav_margin)
            bottom = dp(Spacing.safe_bottom)
        except Exception:
            margin, bottom = dp(12), dp(16)
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
        if key == "lens":
            self._navigate_lens()
            return
        if key == "camera":
            try:
                cam = self.sm.get_screen("camera")
                if getattr(cam, "_loupe_on", False) and hasattr(cam, "set_loupe_enabled"):
                    cam.set_loupe_enabled(False)
            except Exception:
                log.exception("camera nav: clear loupe failed")
        if key in self.sm.screen_names:
            self.sm.transition.direction = "left"
            self.sm.current = key

    def _navigate_lens(self):
        try:
            self.sm.transition.direction = "left"
            if self.sm.current != "camera":
                self.sm.current = "camera"
            self.nav.active = "lens"
            Clock.schedule_once(self._enable_lens_loupe, 0)
        except Exception:
            log.exception("navigate lens failed")

    def _enable_lens_loupe(self, *_a):
        try:
            cam = self.sm.get_screen("camera")
            if hasattr(cam, "set_loupe_enabled"):
                cam.set_loupe_enabled(True)
            self.nav.active = "lens"
        except Exception:
            log.exception("enable lens loupe failed")

    def set_nav_active(self, screen_name: str):
        if screen_name == "lens":
            self._navigate_lens()
            return
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
        reset_startup_clock()
        reset_fallback_gate()
        try:
            return self._build_ui()
        except Exception as exc:
            log.exception("build() failed")
            breadcrumb("build_fatal", type(exc).__name__)
            try:
                from colorsight.fallback_screen import build_fallback_root

                return build_fallback_root(exc)
            except Exception as exc2:
                log.exception("fallback build also failed: %s", exc2)
                # Absolute last resort
                from kivy.uix.label import Label

                return Label(text=f"ColorSight could not start\n{type(exc).__name__}: {exc}")

    def _build_ui(self):
        breadcrumb("logging_setup_begin")
        setup_logging()
        breadcrumb("logging_setup_done")

        breadcrumb("exception_handler")
        install_exception_handler()

        breadcrumb("fonts_begin")
        try:
            from colorsight.theme import register_fonts

            register_fonts()
        except Exception as exc:
            log.warning("fonts failed: %s", exc)
            try:
                from colorsight.theme.theme import _use_default_font_names

                _use_default_font_names()
            except Exception:
                pass
        breadcrumb("fonts_done")

        breadcrumb("safe_area_begin")
        try:
            from colorsight.safe_area import refresh_safe_insets

            refresh_safe_insets()
        except Exception as exc:
            log.warning("safe_area failed: %s", exc)
        breadcrumb("safe_area_done")

        breadcrumb("prefs_theme_begin")
        try:
            from colorsight.prefs import get_theme_pref
            from colorsight.theme.theme import get_theme
            from colorsight.theme.tokens import Colors

            theme = get_theme()
            pref = get_theme_pref()
            if pref not in ("system", "light", "dark"):
                pref = "light"
            theme.preference = pref
            theme.apply(rebuild=False)
            Window.clearcolor = Colors.bg
        except Exception as exc:
            log.warning("theme/prefs failed — Light fallback: %s", exc)
            try:
                from colorsight.theme.tokens import apply_color_set

                apply_color_set("light")
                Window.clearcolor = (1, 1, 1, 1)
            except Exception:
                Window.clearcolor = (1, 1, 1, 1)
        breadcrumb("prefs_theme_done")

        breadcrumb("profile_load_begin")
        try:
            from colorsight.storage import profile_path
            from core.profile import CorrectionProfile

            path = profile_path()
            if path.is_file():
                self.correction_profile = CorrectionProfile.load(path)
                breadcrumb("profile_load_ok")
            else:
                breadcrumb("profile_load_none")
        except Exception as exc:
            log.warning("profile load failed: %s", exc)
            breadcrumb("profile_load_fail", type(exc).__name__)

        Window.bind(on_resize=self._on_window_resize)
        breadcrumb("root_shell_begin")
        shell = RootShell()
        breadcrumb("root_shell_done")
        Clock.schedule_once(self._after_first_frame, 0)
        Clock.schedule_once(self._layout_watchdog, 3.0)
        return shell

    def _after_first_frame(self, *_a):
        if App.get_running_app() is not None and App.get_running_app() is not self:
            return
        mark_first_frame()
        root = self.root
        breadcrumb("first_frame", describe_widget(root))
        try:
            if isinstance(root, RootShell):
                # Ensure SM fills the shell after Window has a real size
                root._sync_sm()
                breadcrumb("layout_root", describe_widget(root))
                breadcrumb("layout_sm", describe_widget(root.sm))
                try:
                    cur = root.sm.get_screen(root.sm.current)
                    breadcrumb("layout_current", describe_widget(cur))
                except Exception as exc:
                    breadcrumb("layout_current_fail", str(exc))
                for name in list(root.sm.screen_names)[:6]:
                    try:
                        breadcrumb("layout_screen", describe_widget(root.sm.get_screen(name)))
                    except Exception:
                        pass
            broken, reason = layout_looks_broken(root)
            if broken:
                log.error("layout broken after first frame: %s", reason)
                show_fallback_error(None, detail=reason)
        except Exception:
            log.exception("after_first_frame probe failed")

    def _layout_watchdog(self, *_a):
        """If nothing visible after 3s, show the fallback error screen."""
        try:
            if App.get_running_app() is not None and App.get_running_app() is not self:
                return
            root = self.root
            if root is None:
                show_fallback_error(None, detail="root is None after 3s")
                return
            # Already on fallback
            if not isinstance(root, RootShell) and not hasattr(root, "sm"):
                return
            if isinstance(root, RootShell):
                root._sync_sm()
            broken, reason = layout_looks_broken(root)
            if broken or not first_frame_drawn():
                detail = reason or "first frame never drawn / layout invalid after 3s"
                breadcrumb("watchdog_fallback", detail)
                show_fallback_error(None, detail=detail)
        except Exception:
            log.exception("layout watchdog failed")

    def rebuild_ui(self, return_to: str | None = None):
        """Recreate ScreenManager + screens + nav with current tokens/insets."""
        if self._rebuilding:
            return
        self._rebuilding = True
        reset_fallback_gate()
        try:
            breadcrumb("rebuild_begin", return_to or "")
            try:
                from colorsight.safe_area import refresh_safe_insets
                from colorsight.theme.tokens import Colors

                refresh_safe_insets()
                Window.clearcolor = Colors.bg
            except Exception as exc:
                log.warning("rebuild preamble failed: %s", exc)
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
            breadcrumb("rebuild_done", cur or "")
            Clock.schedule_once(self._after_first_frame, 0)
            Clock.schedule_once(self._layout_watchdog, 3.0)
        except Exception as exc:
            log.exception("rebuild_ui failed")
            breadcrumb("rebuild_fatal", type(exc).__name__)
            show_fallback_error(exc, detail="rebuild_ui failed")
        finally:
            self._rebuilding = False

    def _on_window_resize(self, *_a):
        try:
            from colorsight.safe_area import refresh_safe_insets

            refresh_safe_insets()
        except Exception:
            pass
        root = self.root
        if isinstance(root, RootShell):
            root._place_nav()
            root._sync_sm()

    def on_pause(self):
        root = self.root
        if root is not None and hasattr(root, "sm"):
            try:
                scr = root.sm.get_screen(root.sm.current)
                if hasattr(scr, "on_pause"):
                    scr.on_pause()
            except Exception:
                pass
        return True

    def on_resume(self):
        root = self.root
        if root is not None and hasattr(root, "sm"):
            try:
                scr = root.sm.get_screen(root.sm.current)
                if hasattr(scr, "on_resume"):
                    scr.on_resume()
            except Exception:
                pass
        try:
            from colorsight.safe_area import refresh_safe_insets

            refresh_safe_insets()
        except Exception:
            pass
        try:
            from colorsight.theme.theme import get_theme, system_prefers_dark

            theme = get_theme()
            if theme.preference == "system":
                dark = system_prefers_dark()
                if self._last_system_dark is None or dark != self._last_system_dark:
                    self._last_system_dark = dark
                    cur = root.sm.current if isinstance(root, RootShell) else None
                    theme.apply(rebuild=True, return_to=cur)
                elif isinstance(root, RootShell):
                    root._place_nav()
            elif isinstance(root, RootShell):
                root._place_nav()
        except Exception:
            log.exception("on_resume theme failed")

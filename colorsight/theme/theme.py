"""Font registration + live light/dark theme controller."""

from __future__ import annotations

import logging
from pathlib import Path

from kivy.app import App
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.event import EventDispatcher
from kivy.properties import NumericProperty, StringProperty
from kivy.utils import platform

from .tokens import Fonts, apply_color_set

log = logging.getLogger("colorsight.theme")

_ROOT = Path(__file__).resolve().parents[2]
_FONTS_DIR = _ROOT / "assets" / "fonts"
_ICONS_DIR = _ROOT / "assets" / "icons"
_registered = False


def _use_default_font_names() -> None:
    """Point Fonts.* at Kivy's built-in Roboto so Labels never look for missing TTF files."""
    Fonts.regular = "Roboto"
    Fonts.medium = "Roboto"
    Fonts.semibold = "Roboto"
    Fonts.bold = "Roboto"
    # Icons will show as tofu without MaterialIcons — better than a blank app
    Fonts.icons = "Roboto"


def register_fonts() -> None:
    global _registered
    if _registered:
        return
    # Prefer Android/app cwd + __file__ parents so packaged APKs resolve assets/
    fonts_dir, icons_dir = _resolve_asset_dirs()
    files = (
        (fonts_dir / "Lexend-Regular.ttf", Fonts.regular),
        (fonts_dir / "Lexend-Medium.ttf", Fonts.medium),
        (fonts_dir / "Lexend-SemiBold.ttf", Fonts.semibold),
        (fonts_dir / "Lexend-Bold.ttf", Fonts.bold),
        (icons_dir / "MaterialIcons-Regular.ttf", Fonts.icons),
    )
    missing = [str(p) for p, _ in files if not p.is_file()]
    if missing:
        log.warning("font files missing — using Roboto defaults: %s", missing)
        _use_default_font_names()
        _registered = True
        return
    try:
        for path, name in files:
            LabelBase.register(name=name, fn_regular=str(path))
        _registered = True
        log.info("fonts registered Lexend + MaterialIcons from %s", fonts_dir)
    except Exception as exc:
        log.warning("font registration failed (using Roboto defaults): %s", exc)
        _use_default_font_names()
        _registered = True  # do not retry forever


def _resolve_asset_dirs() -> tuple[Path, Path]:
    """Find assets/fonts and assets/icons on desktop and inside the APK tree."""
    candidates: list[Path] = []
    try:
        candidates.append(Path(__file__).resolve().parents[2])
    except Exception:
        pass
    try:
        import os

        arg = os.environ.get("ANDROID_ARGUMENT") or os.environ.get("ANDROID_APP_PATH")
        if arg:
            candidates.append(Path(arg))
    except Exception:
        pass
    try:
        candidates.append(Path.cwd())
    except Exception:
        pass
    for root in candidates:
        fonts = root / "assets" / "fonts"
        icons = root / "assets" / "icons"
        if (fonts / "Lexend-Regular.ttf").is_file():
            return fonts, icons if icons.is_dir() else _ICONS_DIR
    return _FONTS_DIR, _ICONS_DIR


def verify_fonts_usable() -> bool:
    """Return False only when Labels cannot resolve Fonts.bold (missing file).

    An empty texture_size before the GL context is fully ready is NOT a failure —
    that previously forced Roboto on every launch.
    """
    try:
        from kivy.uix.label import Label

        lbl = Label(text="Ag", font_name=Fonts.bold, font_size=12)
        try:
            lbl.texture_update()
        except Exception:
            pass
        return True
    except OSError as exc:
        log.warning("font probe OSError for %s: %s", Fonts.bold, exc)
        return False
    except Exception as exc:
        # Unexpected — keep registered names; screen builds will catch real failures
        log.warning("font probe soft-fail for %s: %s", Fonts.bold, exc)
        return True


def font_name(weight: str = "regular") -> str:
    return {
        "regular": Fonts.regular,
        "medium": Fonts.medium,
        "semibold": Fonts.semibold,
        "bold": Fonts.bold,
        "icons": Fonts.icons,
    }.get(weight, Fonts.regular)


def system_prefers_dark() -> bool:
    """Android: Configuration.uiMode & UI_MODE_NIGHT_MASK. Desktop / failure: False (Light)."""
    if platform != "android":
        return False
    try:
        from jnius import autoclass

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Configuration = autoclass("android.content.res.Configuration")
        activity = PythonActivity.mActivity
        if activity is None:
            return False
        ui_mode = activity.getResources().getConfiguration().uiMode
        night = ui_mode & Configuration.UI_MODE_NIGHT_MASK
        return night == Configuration.UI_MODE_NIGHT_YES
    except Exception as exc:
        log.warning("system dark-mode probe failed (Light fallback): %s", exc)
        return False


def _rgba_to_argb_int(rgba) -> int:
    """Kivy (r,g,b,a) floats 0–1 → Android Color int (opaque)."""
    r = max(0, min(255, int(round(float(rgba[0]) * 255))))
    g = max(0, min(255, int(round(float(rgba[1]) * 255))))
    b = max(0, min(255, int(round(float(rgba[2]) * 255))))
    return (0xFF << 24) | (r << 16) | (g << 8) | b


def apply_system_bars(resolved: str | None = None) -> None:
    """Paint Android status + nav bars to match the theme (kills white system chrome).

    Desktop: no-op. Failures are logged and ignored — UI still runs.
    """
    if platform != "android":
        return
    try:
        from colorsight.theme.tokens import Colors

        resolved = (resolved or "light").lower()
        # Match app canvas so letterboxed edges never flash cream/white
        Window.clearcolor = Colors.bg
        color_int = _rgba_to_argb_int(Colors.bg)
        light_icons = resolved != "dark"  # dark icons on light bars

        from jnius import autoclass

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        if activity is None:
            return
        View = autoclass("android.view.View")
        window = activity.getWindow()
        # Draw app behind system bars, then color the bars themselves
        try:
            LayoutParams = autoclass("android.view.WindowManager$LayoutParams")
            window.addFlags(LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS)
            try:
                window.clearFlags(LayoutParams.FLAG_TRANSLUCENT_STATUS)
                window.clearFlags(LayoutParams.FLAG_TRANSLUCENT_NAVIGATION)
            except Exception:
                pass
        except Exception:
            pass
        try:
            window.setStatusBarColor(color_int)
            window.setNavigationBarColor(color_int)
        except Exception as exc:
            log.warning("system bar color set failed: %s", exc)
            return

        # Icon contrast: light bars → dark icons; dark bars → light icons
        try:
            decor = window.getDecorView()
            flags = decor.getSystemUiVisibility()
            LIGHT_STATUS = View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR
            # LIGHT_NAVIGATION_BAR = 0x00000010 on API 26+
            LIGHT_NAV = 16
            if light_icons:
                flags = flags | LIGHT_STATUS | LIGHT_NAV
            else:
                flags = flags & ~LIGHT_STATUS & ~LIGHT_NAV
            decor.setSystemUiVisibility(flags)
        except Exception as exc:
            log.debug("systemUiVisibility tweak skipped: %s", exc)
        log.info("system bars applied resolved=%s", resolved)
    except Exception as exc:
        log.warning("apply_system_bars failed: %s", exc)


class ThemeController(EventDispatcher):
    """preference: system | light | dark; revision bumps on every apply."""

    preference = StringProperty("system")
    resolved = StringProperty("light")
    revision = NumericProperty(0)

    def set_preference(self, pref: str, *, persist: bool = True, return_to: str | None = "settings"):
        pref = (pref or "system").lower()
        if pref not in ("system", "light", "dark"):
            pref = "system"
        self.preference = pref
        if persist:
            try:
                from colorsight.prefs import load_prefs, save_prefs

                data = load_prefs()
                data["theme"] = pref
                save_prefs(data)
            except Exception as exc:
                log.warning("theme pref save failed: %s", exc)
        self.apply(rebuild=True, return_to=return_to)

    def apply(self, *, rebuild: bool = True, return_to: str | None = None):
        try:
            pref = (self.preference or "light").lower()
            if pref not in ("system", "light", "dark"):
                pref = "light"
                self.preference = "light"
            if pref == "dark":
                resolved = "dark"
            elif pref == "light":
                resolved = "light"
            else:
                try:
                    resolved = "dark" if system_prefers_dark() else "light"
                except Exception:
                    resolved = "light"
            apply_color_set(resolved)
            self.resolved = resolved
            from colorsight.theme.tokens import Colors

            Window.clearcolor = Colors.bg
            try:
                apply_system_bars(resolved)
            except Exception:
                pass
            self.revision += 1
            log.info("theme applied preference=%s resolved=%s", self.preference, resolved)
        except Exception as exc:
            log.warning("theme apply failed — forcing Light: %s", exc)
            try:
                apply_color_set("light")
                self.resolved = "light"
                self.preference = "light"
                from colorsight.theme.tokens import Colors

                Window.clearcolor = Colors.bg
                apply_system_bars("light")
            except Exception:
                pass
            return

        app = App.get_running_app()
        if rebuild and app is not None and hasattr(app, "rebuild_ui"):
            # Full in-process UI rebuild so canvas colors cannot stay stale
            app.rebuild_ui(return_to=return_to)
        elif app is not None and getattr(app, "root", None) is not None:
            _refresh_tree(app.root)

_controller: ThemeController | None = None


def get_theme() -> ThemeController:
    global _controller
    if _controller is None:
        _controller = ThemeController()
    return _controller


def _refresh_tree(root):
    """Legacy walk — used only when rebuild_ui is unavailable."""
    from colorsight.theme.tokens import Colors

    if hasattr(root, "_bg") and hasattr(root, "_bg_color"):
        try:
            root._bg_color.rgba = Colors.bg
        except Exception:
            pass
    for w in root.walk():
        fn = getattr(w, "apply_theme", None)
        if callable(fn):
            try:
                fn()
            except Exception as exc:
                log.debug("apply_theme failed on %s: %s", type(w).__name__, exc)

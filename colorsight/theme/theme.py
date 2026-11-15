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


def register_fonts() -> None:
    global _registered
    if _registered:
        return
    LabelBase.register(
        name=Fonts.regular,
        fn_regular=str(_FONTS_DIR / "Lexend-Regular.ttf"),
    )
    LabelBase.register(
        name=Fonts.medium,
        fn_regular=str(_FONTS_DIR / "Lexend-Medium.ttf"),
    )
    LabelBase.register(
        name=Fonts.semibold,
        fn_regular=str(_FONTS_DIR / "Lexend-SemiBold.ttf"),
    )
    LabelBase.register(
        name=Fonts.bold,
        fn_regular=str(_FONTS_DIR / "Lexend-Bold.ttf"),
    )
    LabelBase.register(
        name=Fonts.icons,
        fn_regular=str(_ICONS_DIR / "MaterialIcons-Regular.ttf"),
    )
    _registered = True


def font_name(weight: str = "regular") -> str:
    return {
        "regular": Fonts.regular,
        "medium": Fonts.medium,
        "semibold": Fonts.semibold,
        "bold": Fonts.bold,
        "icons": Fonts.icons,
    }.get(weight, Fonts.regular)


def system_prefers_dark() -> bool:
    """Android: Configuration.uiMode & UI_MODE_NIGHT_MASK. Desktop: False (Light)."""
    if platform != "android":
        return False
    try:
        from jnius import autoclass

        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Configuration = autoclass("android.content.res.Configuration")
        activity = PythonActivity.mActivity
        ui_mode = activity.getResources().getConfiguration().uiMode
        night = ui_mode & Configuration.UI_MODE_NIGHT_MASK
        return night == Configuration.UI_MODE_NIGHT_YES
    except Exception as exc:
        log.warning("system dark-mode probe failed: %s", exc)
        return False


class ThemeController(EventDispatcher):
    """preference: system | light | dark; revision bumps on every apply."""

    preference = StringProperty("system")
    resolved = StringProperty("light")
    revision = NumericProperty(0)

    def set_preference(self, pref: str, *, persist: bool = True):
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
        self.apply()

    def apply(self):
        if self.preference == "dark":
            resolved = "dark"
        elif self.preference == "light":
            resolved = "light"
        else:
            resolved = "dark" if system_prefers_dark() else "light"
        apply_color_set(resolved)
        self.resolved = resolved
        self.revision += 1
        from colorsight.theme.tokens import Colors

        Window.clearcolor = Colors.bg
        app = App.get_running_app()
        if app is not None and getattr(app, "root", None) is not None:
            _refresh_tree(app.root)
        log.info("theme applied preference=%s resolved=%s", self.preference, resolved)


_controller: ThemeController | None = None


def get_theme() -> ThemeController:
    global _controller
    if _controller is None:
        _controller = ThemeController()
    return _controller


def _refresh_tree(root):
    from colorsight.theme.tokens import Colors

    # Root opaque bg
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

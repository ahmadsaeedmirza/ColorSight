"""Font / icon registration and theme helpers."""

from pathlib import Path

from kivy.core.text import LabelBase

from .tokens import Fonts

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

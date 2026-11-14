"""Font registration and theme helpers."""

from pathlib import Path

from kivy.core.text import LabelBase

from .tokens import Fonts

_FONTS_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"
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
    _registered = True


def font_name(weight: str = "regular") -> str:
    return {
        "regular": Fonts.regular,
        "medium": Fonts.medium,
        "semibold": Fonts.semibold,
        "bold": Fonts.bold,
    }.get(weight, Fonts.regular)

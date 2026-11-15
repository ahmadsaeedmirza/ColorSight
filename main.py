"""ColorSight entry point — run with: python main.py"""

from kivy.utils import platform

# Desktop-only default window — never touch Window/Config size on Android/iOS
# (that was clipping the whole UI into a ~390×844 box on phones).
if platform not in ("android", "ios"):
    from kivy.config import Config

    Config.set("graphics", "width", "390")
    Config.set("graphics", "height", "844")
    Config.set("graphics", "resizable", "1")

from colorsight.app import ColorSightApp  # noqa: E402


if __name__ == "__main__":
    ColorSightApp().run()

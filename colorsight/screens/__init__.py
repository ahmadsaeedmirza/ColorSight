"""Screen package — lazy exports so importing one screen cannot pull cv2/camera.

RootShell imports each submodule via importlib. Do not eager-import here.
"""

from __future__ import annotations

__all__ = [
    "WelcomeScreen",
    "HomeScreen",
    "TestScreen",
    "PhotosScreen",
    "CameraScreen",
    "LensScreen",
    "ProfileScreen",
    "SettingsScreen",
    "LogViewerScreen",
]


def __getattr__(name: str):
    """Lazy attribute access for `from colorsight.screens import X` callers."""
    mapping = {
        "WelcomeScreen": "colorsight.screens.welcome",
        "HomeScreen": "colorsight.screens.home",
        "TestScreen": "colorsight.screens.test_screen",
        "PhotosScreen": "colorsight.screens.photos",
        "CameraScreen": "colorsight.screens.camera",
        "LensScreen": "colorsight.screens.lens",
        "ProfileScreen": "colorsight.screens.profile",
        "SettingsScreen": "colorsight.screens.settings",
        "LogViewerScreen": "colorsight.screens.settings",
    }
    if name not in mapping:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    mod = importlib.import_module(mapping[name])
    return getattr(mod, name)

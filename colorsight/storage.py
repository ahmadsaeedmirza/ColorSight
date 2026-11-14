"""Local app data paths (profiles, etc.)."""

from __future__ import annotations

from pathlib import Path

from kivy.app import App


def profile_path() -> Path:
    app = App.get_running_app()
    if app is not None:
        base = Path(app.user_data_dir)
    else:
        base = Path.home() / ".colorsight"
    base.mkdir(parents=True, exist_ok=True)
    return base / "correction_profile.json"

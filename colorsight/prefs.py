"""Lightweight local prefs (first-run flag, etc.) — no paths shown in UI."""

from __future__ import annotations

import json
from pathlib import Path

from kivy.app import App


def _prefs_path() -> Path:
    app = App.get_running_app()
    if app is not None:
        base = Path(app.user_data_dir)
    else:
        base = Path.home() / ".colorsight"
    base.mkdir(parents=True, exist_ok=True)
    return base / "prefs.json"


def load_prefs() -> dict:
    path = _prefs_path()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_prefs(data: dict) -> None:
    path = _prefs_path()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def is_first_run() -> bool:
    return not bool(load_prefs().get("onboarding_done"))


def mark_onboarding_done() -> None:
    data = load_prefs()
    data["onboarding_done"] = True
    save_prefs(data)


def get_theme_pref() -> str:
    pref = str(load_prefs().get("theme", "system")).lower()
    return pref if pref in ("system", "light", "dark") else "system"


def set_theme_pref(pref: str) -> None:
    pref = pref if pref in ("system", "light", "dark") else "system"
    data = load_prefs()
    data["theme"] = pref
    save_prefs(data)

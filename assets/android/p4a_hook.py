"""Single p4a.hook entry: CameraX gradle options + FileProvider manifest inject.

Buildozer only accepts one ``p4a.hook``. This module chains:
1. ``before_apk_build`` → vendored ``camerax_provider/gradle_options.py``
2. ``after_apk_build`` → FileProvider ``<provider>`` + ``@xml/file_paths``
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load hook module from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def before_apk_build(toolchain) -> None:
    root = Path(__file__).resolve().parents[2]  # project root
    camerax = root / "camerax_provider" / "gradle_options.py"
    if not camerax.is_file():
        print(f"[ColorSight p4a_hook] ERROR: missing {camerax}")
        return
    mod = _load_module(camerax, "colorsight_camerax_gradle_options")
    mod.before_apk_build(toolchain)
    print("[ColorSight p4a_hook] CameraX before_apk_build OK")


def after_apk_build(toolchain) -> None:
    here = Path(__file__).resolve().parent
    fp = here / "p4a_fileprovider_hook.py"
    if not fp.is_file():
        print(f"[ColorSight p4a_hook] ERROR: missing {fp}")
        return
    mod = _load_module(fp, "colorsight_fileprovider_hook")
    mod.after_apk_build(toolchain)
    print("[ColorSight p4a_hook] FileProvider after_apk_build OK")

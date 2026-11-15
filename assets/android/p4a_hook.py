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
    # Camera4Kivy camerax_provider adds RECORD_AUDIO for video+audio; we never
    # record. Strip it from the generated manifest (safe — Preview still works).
    _strip_record_audio(toolchain)


def _strip_record_audio(toolchain) -> None:
    dist = Path(toolchain._dist.dist_dir)
    manifest = dist / "src" / "main" / "AndroidManifest.xml"
    if not manifest.is_file():
        return
    text = manifest.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    kept = [
        line
        for line in lines
        if "RECORD_AUDIO" not in line
    ]
    if len(kept) == len(lines):
        print("[ColorSight p4a_hook] RECORD_AUDIO not in manifest — OK")
        return
    manifest.write_text("".join(kept), encoding="utf-8")
    print("[ColorSight p4a_hook] Removed RECORD_AUDIO from AndroidManifest.xml")

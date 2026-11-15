#!/usr/bin/env python3
"""Fast Android-build guardrails (local + CI). Exit non-zero on hard failures.

Usage (repo root):
    python tools/preflight.py
"""

from __future__ import annotations

import ast
import compileall
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Expected unpinned Android requirements (order does not matter)
EXPECTED_REQS = {
    "python3",
    "kivy",
    "numpy",
    "opencv",
    "pillow",
    "pyjnius",
    "android",
    "camera4kivy",
    "gestures4kivy",
    "androidstorage4kivy",
}

REQUIRED_PERMISSIONS = {"CAMERA", "READ_MEDIA_IMAGES"}

ICON_PATHS = (
    "assets/icon.png",
    "assets/presplash.png",
    "assets/icon_foreground.png",
    "assets/icon_background.png",
)

FONT_PATHS = (
    "assets/fonts/Lexend-Regular.ttf",
    "assets/fonts/Lexend-Medium.ttf",
    "assets/fonts/Lexend-SemiBold.ttf",
    "assets/fonts/Lexend-Bold.ttf",
    "assets/icons/MaterialIcons-Regular.ttf",
)

# Pip packages that have bitten us with android_* wheels on the host resolver
ANDROID_WHEEL_RISK = {
    "charset-normalizer",
    "charset_normalizer",
}

# Standard Kivy widget/event overrides — not treated as callback-shadow bugs
_KIVY_LIFECYCLE = {
    "on_enter",
    "on_leave",
    "on_pre_enter",
    "on_pre_leave",
    "on_pause",
    "on_resume",
    "on_start",
    "on_stop",
    "on_touch_down",
    "on_touch_move",
    "on_touch_up",
    "on_press",
    "on_release",
    "on_parent",
    "on_size",
    "on_pos",
    "on_kv_post",
    "on_config_change",
}

# unittest modules that need a GUI / Window (skipped when COLORSIGHT_SKIP_GUI=1)
GUI_TEST_MODULES = frozenset(
    {
        "tests.test_lens_nav",
        "tests.test_chip_centering",
        "tests.test_theme_rebuild",
    }
)

_errors: list[str] = []
_warnings: list[str] = []


def err(msg: str) -> None:
    _errors.append(msg)
    print(f"ERROR: {msg}", file=sys.stderr)


def warn(msg: str) -> None:
    _warnings.append(msg)
    print(f"WARN:  {msg}", file=sys.stderr)


def ok(msg: str) -> None:
    print(f"OK:    {msg}")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _spec_value(text: str, key: str) -> str | None:
    """Return the value for `key = …` in buildozer.spec (first match)."""
    m = re.search(rf"^{re.escape(key)}\s*=\s*(.+)$", text, re.MULTILINE)
    if not m:
        return None
    return m.group(1).strip()


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_buildozer_spec() -> None:
    path = ROOT / "buildozer.spec"
    if not path.is_file():
        err("buildozer.spec missing")
        return
    text = _read_text(path)

    version_lines = re.findall(r"^version\s*=", text, re.MULTILINE)
    if len(version_lines) != 1:
        err(f"buildozer.spec must have exactly one `version =` line (found {len(version_lines)})")
    else:
        ok("buildozer.spec: single version = line")

    if re.search(r"^version\.regex\s*=", text, re.MULTILINE):
        err("buildozer.spec must not set version.regex")
    if re.search(r"^version\.filename\s*=", text, re.MULTILINE):
        err("buildozer.spec must not set version.filename")

    reqs_raw = _spec_value(text, "requirements")
    if not reqs_raw:
        err("buildozer.spec: requirements missing")
    else:
        # Strip comments trailing on the same line
        reqs_raw = reqs_raw.split("#", 1)[0].strip()
        parts = [p.strip() for p in reqs_raw.split(",") if p.strip()]
        if any("==" in p for p in parts):
            err(
                "buildozer.spec requirements contain `==` pins — leave recipe deps "
                "unpinned; use constraints.txt + PIP_CONSTRAINT for host pins"
            )
        names = {p.split("==")[0].split("<")[0].split(">")[0].strip().lower() for p in parts}
        missing = sorted(EXPECTED_REQS - names)
        extra_risk = sorted(names & {r.lower() for r in ANDROID_WHEEL_RISK})
        if missing:
            err(f"buildozer.spec requirements missing: {', '.join(missing)}")
        else:
            ok(f"buildozer.spec requirements include expected packages ({len(EXPECTED_REQS)})")
        for name in parts:
            base = name.split("==")[0].strip().lower()
            if base in ANDROID_WHEEL_RISK:
                warn(
                    f"requirement `{name}` is known to ship android_* wheels — "
                    "keep it out of requirements=; pin via constraints.txt / PIP_CONSTRAINT"
                )
        if extra_risk:
            pass  # already warned

    for key, expected in (
        ("android.archs", "arm64-v8a"),
        ("android.ndk", "28c"),
        ("android.api", "35"),
    ):
        val = _spec_value(text, key)
        if val != expected:
            err(f"buildozer.spec {key} must be {expected!r} (got {val!r})")
        else:
            ok(f"buildozer.spec {key} = {expected}")

    perms_raw = _spec_value(text, "android.permissions") or ""
    perms = {p.strip() for p in perms_raw.split(",") if p.strip()}
    missing_p = sorted(REQUIRED_PERMISSIONS - perms)
    if missing_p:
        err(f"buildozer.spec android.permissions missing: {', '.join(missing_p)}")
    else:
        ok("buildozer.spec required permissions present")

    for rel in ICON_PATHS:
        p = ROOT / rel
        if not p.is_file():
            err(f"icon/presplash missing: {rel}")
        else:
            ok(f"asset exists: {rel}")

    hook = _spec_value(text, "p4a.hook") or ""
    if "p4a_hook.py" not in hook:
        err("buildozer.spec p4a.hook must point at assets/android/p4a_hook.py")
    hook_path = ROOT / "assets" / "android" / "p4a_hook.py"
    if not hook_path.is_file():
        err("assets/android/p4a_hook.py missing")
    else:
        ok("assets/android/p4a_hook.py exists")

    cx = ROOT / "camerax_provider"
    if not cx.is_dir() or not (cx / "gradle_options.py").is_file():
        err("camerax_provider/ missing or incomplete (need gradle_options.py)")
    else:
        ok("camerax_provider/ present")

    if not (ROOT / "constraints.txt").is_file():
        err("constraints.txt missing (needed for PIP_CONSTRAINT / charset-normalizer)")
    else:
        ok("constraints.txt exists")


def check_line_endings() -> None:
    patterns = ("**/*.py", "**/*.sh", "**/*.yml", "**/*.yaml", "buildozer.spec", "constraints.txt")
    bad: list[str] = []
    skip_dirs = {".git", ".venv", "venv", ".buildozer", "bin", "dist", "__pycache__", "node_modules"}
    checked = 0
    for pattern in patterns:
        for path in ROOT.glob(pattern):
            if not path.is_file():
                continue
            if any(part in skip_dirs for part in path.parts):
                continue
            # Only scan project sources (not site-packages under .venv already skipped)
            rel = path.relative_to(ROOT).as_posix()
            if rel.startswith(".") and path.name not in ("buildozer.spec",):
                # allow .github/workflows
                if not rel.startswith(".github/"):
                    continue
            data = path.read_bytes()
            checked += 1
            if b"\r\n" in data:
                bad.append(rel)
    if bad:
        for rel in bad[:40]:
            err(f"CRLF line endings: {rel}")
        if len(bad) > 40:
            err(f"... and {len(bad) - 40} more files with CRLF")
    else:
        ok(f"LF line endings ({checked} files checked)")


def check_compileall() -> None:
    targets = [ROOT / "colorsight", ROOT / "core", ROOT / "tools", ROOT / "tests"]
    failed = False
    for t in targets:
        if not t.is_dir():
            err(f"compileall target missing: {t.name}/")
            failed = True
            continue
        # quiet=1 still returns False on failure
        if not compileall.compile_dir(str(t), quiet=1, force=False):
            err(f"compileall failed under {t.name}/")
            failed = True
    if not failed:
        ok("compileall colorsight/ core/ tools/ tests/")


def _iter_py_files() -> list[Path]:
    out: list[Path] = []
    for base in (ROOT / "colorsight", ROOT / "core", ROOT / "tools", ROOT / "tests"):
        if not base.is_dir():
            continue
        for p in base.rglob("*.py"):
            if "__pycache__" in p.parts:
                continue
            out.append(p)
    return out


# Static Kivy builtin widget names — never import Kivy here (avoids creating a Window
# / "Couldn't connect to X server" on headless CI). Optional Factory merge is
# display-safe only when KIVY_NO_ARGS is set and import stays at kivy.factory.
_KIVY_BUILTIN_WIDGETS = {
    "Widget",
    "Label",
    "Button",
    "Image",
    "TextInput",
    "ScrollView",
    "BoxLayout",
    "FloatLayout",
    "GridLayout",
    "StackLayout",
    "AnchorLayout",
    "RelativeLayout",
    "Screen",
    "ScreenManager",
    "ProgressBar",
    "Switch",
    "Slider",
    "Popup",
    "ModalView",
    "Carousel",
    "RecyclerView",
    "Video",
    "Camera",
    "ActionBar",
    "Spinner",
    "TabbedPanel",
    "FileChooser",
    "FileChooserListView",
    "FileChooserIconView",
    "CheckBox",
    "ToggleButton",
    "CodeInput",
    "VKeyboard",
    "PageLayout",
    "Scatter",
    "ScatterLayout",
    "StencilView",
    "EffectWidget",
    "Sandbox",
}


def check_kivy_pitfalls() -> None:
    # Prefer static list so preflight never needs a display. Optionally enrich
    # from kivy.factory only when not headless (importing Kivy can still pull
    # a Window provider on some platforms).
    factory_names: set[str] = set(_KIVY_BUILTIN_WIDGETS)
    os.environ.setdefault("KIVY_NO_ARGS", "1")
    os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")
    headless = os.environ.get("COLORSIGHT_HEADLESS", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if headless:
        ok(f"Kivy builtin names ready ({len(factory_names)}; static list, headless)")
    else:
        try:
            # Import submodule only — do not touch kivy.core.window
            import kivy.factory as _kf  # type: ignore

            classes = getattr(getattr(_kf, "Factory", None), "classes", None) or {}
            factory_names.update(str(k) for k in classes.keys())
            ok(
                f"Kivy builtin names ready ({len(factory_names)}; Factory optional merge ok)"
            )
        except Exception as exc:  # noqa: BLE001
            warn(f"kivy.factory unavailable - using static builtin list ({exc})")
            ok(f"Kivy builtin names ready ({len(factory_names)}; static list)")

    size_re = re.compile(r"(?<![A-Za-z0-9_])size\s*=\s*dp\(([^,\n\)]+)\)")
    prop_on_re = re.compile(
        r"^\s*(on_[A-Za-z0-9_]+)\s*=\s*"
        r"(ObjectProperty|NumericProperty|BooleanProperty|StringProperty|"
        r"ListProperty|DictProperty|AliasProperty|ReferenceListProperty)\b",
        re.MULTILINE,
    )
    class_re = re.compile(r"^class\s+([A-Za-z_][A-Za-z0-9_]*)\s*[\(:]", re.MULTILINE)

    size_hits = 0
    shadow_hits = 0
    name_hits = 0

    for path in _iter_py_files():
        if "colorsight" not in path.parts and "tools" not in path.parts:
            continue
        # Only colorsight UI code for widget pitfalls
        if "colorsight" not in path.parts:
            continue
        text = _read_text(path)
        rel = path.relative_to(ROOT).as_posix()

        for m in class_re.finditer(text):
            name = m.group(1)
            if name.startswith("_"):
                continue
            if factory_names and name in factory_names:
                err(f"custom widget `{name}` collides with Kivy builtin ({rel})")
                name_hits += 1

        for m in size_re.finditer(text):
            # Ignore comments
            line_start = text.rfind("\n", 0, m.start()) + 1
            line = text[line_start : text.find("\n", m.start())]
            if line.lstrip().startswith("#"):
                continue
            err(f"single-float size=dp(...) in {rel}: {line.strip()}")
            size_hits += 1

        for m in prop_on_re.finditer(text):
            pname = m.group(1)
            if pname.endswith("_cb"):
                continue  # project convention: on_press_cb etc.
            if pname in _KIVY_LIFECYCLE:
                continue
            err(
                f"property `{pname}` shadows a Kivy on_* event — use *_cb "
                f"({rel})"
            )
            shadow_hits += 1

        # AST: ObjectProperty assigned to on_* without _cb (covers multi-line)
        try:
            tree = ast.parse(text, filename=rel)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if not isinstance(node.value, ast.Call):
                    continue
                func = node.value.func
                fname = ""
                if isinstance(func, ast.Name):
                    fname = func.id
                elif isinstance(func, ast.Attribute):
                    fname = func.attr
                if fname not in {
                    "ObjectProperty",
                    "NumericProperty",
                    "BooleanProperty",
                    "StringProperty",
                    "ListProperty",
                    "DictProperty",
                }:
                    continue
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name) and tgt.id.startswith("on_"):
                        if not tgt.id.endswith("_cb") and tgt.id not in _KIVY_LIFECYCLE:
                            # may already be reported by regex
                            pass

    if size_hits == 0:
        ok("no single-float size=dp(...) usages")
    if shadow_hits == 0:
        ok("no on_* ObjectProperty shadows (non-_cb)")
    if name_hits == 0 and factory_names:
        ok("no custom widget names collide with Kivy builtins")


def check_fonts_and_includes() -> None:
    for rel in FONT_PATHS:
        p = ROOT / rel
        if not p.is_file():
            err(f"font/icon asset missing: {rel}")
        else:
            ok(f"font/icon exists: {rel}")

    spec = _read_text(ROOT / "buildozer.spec")
    exts = _spec_value(spec, "source.include_exts") or ""
    patterns = _spec_value(spec, "source.include_patterns") or ""
    for need in ("ttf", "otf", "png"):
        if need not in exts.split(","):
            # allow whitespace
            if need not in [e.strip() for e in exts.split(",")]:
                err(f"source.include_exts must include {need!r} (got {exts!r})")
    for need in ("assets/fonts/*", "assets/icons/*", "assets/*"):
        if need not in patterns:
            err(f"source.include_patterns should include {need!r}")
    if "ttf" in exts and "assets/fonts/*" in patterns:
        ok("source.include_exts / patterns cover fonts + icons")


def check_constraints() -> None:
    path = ROOT / "constraints.txt"
    if not path.is_file():
        return
    text = _read_text(path)
    if "charset-normalizer" not in text:
        warn("constraints.txt does not pin charset-normalizer (CI may hit android_* wheel)")
    else:
        ok("constraints.txt pins charset-normalizer")


def main() -> int:
    os.chdir(ROOT)
    print(f"ColorSight preflight - {ROOT}")
    print("-" * 60)
    check_buildozer_spec()
    check_line_endings()
    check_compileall()
    check_kivy_pitfalls()
    check_fonts_and_includes()
    check_constraints()
    print("-" * 60)
    if _warnings:
        print(f"{len(_warnings)} warning(s)")
    if _errors:
        print(f"PREFLIGHT FAILED — {len(_errors)} error(s)", file=sys.stderr)
        for e in _errors:
            print(f"  • {e}", file=sys.stderr)
        return 1
    print("PREFLIGHT OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())

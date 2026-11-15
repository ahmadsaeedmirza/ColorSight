#!/usr/bin/env python3
"""Discover and run unit tests.

When COLORSIGHT_SKIP_GUI=1, GUI modules are never imported (avoids headless
X-server aborts at import time). Prefer xvfb-run + COLORSIGHT_HEADLESS=1 in CI
so GUI tests can run or SkipTest cleanly.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Keep in sync with tools/preflight.py GUI_TEST_MODULES
GUI_TEST_MODULES = frozenset(
    {
        "tests.test_lens_nav",
        "tests.test_chip_centering",
        "tests.test_theme_rebuild",
    }
)


def main() -> int:
    os.environ.setdefault("KIVY_NO_ARGS", "1")
    skip_gui = os.environ.get("COLORSIGHT_SKIP_GUI", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    loader = unittest.TestLoader()

    if skip_gui:
        # Load modules individually so GUI files are never imported
        suite = unittest.TestSuite()
        tests_dir = ROOT / "tests"
        for path in sorted(tests_dir.glob("test_*.py")):
            mod_name = f"tests.{path.stem}"
            if mod_name in GUI_TEST_MODULES:
                continue
            suite.addTests(loader.loadTestsFromName(mod_name))
        print(f"COLORSIGHT_SKIP_GUI=1 - excluding {sorted(GUI_TEST_MODULES)}")
    else:
        suite = loader.discover(start_dir=str(ROOT / "tests"), pattern="test_*.py")

    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())

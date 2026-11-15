#!/usr/bin/env python3
"""Discover and run unit tests; skip GUI modules when COLORSIGHT_SKIP_GUI=1.

Does not modify existing test files — exclusion is loader-side only.
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
    skip_gui = os.environ.get("COLORSIGHT_SKIP_GUI", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(ROOT / "tests"), pattern="test_*.py")

    if skip_gui:
        filtered = unittest.TestSuite()

        def _walk(s):
            for t in s:
                if isinstance(t, unittest.TestSuite):
                    _walk(t)
                else:
                    mod = t.__class__.__module__
                    if mod in GUI_TEST_MODULES:
                        continue
                    filtered.addTest(t)

        _walk(suite)
        suite = filtered
        print(f"COLORSIGHT_SKIP_GUI=1 — excluding {sorted(GUI_TEST_MODULES)}")

    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())

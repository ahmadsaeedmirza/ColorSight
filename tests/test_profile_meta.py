"""Profile metadata + plain-language label helpers (UI layer)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from colorsight.screens.profile import profile_plain_label
from core.profile import CorrectionProfile


class TestProfileMeta(unittest.TestCase):
    def test_optional_fields_roundtrip(self):
        p = CorrectionProfile.create(
            "deuteranomaly",
            0.91,
            measured_at="2026-11-14",
            label="Deutan (green-weak) pattern",
            thresholds={"protan": 0.01, "deutan": 0.04, "tritan": 0.01},
            test_severity=0.91,
        )
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "p.json"
            p.save(path)
            loaded = CorrectionProfile.load(path)
        self.assertEqual(loaded.measured_at, "2026-11-14")
        self.assertEqual(loaded.label, "Deutan (green-weak) pattern")
        self.assertAlmostEqual(loaded.thresholds["deutan"], 0.04)
        self.assertAlmostEqual(loaded.test_severity, 0.91)
        self.assertEqual(profile_plain_label(loaded), "Deutan (green-weak) pattern")

    def test_plain_label_fallback(self):
        p = CorrectionProfile.create("protanopia", 0.5)
        self.assertIn("Protan", profile_plain_label(p))


if __name__ == "__main__":
    unittest.main()

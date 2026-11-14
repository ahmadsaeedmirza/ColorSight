"""Tests for daltonization and CorrectionProfile JSON I/O."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from core import (
    CVDType,
    CorrectionProfile,
    apply_correction,
    apply_simulation,
    build_correction_matrix,
)


class TestDaltonize(unittest.TestCase):
    def test_correction_identity_at_zero_severity(self):
        C = build_correction_matrix(CVDType.DEUTERANOPIA, 0.0)
        np.testing.assert_allclose(C, np.eye(3), atol=1e-9)

    def test_profile_create_and_apply(self):
        profile = CorrectionProfile.create(CVDType.PROTANOPIA, 0.8)
        self.assertEqual(profile.type, CVDType.PROTANOPIA)
        self.assertAlmostEqual(profile.severity, 0.8)
        self.assertEqual(profile.matrix.shape, (3, 3))

        img = np.random.randint(0, 256, (40, 40, 3), dtype=np.uint8)
        out = apply_correction(img, profile)
        self.assertEqual(out.shape, img.shape)
        self.assertEqual(out.dtype, np.uint8)

    def test_correction_differs_from_simulation(self):
        img = np.full((16, 16, 3), (200, 40, 40), dtype=np.uint8)
        sim = apply_simulation(img, CVDType.PROTANOPIA, 1.0)
        corr = apply_correction(img, CorrectionProfile.create("protanopia", 1.0))
        self.assertFalse(np.array_equal(sim, corr))

    def test_json_roundtrip(self):
        profile = CorrectionProfile.create(CVDType.TRITANOPIA, 0.35)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profile.json"
            profile.save(path)
            loaded = CorrectionProfile.load(path)
        self.assertEqual(loaded.type, CVDType.TRITANOPIA)
        self.assertAlmostEqual(loaded.severity, 0.35)
        np.testing.assert_allclose(loaded.matrix, profile.matrix)

    def test_rebuild_matrix(self):
        p = CorrectionProfile.create(CVDType.DEUTERANOPIA, 0.2)
        p.severity = 0.9
        p.rebuild_matrix()
        expected = build_correction_matrix(CVDType.DEUTERANOPIA, 0.9)
        np.testing.assert_allclose(p.matrix, expected)

    def test_aliases_parse(self):
        p = CorrectionProfile.create("deuteranomaly", 0.5)
        self.assertEqual(p.type, CVDType.DEUTERANOPIA)


if __name__ == "__main__":
    unittest.main()

"""Tests for Machado CVD simulation matrices."""

from __future__ import annotations

import numpy as np
import unittest

from core import CVDType, apply_simulation, simulation_matrix


class TestMachadoMatrices(unittest.TestCase):
    def test_severity_zero_is_identity(self):
        for cvd in CVDType:
            M = simulation_matrix(cvd, 0.0)
            np.testing.assert_allclose(M, np.eye(3), atol=1e-6)

    def test_severity_clamped(self):
        M_lo = simulation_matrix(CVDType.DEUTERANOPIA, -1.0)
        M_hi = simulation_matrix(CVDType.DEUTERANOPIA, 2.0)
        np.testing.assert_allclose(M_lo, simulation_matrix(CVDType.DEUTERANOPIA, 0.0))
        np.testing.assert_allclose(M_hi, simulation_matrix(CVDType.DEUTERANOPIA, 1.0))

    def test_known_protanopia_full(self):
        M = simulation_matrix("protanopia", 1.0)
        expected = np.array(
            [
                [0.152286, 1.052583, -0.204868],
                [0.114503, 0.786281, 0.099216],
                [-0.003882, -0.048116, 1.051998],
            ]
        )
        np.testing.assert_allclose(M, expected, atol=1e-6)

    def test_interpolation_between_knots(self):
        M0 = simulation_matrix(CVDType.TRITANOPIA, 0.5)
        M1 = simulation_matrix(CVDType.TRITANOPIA, 0.6)
        M = simulation_matrix(CVDType.TRITANOPIA, 0.55)
        mid = 0.5 * (M0 + M1)
        np.testing.assert_allclose(M, mid, atol=1e-9)

    def test_apply_simulation_identity_on_uint8(self):
        img = np.random.randint(0, 256, (32, 48, 3), dtype=np.uint8)
        out = apply_simulation(img, CVDType.PROTANOPIA, 0.0)
        np.testing.assert_array_equal(out, img)
        self.assertEqual(out.dtype, np.uint8)

    def test_apply_simulation_changes_colors_at_full_severity(self):
        # Pure red should shift under protanopia simulation
        img = np.zeros((8, 8, 3), dtype=np.uint8)
        img[..., 0] = 255
        out = apply_simulation(img, CVDType.PROTANOPIA, 1.0)
        self.assertFalse(np.array_equal(out, img))
        self.assertTrue(np.all(out >= 0) and np.all(out <= 255))

    def test_no_python_pixel_loop_shape_preserved(self):
        img = np.zeros((120, 160, 3), dtype=np.uint8)
        img[:, :80] = (255, 0, 0)
        img[:, 80:] = (0, 255, 0)
        out = apply_simulation(img, "deuteranopia", 0.7)
        self.assertEqual(out.shape, img.shape)


if __name__ == "__main__":
    unittest.main()

"""GPU preview matrix must match core.apply_correction / apply_simulation within 1/255."""

from __future__ import annotations

import unittest

import numpy as np

from colorsight.camera_gpu import (
    apply_matrix_shader_emulation,
    identity_matrix,
    mat3_uniform,
    matrix_for_mode,
)
from core.engine import apply_correction, apply_simulation, build_correction_matrix
from core.profile import CorrectionProfile


class TestShaderMatrixMatchesCore(unittest.TestCase):
    def test_identity_is_eye(self):
        m = identity_matrix()
        np.testing.assert_allclose(m, np.eye(3), atol=0)

    def test_mat3_uniform_column_major(self):
        m = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.float64)
        u = mat3_uniform(m)
        self.assertEqual(u, (1.0, 4.0, 7.0, 2.0, 5.0, 8.0, 3.0, 6.0, 9.0))

    def test_correction_matches_core_random(self):
        rng = np.random.default_rng(42)
        for cvd in ("deuteranomaly", "protanomaly", "tritanomaly"):
            for sev in (0.25, 0.5, 0.91, 1.0):
                img = rng.integers(0, 256, size=(32, 48, 3), dtype=np.uint8)
                profile = CorrectionProfile.create(cvd, sev)
                expected = apply_correction(img, profile)
                mat = matrix_for_mode("corrected", cvd_type=cvd, severity=sev)
                got = apply_matrix_shader_emulation(img, mat)
                max_err = int(np.max(np.abs(got.astype(np.int16) - expected.astype(np.int16))))
                self.assertLessEqual(
                    max_err,
                    1,
                    f"corrected {cvd} sev={sev} max_err={max_err}",
                )

    def test_simulation_matches_core_random(self):
        rng = np.random.default_rng(7)
        for cvd in ("deuteranomaly", "protanomaly"):
            for sev in (0.3, 0.8):
                img = rng.integers(0, 256, size=(24, 40, 3), dtype=np.uint8)
                expected = apply_simulation(img, cvd, sev)
                mat = matrix_for_mode("simulation", cvd_type=cvd, severity=sev)
                got = apply_matrix_shader_emulation(img, mat)
                max_err = int(np.max(np.abs(got.astype(np.int16) - expected.astype(np.int16))))
                self.assertLessEqual(max_err, 1, f"sim {cvd} sev={sev} max_err={max_err}")

    def test_original_is_identity(self):
        mat = matrix_for_mode("original", cvd_type="deuteranomaly", severity=0.9)
        np.testing.assert_allclose(mat, np.eye(3), atol=0)
        img = np.arange(60, dtype=np.uint8).reshape(4, 5, 3)
        got = apply_matrix_shader_emulation(img, mat)
        np.testing.assert_array_equal(got, img)

    def test_matrix_for_mode_matches_build_correction(self):
        m1 = matrix_for_mode("corrected", cvd_type="deuteranomaly", severity=0.91)
        m2 = build_correction_matrix("deuteranomaly", 0.91)
        np.testing.assert_allclose(m1, m2, atol=1e-12)


if __name__ == "__main__":
    unittest.main()

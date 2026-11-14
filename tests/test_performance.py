"""Lightweight real-time readiness check (vectorized path, no per-pixel Python)."""

from __future__ import annotations

import time
import unittest

import numpy as np

from core import CorrectionProfile, apply_correction, apply_simulation


class TestPerformance(unittest.TestCase):
    def test_720p_frame_under_budget(self):
        # ~720p RGB frame; should complete well under 100ms on a typical laptop CPU
        frame = np.random.randint(0, 256, (720, 1280, 3), dtype=np.uint8)
        profile = CorrectionProfile.create("deuteranopia", 0.8)

        # Warm-up
        apply_simulation(frame, "deuteranopia", 0.8)
        apply_correction(frame, profile)

        t0 = time.perf_counter()
        apply_simulation(frame, "deuteranopia", 0.8)
        t_sim = time.perf_counter() - t0

        t0 = time.perf_counter()
        apply_correction(frame, profile)
        t_corr = time.perf_counter() - t0

        # Soft budget: 150ms each (CI / low-end machines). Documented as real-time capable.
        self.assertLess(t_sim, 0.15, f"simulation too slow: {t_sim:.3f}s")
        self.assertLess(t_corr, 0.15, f"correction too slow: {t_corr:.3f}s")


if __name__ == "__main__":
    unittest.main()

"""Unit tests for Photos severity defaults, divider rules, correction MAD, comparison card, mode save."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from colorsight.image_pipeline import (
    before_after_split,
    build_comparison_card,
    divider_visible,
    mean_abs_diff,
    render_mode_rgb,
    resize_longest,
    right_label_for_mode,
    severity_for_slider,
)
from colorsight.photo_io import pictures_dir, save_corrected_image, share_image
from core.profile import CorrectionProfile


def _strong_sample(h: int = 48, w: int = 96) -> np.ndarray:
    """Image with strong reds / greens / oranges / blues."""
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    q = w // 4
    rgb[:, :q] = (220, 40, 30)
    rgb[:, q : 2 * q] = (40, 180, 50)
    rgb[:, 2 * q : 3 * q] = (240, 140, 30)
    rgb[:, 3 * q :] = (30, 90, 220)
    return rgb


class TestSeverityDefaults(unittest.TestCase):
    def test_severity_for_slider_rounds_percent(self):
        self.assertEqual(severity_for_slider(0.91), 0.91)
        self.assertEqual(severity_for_slider(0.914), 0.91)
        self.assertEqual(severity_for_slider(0.915), 0.92)
        self.assertEqual(severity_for_slider(1.5), 1.0)
        self.assertEqual(severity_for_slider(-0.2), 0.0)

    def test_reset_matches_saved(self):
        saved = severity_for_slider(0.91)
        preview = 1.0
        self.assertNotAlmostEqual(preview, saved)
        preview = saved
        self.assertAlmostEqual(preview, 0.91)


class TestDividerRules(unittest.TestCase):
    def test_visibility_per_mode(self):
        self.assertFalse(divider_visible("original"))
        self.assertTrue(divider_visible("corrected"))
        self.assertTrue(divider_visible("simulation"))

    def test_right_labels(self):
        self.assertEqual(right_label_for_mode("corrected"), "Corrected")
        self.assertEqual(right_label_for_mode("simulation"), "Simulation")
        self.assertEqual(right_label_for_mode("original"), "")

    def test_split_uses_different_halves(self):
        left = np.full((10, 20, 3), 10, dtype=np.uint8)
        right = np.full((10, 20, 3), 200, dtype=np.uint8)
        out = before_after_split(left, right, 0.5)
        self.assertFalse(np.array_equal(out[:, :10], out[:, 10:]))


class TestCorrectionApplied(unittest.TestCase):
    def test_deutan_091_corrected_and_simulation_differ(self):
        rgb = _strong_sample()
        profile = CorrectionProfile.create("deuteranomaly", 0.91)
        corrected = render_mode_rgb(rgb, "corrected", cvd_type=profile.type, severity=0.91)
        simulated = render_mode_rgb(rgb, "simulation", cvd_type=profile.type, severity=0.91)
        original = render_mode_rgb(rgb, "original", cvd_type=profile.type, severity=0.91)

        self.assertEqual(corrected.shape, rgb.shape)
        self.assertEqual(corrected.dtype, np.uint8)
        mad_c = mean_abs_diff(corrected, original)
        mad_s = mean_abs_diff(simulated, original)
        # Visibly different on a strong sample (well above noise / rounding)
        self.assertGreater(mad_c, 2.0, f"corrected MAD too small: {mad_c}")
        self.assertGreater(mad_s, 2.0, f"simulation MAD too small: {mad_s}")
        self.assertFalse(np.array_equal(corrected, original))
        self.assertFalse(np.array_equal(simulated, original))

        # Before/after composite must expose the difference on the right half
        split = before_after_split(original, corrected, 0.5)
        self.assertGreater(mean_abs_diff(split[:, split.shape[1] // 2 :], original[:, original.shape[1] // 2 :]), 2.0)


class TestComparisonCard(unittest.TestCase):
    def test_builder_size_and_aspect(self):
        rgb = _strong_sample(120, 200)
        sim = render_mode_rgb(rgb, "simulation", cvd_type="deuteranomaly", severity=0.91)
        card = build_comparison_card(rgb, sim, longest=512)
        self.assertEqual(card.dtype, np.uint8)
        self.assertEqual(card.ndim, 3)
        self.assertEqual(card.shape[2], 3)
        self.assertLessEqual(max(card.shape[:2]), 512 + 120)  # padding/footer budget
        # Wider than tall for landscape source (plus labels)
        self.assertGreater(card.shape[1], card.shape[0] // 2)

    def test_portrait_aspect(self):
        rgb = _strong_sample(200, 100)
        sim = rgb.copy()
        sim[..., 0] = np.clip(sim[..., 0].astype(int) - 40, 0, 255).astype(np.uint8)
        card = build_comparison_card(rgb, sim, longest=400)
        self.assertLessEqual(max(card.shape[0], card.shape[1]), 400 + 100)


class TestModeSave(unittest.TestCase):
    def test_save_each_mode(self):
        rgb = resize_longest(_strong_sample(80, 120), 120)
        profile = CorrectionProfile.create("deuteranomaly", 0.91)
        album = pictures_dir() / "ColorSight"
        for mode in ("original", "corrected", "simulation"):
            out = render_mode_rgb(rgb, mode, cvd_type=profile.type, severity=0.91)
            label = save_corrected_image(out, preferred_name=f"ColorSight_test_{mode}.jpg")
            self.assertEqual(label, "Saved to your gallery")
            self.assertTrue((album / f"ColorSight_test_{mode}.jpg").exists())

    def test_share_desktop_fallback(self):
        rgb = _strong_sample(32, 32)
        msg = share_image(rgb, preferred_name="ColorSight_share_test.jpg")
        self.assertEqual(msg, "Saved to your gallery")
        self.assertTrue((pictures_dir() / "ColorSight" / "ColorSight_share_test.jpg").exists())


if __name__ == "__main__":
    unittest.main()

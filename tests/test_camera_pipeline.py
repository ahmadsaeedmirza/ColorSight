"""Unit tests for live camera helpers + Photos/Camera default-mode logic."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from colorsight.camera_pipeline import (
    LabelSmoother,
    camera_default_mode,
    downscale_live,
    ensure_rgb_uint8,
    loupe_patch_median,
    loupe_zoom_crop,
    name_loupe_color,
)
from colorsight.image_pipeline import (
    photos_default_mode,
    photos_default_split,
    reset_link_visible,
    severity_for_slider,
    strength_percent,
)
from core.profile import CorrectionProfile


class TestFrameHelpers(unittest.TestCase):
    def test_bgr_rgb_boundary(self):
        bgr = np.zeros((8, 8, 3), dtype=np.uint8)
        bgr[..., 0] = 10
        bgr[..., 2] = 200
        rgb = ensure_rgb_uint8(bgr, from_bgr=True)
        self.assertEqual(rgb[0, 0, 0], 200)
        self.assertEqual(rgb[0, 0, 2], 10)

    def test_downscale_live(self):
        rgb = np.zeros((1200, 1600, 3), dtype=np.uint8)
        out = downscale_live(rgb, longest=640)
        self.assertEqual(max(out.shape[:2]), 640)
        self.assertEqual(out.dtype, np.uint8)

    def test_loupe_patch_median(self):
        rgb = np.zeros((40, 40, 3), dtype=np.uint8)
        rgb[18:23, 18:23] = (10, 20, 30)
        med = loupe_patch_median(rgb, 20, 20, patch=5)
        self.assertEqual(tuple(med.tolist()), (10, 20, 30))

    def test_loupe_zoom_at_edge(self):
        rgb = np.full((60, 80, 3), 40, dtype=np.uint8)
        crop = loupe_zoom_crop(rgb, 0, 0, zoom=3.0, out_size=64)
        self.assertEqual(crop.shape, (64, 64, 3))
        crop2 = loupe_zoom_crop(rgb, 79, 59, zoom=2.0, out_size=64)
        self.assertEqual(crop2.shape, (64, 64, 3))

    def test_label_smoothing(self):
        s = LabelSmoother(window=5)
        self.assertEqual(s.push("red"), "red")
        for _ in range(3):
            s.push("blue")
        self.assertEqual(s.push("blue"), "blue")

    def test_name_loupe_color(self):
        rgb = np.zeros((32, 32, 3), dtype=np.uint8)
        rgb[:] = (200, 30, 30)
        name, med = name_loupe_color(rgb, 16, 16)
        self.assertIsInstance(name, str)
        self.assertTrue(len(name) > 0)
        self.assertEqual(med.shape, (3,))


class TestDefaultModes(unittest.TestCase):
    def test_photos_defaults(self):
        self.assertEqual(photos_default_mode(True), "corrected")
        self.assertEqual(photos_default_mode(False), "original")
        self.assertEqual(photos_default_split(), 0.0)

    def test_camera_defaults(self):
        self.assertEqual(camera_default_mode(True), "corrected")
        self.assertEqual(camera_default_mode(False), "original")


class TestPhotosStrengthFromProfile(unittest.TestCase):
    def _write_profile(self, path: Path, severity: float) -> CorrectionProfile:
        p = CorrectionProfile.create("deuteranomaly", severity)
        p.save(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertAlmostEqual(data["severity"], float(np.clip(severity, 0, 1)))
        return p

    def test_severity_091_shows_91_no_reset(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "correction_profile.json"
            self._write_profile(path, 0.91)
            loaded = CorrectionProfile.load(path)
            sev = severity_for_slider(loaded.severity)
            self.assertEqual(strength_percent(sev), 91)
            self.assertFalse(reset_link_visible(sev, sev))
            # After moving the slider
            self.assertTrue(reset_link_visible(1.0, sev))

    def test_severity_10_shows_100_not_hardcoded(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "correction_profile.json"
            self._write_profile(path, 1.0)
            loaded = CorrectionProfile.load(path)
            sev = severity_for_slider(loaded.severity)
            self.assertEqual(strength_percent(sev), 100)
            self.assertFalse(reset_link_visible(sev, sev))
            self.assertTrue(reset_link_visible(0.5, sev))


if __name__ == "__main__":
    unittest.main()

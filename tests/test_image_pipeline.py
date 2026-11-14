"""Unit tests for photo image pipeline helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image as PILImage

from colorsight.image_pipeline import (
    PREVIEW_LONGEST,
    before_after_split,
    bgr_to_rgb,
    encode_image,
    load_rgb_uint8,
    resize_longest,
    rgb_to_bgr,
)


class TestImagePipeline(unittest.TestCase):
    def test_resize_longest_downscales(self):
        rgb = np.zeros((2000, 3000, 3), dtype=np.uint8)
        out = resize_longest(rgb, longest=1080)
        self.assertEqual(max(out.shape[:2]), 1080)
        self.assertEqual(out.dtype, np.uint8)
        self.assertEqual(out.shape[2], 3)

    def test_resize_longest_no_upscale(self):
        rgb = np.zeros((100, 200, 3), dtype=np.uint8)
        out = resize_longest(rgb, longest=1080)
        self.assertEqual(out.shape, (100, 200, 3))

    def test_rgb_bgr_roundtrip(self):
        rgb = np.zeros((8, 8, 3), dtype=np.uint8)
        rgb[..., 0] = 10
        rgb[..., 1] = 20
        rgb[..., 2] = 30
        bgr = rgb_to_bgr(rgb)
        self.assertEqual(bgr[0, 0, 0], 30)
        self.assertEqual(bgr[0, 0, 2], 10)
        back = bgr_to_rgb(bgr)
        np.testing.assert_array_equal(back, rgb)

    def test_before_after_split_edges(self):
        left = np.full((10, 20, 3), 10, dtype=np.uint8)
        right = np.full((10, 20, 3), 200, dtype=np.uint8)
        np.testing.assert_array_equal(before_after_split(left, right, 1.0), left)
        np.testing.assert_array_equal(before_after_split(left, right, 0.0), right)

    def test_before_after_split_mid(self):
        left = np.full((4, 10, 3), 1, dtype=np.uint8)
        right = np.full((4, 10, 3), 9, dtype=np.uint8)
        out = before_after_split(left, right, 0.5)
        self.assertEqual(out.dtype, np.uint8)
        self.assertEqual(out.shape, (4, 10, 3))
        np.testing.assert_array_equal(out[:, :5], left[:, :5])
        np.testing.assert_array_equal(out[:, 5:], right[:, 5:])

    def test_before_after_shape_mismatch(self):
        a = np.zeros((4, 4, 3), dtype=np.uint8)
        b = np.zeros((4, 5, 3), dtype=np.uint8)
        with self.assertRaises(ValueError):
            before_after_split(a, b, 0.5)

    def test_load_rgb_and_encode(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sample.png"
            arr = np.zeros((32, 48, 3), dtype=np.uint8)
            arr[..., 0] = 255
            PILImage.fromarray(arr, mode="RGB").save(path)
            loaded = load_rgb_uint8(path)
            self.assertEqual(loaded.shape, (32, 48, 3))
            self.assertEqual(loaded.dtype, np.uint8)
            self.assertEqual(loaded[0, 0, 0], 255)

            rgb = np.full((16, 16, 3), 128, dtype=np.uint8)
            jpg = encode_image(rgb, Path(td) / "a.jpg", quality=95)
            png = encode_image(rgb, Path(td) / "b.png")
            self.assertTrue(jpg.exists() and png.exists())
            self.assertEqual(load_rgb_uint8(jpg).shape, (16, 16, 3))
            self.assertEqual(load_rgb_uint8(png).dtype, np.uint8)

    def test_load_applies_exif_orientation(self):
        """EXIF orientation 6 (rotate 90 CW) should yield transposed dimensions."""
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "oriented.jpg"
            arr = np.zeros((10, 20, 3), dtype=np.uint8)
            arr[:, :10, 0] = 255
            im = PILImage.fromarray(arr, mode="RGB")
            exif = im.getexif()
            exif[274] = 6
            im.save(path, format="JPEG", quality=95, exif=exif.tobytes())
            loaded = load_rgb_uint8(path)
            self.assertEqual(loaded.shape[0], 20)
            self.assertEqual(loaded.shape[1], 10)

    def test_preview_constant(self):
        self.assertEqual(PREVIEW_LONGEST, 1080)


if __name__ == "__main__":
    unittest.main()

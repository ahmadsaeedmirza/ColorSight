"""Tests for procedural plates and screening score."""

from __future__ import annotations

import unittest

import numpy as np

from core import (
    CVDType,
    DEFAULT_BATTERY,
    PlateAxis,
    generate_battery,
    hue_arrangement_error,
    hue_tile_colors,
    make_answers,
    render_plate,
    score_screening,
)


class TestPlates(unittest.TestCase):
    def test_battery_size(self):
        self.assertGreaterEqual(len(DEFAULT_BATTERY), 12)
        self.assertLessEqual(len(DEFAULT_BATTERY), 16)

    def test_render_shape_and_dtype(self):
        img = render_plate(DEFAULT_BATTERY[0], size=256, seed=1)
        self.assertEqual(img.shape, (256, 256, 3))
        self.assertEqual(img.dtype, np.uint8)

    def test_generate_battery(self):
        plates = generate_battery(size=128, seed=7)
        self.assertEqual(len(plates), len(DEFAULT_BATTERY))
        self.assertEqual(plates[0][1].shape[0], 128)

    def test_hue_tiles(self):
        cols = hue_tile_colors(7)
        self.assertEqual(len(cols), 7)
        self.assertEqual(len(cols[0]), 3)


class TestScoring(unittest.TestCase):
    def test_perfect_answers_normal(self):
        responses = [s.digit for s in DEFAULT_BATTERY]
        answers = make_answers(DEFAULT_BATTERY, responses)
        result = score_screening(answers, hue_order=list(range(7)))
        self.assertEqual(result.classification, "normal")
        self.assertLessEqual(result.severity, 0.25)
        self.assertEqual(result.plate_correct, len(DEFAULT_BATTERY))

    def test_rg_misses_classify_deutan_or_protan(self):
        responses = []
        for s in DEFAULT_BATTERY:
            if s.axis in (PlateAxis.RED_GREEN, PlateAxis.PROTAN, PlateAxis.DEUTAN):
                responses.append(None)
            else:
                responses.append(s.digit)
        answers = make_answers(DEFAULT_BATTERY, responses)
        result = score_screening(answers, hue_order=list(reversed(range(7))))
        self.assertIn(
            result.classification,
            {CVDType.DEUTERANOPIA.value, CVDType.PROTANOPIA.value},
        )
        self.assertGreater(result.severity, 0.1)

    def test_by_misses_classify_tritan(self):
        responses = []
        for s in DEFAULT_BATTERY:
            if s.axis == PlateAxis.BLUE_YELLOW:
                responses.append(None)
            else:
                responses.append(s.digit)
        answers = make_answers(DEFAULT_BATTERY, responses)
        # Scramble hue moderately
        order = [0, 2, 1, 4, 3, 6, 5]
        result = score_screening(answers, hue_order=order)
        self.assertEqual(result.classification, CVDType.TRITANOPIA.value)

    def test_hue_error_bounds(self):
        self.assertAlmostEqual(hue_arrangement_error(list(range(7))), 0.0)
        self.assertGreater(hue_arrangement_error(list(reversed(range(7)))), 0.9)

    def test_profile_from_result(self):
        answers = make_answers(DEFAULT_BATTERY, [s.digit for s in DEFAULT_BATTERY])
        normal = score_screening(answers, list(range(7)))
        profile = normal.to_profile()
        self.assertIsNotNone(profile)
        self.assertAlmostEqual(profile.severity, 0.0)


if __name__ == "__main__":
    unittest.main()

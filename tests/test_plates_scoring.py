"""Tests for plate battery metadata and screening classification."""

from __future__ import annotations

import unittest

from core import (
    CVDType,
    DEFAULT_BATTERY,
    PlateAxis,
    generate_battery,
    hue_arrangement_error,
    hue_tile_colors,
    make_answers,
    score_screening,
    simulate_respondent,
)


class TestBattery(unittest.TestCase):
    def test_battery_composition(self):
        self.assertGreaterEqual(len(DEFAULT_BATTERY), 12)
        self.assertLessEqual(len(DEFAULT_BATTERY), 16)
        axes = [s.axis for s in DEFAULT_BATTERY]
        self.assertEqual(axes.count(PlateAxis.CONTROL), 1)
        self.assertGreaterEqual(axes.count(PlateAxis.HIDDEN_RG), 4)
        self.assertGreaterEqual(axes.count(PlateAxis.CLASSIFY_PROTAN), 2)
        self.assertGreaterEqual(axes.count(PlateAxis.CLASSIFY_DEUTAN), 2)
        self.assertEqual(axes.count(PlateAxis.TRITAN), 2)

    def test_expected_answer_table_complete(self):
        for s in DEFAULT_BATTERY:
            for viewer in ("normal", "protanopia", "deuteranopia", "tritanopia"):
                _ = s.expected_for(viewer)

    def test_generate_battery(self):
        plates = generate_battery(size=128, seed=7)
        self.assertEqual(len(plates), len(DEFAULT_BATTERY))
        self.assertEqual(plates[0].image.shape[0], 128)

    def test_hue_tiles(self):
        cols = hue_tile_colors(7)
        self.assertEqual(len(cols), 7)


class TestScoring(unittest.TestCase):
    def test_simulated_normal_classifies_normal(self):
        answers = simulate_respondent("normal")
        result = score_screening(answers, hue_order=list(range(7)))
        self.assertEqual(result.classification, "normal")
        self.assertLessEqual(result.severity, 0.25)

    def test_simulated_protan_classifies_protan(self):
        answers = simulate_respondent("protanopia")
        result = score_screening(answers, hue_order=list(reversed(range(7))))
        self.assertEqual(result.classification, CVDType.PROTANOPIA.value)

    def test_simulated_deutan_classifies_deutan(self):
        answers = simulate_respondent("deuteranopia")
        result = score_screening(answers, hue_order=list(reversed(range(7))))
        self.assertEqual(result.classification, CVDType.DEUTERANOPIA.value)

    def test_simulated_tritan_classifies_tritan(self):
        answers = simulate_respondent("tritanopia")
        result = score_screening(answers, hue_order=[0, 2, 1, 4, 3, 6, 5])
        self.assertEqual(result.classification, CVDType.TRITANOPIA.value)

    def test_mixed_answers_can_be_inconclusive(self):
        # Alternate nonsense responses
        responses = [0 if i % 2 == 0 else None for i in range(len(DEFAULT_BATTERY))]
        answers = make_answers(DEFAULT_BATTERY, responses)
        result = score_screening(answers, hue_order=list(range(7)))
        self.assertEqual(result.classification, "inconclusive")

    def test_hue_error_bounds(self):
        self.assertAlmostEqual(hue_arrangement_error(list(range(7))), 0.0)
        self.assertGreater(hue_arrangement_error(list(reversed(range(7)))), 0.9)

    def test_profile_from_normal(self):
        result = score_screening(simulate_respondent("normal"), list(range(7)))
        profile = result.to_profile()
        self.assertAlmostEqual(profile.severity, 0.0)


if __name__ == "__main__":
    unittest.main()

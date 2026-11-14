"""Color-independent digit shape recognizability for every screening plate."""

from __future__ import annotations

import unittest

from core import (
    DEFAULT_BATTERY,
    EXPECTED_DIGIT_HOLES,
    RECOG_MARGIN,
    count_digit_holes,
    digit_recognizability,
    generate_battery,
    rasterize_figure_dots,
)


class TestPlateRecognizability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plates = generate_battery(DEFAULT_BATTERY, size=360, seed=42)

    def test_every_plate_digit_is_recognizable(self):
        failures = []
        for plate in self.plates:
            pid = plate.spec.plate_id
            expected = plate.spec.expected_normal
            if expected is None:
                failures.append(f"[{pid}] expected_normal is None (control/figure must be readable)")
                continue

            info = digit_recognizability(plate)
            if info["best_digit"] != int(expected):
                failures.append(
                    f"[{pid}] best match digit={info['best_digit']} "
                    f"(score={info['best_score']:.3f}) != expected {expected}; "
                    f"runner-up score={info['runner_up_score']:.3f}"
                )
            elif info["margin"] < RECOG_MARGIN:
                failures.append(
                    f"[{pid}] margin {info['margin']:.3f} < {RECOG_MARGIN} "
                    f"(best={info['best_score']:.3f}, runner={info['runner_up_score']:.3f})"
                )

            exp_holes = EXPECTED_DIGIT_HOLES[int(expected)]
            if info["holes"] != exp_holes:
                failures.append(
                    f"[{pid}] hole count {info['holes']} != expected {exp_holes} "
                    f"for digit {expected}"
                )

        if failures:
            self.fail(
                "Digit recognizability failed for "
                f"{len(failures)} check(s):\n" + "\n".join(failures)
            )

    def test_clean_templates_have_expected_topology(self):
        """Sanity: Lexend digit hole counts for reference templates."""
        from core import clean_digit_mask

        for d, holes in EXPECTED_DIGIT_HOLES.items():
            mask = clean_digit_mask(d, 256, dilate_px=0, angle=0.0)
            got = count_digit_holes(mask)
            self.assertEqual(
                got,
                holes,
                f"clean digit {d}: holes={got}, expected {holes}",
            )

    def test_figure_raster_not_empty(self):
        for plate in self.plates:
            fig = rasterize_figure_dots(plate)
            self.assertGreater(
                int((fig > 0).sum()),
                100,
                f"[{plate.spec.plate_id}] empty figure raster",
            )


if __name__ == "__main__":
    unittest.main()

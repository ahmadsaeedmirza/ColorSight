"""Strict geometric / colorimetric validation for every screening plate."""

from __future__ import annotations

import unittest

from core import DEFAULT_BATTERY, PlateAxis, generate_battery, plate_metrics, render_plate


class TestPlateValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plates = generate_battery(DEFAULT_BATTERY, size=360, seed=42)

    def test_every_plate_passes_quality_gates(self):
        failures = []
        for plate in self.plates:
            pid = plate.spec.plate_id
            m = plate_metrics(plate)
            axis = plate.spec.axis

            def fail(msg: str):
                failures.append(f"[{pid}] {msg} | metrics={m}")

            if m["figure_count"] < 40:
                fail(f"figure_count {m['figure_count']} < 40")
            if m["stroke_widths_in_dots"] < 3.0:
                fail(f"stroke_width {m['stroke_widths_in_dots']:.2f} < 3 dots")
            if m["delta_e_normal"] < 20:
                fail(f"normal delta-E {m['delta_e_normal']:.2f} < 20")
            if m["delta_L"] >= 3.0:
                fail(f"delta L* {m['delta_L']:.2f} >= 3 (brightness cue)")
            if m["iou"] < 0.7:
                fail(f"figure IoU {m['iou']:.3f} < 0.7")

            # Matching deficiency must collapse figure/ground on non-control plates
            if axis == PlateAxis.CONTROL:
                continue
            if axis == PlateAxis.HIDDEN_RG:
                if m["delta_e_protan"] > 6:
                    fail(f"protan delta-E {m['delta_e_protan']:.2f} > 6")
                if m["delta_e_deutan"] > 6:
                    fail(f"deutan delta-E {m['delta_e_deutan']:.2f} > 6")
            elif axis == PlateAxis.CLASSIFY_PROTAN:
                if m["delta_e_protan"] > 6:
                    fail(f"protan delta-E {m['delta_e_protan']:.2f} > 6")
            elif axis == PlateAxis.CLASSIFY_DEUTAN:
                if m["delta_e_deutan"] > 6:
                    fail(f"deutan delta-E {m['delta_e_deutan']:.2f} > 6")
            elif axis == PlateAxis.TRITAN:
                if m["delta_e_tritan"] > 6:
                    fail(f"tritan delta-E {m['delta_e_tritan']:.2f} > 6")

        if failures:
            self.fail(
                "Plate validation failed for "
                f"{len(failures)} check(s):\n" + "\n".join(failures)
            )

    def test_render_returns_mask_and_dots(self):
        p = render_plate(DEFAULT_BATTERY[0], size=256, seed=1)
        self.assertEqual(p.image.shape[2], 3)
        self.assertEqual(p.mask.shape, p.image.shape[:2])
        self.assertGreater(len(p.dots), 100)


if __name__ == "__main__":
    unittest.main()

"""Home Chip labels must be vertically + horizontally centered in their pill."""

from __future__ import annotations

import unittest

from kivy.base import EventLoop
from kivy.clock import Clock
from kivy.metrics import dp

from colorsight.theme import register_fonts
from colorsight.widgets.chip import Chip, ChipRow


class ChipCenteringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        register_fonts()
        EventLoop.ensure_window()

    def test_each_chip_label_center_within_1dp(self):
        row = ChipRow(
            options=["All", "Test", "Photos", "Camera", "Lens", "Profile"],
            selected="All",
        )
        # Force a layout pass
        row.width = dp(360)
        row.height = dp(40)
        row.pos = (0, 0)
        Clock.tick()
        for _ in range(3):
            Clock.tick()

        chips = [c for c in row._row.children if isinstance(c, Chip)]
        self.assertGreaterEqual(len(chips), 6)
        tol = dp(1) + 0.5
        for chip in chips:
            chip._fit()
            chip._layout()
            lbl = chip._label
            self.assertAlmostEqual(
                lbl.center_x,
                chip.center_x,
                delta=tol,
                msg=f"{chip.text}: center_x label={lbl.center_x} chip={chip.center_x}",
            )
            self.assertAlmostEqual(
                lbl.center_y,
                chip.center_y,
                delta=tol,
                msg=f"{chip.text}: center_y label={lbl.center_y} chip={chip.center_y}",
            )
            self.assertEqual(chip.height, dp(40))
            # Single-line width rule: width ≈ texture + 36dp
            chip._label.text_size = (None, None)
            chip._label.texture_update()
            tw = chip._label.texture_size[0]
            self.assertGreaterEqual(chip.width + 0.5, tw + dp(36) - 1)


if __name__ == "__main__":
    unittest.main()

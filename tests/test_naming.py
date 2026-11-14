"""Tests for name_color."""

from __future__ import annotations

import unittest

from core import name_color


class TestNameColor(unittest.TestCase):
    def test_primary_colors(self):
        self.assertIn(name_color((255, 0, 0)), {"red", "dark red", "light red"})
        self.assertIn(name_color((0, 128, 0)), {"green", "dark green", "olive"})
        self.assertIn(name_color((0, 0, 255)), {"blue", "dark blue"})

    def test_neutrals(self):
        self.assertEqual(name_color((0, 0, 0)), "black")
        self.assertEqual(name_color((255, 255, 255)), "white")
        self.assertIn(name_color((128, 128, 128)), {"gray", "dark gray", "light gray"})

    def test_named_examples(self):
        self.assertEqual(name_color((128, 128, 0)), "olive")
        self.assertIn(name_color((144, 238, 144)), {"light green", "green", "lime"})
        self.assertIn(name_color((139, 0, 0)), {"dark red", "red", "brown"})

    def test_float_rgb_accepted(self):
        self.assertEqual(name_color((0.0, 0.0, 0.0)), "black")
        name = name_color((1.0, 1.0, 1.0))
        self.assertEqual(name, "white")


if __name__ == "__main__":
    unittest.main()

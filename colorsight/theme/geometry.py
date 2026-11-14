"""Geometry helpers for canvas drawing."""


def clamp_radius(radius: float, width: float, height: float) -> float:
    """Clamp a corner radius so pills stay capsules and circles stay circles.

    Always use this (and the same value for matching shadow layers) instead of
    passing raw design tokens like 999 into RoundedRectangle.
    """
    if width <= 0 or height <= 0:
        return 0.0
    return float(min(radius, width * 0.5, height * 0.5))


def clamped_radii(radius: float, width: float, height: float) -> list:
    """Kivy RoundedRectangle radius list with clamping applied."""
    r = clamp_radius(radius, width, height)
    return [r]

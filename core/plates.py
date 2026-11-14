"""Procedural Ishihara-style pseudoisochromatic plates (original artwork, not copyrighted plates)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

import cv2
import numpy as np


class PlateAxis(str, Enum):
    CONTROL = "control"  # high-contrast; nearly everyone should read
    RED_GREEN = "red_green"  # confusable for protan & deutan
    PROTAN = "protan"  # weighted toward L-cone confusion
    DEUTAN = "deutan"  # weighted toward M-cone confusion
    BLUE_YELLOW = "blue_yellow"  # confusable for tritan


@dataclass(frozen=True)
class PlateSpec:
    """Metadata for one plate in the screening battery."""

    plate_id: str
    digit: int  # 0–9 expected answer (single digit for pad simplicity)
    axis: PlateAxis
    # Which deficiencies are expected to miss this plate (empty for control)
    targets: tuple[str, ...] = ()


# Screening battery: 14 plates (within 12–16)
DEFAULT_BATTERY: tuple[PlateSpec, ...] = (
    PlateSpec("c1", 8, PlateAxis.CONTROL),
    PlateSpec("c2", 3, PlateAxis.CONTROL),
    PlateSpec("rg1", 5, PlateAxis.RED_GREEN, ("protanopia", "deuteranopia")),
    PlateSpec("rg2", 2, PlateAxis.RED_GREEN, ("protanopia", "deuteranopia")),
    PlateSpec("rg3", 6, PlateAxis.RED_GREEN, ("protanopia", "deuteranopia")),
    PlateSpec("rg4", 9, PlateAxis.RED_GREEN, ("protanopia", "deuteranopia")),
    PlateSpec("p1", 4, PlateAxis.PROTAN, ("protanopia",)),
    PlateSpec("p2", 7, PlateAxis.PROTAN, ("protanopia",)),
    PlateSpec("d1", 1, PlateAxis.DEUTAN, ("deuteranopia",)),
    PlateSpec("d2", 5, PlateAxis.DEUTAN, ("deuteranopia",)),
    PlateSpec("by1", 2, PlateAxis.BLUE_YELLOW, ("tritanopia",)),
    PlateSpec("by2", 6, PlateAxis.BLUE_YELLOW, ("tritanopia",)),
    PlateSpec("by3", 9, PlateAxis.BLUE_YELLOW, ("tritanopia",)),
    PlateSpec("rg5", 3, PlateAxis.RED_GREEN, ("protanopia", "deuteranopia")),
)


# Palette pairs: (figure_colors[], ground_colors[]) as RGB 0–255
_PALETTES = {
    PlateAxis.CONTROL: (
        [(40, 40, 40), (60, 60, 60), (25, 25, 25)],
        [(220, 220, 210), (200, 200, 190), (235, 235, 225)],
    ),
    PlateAxis.RED_GREEN: (
        [(200, 70, 60), (180, 90, 50), (210, 100, 80), (170, 60, 55)],
        [(70, 150, 90), (90, 160, 100), (60, 130, 80), (100, 170, 110)],
    ),
    PlateAxis.PROTAN: (
        # Darker reds vs olive/brown — harder when L-cone weak
        [(160, 50, 45), (140, 40, 40), (180, 70, 55)],
        [(120, 110, 50), (100, 100, 45), (130, 120, 60)],
    ),
    PlateAxis.DEUTAN: (
        # Magenta-red vs green — harder when M-cone weak
        [(210, 60, 100), (190, 50, 90), (220, 80, 110)],
        [(50, 140, 80), (40, 120, 70), (70, 150, 90)],
    ),
    PlateAxis.BLUE_YELLOW: (
        [(60, 90, 200), (50, 80, 180), (80, 100, 210)],
        [(210, 190, 60), (200, 170, 50), (220, 200, 80)],
    ),
}


def _digit_mask(digit: int, size: int, rng: np.random.Generator) -> np.ndarray:
    """Binary mask (size×size) with a centered digit; 255 = figure."""
    canvas = np.zeros((size, size), dtype=np.uint8)
    text = str(int(digit) % 10)
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = size / 160.0
    thickness = max(2, int(size / 28))
    (tw, th), baseline = cv2.getTextSize(text, font, scale, thickness)
    x = (size - tw) // 2
    y = (size + th) // 2
    cv2.putText(canvas, text, (x, y), font, scale, 255, thickness, cv2.LINE_AA)
    # Mild random rotation for less "font-like" look
    angle = float(rng.uniform(-8, 8))
    M = cv2.getRotationMatrix2D((size / 2, size / 2), angle, 1.0)
    canvas = cv2.warpAffine(canvas, M, (size, size), flags=cv2.INTER_NEAREST)
    # Dilate slightly so circle centers catch the stroke
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    return cv2.dilate(canvas, kernel, iterations=1)


def _pack_circles(
    size: int,
    rng: np.random.Generator,
    n_target: int | None = None,
) -> list[tuple[float, float, float]]:
    """Fast-ish rejection circle packing inside a disk."""
    if n_target is None:
        n_target = max(180, int(280 * (size / 420.0)))
    cx = cy = size / 2.0
    R = size * 0.48
    circles: list[tuple[float, float, float]] = []
    attempts = 0
    max_attempts = n_target * 25
    # Spatial hash to speed collision checks
    cell = size * 0.04
    grid: dict[tuple[int, int], list[int]] = {}
    while len(circles) < n_target and attempts < max_attempts:
        attempts += 1
        r = float(rng.uniform(size * 0.014, size * 0.03))
        ang = float(rng.uniform(0, 2 * np.pi))
        rad = float(rng.uniform(0, R - r))
        x = cx + rad * np.cos(ang)
        y = cy + rad * np.sin(ang)
        gi, gj = int(x / cell), int(y / cell)
        ok = True
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                for idx in grid.get((gi + di, gj + dj), ()):
                    px, py, pr = circles[idx]
                    dx, dy = x - px, y - py
                    if dx * dx + dy * dy < (r + pr + 0.5) ** 2:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            grid.setdefault((gi, gj), []).append(len(circles))
            circles.append((x, y, r))
    return circles


def render_plate(
    spec: PlateSpec,
    size: int = 512,
    seed: int | None = None,
) -> np.ndarray:
    """Render one plate as RGB uint8 HxWx3 (procedural, not copyrighted)."""
    rng = np.random.default_rng(seed if seed is not None else hash(spec.plate_id) % (2**31))
    fig_cols, gnd_cols = _PALETTES[spec.axis]
    mask = _digit_mask(spec.digit, size, rng)
    circles = _pack_circles(size, rng)

    img = np.full((size, size, 3), 245, dtype=np.uint8)  # outer cream
    # Disk background wash
    yy, xx = np.ogrid[:size, :size]
    disk = (xx - size / 2) ** 2 + (yy - size / 2) ** 2 <= (size * 0.48) ** 2
    img[disk] = (235, 232, 225)

    for x, y, r in circles:
        ix, iy = int(x), int(y)
        if 0 <= iy < size and 0 <= ix < size and mask[iy, ix] > 0:
            color = fig_cols[int(rng.integers(0, len(fig_cols)))]
        else:
            color = gnd_cols[int(rng.integers(0, len(gnd_cols)))]
        cv2.circle(img, (ix, iy), max(1, int(r)), color, -1, lineType=cv2.LINE_AA)

    return img


def generate_battery(
    specs: Sequence[PlateSpec] | None = None,
    size: int = 512,
    seed: int = 42,
) -> list[tuple[PlateSpec, np.ndarray]]:
    """Render the full screening battery."""
    specs = tuple(specs) if specs is not None else DEFAULT_BATTERY
    out = []
    for i, spec in enumerate(specs):
        img = render_plate(spec, size=size, seed=seed + i * 97)
        out.append((spec, img))
    return out


def hue_tile_colors(n: int = 7, saturation: int = 200, value: int = 220) -> list[tuple[int, int, int]]:
    """Evenly spaced hues (RGB) for the arrangement task — correct order is index order."""
    colors = []
    for i in range(n):
        h = int(180 * i / n)  # OpenCV H in [0,180)
        hsv = np.uint8([[[h, saturation, value]]])
        bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0, 0]
        colors.append((int(bgr[2]), int(bgr[1]), int(bgr[0])))
    return colors

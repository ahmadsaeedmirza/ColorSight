"""Nearest-name color labeling using Lab (+ HSV cues for dark/light)."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

# Small curated palette: (name, RGB 0–255). Lab centroids are computed once.
_NAMED_RGB: list[tuple[str, tuple[int, int, int]]] = [
    ("black", (0, 0, 0)),
    ("dark gray", (64, 64, 64)),
    ("gray", (128, 128, 128)),
    ("light gray", (192, 192, 192)),
    ("white", (255, 255, 255)),
    ("dark red", (139, 0, 0)),
    ("red", (220, 20, 60)),
    ("light red", (255, 102, 102)),
    ("pink", (255, 105, 180)),
    ("magenta", (255, 0, 255)),
    ("purple", (128, 0, 128)),
    ("lavender", (230, 190, 255)),
    ("dark blue", (0, 0, 139)),
    ("blue", (30, 144, 255)),
    ("light blue", (135, 206, 250)),
    ("cyan", (0, 200, 200)),
    ("teal", (0, 128, 128)),
    ("dark green", (0, 100, 0)),
    ("green", (34, 139, 34)),
    ("light green", (144, 238, 144)),
    ("lime", (50, 205, 50)),
    ("olive", (128, 128, 0)),
    ("yellow", (255, 215, 0)),
    ("gold", (255, 185, 15)),
    ("orange", (255, 140, 0)),
    ("peach", (255, 178, 140)),
    ("brown", (139, 90, 43)),
    ("beige", (245, 222, 179)),
]


@dataclass(frozen=True)
class _NamedSwatch:
    name: str
    rgb: np.ndarray  # uint8 (3,)
    lab: np.ndarray  # float Lab


def _rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """RGB uint8 (…, 3) → OpenCV Lab float (L, a, b)."""
    arr = np.asarray(rgb, dtype=np.uint8)
    single = arr.ndim == 1
    if single:
        arr = arr.reshape(1, 1, 3)
    elif arr.ndim == 2:
        arr = arr.reshape(-1, 1, 3)
    # OpenCV expects BGR for COLOR_BGR2LAB
    bgr = arr[..., ::-1]
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float64)
    # OpenCV Lab: L in [0,255], a/b in [0,255] with 128 = 0
    lab[..., 0] = lab[..., 0] * (100.0 / 255.0)
    lab[..., 1] = lab[..., 1] - 128.0
    lab[..., 2] = lab[..., 2] - 128.0
    if single:
        return lab.reshape(3)
    return lab.reshape(-1, 3)


def _rgb_to_hsv(rgb: np.ndarray) -> np.ndarray:
    arr = np.asarray(rgb, dtype=np.uint8).reshape(1, 1, 3)
    bgr = arr[..., ::-1]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).reshape(3).astype(np.float64)
    # H [0,180], S/V [0,255] in OpenCV
    return hsv


def _build_swatches() -> list[_NamedSwatch]:
    out: list[_NamedSwatch] = []
    for name, rgb in _NAMED_RGB:
        rgb_arr = np.array(rgb, dtype=np.uint8)
        out.append(_NamedSwatch(name=name, rgb=rgb_arr, lab=_rgb_to_lab(rgb_arr)))
    return out


_SWATCHES = _build_swatches()
_LAB_TABLE = np.stack([s.lab for s in _SWATCHES], axis=0)  # Nx3


def name_color(rgb) -> str:
    """Return the closest named color for an RGB triple.

    ``rgb`` may be a length-3 sequence or ndarray with values in 0–255
    (or 0–1 floats). Matching uses Euclidean distance in CIE Lab; near-
    neutral colors prefer gray/black/white via low HSV saturation.
    """
    arr = np.asarray(rgb, dtype=np.float64).reshape(3)
    if arr.max() <= 1.0 + 1e-6:
        arr = arr * 255.0
    arr = np.clip(np.rint(arr), 0, 255).astype(np.uint8)

    hsv = _rgb_to_hsv(arr)
    sat, val = hsv[1], hsv[2]

    # Strong neutrals: skip chromatic names
    if sat < 25:
        if val < 40:
            return "black"
        if val < 90:
            return "dark gray"
        if val < 170:
            return "gray"
        if val < 230:
            return "light gray"
        return "white"

    lab = _rgb_to_lab(arr)
    dists = np.linalg.norm(_LAB_TABLE - lab, axis=1)
    idx = int(np.argmin(dists))
    name = _SWATCHES[idx].name

    # Lightness qualifier tweak when the nearest name lacks one
    if sat >= 40 and " " not in name and name not in {"black", "white", "gray", "olive", "gold", "beige", "teal", "cyan", "lime", "pink", "magenta", "lavender", "peach", "brown"}:
        if val < 90 and not name.startswith("dark"):
            dark = f"dark {name}"
            if any(s.name == dark for s in _SWATCHES):
                return dark
        if val > 200 and not name.startswith("light"):
            light = f"light {name}"
            if any(s.name == light for s in _SWATCHES):
                return light
    return name

"""Live-camera frame helpers (pure NumPy — no Kivy)."""

from __future__ import annotations

from collections import deque

import numpy as np

from colorsight.image_pipeline import resize_longest, rgb_to_bgr, bgr_to_rgb

LIVE_LONGEST = 640  # analysis ~640×480; drop to 480 via env if a device still stutters
LOUPE_PATCH = 9
LOUPE_DIAMETER_DP = 140
DEFAULT_ZOOM = 2.5


def camera_default_mode(has_profile: bool) -> str:
    return "corrected" if has_profile else "original"


def ensure_rgb_uint8(frame: np.ndarray, *, from_bgr: bool = False) -> np.ndarray:
    """Normalize a camera frame to HxWx3 RGB uint8."""
    arr = np.asarray(frame)
    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=-1)
    if arr.ndim != 3 or arr.shape[2] < 3:
        raise ValueError(f"expected HxWx3 frame, got {arr.shape}")
    arr = arr[..., :3]
    if from_bgr:
        arr = bgr_to_rgb(arr)
    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)
    return np.ascontiguousarray(arr)


def downscale_live(rgb: np.ndarray, longest: int = LIVE_LONGEST) -> np.ndarray:
    return resize_longest(rgb, longest=longest)


def loupe_patch_median(
    rgb: np.ndarray,
    cx: float,
    cy: float,
    *,
    patch: int = LOUPE_PATCH,
) -> np.ndarray:
    """Median RGB of a small patch around (cx, cy) in image pixel coords (float ok)."""
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("rgb must be HxWx3")
    h, w = rgb.shape[:2]
    half = max(1, patch // 2)
    x = int(np.clip(round(cx), 0, w - 1))
    y = int(np.clip(round(cy), 0, h - 1))
    x0, x1 = max(0, x - half), min(w, x + half + 1)
    y0, y1 = max(0, y - half), min(h, y + half + 1)
    region = rgb[y0:y1, x0:x1]
    med = np.median(region.reshape(-1, 3), axis=0)
    return np.clip(np.rint(med), 0, 255).astype(np.uint8)


def loupe_zoom_crop(
    rgb: np.ndarray,
    cx: float,
    cy: float,
    *,
    zoom: float = DEFAULT_ZOOM,
    out_size: int = 128,
) -> np.ndarray:
    """Crop a zoomed square around (cx, cy), clamped to image edges."""
    h, w = rgb.shape[:2]
    zoom = float(np.clip(zoom, 1.0, 4.0))
    src = max(2, int(round(out_size / zoom)))
    half = src / 2.0
    x0 = int(np.clip(cx - half, 0, max(0, w - src)))
    y0 = int(np.clip(cy - half, 0, max(0, h - src)))
    x1, y1 = min(w, x0 + src), min(h, y0 + src)
    crop = rgb[y0:y1, x0:x1]
    if crop.size == 0:
        return np.zeros((out_size, out_size, 3), dtype=np.uint8)
    # Pad if we hit a corner with a short edge
    if crop.shape[0] < src or crop.shape[1] < src:
        pad = np.zeros((src, src, 3), dtype=np.uint8)
        pad[: crop.shape[0], : crop.shape[1]] = crop
        crop = pad
    from PIL import Image as PILImage

    im = PILImage.fromarray(crop, mode="RGB")
    im = im.resize((out_size, out_size), PILImage.Resampling.BILINEAR)
    return np.ascontiguousarray(np.asarray(im, dtype=np.uint8))


class LabelSmoother:
    """Majority vote over the last N name strings to reduce flicker."""

    def __init__(self, window: int = 5):
        self._buf: deque[str] = deque(maxlen=max(1, window))

    def push(self, name: str) -> str:
        self._buf.append(name)
        counts: dict[str, int] = {}
        for n in self._buf:
            counts[n] = counts.get(n, 0) + 1
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def clear(self) -> None:
        self._buf.clear()


def name_loupe_color(rgb_original: np.ndarray, cx: float, cy: float) -> tuple[str, np.ndarray]:
    """Median patch → ``core.name_color``. Returns (name, median_rgb)."""
    from core.naming import name_color

    med = loupe_patch_median(rgb_original, cx, cy)
    return name_color(med), med

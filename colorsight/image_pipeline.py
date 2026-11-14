"""Photo load / resize / composite helpers (UI layer — uses Pillow + NumPy only)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image as PILImage
from PIL import ImageOps


PREVIEW_LONGEST = 1080


def load_rgb_uint8(path: str | Path) -> np.ndarray:
    """Load image as HxWx3 RGB uint8, applying EXIF orientation."""
    path = Path(path)
    with PILImage.open(path) as im:
        im = ImageOps.exif_transpose(im)
        if im.mode == "RGBA":
            bg = PILImage.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[3])
            im = bg
        elif im.mode != "RGB":
            im = im.convert("RGB")
        arr = np.asarray(im, dtype=np.uint8)
    if arr.ndim != 3 or arr.shape[2] != 3:
        raise ValueError(f"expected HxWx3 RGB, got {arr.shape}")
    return np.ascontiguousarray(arr)


def resize_longest(rgb: np.ndarray, longest: int = PREVIEW_LONGEST) -> np.ndarray:
    """Downscale so the longest side is ``longest`` (no upscale)."""
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("rgb must be HxWx3")
    h, w = rgb.shape[:2]
    m = max(h, w)
    if m <= longest:
        return np.ascontiguousarray(rgb)
    scale = longest / float(m)
    nw, nh = max(1, int(round(w * scale))), max(1, int(round(h * scale)))
    im = PILImage.fromarray(rgb, mode="RGB")
    im = im.resize((nw, nh), PILImage.Resampling.LANCZOS)
    return np.ascontiguousarray(np.asarray(im, dtype=np.uint8))


def rgb_to_bgr(rgb: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(rgb[..., ::-1])


def bgr_to_rgb(bgr: np.ndarray) -> np.ndarray:
    return np.ascontiguousarray(bgr[..., ::-1])


def before_after_split(
    original: np.ndarray,
    corrected: np.ndarray,
    split: float,
) -> np.ndarray:
    """Composite: left of ``split`` = original, right = corrected (same shape)."""
    if original.shape != corrected.shape:
        raise ValueError("original and corrected must match shape")
    if original.dtype != np.uint8 or corrected.dtype != np.uint8:
        raise ValueError("expected uint8 images")
    s = float(np.clip(split, 0.0, 1.0))
    h, w = original.shape[:2]
    x = int(round(s * w))
    out = corrected.copy()
    if x > 0:
        out[:, :x] = original[:, :x]
    return out


def encode_image(rgb: np.ndarray, path: str | Path, *, quality: int = 95) -> Path:
    """Write RGB uint8 to JPEG (q=95) or PNG based on suffix."""
    path = Path(path)
    if rgb.ndim != 3 or rgb.shape[2] != 3 or rgb.dtype != np.uint8:
        raise ValueError("rgb must be HxWx3 uint8")
    im = PILImage.fromarray(rgb, mode="RGB")
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    if suffix in (".jpg", ".jpeg"):
        im.save(path, format="JPEG", quality=int(quality), optimize=True)
    elif suffix == ".png":
        im.save(path, format="PNG", optimize=True)
    elif suffix == ".webp":
        im.save(path, format="WEBP", quality=int(quality))
    else:
        path = path.with_suffix(".jpg")
        im.save(path, format="JPEG", quality=int(quality), optimize=True)
    return path

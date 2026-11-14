"""Photo load / resize / composite helpers (UI layer — uses Pillow + NumPy only)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont, ImageOps


PREVIEW_LONGEST = 1080
COMPARISON_LONGEST = 2048


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


def mean_abs_diff(a: np.ndarray, b: np.ndarray) -> float:
    """Mean absolute per-channel difference (0–255 scale)."""
    if a.shape != b.shape:
        raise ValueError("shapes must match")
    return float(np.mean(np.abs(a.astype(np.float64) - b.astype(np.float64))))


def severity_for_slider(profile_severity: float) -> float:
    """Map saved 0–1 severity onto the slider scale (percent steps)."""
    s = float(np.clip(profile_severity, 0.0, 1.0))
    return round(s * 100.0) / 100.0


def divider_visible(mode: str) -> bool:
    """Divider/handle shown for Corrected and Simulation only."""
    return mode in ("corrected", "simulation")


def photos_default_mode(has_profile: bool) -> str:
    """Open Corrected when a profile exists; otherwise Original."""
    return "corrected" if has_profile else "original"


def photos_default_split() -> float:
    """Start at 0% so the whole image shows the filtered side; drag right to reveal original."""
    return 0.0


def strength_percent(severity: float) -> int:
    return int(round(severity_for_slider(severity) * 100.0))


def reset_link_visible(preview_severity: float, saved_severity: float) -> bool:
    return abs(float(preview_severity) - float(saved_severity)) > 0.005


def right_label_for_mode(mode: str) -> str:
    if mode == "simulation":
        return "Simulation"
    if mode == "corrected":
        return "Corrected"
    return ""


def render_mode_rgb(original: np.ndarray, mode: str, *, cvd_type, severity: float) -> np.ndarray:
    """Full-res (or any size) RGB for the active mode. Does not touch saved profiles."""
    from core.engine import apply_correction, apply_simulation
    from core.profile import CorrectionProfile

    if mode == "original":
        return np.ascontiguousarray(original)
    sev = float(np.clip(severity, 0.0, 1.0))
    if mode == "simulation":
        return apply_simulation(original, cvd_type, sev)
    # corrected (default)
    tmp = CorrectionProfile.create(cvd_type, sev)
    return apply_correction(original, tmp)


def build_comparison_card(
    original: np.ndarray,
    simulation: np.ndarray,
    *,
    longest: int = COMPARISON_LONGEST,
    left_caption: str = "Normal vision",
    right_caption: str = "How I see it",
    brand: str = "ColorSight",
) -> np.ndarray:
    """Side-by-side pastel comparison card (max ``longest`` on the long side)."""
    if original.shape != simulation.shape:
        raise ValueError("original and simulation must match shape")
    pair = before_after_split(original, simulation, 0.5)
    pair = resize_longest(pair, longest=longest)
    h, w = pair.shape[:2]
    pad = max(12, w // 40)
    footer = max(36, h // 14)
    label_h = max(28, h // 18)
    canvas_h = h + label_h + footer + pad
    canvas_w = w + pad * 2
    # Pastel cream background (#F6F4F1)
    bg = np.full((canvas_h, canvas_w, 3), (246, 244, 241), dtype=np.uint8)
    y0 = pad // 2 + label_h
    bg[y0 : y0 + h, pad : pad + w] = pair

    im = PILImage.fromarray(bg, mode="RGB")
    draw = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("arial.ttf", max(14, label_h // 2))
        font_sm = ImageFont.truetype("arial.ttf", max(12, footer // 3))
    except OSError:
        font = ImageFont.load_default()
        font_sm = font

    # Captions over left / right halves
    mid = pad + w // 2
    draw.text((pad + 8, 6), left_caption, fill=(28, 28, 28), font=font)
    # right caption roughly right-aligned in right half
    tw = draw.textlength(right_caption, font=font) if hasattr(draw, "textlength") else len(right_caption) * 7
    draw.text((max(mid + 8, pad + w - 8 - tw), 6), right_caption, fill=(28, 28, 28), font=font)
    # Center divider tick
    draw.line([(mid, y0), (mid, y0 + h)], fill=(255, 255, 255), width=2)
    # Brand footer
    bw = draw.textlength(brand, font=font_sm) if hasattr(draw, "textlength") else len(brand) * 6
    draw.text(((canvas_w - bw) / 2, canvas_h - footer + 8), brand, fill=(107, 107, 107), font=font_sm)
    return np.ascontiguousarray(np.asarray(im, dtype=np.uint8))

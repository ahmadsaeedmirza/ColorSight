"""Procedural Ishihara-style plates (original artwork — not copyrighted Ishihara prints)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np
from PIL import Image as PILImage
from PIL import ImageDraw, ImageFont

from .cvd_types import CVDType
from .engine import apply_simulation

# SemiBold keeps a bold sans look with more open counters than Bold (3/6/8/9).
_FONTS = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "Lexend-SemiBold.ttf"
_FONTS_BOLD = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "Lexend-Bold.ttf"
if not _FONTS.exists():
    _FONTS = _FONTS_BOLD

# Precomputed equiluminant confusion pairs (validated against Machado sim @ 1.0)
_FALLBACK_PAIRS = {
    "control": ((90, 140, 200), (172, 129, 69)),  # equiluminant, high ΔE
    CVDType.DEUTERANOPIA: ((132, 174, 158), (234, 132, 164)),
    CVDType.PROTANOPIA: ((34, 167, 211), (154, 149, 212)),
    CVDType.TRITANOPIA: ((215, 52, 56), (219, 0, 145)),
    # Collapses under BOTH protan and deutan (Machado @ 1.0)
    "hidden_rg": ((123, 166, 38), (205, 139, 29)),
}


class PlateAxis(str, Enum):
    CONTROL = "control"
    HIDDEN_RG = "hidden_rg"
    CLASSIFY_PROTAN = "classify_protan"
    CLASSIFY_DEUTAN = "classify_deutan"
    TRITAN = "tritan"


@dataclass(frozen=True)
class PlateSpec:
    plate_id: str
    digit: int
    axis: PlateAxis
    expected_normal: int | None
    expected_protan: int | None
    expected_deutan: int | None
    expected_tritan: int | None

    def expected_for(self, viewer: str) -> int | None:
        key = str(viewer).lower()
        if key in ("normal", "typical"):
            return self.expected_normal
        if key in ("protanopia", "protan", "protanomaly"):
            return self.expected_protan
        if key in ("deuteranopia", "deutan", "deuteranomaly"):
            return self.expected_deutan
        if key in ("tritanopia", "tritan", "tritanomaly"):
            return self.expected_tritan
        raise ValueError(f"unknown viewer type: {viewer}")


DEFAULT_BATTERY: tuple[PlateSpec, ...] = (
    PlateSpec("c1", 8, PlateAxis.CONTROL, 8, 8, 8, 8),
    PlateSpec("h1", 5, PlateAxis.HIDDEN_RG, 5, None, None, 5),
    PlateSpec("h2", 2, PlateAxis.HIDDEN_RG, 2, None, None, 2),
    PlateSpec("h3", 6, PlateAxis.HIDDEN_RG, 6, None, None, 6),
    PlateSpec("h4", 9, PlateAxis.HIDDEN_RG, 9, None, None, 9),
    PlateSpec("h5", 3, PlateAxis.HIDDEN_RG, 3, None, None, 3),
    PlateSpec("h6", 7, PlateAxis.HIDDEN_RG, 7, None, None, 7),
    PlateSpec("cp1", 4, PlateAxis.CLASSIFY_PROTAN, 4, None, 4, 4),
    PlateSpec("cp2", 1, PlateAxis.CLASSIFY_PROTAN, 1, None, 1, 1),
    PlateSpec("cd1", 5, PlateAxis.CLASSIFY_DEUTAN, 5, 5, None, 5),
    PlateSpec("cd2", 2, PlateAxis.CLASSIFY_DEUTAN, 2, 2, None, 2),
    PlateSpec("cd3", 6, PlateAxis.CLASSIFY_DEUTAN, 6, 6, None, 6),
    PlateSpec("t1", 3, PlateAxis.TRITAN, 3, 3, 3, None),
    PlateSpec("t2", 9, PlateAxis.TRITAN, 9, 9, 9, None),
)


@dataclass
class CircleDot:
    x: float
    y: float
    r: float
    is_figure: bool
    rgb: tuple[int, int, int]


@dataclass
class RenderedPlate:
    spec: PlateSpec
    image: np.ndarray
    mask: np.ndarray
    dots: list[CircleDot] = field(default_factory=list)

    @property
    def figure_count(self) -> int:
        return sum(1 for d in self.dots if d.is_figure)


def _rgb_to_lab_arr(rgb: np.ndarray) -> np.ndarray:
    arr = np.asarray(rgb, dtype=np.uint8)
    shape = arr.shape
    flat = arr.reshape(-1, 1, 3)
    lab = cv2.cvtColor(flat[..., ::-1], cv2.COLOR_BGR2LAB).astype(np.float64)
    lab[..., 0] *= 100.0 / 255.0
    lab[..., 1] -= 128.0
    lab[..., 2] -= 128.0
    return lab.reshape(shape)


def _lab_to_rgb(lab: np.ndarray) -> tuple[int, int, int]:
    lab_cv = lab.astype(np.float64).copy()
    lab_cv[0] = np.clip(lab_cv[0] * 255.0 / 100.0, 0, 255)
    lab_cv[1] = np.clip(lab_cv[1] + 128.0, 0, 255)
    lab_cv[2] = np.clip(lab_cv[2] + 128.0, 0, 255)
    bgr = cv2.cvtColor(np.uint8([[lab_cv]]), cv2.COLOR_LAB2BGR)[0, 0]
    return int(bgr[2]), int(bgr[1]), int(bgr[0])


def _delta_e(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))


def _match_L(rgb: np.ndarray, target_L: float) -> np.ndarray:
    g = rgb.astype(np.float64)
    for _ in range(12):
        lab = _rgb_to_lab_arr(np.uint8([[np.clip(g, 0, 255)]]))[0, 0]
        if abs(lab[0] - target_L) < 0.35:
            break
        g = np.clip(g * ((target_L + 1.0) / (lab[0] + 1.0)), 0, 255)
    return g


def _chroma_jitter(base: tuple[int, int, int], rng: np.random.Generator) -> tuple[int, int, int]:
    # Keep jitter small so mean figure/ground still collapse under CVD
    lab = _rgb_to_lab_arr(np.uint8([base]))[0].astype(np.float64)
    lab[1] += float(rng.normal(0, 1.8))
    lab[2] += float(rng.normal(0, 1.8))
    return _lab_to_rgb(lab)


def _search_pair(
    rng: np.random.Generator,
    cvd: CVDType | None = None,
    also_cvd: CVDType | None = None,
    n_tries: int = 5000,
) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    best = None
    best_score = -1e9
    for _ in range(n_tries):
        f = rng.integers(20, 240, 3).astype(np.float64)
        g = np.clip(f + rng.normal(0, 60, 3), 0, 255)
        lf = _rgb_to_lab_arr(np.uint8([[f]]))[0, 0]
        g = _match_L(g, float(lf[0]))
        lg = _rgb_to_lab_arr(np.uint8([[g]]))[0, 0]
        dL = abs(float(lf[0] - lg[0]))
        if dL >= 2.4:
            continue
        de_n = _delta_e(lf, lg)
        if de_n < 22:
            continue
        patch = np.stack([f, g]).reshape(2, 1, 3).astype(np.uint8)
        de_s = 0.0
        if cvd is not None:
            sim = apply_simulation(patch, cvd, 1.0)
            de_s = _delta_e(_rgb_to_lab_arr(sim[0:1])[0, 0], _rgb_to_lab_arr(sim[1:2])[0, 0])
            if also_cvd is not None:
                sim2 = apply_simulation(patch, also_cvd, 1.0)
                de_s = max(
                    de_s,
                    _delta_e(_rgb_to_lab_arr(sim2[0:1])[0, 0], _rgb_to_lab_arr(sim2[1:2])[0, 0]),
                )
            if de_s > 5.5:
                continue
        score = de_n - 4.0 * de_s - 2.0 * dL
        if score > best_score:
            best_score = score
            best = (tuple(int(x) for x in f), tuple(int(x) for x in g))
    return best  # type: ignore[return-value]


_PAIR_CACHE: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {}


def _pair_for_axis(axis: PlateAxis, rng: np.random.Generator):
    """Return figure/ground bases. Prefer searched pairs; fall back to validated constants."""
    key = axis.value
    if key in _PAIR_CACHE:
        return _PAIR_CACHE[key]

    def _ok(pair, cvd=None, also=None) -> bool:
        f, g = pair
        patch = np.stack([f, g]).reshape(2, 1, 3).astype(np.uint8)
        lf = _rgb_to_lab_arr(patch[0:1])[0, 0]
        lg = _rgb_to_lab_arr(patch[1:2])[0, 0]
        if abs(float(lf[0] - lg[0])) >= 2.5:
            return False
        if _delta_e(lf, lg) < 22:
            return False
        if cvd is None:
            return True
        sim = apply_simulation(patch, cvd, 1.0)
        de = _delta_e(_rgb_to_lab_arr(sim[0:1])[0, 0], _rgb_to_lab_arr(sim[1:2])[0, 0])
        if also is not None:
            sim2 = apply_simulation(patch, also, 1.0)
            de = max(de, _delta_e(_rgb_to_lab_arr(sim2[0:1])[0, 0], _rgb_to_lab_arr(sim2[1:2])[0, 0]))
        return de <= 5.0

    # Use lab-validated fallbacks (fast + stable under chroma jitter). Optional search
    # can refine when it clearly beats the fallback gates.
    if axis == PlateAxis.CONTROL:
        found = _search_pair(rng, None, n_tries=1500)
        pair = found if found and _ok(found) else _FALLBACK_PAIRS["control"]
    elif axis == PlateAxis.HIDDEN_RG:
        pair = _FALLBACK_PAIRS["hidden_rg"]
    elif axis == PlateAxis.CLASSIFY_PROTAN:
        pair = _FALLBACK_PAIRS[CVDType.PROTANOPIA]
    elif axis == PlateAxis.CLASSIFY_DEUTAN:
        pair = _FALLBACK_PAIRS[CVDType.DEUTERANOPIA]
    else:
        pair = _FALLBACK_PAIRS[CVDType.TRITANOPIA]
    _PAIR_CACHE[key] = pair
    return pair


def clean_digit_mask(
    digit: int,
    size: int,
    *,
    dilate_px: int = 0,
    angle: float = 0.0,
) -> np.ndarray:
    """Clean centered Lexend digit (~60% of plate). Optional light dilation only."""
    canvas = PILImage.new("L", (size, size), 0)
    draw = ImageDraw.Draw(canvas)
    font_size = int(size * 0.60)
    font_path = _FONTS if _FONTS.exists() else _FONTS_BOLD
    font = ImageFont.truetype(str(font_path), font_size)
    text = str(int(digit) % 10)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) // 2 - bbox[0]
    y = (size - th) // 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=255)
    arr = np.array(canvas, dtype=np.uint8)
    if abs(angle) > 1e-3:
        M = cv2.getRotationMatrix2D((size / 2, size / 2), angle, 1.0)
        arr = cv2.warpAffine(arr, M, (size, size), flags=cv2.INTER_NEAREST)
    if dilate_px > 0:
        k = dilate_px if dilate_px % 2 == 1 else dilate_px + 1
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        # Single pass — keep counters (holes) of 3/6/8/9 open
        arr = cv2.dilate(arr, kernel, iterations=1)
    _, arr = cv2.threshold(arr, 127, 255, cv2.THRESH_BINARY)
    return arr


def _digit_mask(digit: int, size: int, rng: np.random.Generator) -> np.ndarray:
    """Plate figure mask: Lexend SemiBold ~60%, light erode so counters stay open."""
    angle = float(rng.uniform(-3, 3))
    arr = clean_digit_mask(digit, size, dilate_px=0, angle=angle)
    # One light erode — opens bowls/loops without collapsing stroke below ~3 dots
    k = max(3, int(size * 0.007))
    if k % 2 == 0:
        k += 1
    arr = cv2.erode(arr, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)), iterations=1)
    _, arr = cv2.threshold(arr, 127, 255, cv2.THRESH_BINARY)
    return arr


def _stroke_px(mask: np.ndarray) -> float:
    if mask.max() == 0:
        return 0.0
    binary = (mask > 0).astype(np.uint8)
    dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    inside = dist[binary > 0]
    if inside.size == 0:
        return 0.0
    return 2.0 * float(np.median(inside))


def _estimate_stroke_width_dots(mask: np.ndarray, avg_dot_diam: float) -> float:
    if avg_dot_diam <= 0:
        return 0.0
    return _stroke_px(mask) / avg_dot_diam


def _radius_band_for_stroke(stroke_px: float, size: int) -> tuple[float, float]:
    """Choose radii so ~3.2–3.8 dots span the stroke; keep paint radius ≥ 2.2 px."""
    # Smaller dots after Bold erode — diameter ≈ stroke/3.5 → radius ≈ stroke/7
    target_r = max(2.2, stroke_px / 7.0) if stroke_px > 0 else size * 0.009
    r_min = max(2.0, target_r * 0.82)
    r_max = min(target_r * 1.08, stroke_px / 6.2 if stroke_px > 0 else target_r * 1.08)
    if r_max < r_min:
        r_max = r_min + 0.12
    return r_min, r_max


def pack_circles_dense(
    size: int,
    rng: np.random.Generator,
    r_min: float | None = None,
    r_max: float | None = None,
) -> list[tuple[float, float, float]]:
    """Public dense circle packer (used by plates + trivector Landolt fields)."""
    return _pack_circles_dense(size, rng, r_min=r_min, r_max=r_max)


def _pack_circles_dense(
    size: int,
    rng: np.random.Generator,
    r_min: float | None = None,
    r_max: float | None = None,
) -> list[tuple[float, float, float]]:
    """Dense packing: many small dots, light touch (not blobbing) to fill strokes."""
    cx = cy = size / 2.0
    R = size * 0.475
    if r_min is None or r_max is None:
        r_min = size * 0.0075
        r_max = size * 0.0125
    # Air between dots (Ishihara-like stipple); avoid solid blobbing that closes bowls
    spacing = max(r_min + r_max + 1.0, size * 0.019)
    gap = 0.75
    circles: list[tuple[float, float, float]] = []
    row = 0
    y = cy - R
    while y <= cy + R:
        x_off = (spacing * 0.5) if (row % 2) else 0.0
        x = cx - R + x_off
        while x <= cx + R:
            r = float(rng.uniform(r_min, r_max))
            jx = float(rng.uniform(-spacing * 0.10, spacing * 0.10))
            jy = float(rng.uniform(-spacing * 0.10, spacing * 0.10))
            px, py = x + jx, y + jy
            if (px - cx) ** 2 + (py - cy) ** 2 <= (R - r) ** 2:
                circles.append((px, py, r))
            x += spacing
        y += spacing * 0.866
        row += 1
    cell = spacing
    grid: dict[tuple[int, int], list[int]] = {}
    for i, (x, y, r) in enumerate(circles):
        grid.setdefault((int(x / cell), int(y / cell)), []).append(i)
    extras = attempts = 0
    target_extras = len(circles) // 3
    while extras < target_extras and attempts < len(circles) * 14:
        attempts += 1
        r = float(rng.uniform(r_min, r_max))
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
                    if (x - px) ** 2 + (y - py) ** 2 < (r + pr + gap) ** 2:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            grid.setdefault((gi, gj), []).append(len(circles))
            circles.append((x, y, r))
            extras += 1
    return circles


def _paint_dots(
    img: np.ndarray,
    disk: np.ndarray,
    circles: list[tuple[float, float, float]],
    mask: np.ndarray,
    fig_base: tuple[int, int, int],
    gnd_base: tuple[int, int, int],
    rng: np.random.Generator,
) -> list[CircleDot]:
    size = img.shape[0]
    img[disk] = (238, 235, 228)
    dots: list[CircleDot] = []
    for x, y, r in circles:
        ix, iy = int(round(x)), int(round(y))
        if not (0 <= iy < size and 0 <= ix < size):
            continue
        is_fig = bool(mask[iy, ix] > 0)
        rgb = _chroma_jitter(fig_base if is_fig else gnd_base, rng)
        # Perfect disk via ellipse mask (avoids Bresenham star/jagged artifacts)
        rad_px = max(2, int(np.ceil(r - 1e-6)))
        cv2.ellipse(img, (ix, iy), (rad_px, rad_px), 0, 0, 360, rgb, -1, lineType=cv2.LINE_8)
        dots.append(CircleDot(x=x, y=y, r=r, is_figure=is_fig, rgb=rgb))
    return dots


def _inset_mask_for_dots(mask: np.ndarray, r_max: float) -> np.ndarray:
    """Erode ink by ~dot radius so painted circles stay inside the stroke (open counters)."""
    k = max(3, int(np.ceil(r_max * 1.25)))
    if k % 2 == 0:
        k += 1
    out = cv2.erode(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)), iterations=1)
    _, out = cv2.threshold(out, 127, 255, cv2.THRESH_BINARY)
    return out


def render_plate(spec: PlateSpec, size: int = 512, seed: int | None = None) -> RenderedPlate:
    rng = np.random.default_rng(seed if seed is not None else abs(hash(spec.plate_id)) % (2**31))
    fig_base, gnd_base = _pair_for_axis(spec.axis, rng)
    ink = _digit_mask(spec.digit, size, rng)
    stroke_px = _stroke_px(ink)
    r_min, r_max = _radius_band_for_stroke(stroke_px, size)
    # Assignment inset so painted circles stay inside ink (open counters / bowls)
    assign = _inset_mask_for_dots(ink, r_max)
    if assign.max() == 0:
        assign = ink
    circles = _pack_circles_dense(size, rng, r_min=r_min, r_max=r_max)

    img = np.full((size, size, 3), 245, dtype=np.uint8)
    yy, xx = np.ogrid[:size, :size]
    disk = (xx - size / 2) ** 2 + (yy - size / 2) ** 2 <= (size * 0.48) ** 2

    dots = _paint_dots(img, disk, circles, assign, fig_base, gnd_base, rng)

    fig_n = sum(1 for d in dots if d.is_figure)
    if fig_n < 40:
        # Milder inset only — never dilate (dilation closes 3/9 counters)
        assign = _inset_mask_for_dots(ink, max(1.0, r_max * 0.5))
        if assign.max() == 0:
            assign = ink
        dots = _paint_dots(img, disk, circles, assign, fig_base, gnd_base, rng)

    # Store ink (not inset) so stroke/IoU gates measure the intended digit shape
    return RenderedPlate(spec=spec, image=img, mask=ink, dots=dots)


def generate_battery(
    specs: Sequence[PlateSpec] | None = None,
    size: int = 512,
    seed: int = 42,
) -> list[RenderedPlate]:
    specs = tuple(specs) if specs is not None else DEFAULT_BATTERY
    return [render_plate(spec, size=size, seed=seed + i * 97) for i, spec in enumerate(specs)]


def rasterize_figure_dots(plate: RenderedPlate, size: int | None = None) -> np.ndarray:
    h = size or plate.image.shape[0]
    out = np.zeros((h, h), dtype=np.uint8)
    scale = h / plate.image.shape[0]
    for d in plate.dots:
        if d.is_figure:
            rr = max(2, int(np.ceil(d.r * scale - 1e-6)))
            cv2.ellipse(
                out,
                (int(round(d.x * scale)), int(round(d.y * scale))),
                (rr, rr),
                0,
                0,
                360,
                255,
                -1,
                lineType=cv2.LINE_8,
            )
    return out


# Topology of Lexend digits (closed counters / holes).
EXPECTED_DIGIT_HOLES: dict[int, int] = {
    0: 1,
    1: 0,
    2: 0,
    3: 0,
    4: 1,  # Lexend closed triangular counter
    5: 0,
    6: 1,
    7: 0,
    8: 2,
    9: 1,
}

# Minimum IoU lead of best digit over runner-up (shape recognizability)
RECOG_MARGIN = 0.08


def normalize_binary_digit(binary: np.ndarray, out_size: int = 128) -> np.ndarray:
    """Crop ink bbox and fit into a fixed square for template comparison."""
    bin_u8 = (binary > 0).astype(np.uint8) * 255
    ys, xs = np.where(bin_u8 > 0)
    canvas = np.zeros((out_size, out_size), dtype=np.uint8)
    if xs.size == 0:
        return canvas
    pad = 2
    y0, y1 = max(0, int(ys.min()) - pad), min(bin_u8.shape[0], int(ys.max()) + 1 + pad)
    x0, x1 = max(0, int(xs.min()) - pad), min(bin_u8.shape[1], int(xs.max()) + 1 + pad)
    crop = bin_u8[y0:y1, x0:x1]
    ch, cw = crop.shape
    scale = (out_size - 8) / max(ch, cw)
    nh, nw = max(1, int(round(ch * scale))), max(1, int(round(cw * scale)))
    resized = cv2.resize(crop, (nw, nh), interpolation=cv2.INTER_NEAREST)
    yy = (out_size - nh) // 2
    xx = (out_size - nw) // 2
    canvas[yy : yy + nh, xx : xx + nw] = resized
    _, canvas = cv2.threshold(canvas, 127, 255, cv2.THRESH_BINARY)
    return canvas


def fill_figure_stroke_gaps(binary: np.ndarray, avg_dot_r: float | None = None) -> np.ndarray:
    """Morph-close inter-dot gaps inside strokes without sealing digit counters."""
    bin_u8 = (binary > 0).astype(np.uint8) * 255
    if avg_dot_r is None:
        # Infer from foreground area / perimeter-ish: use ~2% of min side, capped
        k = max(3, int(min(bin_u8.shape) * 0.018))
    else:
        # Close gaps ~ one diameter; counters of 6/8/9 are much larger
        k = max(3, int(round(avg_dot_r * 2.2)))
    if k % 2 == 0:
        k += 1
    closed = cv2.morphologyEx(
        bin_u8, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    )
    # Drop speckles that are not part of the digit
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(closed, connectivity=8)
    if n_labels <= 1:
        return closed
    areas = stats[1:, cv2.CC_STAT_AREA]
    keep = 1 + int(np.argmax(areas))
    out = np.zeros_like(closed)
    out[labels == keep] = 255
    return out


def count_digit_holes(binary: np.ndarray, avg_dot_r: float | None = None) -> int:
    """Count closed counters via contour hierarchy (holes = children of outer contours)."""
    closed = fill_figure_stroke_gaps(binary, avg_dot_r)
    contours, hierarchy = cv2.findContours(closed, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        return 0
    # Ignore tiny spurious holes (noise) — real counters are sizable
    min_hole_area = (min(closed.shape) * 0.03) ** 2
    holes = 0
    for i, h in enumerate(hierarchy[0]):
        if h[3] < 0:
            continue
        area = cv2.contourArea(contours[i])
        if area >= min_hole_area:
            holes += 1
    return holes


def _binary_iou(a: np.ndarray, b: np.ndarray) -> float:
    aa = a > 0
    bb = b > 0
    inter = np.logical_and(aa, bb).sum()
    union = np.logical_or(aa, bb).sum()
    return float(inter / union) if union else 0.0


def match_digit_scores(figure_binary: np.ndarray, avg_dot_r: float | None = None) -> dict[int, float]:
    """IoU (+ optional template correlation) of filled figure vs clean Lexend 0–9."""
    filled = fill_figure_stroke_gaps(figure_binary, avg_dot_r)
    probe = normalize_binary_digit(filled)
    size = 256
    scores: dict[int, float] = {}
    for d in range(10):
        tmpl = clean_digit_mask(d, size, dilate_px=0, angle=0.0)
        tnorm = normalize_binary_digit(tmpl)
        iou = _binary_iou(probe, tnorm)
        # Correlation on float masks sharpens the margin between near digits (3/8/9)
        corr = float(
            cv2.matchTemplate(
                probe.astype(np.float32) / 255.0,
                tnorm.astype(np.float32) / 255.0,
                cv2.TM_CCOEFF_NORMED,
            )[0, 0]
        )
        scores[d] = 0.55 * iou + 0.45 * max(0.0, corr)
    return scores


def recognize_figure_digit(
    figure_binary: np.ndarray, avg_dot_r: float | None = None
) -> tuple[int, float, float]:
    """Return (best_digit, best_score, runner_up_score)."""
    scores = match_digit_scores(figure_binary, avg_dot_r)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_d, best_s = ranked[0]
    runner_s = ranked[1][1] if len(ranked) > 1 else 0.0
    return best_d, best_s, runner_s


def digit_recognizability(plate: RenderedPlate) -> dict:
    """Color-independent shape check against expected_normal digit."""
    expected = plate.spec.expected_normal
    fig = rasterize_figure_dots(plate)
    avg_r = float(np.mean([d.r for d in plate.dots])) if plate.dots else None
    best, best_s, runner_s = recognize_figure_digit(fig, avg_r)
    holes = count_digit_holes(fig, avg_r)
    exp_holes = EXPECTED_DIGIT_HOLES.get(int(expected) if expected is not None else -1, -1)
    return {
        "plate_id": plate.spec.plate_id,
        "expected": expected,
        "best_digit": best,
        "best_score": best_s,
        "runner_up_score": runner_s,
        "margin": best_s - runner_s,
        "holes": holes,
        "expected_holes": exp_holes,
        "ok_match": expected is not None and best == int(expected) and (best_s - runner_s) >= RECOG_MARGIN,
        "ok_holes": expected is not None and holes == exp_holes,
    }


def plate_metrics(plate: RenderedPlate) -> dict:
    fig = [d for d in plate.dots if d.is_figure]
    gnd = [d for d in plate.dots if not d.is_figure]
    fig_rgb = np.array([d.rgb for d in fig], dtype=np.uint8)
    gnd_rgb = np.array([d.rgb for d in gnd], dtype=np.uint8)
    lab_f = _rgb_to_lab_arr(fig_rgb).mean(axis=0)
    lab_g = _rgb_to_lab_arr(gnd_rgb).mean(axis=0)
    de_normal = _delta_e(lab_f, lab_g)
    dL = abs(float(lab_f[0] - lab_g[0]))

    def de_under(cvd: CVDType) -> float:
        patch = np.stack([fig_rgb.mean(0), gnd_rgb.mean(0)]).reshape(2, 1, 3).astype(np.uint8)
        sim = apply_simulation(patch, cvd, 1.0)
        return _delta_e(_rgb_to_lab_arr(sim[0:1])[0, 0], _rgb_to_lab_arr(sim[1:2])[0, 0])

    avg_diam = float(np.mean([2 * d.r for d in plate.dots])) if plate.dots else 1.0
    avg_r = float(np.mean([d.r for d in plate.dots])) if plate.dots else 1.0
    stroke = _estimate_stroke_width_dots(plate.mask, avg_diam)
    # Close inter-dot gaps before IoU so sparse packing still covers the ink stroke
    fig_rast = fill_figure_stroke_gaps(rasterize_figure_dots(plate), avg_r)
    mask = plate.mask
    if fig_rast.shape != mask.shape:
        fig_rast = cv2.resize(fig_rast, (mask.shape[1], mask.shape[0]), interpolation=cv2.INTER_NEAREST)
    inter = np.logical_and(fig_rast > 0, mask > 0).sum()
    union = np.logical_or(fig_rast > 0, mask > 0).sum()
    iou = float(inter / union) if union else 0.0
    return {
        "figure_count": len(fig),
        "ground_count": len(gnd),
        "delta_e_normal": de_normal,
        "delta_e_protan": de_under(CVDType.PROTANOPIA),
        "delta_e_deutan": de_under(CVDType.DEUTERANOPIA),
        "delta_e_tritan": de_under(CVDType.TRITANOPIA),
        "delta_L": dL,
        "stroke_widths_in_dots": stroke,
        "iou": iou,
    }


def hue_tile_colors(n: int = 7, saturation: int = 200, value: int = 220) -> list[tuple[int, int, int]]:
    colors = []
    for i in range(n):
        h = int(180 * i / n)
        hsv = np.uint8([[[h, saturation, value]]])
        bgr = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[0, 0]
        colors.append((int(bgr[2]), int(bgr[1]), int(bgr[0])))
    return colors

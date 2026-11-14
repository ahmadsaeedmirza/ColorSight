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

_FONTS = Path(__file__).resolve().parents[1] / "assets" / "fonts" / "Lexend-Bold.ttf"

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


def _digit_mask(digit: int, size: int, rng: np.random.Generator) -> np.ndarray:
    canvas = PILImage.new("L", (size, size), 0)
    draw = ImageDraw.Draw(canvas)
    font_size = int(size * 0.60)
    font = ImageFont.truetype(str(_FONTS), font_size)
    text = str(int(digit) % 10)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) // 2 - bbox[0]
    y = (size - th) // 2 - bbox[1]
    draw.text((x, y), text, font=font, fill=255)
    arr = np.array(canvas, dtype=np.uint8)
    angle = float(rng.uniform(-5, 5))
    M = cv2.getRotationMatrix2D((size / 2, size / 2), angle, 1.0)
    arr = cv2.warpAffine(arr, M, (size, size), flags=cv2.INTER_NEAREST)
    # Thick stroke: ≥3–4 average dots (avg diam ≈ 0.04*size)
    k = max(11, int(size * 0.065))
    if k % 2 == 0:
        k += 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    arr = cv2.dilate(arr, kernel, iterations=4)
    _, arr = cv2.threshold(arr, 127, 255, cv2.THRESH_BINARY)
    return arr


def _pack_circles_dense(size: int, rng: np.random.Generator) -> list[tuple[float, float, float]]:
    cx = cy = size / 2.0
    R = size * 0.475
    r_min, r_max = size * 0.011, size * 0.030
    spacing = size * 0.036
    circles: list[tuple[float, float, float]] = []
    row = 0
    y = cy - R
    while y <= cy + R:
        x_off = (spacing * 0.5) if (row % 2) else 0.0
        x = cx - R + x_off
        while x <= cx + R:
            r = float(rng.uniform(r_min, r_max))
            jx = float(rng.uniform(-spacing * 0.2, spacing * 0.2))
            jy = float(rng.uniform(-spacing * 0.2, spacing * 0.2))
            px, py = x + jx, y + jy
            if (px - cx) ** 2 + (py - cy) ** 2 <= (R - r) ** 2:
                circles.append((px, py, r))
            x += spacing
        y += spacing * 0.86
        row += 1
    cell = spacing
    grid: dict[tuple[int, int], list[int]] = {}
    for i, (x, y, r) in enumerate(circles):
        grid.setdefault((int(x / cell), int(y / cell)), []).append(i)
    extras = attempts = 0
    while extras < len(circles) // 4 and attempts < len(circles) * 10:
        attempts += 1
        r = float(rng.uniform(r_min * 0.85, r_max * 0.95))
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
                    if (x - px) ** 2 + (y - py) ** 2 < (r + pr + 0.35) ** 2:
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


def _estimate_stroke_width_dots(mask: np.ndarray, avg_dot_diam: float) -> float:
    if mask.max() == 0 or avg_dot_diam <= 0:
        return 0.0
    binary = (mask > 0).astype(np.uint8)
    dist = cv2.distanceTransform(binary, cv2.DIST_L2, 5)
    inside = dist[binary > 0]
    if inside.size == 0:
        return 0.0
    return (2.0 * float(np.median(inside))) / avg_dot_diam


def render_plate(spec: PlateSpec, size: int = 512, seed: int | None = None) -> RenderedPlate:
    rng = np.random.default_rng(seed if seed is not None else abs(hash(spec.plate_id)) % (2**31))
    fig_base, gnd_base = _pair_for_axis(spec.axis, rng)
    mask = _digit_mask(spec.digit, size, rng)
    circles = _pack_circles_dense(size, rng)

    img = np.full((size, size, 3), 245, dtype=np.uint8)
    yy, xx = np.ogrid[:size, :size]
    disk = (xx - size / 2) ** 2 + (yy - size / 2) ** 2 <= (size * 0.48) ** 2
    img[disk] = (238, 235, 228)

    dots: list[CircleDot] = []
    for x, y, r in circles:
        ix, iy = int(round(x)), int(round(y))
        if not (0 <= iy < size and 0 <= ix < size):
            continue
        is_fig = bool(mask[iy, ix] > 0)
        rgb = _chroma_jitter(fig_base if is_fig else gnd_base, rng)
        cv2.circle(img, (ix, iy), max(1, int(round(r))), rgb, -1, lineType=cv2.LINE_AA)
        dots.append(CircleDot(x=x, y=y, r=r, is_figure=is_fig, rgb=rgb))

    fig_n = sum(1 for d in dots if d.is_figure)
    if fig_n < 40:
        k = max(11, int(size * 0.07))
        if k % 2 == 0:
            k += 1
        mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)), 1)
        dots = []
        img[disk] = (238, 235, 228)
        for x, y, r in circles:
            ix, iy = int(round(x)), int(round(y))
            if not (0 <= iy < size and 0 <= ix < size):
                continue
            is_fig = bool(mask[iy, ix] > 0)
            rgb = _chroma_jitter(fig_base if is_fig else gnd_base, rng)
            cv2.circle(img, (ix, iy), max(1, int(round(r))), rgb, -1, lineType=cv2.LINE_AA)
            dots.append(CircleDot(x=x, y=y, r=r, is_figure=is_fig, rgb=rgb))

    return RenderedPlate(spec=spec, image=img, mask=mask, dots=dots)


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
            cv2.circle(
                out,
                (int(round(d.x * scale)), int(round(d.y * scale))),
                max(1, int(round(d.r * scale))),
                255,
                -1,
            )
    return out


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
    stroke = _estimate_stroke_width_dots(plate.mask, avg_diam)
    fig_rast = rasterize_figure_dots(plate)
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

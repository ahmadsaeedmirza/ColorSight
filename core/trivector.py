"""Cambridge Colour Test (Trivector) — CIE u'v' staircases on confusion axes.

Pure NumPy/OpenCV; no UI. Plate-based screening remains in ``plates.py`` (legacy).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Literal, Sequence

import cv2
import numpy as np

from .cvd_types import CVDType
from .engine import apply_simulation
from .plates import pack_circles_dense
from .profile import CorrectionProfile

# ── CIE 1976 u'v' constants (D65) ──────────────────────────────────────────
# D65 XYZ (Y=1): X=0.95047, Z=1.08883 → u'≈0.1978, v'≈0.4683
BG_U = 0.1978
BG_V = 0.4683
BG_UV = np.array([BG_U, BG_V], dtype=np.float64)
BG_Y = 0.45  # mid luminance for stimulus (relative)

# Copunctal points in u'v' (Regan / Cambridge Colour Test literature)
COPUNCTAL = {
    "protan": np.array([0.6579, 0.5013], dtype=np.float64),
    "deutan": np.array([-1.2174, 0.7826], dtype=np.float64),
    "tritan": np.array([0.2573, 0.0], dtype=np.float64),
}

# Normal cutoffs (Δu'v')
NORMAL_CUTOFF = {"protan": 0.0100, "deutan": 0.0100, "tritan": 0.0150}

# Staircase modes
STAIRCASE_MODES = {
    "phone": {"reversals": 8, "mean_last": 4},
    "full": {"reversals": 11, "mean_last": 6},
}

START_D = 0.040  # starting Δu'v'
MIN_D = 0.001
MAX_D_SEARCH = 0.20
RATIO_MARGIN = 1.15  # protan/deutan elevation must beat the other by this factor

Orientation = Literal["up", "down", "left", "right"]
ORIENTATIONS: tuple[Orientation, ...] = ("up", "down", "left", "right")
AxisName = Literal["protan", "deutan", "tritan"]
AXES: tuple[AxisName, ...] = ("protan", "deutan", "tritan")


# ── Color science ──────────────────────────────────────────────────────────

def uv_to_xyz(u: float, v: float, Y: float) -> np.ndarray:
    """CIE 1976 u'v' + Y → XYZ."""
    if abs(v) < 1e-12:
        return np.array([0.0, Y, 0.0], dtype=np.float64)
    X = (9.0 * u * Y) / (4.0 * v)
    Z = ((12.0 - 3.0 * u - 20.0 * v) * Y) / (4.0 * v)
    return np.array([X, Y, Z], dtype=np.float64)


def xyz_to_uv(xyz: np.ndarray) -> np.ndarray:
    X, Y, Z = float(xyz[0]), float(xyz[1]), float(xyz[2])
    denom = X + 15.0 * Y + 3.0 * Z
    if denom <= 1e-12:
        return np.array([BG_U, BG_V], dtype=np.float64)
    return np.array([4.0 * X / denom, 9.0 * Y / denom], dtype=np.float64)


# sRGB (IEC 61966-2-1) D65
_M_XYZ_TO_LINEAR_SRGB = np.array(
    [
        [3.2406, -1.5372, -0.4986],
        [-0.9689, 1.8758, 0.0415],
        [0.0557, -0.2040, 1.0570],
    ],
    dtype=np.float64,
)
_M_LINEAR_SRGB_TO_XYZ = np.linalg.inv(_M_XYZ_TO_LINEAR_SRGB)


def _linear_to_srgb(c: np.ndarray) -> np.ndarray:
    c = np.asarray(c, dtype=np.float64)
    out = np.empty_like(c)
    mask = c <= 0.0031308
    out[mask] = 12.92 * c[mask]
    out[~mask] = 1.055 * np.power(np.clip(c[~mask], 0, None), 1.0 / 2.4) - 0.055
    return out


def _srgb_to_linear(c: np.ndarray) -> np.ndarray:
    c = np.asarray(c, dtype=np.float64)
    out = np.empty_like(c)
    mask = c <= 0.04045
    out[mask] = c[mask] / 12.92
    out[~mask] = np.power((c[~mask] + 0.055) / 1.055, 2.4)
    return out


def xyz_to_srgb(xyz: np.ndarray) -> np.ndarray:
    linear = _M_XYZ_TO_LINEAR_SRGB @ np.asarray(xyz, dtype=np.float64)
    return _linear_to_srgb(linear)


def srgb_to_xyz(rgb: np.ndarray) -> np.ndarray:
    linear = _srgb_to_linear(np.asarray(rgb, dtype=np.float64))
    return _M_LINEAR_SRGB_TO_XYZ @ linear


def srgb_uint8_to_uv(rgb: np.ndarray) -> np.ndarray:
    """Nx3 or HxWx3 uint8 → u'v' (…, 2)."""
    flat = rgb.reshape(-1, 3).astype(np.float64) / 255.0
    xyz = np.array([srgb_to_xyz(p) for p in flat])
    return np.array([xyz_to_uv(row) for row in xyz]).reshape(rgb.shape[:-1] + (2,))


def in_srgb_gamut(xyz: np.ndarray, eps: float = 1e-4) -> bool:
    rgb = xyz_to_srgb(xyz)
    return bool(np.all(rgb >= -eps) and np.all(rgb <= 1.0 + eps))


def axis_unit_vector(axis: AxisName) -> np.ndarray:
    d = COPUNCTAL[axis] - BG_UV
    n = np.linalg.norm(d)
    if n < 1e-12:
        raise ValueError(f"degenerate axis {axis}")
    return d / n


def max_in_gamut_d(axis: AxisName, Y: float = BG_Y) -> float:
    """Largest Δu'v' along axis that stays in sRGB gamut at luminance Y."""
    direction = axis_unit_vector(axis)
    lo, hi = 0.0, MAX_D_SEARCH
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        uv = BG_UV + mid * direction
        xyz = uv_to_xyz(float(uv[0]), float(uv[1]), Y)
        if in_srgb_gamut(xyz):
            lo = mid
        else:
            hi = mid
    return float(lo)


def chromaticity_at(axis: AxisName, d: float, Y: float = BG_Y) -> tuple[np.ndarray, np.ndarray]:
    """Return (xyz_target, rgb_float01) for distance d along axis (clamped to gamut)."""
    d_max = max_in_gamut_d(axis, Y)
    d_use = float(np.clip(d, 0.0, d_max))
    uv = BG_UV + d_use * axis_unit_vector(axis)
    xyz = uv_to_xyz(float(uv[0]), float(uv[1]), Y)
    rgb = np.clip(xyz_to_srgb(xyz), 0.0, 1.0)
    return xyz, rgb


def background_rgb(Y: float = BG_Y) -> np.ndarray:
    xyz = uv_to_xyz(BG_U, BG_V, Y)
    return np.clip(xyz_to_srgb(xyz), 0.0, 1.0)


# ── Landolt C stimulus ─────────────────────────────────────────────────────

def landolt_c_mask(
    size: int,
    orientation: Orientation,
    *,
    outer_frac: float = 0.72,
    thickness_frac: float = 0.20,
    gap_frac: float = 0.20,
) -> np.ndarray:
    """Binary mask (255 = C ring) with gap = gap_frac of outer diameter."""
    mask = np.zeros((size, size), dtype=np.uint8)
    cx = cy = size / 2.0
    outer_r = size * outer_frac / 2.0
    thickness = outer_r * 2.0 * thickness_frac  # stroke ≈ gap width when gap_frac=thickness
    # CCT: gap ≈ 1/5 of diameter → thickness of ring ≈ gap
    gap_w = (2.0 * outer_r) * gap_frac
    thickness = gap_w
    inner_r = max(1.0, outer_r - thickness)
    cv2.circle(mask, (int(cx), int(cy)), int(round(outer_r)), 255, -1)
    cv2.circle(mask, (int(cx), int(cy)), int(round(inner_r)), 0, -1)
    # Cut gap
    half = gap_w / 2.0
    if orientation == "up":
        x0, x1 = int(cx - half), int(cx + half)
        y0, y1 = 0, int(cy)
        mask[y0:y1, x0:x1] = 0
    elif orientation == "down":
        x0, x1 = int(cx - half), int(cx + half)
        y0, y1 = int(cy), size
        mask[y0:y1, x0:x1] = 0
    elif orientation == "left":
        x0, x1 = 0, int(cx)
        y0, y1 = int(cy - half), int(cy + half)
        mask[y0:y1, x0:x1] = 0
    else:  # right
        x0, x1 = int(cx), size
        y0, y1 = int(cy - half), int(cy + half)
        mask[y0:y1, x0:x1] = 0
    return mask


def _y_jitter(rng: np.random.Generator, n: int, y0: float = BG_Y) -> np.ndarray:
    """Shared luminance distribution for target and background dots."""
    # Relative jitter ±18% (log-ish), same for both pools
    return y0 * rng.uniform(0.82, 1.18, size=n)


@dataclass
class Stimulus:
    image: np.ndarray  # HxWx3 uint8
    axis: AxisName
    d: float
    orientation: Orientation
    target_ys: np.ndarray
    background_ys: np.ndarray
    d_clamped: float


def render_landolt_stimulus(
    axis: AxisName,
    d: float,
    orientation: Orientation,
    *,
    size: int = 256,
    seed: int | None = None,
) -> Stimulus:
    """Dot-field Landolt C: target chromaticity at Δu'v'=d along axis."""
    rng = np.random.default_rng(seed)
    d_max = max_in_gamut_d(axis, BG_Y)
    d_use = float(np.clip(d, 0.0, d_max))
    mask = landolt_c_mask(size, orientation)
    circles = pack_circles_dense(
        size,
        rng,
        r_min=size * 0.012,
        r_max=size * 0.022,
    )
    # Classify dots
    fig_idx: list[int] = []
    gnd_idx: list[int] = []
    for i, (x, y, _r) in enumerate(circles):
        ix, iy = int(round(x)), int(round(y))
        if 0 <= iy < size and 0 <= ix < size and mask[iy, ix] > 0:
            fig_idx.append(i)
        else:
            # keep only dots inside the plate disk (packer already does)
            gnd_idx.append(i)

    n_fig = max(1, len(fig_idx))
    n_gnd = max(1, len(gnd_idx))
    # Draw from SAME luminance distribution
    all_y = _y_jitter(rng, n_fig + n_gnd, BG_Y)
    y_fig = all_y[:n_fig]
    y_gnd = all_y[n_fig : n_fig + n_gnd]

    img = np.full((size, size, 3), 245, dtype=np.uint8)
    # Field disk background (paper)
    yy, xx = np.ogrid[:size, :size]
    disk = (xx - size / 2) ** 2 + (yy - size / 2) ** 2 <= (size * 0.48) ** 2
    paper = (np.clip(background_rgb(BG_Y * 0.95), 0, 1) * 255).astype(np.uint8)
    img[disk] = paper

    def paint(indices: list[int], ys: np.ndarray, is_target: bool):
        for k, ci in enumerate(indices):
            x, y, r = circles[ci]
            Y = float(ys[k % len(ys)])
            if is_target:
                _, rgb = chromaticity_at(axis, d_use, Y)
            else:
                rgb = background_rgb(Y)
            color = tuple(int(round(c * 255)) for c in rgb)
            rad = max(2, int(np.ceil(r - 1e-6)))
            cv2.ellipse(
                img,
                (int(round(x)), int(round(y))),
                (rad, rad),
                0,
                0,
                360,
                color,
                -1,
                lineType=cv2.LINE_8,
            )

    paint(gnd_idx, y_gnd, False)
    paint(fig_idx, y_fig, True)
    return Stimulus(
        image=img,
        axis=axis,
        d=d,
        orientation=orientation,
        target_ys=y_fig.copy(),
        background_ys=y_gnd.copy(),
        d_clamped=d_use,
    )


# ── Staircase ──────────────────────────────────────────────────────────────

@dataclass
class AxisStaircase:
    axis: AxisName
    mode: str = "phone"
    d: float = START_D
    step: float = START_D / 2.0
    reversals: list[float] = field(default_factory=list)
    last_correct: bool | None = None
    trial_count: int = 0
    done: bool = False

    def __post_init__(self):
        cfg = STAIRCASE_MODES[self.mode]
        self._need = cfg["reversals"]
        self._mean_last = cfg["mean_last"]
        self.d = float(np.clip(self.d, MIN_D, max_in_gamut_d(self.axis)))
        self.step = max(MIN_D / 2, self.step)

    def record(self, correct: bool) -> None:
        if self.done:
            return
        self.trial_count += 1
        if self.last_correct is not None and correct != self.last_correct:
            self.reversals.append(self.d)
            if len(self.reversals) >= self._need:
                self.done = True
                return
        self.last_correct = correct
        if correct:
            self.step = max(MIN_D / 2, self.step * 0.5)
            self.d = max(MIN_D, self.d - self.step)
        else:
            self.step = min(0.08, self.step * 2.0)
            self.d = min(max_in_gamut_d(self.axis), self.d + self.step)

    @property
    def threshold(self) -> float:
        if not self.reversals:
            return float(self.d)
        use = self.reversals[-self._mean_last :]
        return float(np.mean(use))


@dataclass
class Trial:
    axis: AxisName
    d: float
    orientation: Orientation
    stimulus: Stimulus


class TrivectorSession:
    """Interleaved 4-AFC staircases on protan / deutan / tritan axes."""

    def __init__(self, mode: str = "phone", seed: int | None = 42):
        if mode not in STAIRCASE_MODES:
            raise ValueError(f"mode must be one of {list(STAIRCASE_MODES)}")
        self.mode = mode
        self.rng = np.random.default_rng(seed)
        self.stairs = {a: AxisStaircase(axis=a, mode=mode) for a in AXES}
        self.history: list[dict] = []
        self._trial_i = 0

    @property
    def finished(self) -> bool:
        return all(s.done for s in self.stairs.values())

    @property
    def progress(self) -> float:
        need = STAIRCASE_MODES[self.mode]["reversals"] * 3
        got = sum(len(s.reversals) for s in self.stairs.values())
        return float(np.clip(got / max(1, need), 0.0, 1.0))

    def next_trial(self, size: int = 256) -> Trial | None:
        if self.finished:
            return None
        open_axes = [a for a, s in self.stairs.items() if not s.done]
        axis = self.rng.choice(open_axes)
        orient = self.rng.choice(ORIENTATIONS)
        d = self.stairs[axis].d
        stim = render_landolt_stimulus(
            axis, d, orient, size=size, seed=int(self.rng.integers(0, 2**31 - 1))
        )
        self._trial_i += 1
        return Trial(axis=axis, d=stim.d_clamped, orientation=orient, stimulus=stim)

    def answer(self, trial: Trial, response: Orientation | None) -> bool:
        """Record response; None = can't see (counts as error). Returns whether correct."""
        correct = response is not None and response == trial.orientation
        self.stairs[trial.axis].record(correct)
        self.history.append(
            {
                "axis": trial.axis,
                "d": trial.d,
                "orientation": trial.orientation,
                "response": response,
                "correct": correct,
            }
        )
        return correct

    def thresholds(self) -> dict[str, float]:
        return {a: self.stairs[a].threshold for a in AXES}


# ── Classification + severity calibration ─────────────────────────────────

def severity_label(severity: float) -> str:
    s = float(severity)
    if s < 0.15:
        return "none"
    if s < 0.40:
        return "mild"
    if s < 0.70:
        return "moderate"
    return "strong"


# Monotone calibration knots: measured Δu'v' threshold → severity
# Built / refined by ``build_calibration`` from the model observer.
_DEFAULT_CALIBRATION: dict[str, list[tuple[float, float]]] = {
    # (threshold, severity) — will be replaced after calibration build
    "protan": [(0.008, 0.0), (0.012, 0.25), (0.025, 0.5), (0.045, 0.75), (0.080, 1.0)],
    "deutan": [(0.008, 0.0), (0.012, 0.25), (0.025, 0.5), (0.045, 0.75), (0.080, 1.0)],
    "tritan": [(0.012, 0.0), (0.018, 0.25), (0.035, 0.5), (0.055, 0.75), (0.090, 1.0)],
}

_CALIBRATION = {k: list(v) for k, v in _DEFAULT_CALIBRATION.items()}


def set_calibration(curves: dict[str, list[tuple[float, float]]]) -> None:
    global _CALIBRATION
    _CALIBRATION = {k: list(v) for k, v in curves.items()}


def get_calibration() -> dict[str, list[tuple[float, float]]]:
    return {k: list(v) for k, v in _CALIBRATION.items()}


_CALIBRATION_BUILT = False


def ensure_calibration() -> None:
    global _CALIBRATION_BUILT
    if not _CALIBRATION_BUILT:
        build_calibration()
        _CALIBRATION_BUILT = True


def threshold_to_severity(axis: AxisName, threshold: float) -> float:
    ensure_calibration()
    knots = _CALIBRATION[axis]
    xs = np.array([k[0] for k in knots], dtype=np.float64)
    ys = np.array([k[1] for k in knots], dtype=np.float64)
    t = float(threshold)
    if t <= xs[0]:
        return float(ys[0])
    if t >= xs[-1]:
        return float(ys[-1])
    return float(np.interp(t, xs, ys))


@dataclass
class TrivectorResult:
    classification: str  # normal | protanopia | deuteranopia | tritanopia | inconclusive
    severity: float
    thresholds: dict[str, float]
    severity_axes: dict[str, float]
    hue_error: float = 0.0
    details: dict = field(default_factory=dict)

    @property
    def is_normal(self) -> bool:
        return self.classification == "normal"

    @property
    def is_inconclusive(self) -> bool:
        return self.classification == "inconclusive"

    @property
    def label(self) -> str:
        labels = {
            "normal": "Typical color vision",
            "inconclusive": "Inconclusive result",
            CVDType.PROTANOPIA.value: "Protan (red-weak) pattern",
            CVDType.DEUTERANOPIA.value: "Deutan (green-weak) pattern",
            CVDType.TRITANOPIA.value: "Tritan (blue-yellow) pattern",
        }
        return labels.get(self.classification, self.classification)

    @property
    def severity_label(self) -> str:
        if self.is_normal:
            return "none"
        if self.is_inconclusive:
            return severity_label(self.severity)
        return severity_label(self.severity)

    def to_profile(self) -> CorrectionProfile:
        if self.is_inconclusive:
            return CorrectionProfile.create(CVDType.DEUTERANOPIA, max(0.2, self.severity))
        if self.is_normal:
            return CorrectionProfile.create(CVDType.DEUTERANOPIA, 0.0)
        return CorrectionProfile.create(self.classification, self.severity)


def _is_elevated(axis: AxisName, thr: float) -> bool:
    """Elevated vs published cutoff, or clearly above calibrated normal baseline."""
    cutoff = NORMAL_CUTOFF[axis]
    if thr > cutoff:
        return True
    baseline = get_calibration()[axis][0][0]  # sev=0 knot
    # Machado mid-severity rises gradually — catch clear lifts above normal
    return thr > baseline * 1.10


def classify_thresholds(
    thresholds: dict[str, float],
    *,
    hue_error: float = 0.0,
    hue_weight: float = 0.20,
) -> TrivectorResult:
    """Classify from protan/deutan/tritan Δu'v' thresholds; blend hue lightly into severity."""
    ensure_calibration()
    tp = float(thresholds["protan"])
    td = float(thresholds["deutan"])
    tt = float(thresholds["tritan"])
    elev = {
        "protan": _is_elevated("protan", tp),
        "deutan": _is_elevated("deutan", td),
        "tritan": _is_elevated("tritan", tt),
    }
    sev_axes = {
        "protan": threshold_to_severity("protan", tp),
        "deutan": threshold_to_severity("deutan", td),
        "tritan": threshold_to_severity("tritan", tt),
    }
    # Relative elevation vs cutoff (for RG type pick)
    rel = {
        "protan": tp / NORMAL_CUTOFF["protan"],
        "deutan": td / NORMAL_CUTOFF["deutan"],
        "tritan": tt / NORMAL_CUTOFF["tritan"],
    }

    classification = "normal"
    base_sev = 0.0
    rg = elev["protan"] or elev["deutan"]
    if not any(elev.values()):
        classification = "normal"
        base_sev = float(np.clip(0.4 * max(sev_axes.values()), 0.0, 0.12))
    elif elev["tritan"] and not rg:
        classification = CVDType.TRITANOPIA.value
        base_sev = sev_axes["tritan"]
    elif elev["tritan"] and rg and rel["tritan"] >= max(rel["protan"], rel["deutan"]) * RATIO_MARGIN:
        # Tritan dominates even if RG also mildly elevated
        classification = CVDType.TRITANOPIA.value
        base_sev = sev_axes["tritan"]
    elif rg:
        ep, ed = rel["protan"], rel["deutan"]
        if ep >= ed * 1.04:
            classification = CVDType.PROTANOPIA.value
            base_sev = sev_axes["protan"]
        elif ed >= ep * 1.04:
            classification = CVDType.DEUTERANOPIA.value
            base_sev = sev_axes["deutan"]
        elif tp >= td:
            classification = CVDType.PROTANOPIA.value
            base_sev = sev_axes["protan"]
        else:
            classification = CVDType.DEUTERANOPIA.value
            base_sev = sev_axes["deutan"]
    else:
        classification = "inconclusive"
        base_sev = float(np.mean(list(sev_axes.values())))

    # Hue nudges severity upward when arrangement is poor; does not dilute trivector
    hue_sev = float(np.clip(hue_error, 0.0, 1.0))
    severity = float(np.clip(base_sev + hue_weight * hue_sev * 0.35, 0.0, 1.0))
    if classification == "normal":
        severity = float(np.clip(severity, 0.0, 0.15))

    return TrivectorResult(
        classification=classification,
        severity=severity,
        thresholds={"protan": tp, "deutan": td, "tritan": tt},
        severity_axes=sev_axes,
        hue_error=float(hue_error),
        details={
            "elevated": elev,
            "relative": rel,
            "cutoffs": dict(NORMAL_CUTOFF),
            "hue_weight": hue_weight,
            "base_severity": base_sev,
        },
    )


def score_trivector(
    session: TrivectorSession,
    hue_order: Sequence[int] | None = None,
) -> TrivectorResult:
    from .scoring import hue_arrangement_error

    hue_err = 0.0
    if hue_order is not None:
        hue_err = hue_arrangement_error(hue_order)
    return classify_thresholds(session.thresholds(), hue_error=hue_err)


# ── Model observer + calibration ───────────────────────────────────────────

# Just-noticeable Δu'v' for a normal observer after simulation (tuned in build_calibration)
_MODEL_JND = 0.0065
_MODEL_NOISE = 0.04  # light response noise near threshold


def _patch_delta_uv(
    axis: AxisName,
    d: float,
    cvd_type: str | CVDType,
    severity: float,
    *,
    Y: float = BG_Y,
) -> float:
    """Fast Δu'v' between mean target/background after Machado (2-pixel patch)."""
    _, rgb_t = chromaticity_at(axis, d, Y)
    rgb_g = background_rgb(Y)
    patch = np.stack([rgb_t, rgb_g]).reshape(2, 1, 3)
    patch_u8 = np.clip(np.round(patch * 255), 0, 255).astype(np.uint8)
    sim = apply_simulation(patch_u8, cvd_type, float(severity))
    uv = srgb_uint8_to_uv(sim.reshape(2, 3))
    return float(np.linalg.norm(uv[0] - uv[1]))


def simulated_delta_uv(
    axis: AxisName,
    d: float,
    cvd_type: str | CVDType,
    severity: float,
    *,
    size: int = 128,
    seed: int = 0,
) -> float:
    """Δu'v' after simulation (patch-based; size/seed kept for API compatibility)."""
    del size, seed
    return _patch_delta_uv(axis, d, cvd_type, severity)


def _disk_mask(size: int) -> np.ndarray:
    yy, xx = np.ogrid[:size, :size]
    return (xx - size / 2) ** 2 + (yy - size / 2) ** 2 <= (size * 0.48) ** 2


def model_observer_response(
    trial: Trial,
    cvd_type: str | CVDType,
    severity: float,
    *,
    jnd: float = _MODEL_JND,
    noise: float = _MODEL_NOISE,
    rng: np.random.Generator | None = None,
) -> Orientation | None:
    """Answer correctly iff simulated chromatic step exceeds JND (with noise)."""
    rng = rng or np.random.default_rng()
    delta = _patch_delta_uv(trial.axis, trial.d, cvd_type, severity)
    # Soft threshold with noise
    p_correct = 1.0 / (1.0 + np.exp(-(delta - jnd) / max(1e-4, jnd * 0.35)))
    p_correct = float(np.clip(p_correct * (1.0 - noise) + 0.25 * noise, 0.0, 1.0))
    if rng.random() < p_correct:
        return trial.orientation
    if rng.random() < 0.35:
        return None
    wrong = [o for o in ORIENTATIONS if o != trial.orientation]
    return rng.choice(wrong)


def estimate_threshold_binary(
    axis: AxisName,
    cvd_type: str | CVDType,
    severity: float,
    *,
    jnd: float = _MODEL_JND,
    seed: int = 0,
    size: int = 96,
) -> float:
    """Binary-search the d where simulated Δu'v' crosses JND (fast calibration)."""
    del size, seed
    lo, hi = MIN_D, max_in_gamut_d(axis)
    for _ in range(16):
        mid = 0.5 * (lo + hi)
        if _patch_delta_uv(axis, mid, cvd_type, severity) >= jnd:
            hi = mid
        else:
            lo = mid
    return float(0.5 * (lo + hi))


def build_calibration(
    severities: Sequence[float] | None = None,
    *,
    jnd: float | None = None,
) -> dict[str, list[tuple[float, float]]]:
    """Measure threshold(severity) per axis/type and install monotone curves."""
    global _MODEL_JND, _CALIBRATION_BUILT
    severities = list(severities) if severities is not None else [0.0, 0.3, 0.5, 0.7, 1.0]
    jnd_use = _MODEL_JND if jnd is None else float(jnd)
    # Tune JND so severity 0 stays under normal cutoffs
    if jnd is None:
        for cand in (0.008, 0.007, 0.0065, 0.006, 0.0055):
            ok = True
            for axis, cvd in (
                ("protan", CVDType.PROTANOPIA),
                ("deutan", CVDType.DEUTERANOPIA),
                ("tritan", CVDType.TRITANOPIA),
            ):
                t0 = estimate_threshold_binary(axis, cvd, 0.0, jnd=cand, seed=1)
                if t0 > NORMAL_CUTOFF[axis] * 0.95:
                    ok = False
                    break
            if ok:
                jnd_use = cand
                break

    curves: dict[str, list[tuple[float, float]]] = {}
    for axis, cvd in (
        ("protan", CVDType.PROTANOPIA),
        ("deutan", CVDType.DEUTERANOPIA),
        ("tritan", CVDType.TRITANOPIA),
    ):
        knots: list[tuple[float, float]] = []
        prev_t = 0.0
        for sev in severities:
            t = estimate_threshold_binary(axis, cvd, sev, jnd=jnd_use, seed=3 + int(sev * 100))
            t = max(t, prev_t + 1e-4)  # enforce monotone
            prev_t = t
            knots.append((t, float(sev)))
        curves[axis] = knots
    set_calibration(curves)
    _MODEL_JND = jnd_use
    _CALIBRATION_BUILT = True
    return curves


def run_model_session(
    cvd_type: str | CVDType,
    severity: float,
    *,
    mode: str = "phone",
    seed: int = 0,
    size: int = 128,
    render: bool = False,
) -> TrivectorResult:
    """Interleaved staircase answered by the Machado model observer.

    ``render=False`` (default for tests) skips Landolt image generation and
    uses patch-based Δu'v' only — much faster, same decision rule.
    """
    session = TrivectorSession(mode=mode, seed=seed)
    rng = np.random.default_rng(seed + 99)
    safety = 0
    while not session.finished and safety < 200:
        safety += 1
        open_axes = [a for a, s in session.stairs.items() if not s.done]
        if not open_axes:
            break
        axis = rng.choice(open_axes)
        orient = rng.choice(list(ORIENTATIONS))
        d = session.stairs[axis].d
        if render:
            stim = render_landolt_stimulus(
                axis, d, orient, size=size, seed=int(rng.integers(0, 2**31 - 1))
            )
            trial = Trial(axis=axis, d=stim.d_clamped, orientation=orient, stimulus=stim)
        else:
            d_use = float(np.clip(d, 0.0, max_in_gamut_d(axis)))
            dummy = Stimulus(
                image=np.zeros((8, 8, 3), dtype=np.uint8),
                axis=axis,
                d=d_use,
                orientation=orient,
                target_ys=np.array([BG_Y]),
                background_ys=np.array([BG_Y]),
                d_clamped=d_use,
            )
            trial = Trial(axis=axis, d=d_use, orientation=orient, stimulus=dummy)
        resp = model_observer_response(
            trial, cvd_type, severity, jnd=_MODEL_JND, rng=rng
        )
        session.answer(trial, resp)
    return score_trivector(session)


def run_scripted_staircase(
    true_threshold: float,
    axis: AxisName = "protan",
    *,
    mode: str = "phone",
    seed: int = 0,
) -> float:
    """1-axis staircase with an ideal observer that flips at ``true_threshold``."""
    stair = AxisStaircase(axis=axis, mode=mode)
    rng = np.random.default_rng(seed)
    safety = 0
    while not stair.done and safety < 80:
        safety += 1
        # Correct if current d >= true threshold (with tiny noise)
        correct = stair.d >= true_threshold
        if rng.random() < 0.05:
            correct = not correct
        stair.record(correct)
    return stair.threshold

"""Screening scoring: classify normal / protan / deutan / tritan + severity."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from .cvd_types import CVDType
from .plates import PlateAxis, PlateSpec
from .profile import CorrectionProfile


@dataclass
class PlateAnswer:
    plate_id: str
    expected: int
    response: int | None  # None = "can't see anything"
    axis: PlateAxis
    targets: tuple[str, ...] = ()

    @property
    def correct(self) -> bool:
        return self.response is not None and int(self.response) == int(self.expected)


@dataclass
class TestResult:
    """Outcome of the ColorSight screening battery + hue step."""

    classification: str  # "normal" | CVDType values
    severity: float  # 0–1
    plate_correct: int
    plate_total: int
    hue_error: float  # 0 = perfect order, 1 = worst
    details: dict = field(default_factory=dict)

    @property
    def is_normal(self) -> bool:
        return self.classification == "normal"

    @property
    def label(self) -> str:
        labels = {
            "normal": "Typical color vision",
            CVDType.PROTANOPIA.value: "Protan (red-weak) pattern",
            CVDType.DEUTERANOPIA.value: "Deutan (green-weak) pattern",
            CVDType.TRITANOPIA.value: "Tritan (blue-yellow) pattern",
        }
        return labels.get(self.classification, self.classification)

    def to_profile(self) -> CorrectionProfile | None:
        """Build a CorrectionProfile, or None when classification is normal (severity 0 identity)."""
        if self.is_normal:
            # Identity correction still useful as a saved baseline
            return CorrectionProfile.create(CVDType.DEUTERANOPIA, 0.0)
        return CorrectionProfile.create(self.classification, self.severity)


def hue_arrangement_error(order: Sequence[int], n: int | None = None) -> float:
    """Normalize permutation error to [0, 1].

    ``order`` is the user's left-to-right tile indices (correct = 0..n-1).
    Uses mean absolute deviation from the identity permutation, scaled by
    the maximum possible MAD for length n.
    """
    order = list(order)
    n = n or len(order)
    if n <= 1:
        return 0.0
    if sorted(order) != list(range(n)):
        raise ValueError("order must be a permutation of 0..n-1")
    mad = sum(abs(order[i] - i) for i in range(n)) / n
    # Max MAD for reversing 0..n-1 is ~ n/2 for even-ish layouts
    max_mad = sum(abs((n - 1 - i) - i) for i in range(n)) / n
    if max_mad <= 0:
        return 0.0
    return float(np.clip(mad / max_mad, 0.0, 1.0))


def score_screening(
    answers: Sequence[PlateAnswer],
    hue_order: Sequence[int] | None = None,
) -> TestResult:
    """Classify screening answers and estimate severity.

    Heuristic (screening, not diagnosis):
    - Few misses overall → normal, low severity
    - Misses concentrated on blue-yellow plates → tritan
    - Misses on protan-weighted plates > deutan → protan
    - Misses on deutan-weighted / red-green → deutan (most common RG)
    - Severity blends plate miss rate with hue-arrangement error
    """
    answers = list(answers)
    total = len(answers)
    correct_n = sum(1 for a in answers if a.correct)
    miss_rate = 1.0 - (correct_n / total if total else 1.0)

    def miss_ratio(pred) -> float:
        subset = [a for a in answers if pred(a)]
        if not subset:
            return 0.0
        return sum(1 for a in subset if not a.correct) / len(subset)

    control_miss = miss_ratio(lambda a: a.axis == PlateAxis.CONTROL)
    rg_miss = miss_ratio(
        lambda a: a.axis in (PlateAxis.RED_GREEN, PlateAxis.PROTAN, PlateAxis.DEUTAN)
    )
    protan_miss = miss_ratio(lambda a: a.axis == PlateAxis.PROTAN)
    deutan_miss = miss_ratio(lambda a: a.axis == PlateAxis.DEUTAN)
    by_miss = miss_ratio(lambda a: a.axis == PlateAxis.BLUE_YELLOW)

    hue_err = 0.0
    if hue_order is not None:
        hue_err = hue_arrangement_error(hue_order)

    # Classification
    classification = "normal"
    if control_miss >= 0.5 and miss_rate >= 0.5:
        # Many control misses → treat as severe unspecified RG (deutan default) or display issue
        classification = CVDType.DEUTERANOPIA.value
        severity = float(np.clip(0.55 + 0.4 * miss_rate, 0.0, 1.0))
    elif by_miss >= 0.5 and by_miss >= rg_miss + 0.15:
        classification = CVDType.TRITANOPIA.value
        severity = float(np.clip(0.35 * by_miss + 0.55 * hue_err + 0.15 * miss_rate, 0.15, 1.0))
    elif rg_miss >= 0.35 or protan_miss >= 0.5 or deutan_miss >= 0.5:
        if protan_miss > deutan_miss + 0.2:
            classification = CVDType.PROTANOPIA.value
            axis_miss = max(protan_miss, rg_miss)
        elif deutan_miss > protan_miss + 0.1:
            classification = CVDType.DEUTERANOPIA.value
            axis_miss = max(deutan_miss, rg_miss)
        else:
            # Default RG ambiguity → deutan (more prevalent)
            classification = CVDType.DEUTERANOPIA.value
            axis_miss = rg_miss
        severity = float(np.clip(0.4 * axis_miss + 0.45 * hue_err + 0.2 * miss_rate, 0.15, 1.0))
    elif miss_rate <= 0.2 and hue_err <= 0.25:
        classification = "normal"
        severity = float(np.clip(0.35 * miss_rate + 0.4 * hue_err, 0.0, 0.25))
    else:
        # Mild / ambiguous — lean deutan if any RG signal else normal-low
        if rg_miss >= by_miss:
            classification = CVDType.DEUTERANOPIA.value
            severity = float(np.clip(0.25 + 0.4 * hue_err + 0.3 * rg_miss, 0.1, 0.7))
        else:
            classification = CVDType.TRITANOPIA.value
            severity = float(np.clip(0.25 + 0.4 * hue_err + 0.3 * by_miss, 0.1, 0.7))

    if classification == "normal":
        severity = float(np.clip(severity, 0.0, 0.2))

    details = {
        "control_miss": control_miss,
        "rg_miss": rg_miss,
        "protan_miss": protan_miss,
        "deutan_miss": deutan_miss,
        "by_miss": by_miss,
        "miss_rate": miss_rate,
        "hue_error": hue_err,
    }
    return TestResult(
        classification=classification,
        severity=severity,
        plate_correct=correct_n,
        plate_total=total,
        hue_error=hue_err,
        details=details,
    )


def make_answers(
    specs: Sequence[PlateSpec],
    responses: Sequence[int | None],
) -> list[PlateAnswer]:
    if len(specs) != len(responses):
        raise ValueError("specs and responses length mismatch")
    return [
        PlateAnswer(
            plate_id=s.plate_id,
            expected=s.digit,
            response=responses[i],
            axis=s.axis,
            targets=s.targets,
        )
        for i, s in enumerate(specs)
    ]

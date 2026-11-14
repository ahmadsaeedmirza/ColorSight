"""Screening scoring.

Legacy plate-based expected-answer tables remain for ``plates.py`` tests.
The live Vision Test uses Cambridge Colour Test (Trivector) in ``trivector.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from .cvd_types import CVDType
from .plates import PlateAxis, PlateSpec
from .profile import CorrectionProfile

# Classification thresholds (documented in architecture.md)
MATCH_RATE_CLEAR = 0.75  # viewer type must match at least this fraction of plates
LEAD_MARGIN = 0.12  # best type must beat runner-up by this margin
NORMAL_MIN_MATCH = 0.85
CONTROL_FAIL_INCONCLUSIVE = 0.5  # failing control → inconclusive


@dataclass
class PlateAnswer:
    plate_id: str
    response: int | None  # None = "can't see anything"
    spec: PlateSpec

    def matches(self, viewer: str) -> bool:
        expected = self.spec.expected_for(viewer)
        if expected is None:
            return self.response is None
        return self.response is not None and int(self.response) == int(expected)


@dataclass
class TestResult:
    """Outcome of the ColorSight screening battery + hue step."""

    classification: str  # normal | protanopia | deuteranopia | tritanopia | inconclusive
    severity: float
    plate_correct: int  # matches vs expected_normal
    plate_total: int
    hue_error: float
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

    def to_profile(self):
        if self.is_inconclusive:
            # Mild deutan baseline so Save still works; UI should warn
            return CorrectionProfile.create(CVDType.DEUTERANOPIA, max(0.2, self.severity))
        if self.is_normal:
            return CorrectionProfile.create(CVDType.DEUTERANOPIA, 0.0)
        return CorrectionProfile.create(self.classification, self.severity)


def hue_arrangement_error(order: Sequence[int], n: int | None = None) -> float:
    order = list(order)
    n = n or len(order)
    if n <= 1:
        return 0.0
    if sorted(order) != list(range(n)):
        raise ValueError("order must be a permutation of 0..n-1")
    mad = sum(abs(order[i] - i) for i in range(n)) / n
    max_mad = sum(abs((n - 1 - i) - i) for i in range(n)) / n
    if max_mad <= 0:
        return 0.0
    return float(np.clip(mad / max_mad, 0.0, 1.0))


def _match_rate(answers: Sequence[PlateAnswer], viewer: str) -> float:
    if not answers:
        return 0.0
    return sum(1 for a in answers if a.matches(viewer)) / len(answers)


def score_screening(
    answers: Sequence[PlateAnswer],
    hue_order: Sequence[int] | None = None,
) -> TestResult:
    """Classify using per-plate expected answers for normal/protan/deutan/tritan.

    Thresholds:
    - Pick the viewer type with the highest plate match rate.
    - Require match rate >= MATCH_RATE_CLEAR and lead >= LEAD_MARGIN over #2.
    - If normal match >= NORMAL_MIN_MATCH and leads → normal.
    - Failing the control plate(s) often → inconclusive.
    - Otherwise → inconclusive.
    Severity blends miss-vs-normal rate with hue-arrangement error.
    """
    answers = list(answers)
    total = len(answers)
    normal_match = _match_rate(answers, "normal")
    rates = {
        "normal": normal_match,
        CVDType.PROTANOPIA.value: _match_rate(answers, "protanopia"),
        CVDType.DEUTERANOPIA.value: _match_rate(answers, "deuteranopia"),
        CVDType.TRITANOPIA.value: _match_rate(answers, "tritanopia"),
    }

    hue_err = 0.0
    if hue_order is not None:
        hue_err = hue_arrangement_error(hue_order)

    control = [a for a in answers if a.spec.axis == PlateAxis.CONTROL]
    control_fail = (
        sum(1 for a in control if not a.matches("normal")) / len(control) if control else 0.0
    )

    ranked = sorted(rates.items(), key=lambda kv: kv[1], reverse=True)
    best_type, best_rate = ranked[0]
    second_rate = ranked[1][1] if len(ranked) > 1 else 0.0
    lead = best_rate - second_rate

    plate_correct = sum(1 for a in answers if a.matches("normal"))
    miss_vs_normal = 1.0 - normal_match

    classification = "inconclusive"
    if control_fail >= CONTROL_FAIL_INCONCLUSIVE and normal_match < 0.5:
        classification = "inconclusive"
        severity = float(np.clip(0.3 + 0.4 * hue_err, 0.0, 0.8))
    elif best_type == "normal" and best_rate >= NORMAL_MIN_MATCH and lead >= LEAD_MARGIN * 0.5:
        classification = "normal"
        severity = float(np.clip(0.35 * miss_vs_normal + 0.4 * hue_err, 0.0, 0.2))
    elif best_type != "normal" and best_rate >= MATCH_RATE_CLEAR and lead >= LEAD_MARGIN:
        classification = best_type
        severity = float(np.clip(0.35 * miss_vs_normal + 0.45 * hue_err + 0.15, 0.15, 1.0))
    elif best_type != "normal" and best_rate >= 0.65 and lead >= 0.08:
        classification = best_type
        severity = float(np.clip(0.3 * miss_vs_normal + 0.5 * hue_err + 0.1, 0.1, 0.85))
    else:
        classification = "inconclusive"
        severity = float(np.clip(0.25 * miss_vs_normal + 0.4 * hue_err, 0.0, 0.7))

    details = {
        "match_rates": rates,
        "best_type": best_type,
        "best_rate": best_rate,
        "lead": lead,
        "control_fail": control_fail,
        "hue_error": hue_err,
        "thresholds": {
            "MATCH_RATE_CLEAR": MATCH_RATE_CLEAR,
            "LEAD_MARGIN": LEAD_MARGIN,
            "NORMAL_MIN_MATCH": NORMAL_MIN_MATCH,
        },
    }
    return TestResult(
        classification=classification,
        severity=severity,
        plate_correct=plate_correct,
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
        PlateAnswer(plate_id=s.plate_id, response=responses[i], spec=s)
        for i, s in enumerate(specs)
    ]


def simulate_respondent(viewer: str, specs: Sequence[PlateSpec] | None = None) -> list[PlateAnswer]:
    """Build answers a given viewer type would give according to plate metadata (legacy)."""
    from .plates import DEFAULT_BATTERY

    specs = tuple(specs) if specs is not None else DEFAULT_BATTERY
    return [
        PlateAnswer(plate_id=s.plate_id, response=s.expected_for(viewer), spec=s)
        for s in specs
    ]


# Re-export trivector scoring helpers used by the live test flow
def score_trivector_session(session, hue_order: Sequence[int] | None = None):
    from .trivector import score_trivector

    return score_trivector(session, hue_order=hue_order)

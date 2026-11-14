"""Correction profile persistence (JSON)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .cvd_types import CVDType
from .engine import build_correction_matrix


@dataclass
class CorrectionProfile:
    """User correction parameters derived from a vision test (or set manually).

    Optional metadata (``measured_at``, ``label``, ``thresholds``, ``test_severity``)
    is stored for the Profile UI only and does not affect color math.
    """

    type: CVDType
    severity: float
    matrix: np.ndarray = field(repr=False)
    measured_at: str | None = None
    label: str | None = None
    thresholds: dict[str, float] | None = None
    test_severity: float | None = None

    def __post_init__(self) -> None:
        self.type = CVDType.parse(self.type)
        self.severity = float(np.clip(self.severity, 0.0, 1.0))
        self.matrix = np.asarray(self.matrix, dtype=np.float64)
        if self.matrix.shape != (3, 3):
            raise ValueError("matrix must be shape (3, 3)")
        if self.test_severity is not None:
            self.test_severity = float(np.clip(self.test_severity, 0.0, 1.0))

    @classmethod
    def create(cls, cvd_type: CVDType | str, severity: float, **meta: Any) -> CorrectionProfile:
        """Build a profile and its composite correction matrix."""
        cvd = CVDType.parse(cvd_type)
        sev = float(np.clip(severity, 0.0, 1.0))
        return cls(
            type=cvd,
            severity=sev,
            matrix=build_correction_matrix(cvd, sev),
            measured_at=meta.get("measured_at"),
            label=meta.get("label"),
            thresholds=meta.get("thresholds"),
            test_severity=meta.get("test_severity", sev),
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "type": self.type.value,
            "severity": self.severity,
            "matrix": self.matrix.tolist(),
        }
        if self.measured_at is not None:
            data["measured_at"] = self.measured_at
        if self.label is not None:
            data["label"] = self.label
        if self.thresholds is not None:
            data["thresholds"] = {k: float(v) for k, v in self.thresholds.items()}
        if self.test_severity is not None:
            data["test_severity"] = float(self.test_severity)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CorrectionProfile:
        thr = data.get("thresholds")
        return cls(
            type=CVDType.parse(data["type"]),
            severity=float(data["severity"]),
            matrix=np.asarray(data["matrix"], dtype=np.float64),
            measured_at=data.get("measured_at"),
            label=data.get("label"),
            thresholds={k: float(v) for k, v in thr.items()} if isinstance(thr, dict) else None,
            test_severity=float(data["test_severity"]) if "test_severity" in data else None,
        )

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: str | Path) -> CorrectionProfile:
        path = Path(path)
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    def rebuild_matrix(self) -> None:
        """Recompute ``matrix`` from ``type`` and ``severity``."""
        self.matrix = build_correction_matrix(self.type, self.severity)

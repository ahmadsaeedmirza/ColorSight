"""Color vision deficiency type identifiers."""

from __future__ import annotations

from enum import Enum


class CVDType(str, Enum):
    """Supported deficiency classes (Machado et al. 2009 naming)."""

    PROTANOPIA = "protanopia"  # L-cone / red-weak → protanomaly tables
    DEUTERANOPIA = "deuteranopia"  # M-cone / green-weak → deuteranomaly tables
    TRITANOPIA = "tritanopia"  # S-cone / blue-weak → tritanomaly tables

    @classmethod
    def parse(cls, value: str | CVDType) -> CVDType:
        if isinstance(value, cls):
            return value
        key = str(value).strip().lower().replace(" ", "_")
        aliases = {
            "protan": cls.PROTANOPIA,
            "protanomaly": cls.PROTANOPIA,
            "deutan": cls.DEUTERANOPIA,
            "deuteranomaly": cls.DEUTERANOPIA,
            "tritan": cls.TRITANOPIA,
            "tritanomaly": cls.TRITANOPIA,
        }
        if key in aliases:
            return aliases[key]
        return cls(key)

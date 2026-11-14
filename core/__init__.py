"""ColorSight core color engine (NumPy / OpenCV, no UI)."""

from .cvd_types import CVDType
from .engine import (
    apply_correction,
    apply_simulation,
    build_correction_matrix,
    simulation_matrix,
)
from .profile import CorrectionProfile
from .naming import name_color

__all__ = [
    "CVDType",
    "CorrectionProfile",
    "simulation_matrix",
    "build_correction_matrix",
    "apply_simulation",
    "apply_correction",
    "name_color",
]

__version__ = "0.1.0"

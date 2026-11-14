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
from .plates import (
    DEFAULT_BATTERY,
    EXPECTED_DIGIT_HOLES,
    RECOG_MARGIN,
    CircleDot,
    PlateAxis,
    PlateSpec,
    RenderedPlate,
    clean_digit_mask,
    count_digit_holes,
    digit_recognizability,
    generate_battery,
    hue_tile_colors,
    plate_metrics,
    rasterize_figure_dots,
    recognize_figure_digit,
    render_plate,
)
from .scoring import (
    PlateAnswer,
    TestResult,
    hue_arrangement_error,
    make_answers,
    score_screening,
    simulate_respondent,
)

__all__ = [
    "CVDType",
    "CorrectionProfile",
    "simulation_matrix",
    "build_correction_matrix",
    "apply_simulation",
    "apply_correction",
    "name_color",
    "PlateAxis",
    "PlateSpec",
    "CircleDot",
    "RenderedPlate",
    "DEFAULT_BATTERY",
    "render_plate",
    "generate_battery",
    "plate_metrics",
    "rasterize_figure_dots",
    "clean_digit_mask",
    "count_digit_holes",
    "digit_recognizability",
    "recognize_figure_digit",
    "EXPECTED_DIGIT_HOLES",
    "RECOG_MARGIN",
    "hue_tile_colors",
    "PlateAnswer",
    "TestResult",
    "hue_arrangement_error",
    "make_answers",
    "score_screening",
    "simulate_respondent",
]

__version__ = "0.1.0"

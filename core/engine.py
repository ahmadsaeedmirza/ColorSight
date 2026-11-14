"""Vectorized CVD simulation and daltonization (Fidaner-style error shift).

Math (RGB column vectors, values in [0, 1]):

Simulation (Machado et al. 2009)::

    rgb_sim = S(type, severity) @ rgb

Daltonization / correction::

    error = rgb - rgb_sim = (I - S) @ rgb
    rgb_out = rgb + E(type) @ error
            = (I + E @ (I - S)) @ rgb

``E`` redistributes lost channel information into channels the viewer can still
discriminate (Fidaner / Daltonize). The composite ``C = I + E (I - S)`` is what
``CorrectionProfile.matrix`` stores so real-time paths are a single matmul.
"""

from __future__ import annotations

import numpy as np

from .cvd_types import CVDType
from .machado import machado_matrix

# Fidaner-style error redistribution matrices (rows = output RGB).
# Lost information for the deficient cone is pushed into the other channels.
_ERROR_SHIFT = {
    CVDType.PROTANOPIA: np.array(
        [
            [0.0, 0.0, 0.0],
            [0.7, 1.0, 0.0],
            [0.7, 0.0, 1.0],
        ],
        dtype=np.float64,
    ),
    CVDType.DEUTERANOPIA: np.array(
        [
            [1.0, 0.7, 0.0],
            [0.0, 0.0, 0.0],
            [0.0, 0.7, 1.0],
        ],
        dtype=np.float64,
    ),
    CVDType.TRITANOPIA: np.array(
        [
            [1.0, 0.0, 0.7],
            [0.0, 1.0, 0.7],
            [0.0, 0.0, 0.0],
        ],
        dtype=np.float64,
    ),
}


def simulation_matrix(cvd_type: CVDType | str, severity: float) -> np.ndarray:
    """3×3 Machado simulation matrix for ``cvd_type`` at ``severity``."""
    return machado_matrix(cvd_type, severity)


def build_correction_matrix(cvd_type: CVDType | str, severity: float) -> np.ndarray:
    """Build composite daltonization matrix ``C = I + E (I - S)``."""
    cvd = CVDType.parse(cvd_type)
    s = float(np.clip(severity, 0.0, 1.0))
    S = machado_matrix(cvd, s)
    E = _ERROR_SHIFT[cvd]
    I = np.eye(3, dtype=np.float64)
    return I + E @ (I - S)


def _as_float_rgb(image: np.ndarray) -> tuple[np.ndarray, bool, np.dtype]:
    """Normalize HxWx3 (or Nx3) image to float64 RGB in [0, 1]."""
    if image.ndim not in (2, 3):
        raise ValueError("image must be HxWx3 or Nx3 RGB")
    if image.shape[-1] != 3:
        raise ValueError("last dimension must be 3 (RGB)")
    orig_dtype = image.dtype
    was_uint8 = image.dtype == np.uint8
    rgb = image.astype(np.float64, copy=False)
    if was_uint8 or np.nanmax(rgb) > 1.0 + 1e-6:
        rgb = rgb / 255.0
    return rgb, was_uint8, orig_dtype


def _apply_matrix(image: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Apply 3×3 matrix to every pixel (vectorized). Preserves uint8 if input was."""
    rgb, was_uint8, orig_dtype = _as_float_rgb(image)
    flat = rgb.reshape(-1, 3)
    # row-vector convention: out = flat @ M.T  == (M @ rgb_col).T
    out = flat @ matrix.T
    out = np.clip(out, 0.0, 1.0).reshape(rgb.shape)
    if was_uint8 or orig_dtype == np.uint8:
        return np.rint(out * 255.0).astype(np.uint8)
    return out.astype(np.float64)


def apply_simulation(
    image: np.ndarray,
    cvd_type: CVDType | str,
    severity: float,
) -> np.ndarray:
    """Simulate CVD appearance of an RGB image (NumPy array, vectorized)."""
    M = simulation_matrix(cvd_type, severity)
    return _apply_matrix(image, M)


def apply_correction(image: np.ndarray, profile) -> np.ndarray:
    """Apply a ``CorrectionProfile`` (or any object with ``.matrix``) to an RGB image."""
    matrix = np.asarray(profile.matrix, dtype=np.float64)
    if matrix.shape != (3, 3):
        raise ValueError("profile.matrix must be 3x3")
    return _apply_matrix(image, matrix)

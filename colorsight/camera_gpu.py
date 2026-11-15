"""GPU live-preview color math — 3×3 matrix in a Kivy fragment shader.

Matches ``core.engine._apply_matrix`` (gamma-space, clamp 0..1) so Corrected /
Simulation look identical to the validated NumPy path. Identity = Original.
"""

from __future__ import annotations

import numpy as np

# Kivy ES2 fragment shader. ``texture0`` / ``tex_coord0`` come from $HEADER$.
# Row-vector engine math ``out = rgb @ M.T`` ≡ column ``M * rgb`` in GLSL.
PREVIEW_FS = """
$HEADER$
uniform mat3 u_color_mat;

void main(void) {
    vec4 tex = texture2D(texture0, tex_coord0);
    vec3 rgb = u_color_mat * tex.rgb;
    rgb = clamp(rgb, 0.0, 1.0);
    gl_FragColor = vec4(rgb, 1.0);
}
"""

_IDENTITY = np.eye(3, dtype=np.float64)


def identity_matrix() -> np.ndarray:
    return _IDENTITY.copy()


def matrix_for_mode(
    mode: str,
    *,
    cvd_type=None,
    severity: float = 0.5,
) -> np.ndarray:
    """Return the 3×3 float64 matrix for Original / Corrected / Simulation."""
    if mode == "original" or cvd_type is None:
        return identity_matrix()
    sev = float(np.clip(severity, 0.0, 1.0))
    from core.engine import build_correction_matrix, simulation_matrix

    if mode == "simulation":
        return np.asarray(simulation_matrix(cvd_type, sev), dtype=np.float64)
    return np.asarray(build_correction_matrix(cvd_type, sev), dtype=np.float64)


def mat3_uniform(matrix: np.ndarray) -> tuple[float, ...]:
    """Column-major 9-tuple for a GLSL ``mat3`` uniform."""
    m = np.asarray(matrix, dtype=np.float32).reshape(3, 3)
    # OpenGL column-major: col0, col1, col2
    return tuple(float(x) for x in m.flatten(order="F"))


def apply_matrix_shader_emulation(image: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """CPU stand-in for the fragment shader (unit tests — must match core)."""
    from core.engine import _apply_matrix

    return _apply_matrix(image, np.asarray(matrix, dtype=np.float64))

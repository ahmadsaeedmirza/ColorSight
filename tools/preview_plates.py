"""Save plate previews under normal + CVD simulations to debug/plates/."""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import DEFAULT_BATTERY, apply_simulation, generate_battery  # noqa: E402


def _bgr(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., ::-1].copy()


def main() -> None:
    out = ROOT / "debug" / "plates"
    out.mkdir(parents=True, exist_ok=True)
    plates = generate_battery(DEFAULT_BATTERY, size=420, seed=42)
    views = (
        ("normal", None),
        ("protan", "protanopia"),
        ("deutan", "deuteranopia"),
        ("tritan", "tritanopia"),
    )
    for plate in plates:
        spec = plate.spec
        ans = f"n{spec.expected_normal}_p{spec.expected_protan}_d{spec.expected_deutan}_t{spec.expected_tritan}"
        for tag, cvd in views:
            img = plate.image
            if cvd is not None:
                img = apply_simulation(img, cvd, 1.0)
            name = f"{spec.plate_id}_{spec.axis.value}_digit{spec.digit}_{ans}_{tag}.png"
            cv2.imwrite(str(out / name), _bgr(img))
            print("wrote", name)
    print("done ->", out)


if __name__ == "__main__":
    main()

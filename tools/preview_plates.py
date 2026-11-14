"""Save plate previews under normal + CVD simulations to debug/plates/."""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import (  # noqa: E402
    DEFAULT_BATTERY,
    apply_simulation,
    generate_battery,
    rasterize_figure_dots,
)


def _bgr(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., ::-1].copy()


def _label(img_bgr: np.ndarray, text: str) -> np.ndarray:
    out = img_bgr.copy()
    cv2.rectangle(out, (0, 0), (out.shape[1], 28), (32, 32, 32), -1)
    cv2.putText(
        out,
        text,
        (8, 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (240, 240, 240),
        1,
        cv2.LINE_AA,
    )
    return out


def _contact_sheet(plates, cell: int = 200) -> np.ndarray:
    views = (
        ("normal", None),
        ("protan", "protanopia"),
        ("deutan", "deuteranopia"),
        ("tritan", "tritanopia"),
    )
    rows = len(plates)
    cols = len(views)
    pad = 4
    header = 32
    sheet = np.full(
        (rows * (cell + pad) + header + pad, cols * (cell + pad) + pad, 3),
        40,
        dtype=np.uint8,
    )
    for c, (tag, _) in enumerate(views):
        x = pad + c * (cell + pad)
        cv2.putText(
            sheet,
            tag,
            (x + 8, 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (220, 220, 220),
            1,
            cv2.LINE_AA,
        )
    for r, plate in enumerate(plates):
        for c, (tag, cvd) in enumerate(views):
            img = plate.image
            if cvd is not None:
                img = apply_simulation(img, cvd, 1.0)
            thumb = cv2.resize(_bgr(img), (cell, cell), interpolation=cv2.INTER_AREA)
            label = f"{plate.spec.plate_id} d{plate.spec.digit}"
            thumb = _label(thumb, label if c == 0 else tag)
            y = header + pad + r * (cell + pad)
            x = pad + c * (cell + pad)
            sheet[y : y + cell, x : x + cell] = thumb
    return sheet


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
        ans = (
            f"n{spec.expected_normal}_p{spec.expected_protan}_"
            f"d{spec.expected_deutan}_t{spec.expected_tritan}"
        )
        for tag, cvd in views:
            img = plate.image
            if cvd is not None:
                img = apply_simulation(img, cvd, 1.0)
            name = f"{spec.plate_id}_{spec.axis.value}_digit{spec.digit}_{ans}_{tag}.png"
            cv2.imwrite(str(out / name), _bgr(img))
            print("wrote", name)

        fig = rasterize_figure_dots(plate)
        fig_name = f"{spec.plate_id}_figure_only.png"
        cv2.imwrite(str(out / fig_name), fig)
        print("wrote", fig_name)

    sheet = _contact_sheet(plates, cell=200)
    sheet_path = out / "contact_sheet.png"
    cv2.imwrite(str(sheet_path), sheet)
    print("wrote", sheet_path.name)
    print("done ->", out)


if __name__ == "__main__":
    main()

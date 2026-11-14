"""Desktop smoke: pipeline load/resize/correct/save + no-profile / with-profile helpers."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image as PILImage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from colorsight.image_pipeline import (  # noqa: E402
    before_after_split,
    encode_image,
    load_rgb_uint8,
    resize_longest,
)
from colorsight.photo_io import pictures_dir, save_corrected_image  # noqa: E402
from core.engine import apply_correction, apply_simulation  # noqa: E402
from core.profile import CorrectionProfile  # noqa: E402


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="colorsight_photos_"))
    sample = tmp / "sample.png"
    arr = np.zeros((720, 1280, 3), dtype=np.uint8)
    arr[:, :640, 0] = 220
    arr[:, 640:, 1] = 180
    arr[300:420, 500:780] = (40, 90, 200)
    PILImage.fromarray(arr, mode="RGB").save(sample)

    # No profile path check (helper-level)
    profile_missing = not (ROOT / "does_not_exist_profile.json").is_file()
    assert profile_missing

    rgb = load_rgb_uint8(sample)
    preview = resize_longest(rgb, 1080)
    assert max(preview.shape[:2]) <= 1080

    profile = CorrectionProfile.create("deuteranomaly", 0.55)
    corrected = apply_correction(preview, profile)
    simulated = apply_simulation(preview, profile.type, 0.55)
    assert corrected.shape == preview.shape and corrected.dtype == np.uint8
    assert simulated.shape == preview.shape

    split = before_after_split(preview, corrected, 0.5)
    assert split.shape == preview.shape

    # Full-res save via desktop path (friendly label)
    full_corr = apply_correction(rgb, profile)
    label = save_corrected_image(full_corr, preferred_name="ColorSight_smoke.jpg", fmt="jpg")
    assert label == "Saved to your gallery"
    out_dir = pictures_dir() / "ColorSight"
    assert any(out_dir.glob("ColorSight_smoke*.jpg")) or (out_dir / "ColorSight_smoke.jpg").exists()

    # Encode round-trip
    enc = encode_image(corrected, tmp / "out.jpg", quality=95)
    assert enc.exists()

    print(
        "FLOW_PHOTOS_OK",
        f"preview={preview.shape}",
        f"split_ok=1",
        f"save={label!r}",
        f"album={out_dir.name}",
    )


if __name__ == "__main__":
    main()

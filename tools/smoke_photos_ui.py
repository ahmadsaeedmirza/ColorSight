"""Desktop UI smoke: Photos full flow including strength reset, modes, save, comparison."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image as PILImage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kivy.config import Config  # noqa: E402

Config.set("graphics", "width", "390")
Config.set("graphics", "height", "844")
Config.set("graphics", "borderless", "0")

from kivy.clock import Clock  # noqa: E402

from colorsight.app import ColorSightApp  # noqa: E402
from colorsight.image_pipeline import severity_for_slider  # noqa: E402
from colorsight.storage import profile_path  # noqa: E402
from core.profile import CorrectionProfile  # noqa: E402


def _make_sample() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="cs_photo_smoke_"))
    path = tmp / "smoke.png"
    arr = np.zeros((480, 640, 3), dtype=np.uint8)
    arr[:, :160] = (220, 40, 30)
    arr[:, 160:320] = (40, 180, 50)
    arr[:, 320:480] = (240, 140, 30)
    arr[:, 480:] = (30, 90, 220)
    PILImage.fromarray(arr, mode="RGB").save(path)
    return path


class _Smoke(ColorSightApp):
    def build(self):
        root = super().build()
        Clock.schedule_once(self._run, 0.4)
        return root

    def _run(self, _dt):
        sm = self.root.sm
        photos = sm.get_screen("photos")
        log: list[str] = []

        path = profile_path()
        if path.is_file():
            path.unlink()
        self.correction_profile = None
        sm.current = "photos"
        photos.on_pre_enter()
        assert photos._profile is None
        log.append("no_profile_ok")

        profile = CorrectionProfile.create("deuteranomaly", 0.91)
        profile.save(path)
        self.correction_profile = profile
        photos.on_pre_enter()
        assert photos._profile is not None
        assert abs(photos._preview_severity - 0.91) < 1e-6, photos._preview_severity
        log.append("profile_strength_ok")

        sample = _make_sample()
        photos._on_picked(str(sample))

        def _after_load(_dt2):
            assert photos._preview_rgb is not None
            assert abs(photos._preview_severity - severity_for_slider(0.91)) < 1e-6
            assert abs(photos._sev_bar.value - 0.91) < 1e-6, photos._sev_bar.value
            log.append("pick_ok")

            def _wait(_dt3):
                if photos._cache_get("corrected") is None or photos._cache_get("simulation") is None:
                    Clock.schedule_once(_wait, 0.15)
                    return
                self._exercise(photos, log)

            Clock.schedule_once(_wait, 0.2)

        Clock.schedule_once(_after_load, 0.2)

    def _exercise(self, photos, log: list[str]):
        tb = photos._toolbar
        viewer = photos._viewer

        # Modes + divider visibility
        tb._tap_mode("original")
        assert photos._mode == "original"
        assert viewer._handle.opacity == 0
        tb._tap_mode("corrected")
        assert viewer._handle.opacity == 1
        assert viewer._right_lbl.text == "Corrected"
        tb._tap_mode("simulation")
        assert viewer._handle.opacity == 1
        assert viewer._right_lbl.text == "Simulation"
        log.append("modes_divider_ok")

        # Drag divider
        viewer.split = 0.35
        viewer.split = 0.65
        log.append("split_ok")

        # Strength change + reset
        photos._sev_bar.set_value(1.0, notify=True)

        def _after_sev(_dt):
            assert photos._reset_btn.opacity == 1
            photos._reset_strength()
            assert abs(photos._preview_severity - 0.91) < 1e-6
            assert photos._reset_btn.opacity == 0
            log.append("strength_reset_ok")

            def _after_reset_cache(_dt2):
                if photos._cache_get("corrected") is None:
                    Clock.schedule_once(_after_reset_cache, 0.15)
                    return
                # Save each mode + comparison + share fallback
                for mode in ("original", "corrected", "simulation"):
                    tb._tap_mode(mode)
                    photos._export_current(share=False)
                photos._export_comparison(share=False)
                photos._export_current(share=True)
                log.append("exports_ok")

                def _done(_dt3):
                    print("SMOKE_PHOTOS_OK", " ".join(log))
                    self.stop()

                Clock.schedule_once(_done, 1.2)

            Clock.schedule_once(_after_reset_cache, 0.35)

        Clock.schedule_once(_after_sev, 0.35)


if __name__ == "__main__":
    _Smoke().run()

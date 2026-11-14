"""Desktop UI smoke: Photos no-profile → pick → tap every mode + severity + split → save."""

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
from colorsight.storage import profile_path  # noqa: E402
from core.profile import CorrectionProfile  # noqa: E402


def _make_sample() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="cs_photo_smoke_"))
    path = tmp / "smoke.png"
    arr = np.zeros((480, 640, 3), dtype=np.uint8)
    arr[..., 0] = 200
    arr[100:380, 120:520] = (30, 140, 90)
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

        # 1) No profile
        path = profile_path()
        if path.is_file():
            path.unlink()
        self.correction_profile = None
        sm.current = "photos"
        photos.on_pre_enter()
        assert photos._profile is None, "expected no profile"
        log.append("no_profile_ok")

        # 2) Install profile + re-enter
        profile = CorrectionProfile.create("protanomaly", 0.4)
        profile.save(path)
        self.correction_profile = profile
        photos.on_pre_enter()
        assert photos._profile is not None
        log.append("profile_ok")

        # 3) Load sample (bypass picker)
        sample = _make_sample()
        photos._on_picked(str(sample))

        def _after_load(_dt2):
            assert photos._preview_rgb is not None, "preview missing"
            assert hasattr(photos, "_toolbar"), "toolbar missing after pick"
            log.append("pick_ok")

            def _wait_cache(_dt3):
                if photos._cache_get("corrected") is None or photos._cache_get("simulation") is None:
                    Clock.schedule_once(_wait_cache, 0.15)
                    return
                self._exercise_toolbar(photos, log)

            Clock.schedule_once(_wait_cache, 0.2)

        Clock.schedule_once(_after_load, 0.15)

    def _exercise_toolbar(self, photos, log: list[str]):
        tb = photos._toolbar

        # Tap every mode via the real toolbar path (_tap_mode → mode property → on_mode)
        for key in ("original", "corrected", "simulation", "corrected"):
            tb._tap_mode(key)
            assert tb.mode == key, tb.mode
            assert photos._mode == key, photos._mode
            active = {k: c._active for k, c in tb._chips.items()}
            assert active[key] is True
            assert sum(1 for v in active.values() if v) == 1
        log.append("toolbar_modes_ok")

        # Severity bar (PreviewSeverityBar) — must not throw
        bar = photos._sev_bar
        bar._set_from_x(bar.x + bar.width * 0.7)
        assert abs(photos._preview_severity - bar.value) < 1e-6
        log.append("severity_ok")

        # Before/after divider drag path
        viewer = photos._viewer
        photos._mode = "corrected"
        photos._push_viewer_images()
        viewer.split = 0.25
        viewer.split = 0.75
        assert 0.02 <= viewer.split <= 0.98
        log.append("split_ok")

        def _after_sev(_dt):
            # Re-cache after severity change then save
            if photos._cache_get("corrected") is None:
                Clock.schedule_once(_after_sev, 0.2)
                return
            tb._do_save()

            def _done(_dt5):
                status = getattr(photos, "_status", None)
                text = status.text if status else ""
                assert "gallery" in text.lower() or text == "Saving…", text
                log.append("save_ok")
                print("SMOKE_PHOTOS_OK", " ".join(log))
                self.stop()

            Clock.schedule_once(_done, 0.9)

        Clock.schedule_once(_after_sev, 0.35)


if __name__ == "__main__":
    _Smoke().run()

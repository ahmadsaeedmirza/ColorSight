"""Desktop UI smoke: Photos no-profile → with profile → load sample → modes → save."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image as PILImage

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Headless-ish: allow kivy to open a window briefly
from kivy.config import Config  # noqa: E402

Config.set("graphics", "width", "390")
Config.set("graphics", "height", "844")
Config.set("graphics", "borderless", "0")

from kivy.app import App  # noqa: E402
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
        log = []

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
            log.append("pick_ok")

            def _after_process(_dt3):
                # Wait for bg thread cache
                photos._mode = "original"
                photos._push_viewer_images()
                photos._mode = "corrected"
                photos._push_viewer_images()
                photos._mode = "simulation"
                photos._push_viewer_images()
                log.append("modes_ok")

                def _save(_dt4):
                    # Ensure caches filled then save
                    if photos._cache_get("corrected") is None:
                        Clock.schedule_once(_save, 0.2)
                        return
                    photos._on_save()

                    def _done(_dt5):
                        status = getattr(photos, "_status", None)
                        text = status.text if status else ""
                        assert "gallery" in text.lower() or text == "Saving…", text
                        log.append("save_ok")
                        print("SMOKE_PHOTOS_OK", " ".join(log))
                        self.stop()

                    Clock.schedule_once(_done, 0.8)

                Clock.schedule_once(_save, 0.35)

            Clock.schedule_once(_after_process, 0.45)

        Clock.schedule_once(_after_load, 0.15)


if __name__ == "__main__":
    _Smoke().run()

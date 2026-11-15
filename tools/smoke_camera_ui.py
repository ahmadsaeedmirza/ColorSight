"""Desktop smoke: Camera with fake frames — modes, loupe, freeze/capture, shutdown."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["COLORSIGHT_FAKE_CAMERA"] = "1"

from kivy.config import Config  # noqa: E402

Config.set("graphics", "width", "390")
Config.set("graphics", "height", "844")

from kivy.clock import Clock  # noqa: E402

from colorsight.app import ColorSightApp  # noqa: E402
from colorsight.storage import profile_path  # noqa: E402
from core.profile import CorrectionProfile  # noqa: E402


class _Smoke(ColorSightApp):
    def build(self):
        root = super().build()
        Clock.schedule_once(self._run, 0.5)
        return root

    def _run(self, _dt):
        sm = self.root.sm
        log: list[str] = []
        path = profile_path()
        profile = CorrectionProfile.create("deuteranomaly", 0.91)
        profile.save(path)
        self.correction_profile = profile

        cam = sm.get_screen("camera")
        sm.current = "camera"

        def _after_start(_dt2):
            assert cam._profile is not None
            assert cam._mode == "corrected"
            assert abs(cam._preview_severity - 0.91) < 1e-6
            log.append("camera_default_ok")

            def _wait_frame(_dt3):
                if cam._stage.current_rgb() is None:
                    Clock.schedule_once(_wait_frame, 0.2)
                    return
                log.append("frame_ok")
                # Modes
                cam._toolbar._tap_mode("original")
                cam._toolbar._tap_mode("simulation")
                cam._toolbar._tap_mode("corrected")
                log.append("modes_ok")
                # Loupe
                cam._toggle_loupe()
                assert cam._loupe_on
                cam._update_loupe()
                log.append("loupe_ok")
                # Freeze / capture
                cam._toggle_freeze()
                assert cam._frozen
                cam._capture()
                cam._toggle_freeze()
                assert not cam._frozen
                log.append("freeze_capture_ok")
                # Lens is a Camera loupe state (via RootShell._navigate)
                self.root._navigate("lens")

                def _after_lens(_dt4):
                    assert sm.current == "camera"
                    assert cam._loupe_on
                    assert self.root.nav.active == "lens"
                    log.append("lens_redirect_ok")
                    # Camera nav clears loupe
                    self.root._navigate("camera")

                    def _after_cam(_dt5):
                        assert sm.current == "camera"
                        assert not cam._loupe_on
                        log.append("camera_clears_loupe_ok")
                        # Clean shutdown
                        cam.on_leave()
                        assert cam._poll_ev is None
                        log.append("shutdown_ok")
                        print("SMOKE_CAMERA_OK", " ".join(log))
                        self.stop()

                    Clock.schedule_once(_after_cam, 0.15)

                Clock.schedule_once(_after_lens, 0.15)

            Clock.schedule_once(_wait_frame, 0.4)

        Clock.schedule_once(_after_start, 0.6)


if __name__ == "__main__":
    _Smoke().run()

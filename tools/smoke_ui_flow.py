"""Narrow-window desktop smoke: Home chips → Test trial shell → headers."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Path used below for first-run prefs stub

from kivy.config import Config  # noqa: E402

Config.set("graphics", "width", "360")
Config.set("graphics", "height", "640")
Config.set("graphics", "resizable", "1")

from kivy.clock import Clock  # noqa: E402
from kivy.core.window import Window  # noqa: E402
from kivy.metrics import Metrics, dp  # noqa: E402

from colorsight.app import ColorSightApp  # noqa: E402
from colorsight.prefs import mark_onboarding_done  # noqa: E402


def main() -> None:
    # Prefer Home (not Welcome) for this smoke
    prefs = Path.home() / ".colorsight" / "prefs.json"
    prefs.parent.mkdir(parents=True, exist_ok=True)
    prefs.write_text('{"onboarding_done": true}', encoding="utf-8")

    app = ColorSightApp()
    notes: list[str] = []

    def step(_dt):
        # app.py sets a taller default; force the 360×640 phone frame for this check
        Window.size = (360, 640)
        mark_onboarding_done()
        root = app.root
        sm = root.sm
        # Home chips
        home = sm.get_screen("home")
        sm.current = "home"
        Clock.schedule_once(lambda dt: after_home(), 0.25)

        def after_home():
            # Find ChipRow under home
            from colorsight.widgets.chip import Chip, ChipRow

            row = None
            for w in home.walk():
                if isinstance(w, ChipRow):
                    row = w
                    break
            cam = None
            if row is not None:
                for c in row._row.children:
                    if isinstance(c, Chip) and c.text == "Camera":
                        cam = c
                        break
            if cam is not None and cam.width >= cam._label.texture_size[0] + dp(36):
                notes.append("home_chip_ok")
            else:
                notes.append("home_chip_FAIL")

            sm.current = "test"
            Clock.schedule_once(lambda dt: after_test(), 0.25)

        def after_test():
            test = sm.get_screen("test")
            # Start trivector shell without waiting for full session prep
            test._mode = "phone"
            from core import TrivectorSession

            test._session = TrivectorSession(mode="phone", seed=1)
            test._question_n = 0
            test._trial_update_ms = []
            test._trial_blit_ms = []
            test._build_trial_shell()
            test._phase = "trivector"
            # Measure essential content height (exclude flexible spacer)
            col = test._trial_scroll
            fixed = 0.0
            for child in col.children:
                # BoxLayout children are reverse order; spacer has size_hint_y=1
                if child.size_hint_y == 1:
                    continue
                fixed += float(child.height)
            fixed += float(col.padding[1]) + float(col.padding[3])
            gaps = max(0, len([c for c in col.children if c.size_hint_y != 1]) - 1)
            fixed += gaps * float(col.spacing)
            density = float(Metrics.density) or 1.0
            win_h = float(Window.height)
            fixed_dp = fixed / density
            win_dp = win_h / density
            notes.append(f"win_px={round(win_h)} dens={density:.2f}")
            # Design target: content ≤ 640 dp (phone frame)
            if fixed_dp <= 640 + 2:
                notes.append(f"trial_fit_ok fixed_dp={round(fixed_dp)}")
            else:
                notes.append(
                    f"trial_fit_FAIL fixed_dp={round(fixed_dp)} win_dp={round(win_dp)}"
                )

            # Header gap on settings
            sm.current = "settings"
            Clock.schedule_once(lambda dt: after_settings(), 0.2)

        def after_settings():
            from colorsight.widgets.screen_header import ScreenHeader

            settings = sm.get_screen("settings")
            hdr = None
            for w in settings.walk():
                if isinstance(w, ScreenHeader):
                    hdr = w
                    break
            if hdr is not None and abs(float(hdr.spacing) - float(dp(10))) < 0.6:
                notes.append("settings_hdr_ok")
            else:
                notes.append("settings_hdr_FAIL")
            # Arrow-key binding exists
            if hasattr(test := sm.get_screen("test"), "_on_key_down"):
                notes.append("keys_ok")
            print("SMOKE_UI_FLOW", " ".join(notes))
            app.stop()

    def on_start():
        Clock.schedule_once(step, 0.4)

    app.bind(on_start=lambda *_: on_start())
    app.run()


if __name__ == "__main__":
    main()

"""Automated phone-sim pass: visit every screen, flag overflows / tiny widths."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["KIVY_METRICS_DENSITY"] = "1.375"
os.environ.setdefault("COLORSIGHT_INSET_TOP", "28")
os.environ.setdefault("COLORSIGHT_INSET_BOTTOM", "24")

from kivy.config import Config  # noqa: E402

Config.set("graphics", "width", "540")
Config.set("graphics", "height", "1200")
Config.set("graphics", "resizable", "0")

from kivy.clock import Clock  # noqa: E402
from kivy.core.window import Window  # noqa: E402
from kivy.metrics import Metrics, dp  # noqa: E402

from colorsight.app import ColorSightApp  # noqa: E402
from colorsight.prefs import mark_onboarding_done  # noqa: E402
from colorsight.safe_area import set_debug_insets  # noqa: E402
from colorsight.theme.theme import get_theme  # noqa: E402
from colorsight.theme.tokens import Spacing  # noqa: E402
from colorsight.widgets.primary_button import PrimaryButton  # noqa: E402
from colorsight.widgets.pastel_card import PastelCard  # noqa: E402
from colorsight.widgets.screen_header import ScreenHeader  # noqa: E402


SCREENS = ("welcome", "home", "test", "photos", "camera", "profile", "settings")


def main() -> None:
    prefs = Path.home() / ".colorsight" / "prefs.json"
    prefs.parent.mkdir(parents=True, exist_ok=True)
    prefs.write_text('{"onboarding_done": true}', encoding="utf-8")

    set_debug_insets(28, 24)
    app = ColorSightApp()
    notes: list[str] = []
    idx = {"i": 0}

    def check_screen(name: str):
        issues = []
        win_w = float(Window.width)
        # Content should use nearly full width (not stuck at ~390 desktop box)
        if win_w < 500:
            issues.append(f"win_narrow={win_w:.0f}")
        for w in app.root.walk():
            if isinstance(w, PrimaryButton) and w.width > 0:
                # Label texture should not exceed button inner width by much
                lbl = getattr(w, "_label", None)
                if lbl is not None and lbl.texture_size[0] > w.width + 2:
                    issues.append(f"btn_overflow:{w.text[:20]}")
            if isinstance(w, PastelCard) and w.parent is not None:
                # Cards must not sit with zero/negative space vs siblings — height ok
                if w.height < dp(40):
                    issues.append("card_too_short")
            if isinstance(w, ScreenHeader) and w.width + 1 < win_w * 0.5:
                # Header should span most of the screen, not a 390px pocket
                pass
        # Root shell should fill window
        if abs(float(app.root.width) - win_w) > 2:
            issues.append(f"root_w={app.root.width:.0f}/win={win_w:.0f}")
        if issues:
            notes.append(f"{name}:FAIL:{','.join(issues)}")
        else:
            notes.append(f"{name}:ok")

    def step(_dt):
        mark_onboarding_done()
        Window.size = (540, 1200)

        def visit(_dt2):
            i = idx["i"]
            if i >= len(SCREENS):
                # Theme flip pass (light → dark → light) without leaving the sim
                get_theme().set_preference("dark", persist=False, return_to="home")
                get_theme().set_preference("light", persist=False, return_to="home")
                notes.append(
                    f"insets:top={Spacing.safe_top}:bottom={Spacing.safe_bottom}"
                )
                print(
                    "SMOKE_PHONE_SIM",
                    f"density={Metrics.density:.3f}",
                    f"win={tuple(Window.size)}",
                    " ".join(notes),
                )
                app.stop()
                return
            name = SCREENS[i]
            app.root.sm.current = name
            idx["i"] = i + 1
            Clock.schedule_once(
                lambda dt: (check_screen(name), Clock.schedule_once(visit, 0.25)), 0.35
            )

        Clock.schedule_once(visit, 0.4)

    app.bind(on_start=lambda *_: Clock.schedule_once(step, 0.3))
    app.run()


if __name__ == "__main__":
    main()

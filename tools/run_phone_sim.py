"""Desktop phone-density layout check (half-scale of 1080×2400 @ density 2.75).

Real mid-range phone: 1080×2400 px, density ≈ 2.75 → ~393×873 dp.
This sim opens a 540×1200 window at density 1.375 (half scale) so the same
logical layouts can be inspected before an Android build.

Usage (from repo root, venv active):
    python tools/run_phone_sim.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Half of 2.75 — pairs with 540×1200 (half of 1080×2400)
os.environ["KIVY_METRICS_DENSITY"] = "1.375"

from kivy.config import Config  # noqa: E402

Config.set("graphics", "width", "540")
Config.set("graphics", "height", "1200")
Config.set("graphics", "resizable", "1")

from colorsight.app import ColorSightApp  # noqa: E402
from colorsight.prefs import mark_onboarding_done  # noqa: E402
from kivy.clock import Clock  # noqa: E402
from kivy.core.window import Window  # noqa: E402
from kivy.metrics import Metrics  # noqa: E402


def main() -> None:
    # Prefer Home after first paint so every screen is reachable via nav
    prefs = Path.home() / ".colorsight" / "prefs.json"
    prefs.parent.mkdir(parents=True, exist_ok=True)
    if not prefs.is_file():
        prefs.write_text('{"onboarding_done": true}', encoding="utf-8")

    app = ColorSightApp()

    def _announce(_dt):
        mark_onboarding_done()
        Window.size = (540, 1200)
        print(
            "PHONE_SIM",
            f"window={tuple(Window.size)}",
            f"density={Metrics.density:.3f}",
            f"dpi={Metrics.dpi:.1f}",
            "screens=welcome,home,test,photos,camera,profile,settings",
        )
        print("PHONE_SIM_HINT Navigate with the floating nav; Ctrl+C / close window to exit.")

    def on_start():
        Clock.schedule_once(_announce, 0.2)

    app.bind(on_start=lambda *_: on_start())
    app.run()


if __name__ == "__main__":
    main()

"""Desktop smoke: Chip auto-width, inverted-T pad, ScreenHeader gap."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kivy.config import Config  # noqa: E402

Config.set("graphics", "width", "360")
Config.set("graphics", "height", "640")
Config.set("graphics", "resizable", "1")

from kivy.app import App  # noqa: E402
from kivy.clock import Clock  # noqa: E402
from kivy.metrics import dp  # noqa: E402
from kivy.uix.boxlayout import BoxLayout  # noqa: E402

from colorsight.screens.test_widgets import ARROW_GAP_DP, ARROW_KEY_DP, ArrowPad  # noqa: E402
from colorsight.theme.theme import register_fonts  # noqa: E402
from colorsight.widgets.chip import ChipRow  # noqa: E402
from colorsight.widgets.screen_header import ScreenHeader  # noqa: E402


class SmokeUiPolishApp(App):
    def build(self):
        register_fonts()
        root = BoxLayout(orientation="vertical", padding=10, spacing=8)
        self._row = ChipRow(
            options=["All", "Test", "Photos", "Camera", "Lens", "Profile"],
            selected="All",
        )
        root.add_widget(self._row)
        self._pad = ArrowPad(on_orient=lambda o: None, on_cant_see=lambda: None)
        root.add_widget(self._pad)
        self._hdr = ScreenHeader(title="Vision Test", on_back=lambda: None)
        root.add_widget(self._hdr)
        Clock.schedule_once(self._check, 0.35)
        return root

    def _check(self, _dt):
        chips = [c for c in self._row._row.children]
        cam = next((c for c in chips if c.text == "Camera"), None)
        pad_x = dp(18) * 2
        ok_chip = (
            cam is not None
            and cam._label.texture_size[0] > 0
            and cam.width + 0.5 >= cam._label.texture_size[0] + pad_x
            and cam._label.texture_size[1] <= dp(22)
        )
        widths = [
            (c.text, round(float(c.width)), int(c._label.texture_size[0]))
            for c in reversed(chips)
        ]
        ok_pad = (
            ARROW_KEY_DP == 72
            and ARROW_GAP_DP == 8
            and self._pad.height <= dp(230)
        )
        ok_hdr = abs(float(self._hdr.spacing) - float(dp(10))) < 0.5
        print("CHIP_WIDTHS", widths)
        print(
            "ARROW",
            ARROW_KEY_DP,
            ARROW_GAP_DP,
            "pad_h",
            round(float(self._pad.height)),
        )
        print(
            "HEADER",
            round(float(self._hdr.height)),
            "spacing",
            round(float(self._hdr.spacing)),
        )
        status = []
        status.append("chip_ok" if ok_chip else "chip_FAIL")
        status.append("pad_ok" if ok_pad else "pad_FAIL")
        status.append("hdr_ok" if ok_hdr else "hdr_FAIL")
        print("SMOKE_UI_POLISH", " ".join(status))
        self.stop()


if __name__ == "__main__":
    SmokeUiPolishApp().run()

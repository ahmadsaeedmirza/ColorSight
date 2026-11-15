"""Lens nav entry — Camera screen state (loupe), not a separate live pipeline.

Navigating here is handled by ``RootShell._navigate``: switch to Camera, then
``Clock.schedule_once`` enable loupe after the transition finishes. This screen
exists so ``sm.screen_names`` still includes ``lens`` for Home tiles / prefs;
it never runs camera code and never flips ``sm.current`` from ``on_pre_enter``.
"""

from __future__ import annotations

import logging

from kivy.clock import Clock
from kivy.uix.screenmanager import Screen

log = logging.getLogger("colorsight")


class LensScreen(Screen):
    """Placeholder screen — redirect is owned by RootShell to avoid mid-transition crashes."""

    def __init__(self, **kwargs):
        super().__init__(name="lens", **kwargs)

    def on_enter(self, *_args):
        # Safety net if something sets sm.current="lens" directly (smokes / old code)
        Clock.schedule_once(self._bounce_to_camera, 0)

    def _bounce_to_camera(self, *_a):
        try:
            if not self.manager:
                return
            if self.manager.current != "lens":
                return
            cam = self.manager.get_screen("camera")
            self.manager.transition.direction = "left"
            self.manager.current = "camera"
            Clock.schedule_once(lambda dt: self._enable_loupe(cam), 0)
        except Exception:
            log.exception("lens: bounce_to_camera failed")

    def _enable_loupe(self, cam):
        try:
            if hasattr(cam, "set_loupe_enabled"):
                cam.set_loupe_enabled(True)
            elif hasattr(cam, "enable_loupe_on_enter"):
                cam.enable_loupe_on_enter(True)
        except Exception:
            log.exception("lens: enable loupe failed")

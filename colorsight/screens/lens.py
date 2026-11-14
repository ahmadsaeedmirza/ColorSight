"""Lens nav entry — opens Camera with the loupe enabled (shared pipeline)."""

from __future__ import annotations

from kivy.uix.screenmanager import Screen


class LensScreen(Screen):
    """Thin redirect so Lens and Camera share one live pipeline + loupe widgets."""

    def __init__(self, **kwargs):
        super().__init__(name="lens", **kwargs)

    def on_pre_enter(self, *_args):
        if not self.manager:
            return
        cam = self.manager.get_screen("camera")
        if hasattr(cam, "enable_loupe_on_enter"):
            cam.enable_loupe_on_enter(True)
        self.manager.transition.direction = "left"
        self.manager.current = "camera"

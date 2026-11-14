"""Live Camera screen — shared pipeline with Lens (loupe)."""

from __future__ import annotations

import logging
import threading
import time

import numpy as np
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from colorsight.camera_pipeline import (
    LabelSmoother,
    LIVE_LONGEST,
    camera_default_mode,
    downscale_live,
    loupe_zoom_crop,
    name_loupe_color,
)
from colorsight.camera_source import (
    create_frame_source,
    open_settings_camera,
    request_camera_permission,
)
from colorsight.image_pipeline import (
    render_mode_rgb,
    reset_link_visible,
    severity_for_slider,
    strength_percent,
)
from colorsight.photo_io import is_android, save_corrected_image
from colorsight.screens.camera_widgets import CameraModeToolbar, LivePreviewStage, LoupeOverlay
from colorsight.screens.photo_widgets import PreviewSeverityBar, TextLinkButton
from colorsight.storage import profile_path
from colorsight.theme.tokens import Colors, Fonts, Icons, Spacing
from colorsight.widgets import PastelCard, PrimaryButton, RoundIconButton

log = logging.getLogger(__name__)


class CameraScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="camera", **kwargs)
        self._profile = None
        self._mode = "corrected"
        self._preview_severity = 0.5
        self._saved_severity = 0.5
        self._source = None
        self._frozen = False
        self._frozen_rgb = None
        self._latest_original = None
        self._processing = False
        self._poll_ev = None
        self._loupe_on = False
        self._start_with_loupe = False
        self._smoother = LabelSmoother(5)
        self._fps_n = 0
        self._fps_t0 = time.time()
        self._fps_value = 0.0
        self._perm_denied = False
        self._root = FloatLayout()
        self.add_widget(self._root)
        self._build_chrome()

    # --- public ----------------------------------------------------------

    def enable_loupe_on_enter(self, enabled: bool = True):
        self._start_with_loupe = enabled

    # --- lifecycle -------------------------------------------------------

    def on_pre_enter(self, *_a):
        self._reload_profile()
        self._mode = camera_default_mode(self._profile is not None)
        if self._start_with_loupe:
            self._loupe_on = True
            self._start_with_loupe = False
        self._rebuild()

    def on_enter(self, *_a):
        self._start_camera()

    def on_leave(self, *_a):
        self._stop_camera()

    def on_pause(self):
        self._stop_camera()
        return True

    def on_resume(self):
        if self.manager and self.manager.current == "camera":
            self._start_camera()

    # --- profile ---------------------------------------------------------

    def _reload_profile(self):
        app = App.get_running_app()
        path = profile_path()
        profile = None
        if path.is_file():
            try:
                from core.profile import CorrectionProfile

                profile = CorrectionProfile.load(path)
                if app is not None:
                    app.correction_profile = profile
            except Exception as exc:  # noqa: BLE001
                log.warning("Camera profile load failed: %s", exc)
        self._profile = profile
        if profile is not None:
            sev = severity_for_slider(float(profile.severity))
            self._saved_severity = sev
            self._preview_severity = sev
            log.info(
                "camera_strength profile_severity=%.4f slider=%d",
                float(profile.severity),
                strength_percent(sev),
            )

    # --- UI --------------------------------------------------------------

    def _build_chrome(self):
        self._root.clear_widgets()
        self._stage = LivePreviewStage(size_hint=(1, 1))
        self._root.add_widget(self._stage)

        self._overlay = BoxLayout(
            orientation="vertical",
            size_hint=(1, 1),
            padding=[
                dp(Spacing.screen_x),
                dp(Spacing.sm),
                dp(Spacing.screen_x),
                dp(Spacing.nav_clearance),
            ],
            spacing=dp(Spacing.xs),
        )
        self._root.add_widget(self._overlay)

    def _rebuild(self):
        self._overlay.clear_widgets()
        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44), spacing=dp(8))
        back = RoundIconButton(icon=Icons.arrow_back, diameter=40)
        back.on_press_cb = lambda *_: self._go("home")
        header.add_widget(back)
        title = Label(
            text="Camera",
            font_name=Fonts.bold,
            font_size=dp(20),
            color=Colors.text,
            halign="left",
            valign="middle",
        )
        title.bind(size=lambda *_: setattr(title, "text_size", title.size))
        header.add_widget(title)
        self._fps_lbl = Label(
            text="",
            font_name=Fonts.medium,
            font_size=dp(11),
            color=Colors.text_muted,
            size_hint=(None, 1),
            width=dp(64),
        )
        header.add_widget(self._fps_lbl)
        self._overlay.add_widget(header)

        self._body = FloatLayout(size_hint=(1, 1))
        self._overlay.add_widget(self._body)

        # Status / permission cards sit in body
        self._card_host = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height=dp(1),
            pos_hint={"top": 1},
            spacing=dp(8),
        )
        self._body.add_widget(self._card_host)
        self._refresh_cards()

        # Loupe
        self._loupe = LoupeOverlay()
        self._loupe.opacity = 1 if self._loupe_on else 0
        self._loupe.disabled = not self._loupe_on
        self._loupe.move_cb = self._on_loupe_move
        self._loupe.pos = (dp(40), dp(200))
        self._body.add_widget(self._loupe)

        # Controls
        controls = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height=dp(140),
            spacing=dp(4),
            pos_hint={"x": 0, "y": 0},
        )
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(22))
        row.add_widget(
            Label(
                text="Strength",
                font_name=Fonts.semibold,
                font_size=dp(12),
                color=Colors.text,
                size_hint=(None, 1),
                width=dp(70),
            )
        )
        self._sev_value = Label(
            text=f"{strength_percent(self._preview_severity)}",
            font_name=Fonts.semibold,
            font_size=dp(12),
            color=Colors.text,
            size_hint=(None, 1),
            width=dp(36),
        )
        row.add_widget(Widget())
        row.add_widget(self._sev_value)
        controls.add_widget(row)

        self._sev_bar = PreviewSeverityBar(value=self._preview_severity)
        self._sev_bar.change_cb = self._on_severity
        controls.add_widget(self._sev_bar)

        self._reset_btn = TextLinkButton(text="Reset to my result")
        self._reset_btn.bind(on_release=lambda *_: self._reset_strength())
        controls.add_widget(self._reset_btn)
        self._update_reset()

        self._toolbar = CameraModeToolbar(show_flip=is_android())
        self._toolbar.mode_cb = self._on_mode
        self._toolbar.freeze_cb = self._toggle_freeze
        self._toolbar.capture_cb = self._capture
        self._toolbar.loupe_cb = self._toggle_loupe
        self._toolbar.flip_cb = self._flip
        self._toolbar.mode = self._mode
        controls.add_widget(self._toolbar)

        self._status = Label(
            text="",
            font_name=Fonts.medium,
            font_size=dp(12),
            color=Colors.accent_blue,
            size_hint_y=None,
            height=dp(18),
        )
        controls.add_widget(self._status)
        self._overlay.add_widget(controls)

    def _refresh_cards(self):
        self._card_host.clear_widgets()
        self._card_host.height = dp(8)
        if self._perm_denied:
            card = PastelCard(
                title="Camera access needed",
                subtitle="Allow camera access to use live correction. You can enable it in settings.",
                palette="sky",
                auto_height=True,
                size_hint_y=None,
            )
            self._card_host.add_widget(card)
            btn = PrimaryButton(text="Open settings")
            btn.on_press_cb = lambda *_: open_settings_camera()
            self._card_host.add_widget(btn)
            self._card_host.height = dp(180)
            return
        if self._profile is None:
            card = PastelCard(
                title="Take the color test first",
                subtitle="Live correction needs your profile. You can still preview Original.",
                palette="sky",
                auto_height=True,
                size_hint_y=None,
            )
            self._card_host.add_widget(card)
            btn = PrimaryButton(text="Go to Vision Test")
            btn.on_press_cb = lambda *_: self._go("test")
            self._card_host.add_widget(btn)
            self._card_host.height = dp(180)

    def _go(self, name: str):
        if self.manager:
            self.manager.current = name

    # --- camera loop -----------------------------------------------------

    def _start_camera(self):
        def _after_perm(ok: bool):
            Clock.schedule_once(lambda dt: self._on_perm(ok), 0)

        request_camera_permission(_after_perm)

    def _on_perm(self, ok: bool):
        self._perm_denied = not ok
        self._refresh_cards()
        if not ok:
            return
        if self._source is None:
            self._source = create_frame_source()
        if not self._source.start():
            # Fall back to fake frames on desktop so the UI is still usable
            from colorsight.camera_source import FakeFrameSource

            log.warning("Camera open failed — using synthetic frames")
            self._source = FakeFrameSource()
            self._source.start()
            self._set_status("No webcam — demo frames")
        self._processing = False
        if self._poll_ev is not None:
            self._poll_ev.cancel()
        # Poll ~20 Hz; worker drops frames if still processing
        self._poll_ev = Clock.schedule_interval(self._tick, 1.0 / 20.0)

    def _stop_camera(self):
        if self._poll_ev is not None:
            self._poll_ev.cancel()
            self._poll_ev = None
        if self._source is not None:
            self._source.stop()
        self._processing = False

    def _tick(self, _dt):
        if self._frozen:
            return
        if self._processing or self._source is None:
            return
        frame = self._source.read_latest()
        if frame is None:
            return
        self._processing = True
        mode = self._mode
        sev = float(self._preview_severity)
        cvd = self._profile.type if self._profile is not None else None
        loupe_on = self._loupe_on

        def _work():
            try:
                original = downscale_live(frame, LIVE_LONGEST)
                if mode == "original" or cvd is None:
                    display = original
                else:
                    display = render_mode_rgb(original, mode, cvd_type=cvd, severity=sev)
            except Exception:
                log.exception("frame process failed")
                self._processing = False
                return

            def _blit(_dt=None):
                self._latest_original = original
                self._stage.set_rgb(display)
                self._processing = False
                self._note_fps()
                if loupe_on:
                    self._update_loupe()

            Clock.schedule_once(_blit, 0)

        threading.Thread(target=_work, daemon=True).start()

    def _note_fps(self):
        self._fps_n += 1
        now = time.time()
        if now - self._fps_t0 >= 1.0:
            self._fps_value = self._fps_n / (now - self._fps_t0)
            self._fps_n = 0
            self._fps_t0 = now
            app = App.get_running_app()
            show = bool(getattr(app, "show_camera_fps", False)) if app else False
            if hasattr(self, "_fps_lbl"):
                self._fps_lbl.text = f"{self._fps_value:.0f} fps" if show else ""

    # --- loupe -----------------------------------------------------------

    def _toggle_loupe(self):
        self._loupe_on = not self._loupe_on
        self._loupe.opacity = 1 if self._loupe_on else 0
        self._loupe.disabled = not self._loupe_on
        if self._loupe_on:
            self._update_loupe()

    def _on_loupe_move(self, *_a):
        self._update_loupe()

    def _update_loupe(self):
        if not self._loupe_on or self._latest_original is None:
            return
        gx, gy = self._loupe.glass_center()
        pix = self._stage.image_to_pixel(gx, gy)
        if pix is None:
            return
        cx, cy = pix
        zoom_rgb = loupe_zoom_crop(self._latest_original, cx, cy, zoom=self._loupe.zoom)
        self._loupe.set_zoom_rgb(zoom_rgb)
        try:
            name, med = name_loupe_color(self._latest_original, cx, cy)
            name = self._smoother.push(name)
            corr = None
            if self._mode == "corrected" and self._profile is not None:
                patch = med.reshape(1, 1, 3)
                corr = render_mode_rgb(
                    patch, "corrected", cvd_type=self._profile.type, severity=self._preview_severity
                )[0, 0]
            self._loupe.set_label(name, med, corr)
        except Exception:
            log.exception("loupe name failed")

    # --- controls --------------------------------------------------------

    def _on_mode(self, mode: str):
        if mode in ("corrected", "simulation") and self._profile is None:
            self._set_status("Take the color test to use this mode")
            if hasattr(self, "_toolbar"):
                self._toolbar.mode = "original"
            self._mode = "original"
            return
        self._mode = mode

    def _on_severity(self, value: float):
        self._preview_severity = severity_for_slider(value)
        if hasattr(self, "_sev_value"):
            self._sev_value.text = f"{strength_percent(self._preview_severity)}"
        self._update_reset()

    def _update_reset(self):
        if not hasattr(self, "_reset_btn"):
            return
        show = self._profile is not None and reset_link_visible(
            self._preview_severity, self._saved_severity
        )
        self._reset_btn.opacity = 1 if show else 0
        self._reset_btn.height = dp(28) if show else 0
        self._reset_btn.disabled = not show

    def _reset_strength(self):
        self._preview_severity = self._saved_severity
        if hasattr(self, "_sev_bar"):
            self._sev_bar.set_value(self._preview_severity, notify=False)
        if hasattr(self, "_sev_value"):
            self._sev_value.text = f"{strength_percent(self._preview_severity)}"
        self._update_reset()

    def _toggle_freeze(self):
        if not self._frozen:
            rgb = self._stage.current_rgb()
            if rgb is None:
                return
            self._frozen = True
            self._frozen_rgb = rgb.copy()
            if self._latest_original is not None:
                self._frozen_original = self._latest_original.copy()
            else:
                self._frozen_original = rgb.copy()
        else:
            self._frozen = False
            self._frozen_rgb = None
        if hasattr(self, "_toolbar"):
            self._toolbar.set_frozen(self._frozen)

    def _capture(self):
        src = self._frozen_rgb if self._frozen and self._frozen_rgb is not None else self._stage.current_rgb()
        # Prefer re-processing full latest original at current mode for quality
        base = None
        if self._frozen and getattr(self, "_frozen_original", None) is not None:
            base = self._frozen_original
        elif self._latest_original is not None:
            base = self._latest_original
        if base is None and src is None:
            self._set_status("Nothing to capture yet")
            return
        self._set_status("Saving…")
        mode = self._mode
        sev = float(self._preview_severity)
        cvd = self._profile.type if self._profile is not None else None
        frame = base if base is not None else src

        def _work():
            msg = "Couldn't save that photo"
            try:
                if mode == "original" or cvd is None:
                    out = frame
                else:
                    out = render_mode_rgb(frame, mode, cvd_type=cvd, severity=sev)
                msg = save_corrected_image(out, preferred_name=f"ColorSight_Camera_{mode}", fmt="jpg")
            except Exception:
                log.exception("capture failed")

            def _done(_dt=None):
                self._set_status(msg)

            Clock.schedule_once(_done, 0)

        threading.Thread(target=_work, daemon=True).start()

    def _flip(self):
        if self._source is not None:
            self._source.flip()

    def _set_status(self, text: str):
        if hasattr(self, "_status"):
            self._status.text = text

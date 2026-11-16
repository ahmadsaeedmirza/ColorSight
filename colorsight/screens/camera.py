"""Live Camera screen — shared pipeline with Lens (loupe)."""

from __future__ import annotations

import logging
import threading
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from colorsight.camera_gpu import matrix_for_mode
from colorsight.camera_pipeline import (
    LabelSmoother,
    LIVE_LONGEST,
    camera_default_mode,
    downscale_live,
    loupe_zoom_crop,
    name_loupe_color,
)
from colorsight.camera_source import (
    CameraSessionState,
    FakeFrameSource,
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
from colorsight.theme.screen_bg import install_opaque_bg
from colorsight.theme.tokens import Colors, Fonts, Spacing
from colorsight.widgets import PastelCard, PrimaryButton, ScreenHeader

log = logging.getLogger("colorsight")


class CameraScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="camera", **kwargs)
        install_opaque_bg(self, neutral=True)  # preview accuracy surface
        self._profile = None
        self._mode = "corrected"
        self._preview_severity = 0.5
        self._saved_severity = 0.5
        self._source = None
        self._session = CameraSessionState()
        self._frozen = False
        self._frozen_rgb = None
        self._latest_original = None
        self._pending_frame = None
        self._blit_scheduled = False
        self._poll_ev = None
        self._loupe_on = False
        self._start_with_loupe = False
        self._loupe_name_t = 0.0
        self._smoother = LabelSmoother(5)
        self._fps_n = 0
        self._fps_t0 = time.time()
        self._fps_value = 0.0
        self._frame_w = 0
        self._frame_h = 0
        self._error_code = None
        # Timing (ms) — rolling sums for 5 s log line
        self._t_recv_ms = 0.0
        self._t_upload_ms = 0.0
        self._t_draw_ms = 0.0
        self._t_n = 0
        self._t_log_t0 = time.time()
        self._root = FloatLayout()
        self.add_widget(self._root)
        self._build_chrome()

    # --- public ----------------------------------------------------------

    def enable_loupe_on_enter(self, enabled: bool = True):
        """Legacy flag — prefer ``set_loupe_enabled`` after the screen is shown."""
        self._start_with_loupe = enabled

    def set_loupe_enabled(self, enabled: bool = True):
        """Enable/disable loupe after Camera is fully shown (safe from nav)."""
        try:
            self._loupe_on = bool(enabled)
            if hasattr(self, "_loupe"):
                self._loupe.opacity = 1 if self._loupe_on else 0
                self._loupe.disabled = not self._loupe_on
            if self._loupe_on:
                Clock.schedule_once(lambda dt: self._center_loupe(), 0)
                self._update_loupe(force_name=True)
            self._sync_nav_for_loupe()
        except Exception:
            log.exception("set_loupe_enabled failed")

    def _sync_nav_for_loupe(self):
        """Highlight Lens nav while loupe is on; Camera otherwise."""
        try:
            app = App.get_running_app()
            root = getattr(app, "root", None) if app else None
            nav = getattr(root, "nav", None) if root is not None else None
            if nav is None:
                return
            if self.manager and self.manager.current == "camera":
                nav.active = "lens" if self._loupe_on else "camera"
        except Exception:
            log.exception("nav loupe sync failed")

    # --- lifecycle -------------------------------------------------------

    def on_pre_enter(self, *_a):
        self._reload_profile()
        self._mode = camera_default_mode(self._profile is not None)
        if self._start_with_loupe:
            self._loupe_on = True
            self._start_with_loupe = False
        self._rebuild()
        self._apply_preview_matrix()

    def on_enter(self, *_a):
        # Lazy GPU shader — never compile at app start
        try:
            if hasattr(self, "_stage") and hasattr(self._stage, "ensure_gpu"):
                ok = self._stage.ensure_gpu()
                if not ok and getattr(self._stage, "_cpu_fallback", False):
                    self._set_status("Preview using CPU color (GPU unavailable)")
        except Exception:
            log.exception("camera GPU ensure failed")
        self._start_camera()
        Clock.schedule_once(lambda dt: self._sync_nav_for_loupe(), 0)

    def on_leave(self, *_a):
        self._stop_camera()
        # Leaving Camera turns loupe off so next Camera visit starts clean
        self._loupe_on = False

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
            spacing=dp(Spacing.sm),
        )
        self._root.add_widget(self._overlay)

        self._test_pattern_lbl = Label(
            text="Test pattern",
            font_name=Fonts.semibold,
            font_size=dp(12),
            color=(1, 1, 1, 0.9),
            size_hint=(None, None),
            size=(dp(110), dp(28)),
            pos_hint={"x": 0.02, "top": 0.98},
            halign="center",
            valign="middle",
            opacity=0,
        )
        self._test_pattern_lbl.bind(
            size=lambda *_: setattr(
                self._test_pattern_lbl, "text_size", self._test_pattern_lbl.size
            )
        )
        self._root.add_widget(self._test_pattern_lbl)

        self._loupe = LoupeOverlay()
        self._loupe.opacity = 0
        self._loupe.disabled = True
        self._loupe.move_cb = self._on_loupe_move
        self._root.add_widget(self._loupe)

    def _rebuild(self):
        self._overlay.clear_widgets()
        self._fps_lbl = Label(
            text="",
            font_name=Fonts.medium,
            font_size=dp(11),
            color=Colors.text_muted,
            size_hint=(None, 1),
            width=dp(120),
            halign="right",
            valign="middle",
        )
        self._fps_lbl.bind(
            size=lambda *_: setattr(self._fps_lbl, "text_size", self._fps_lbl.size)
        )
        header = ScreenHeader(
            title="Camera",
            on_back=lambda: self._go("home"),
            trailing=self._fps_lbl,
            include_top_inset=True,
        )
        self._overlay.add_widget(header)

        self._card_host = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height=dp(1),
            spacing=dp(8),
        )
        self._overlay.add_widget(self._card_host)
        self._refresh_cards()

        self._body = Widget(size_hint=(1, 1))
        self._overlay.add_widget(self._body)

        controls = BoxLayout(
            orientation="vertical",
            size_hint=(1, None),
            height=dp(148),
            spacing=dp(6),
        )
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(22))
        self._strength_lbl = Label(
            text="Strength",
            font_name=Fonts.semibold,
            font_size=dp(12),
            color=Colors.text,
            size_hint=(None, 1),
            width=dp(70),
            halign="left",
            valign="middle",
        )
        self._strength_lbl.bind(
            size=lambda *_: setattr(self._strength_lbl, "text_size", self._strength_lbl.size)
        )
        row.add_widget(self._strength_lbl)
        self._sev_value = Label(
            text=f"{strength_percent(self._preview_severity)}",
            font_name=Fonts.semibold,
            font_size=dp(12),
            color=Colors.text,
            size_hint=(None, 1),
            width=dp(36),
            halign="right",
            valign="middle",
        )
        self._sev_value.bind(
            size=lambda *_: setattr(self._sev_value, "text_size", self._sev_value.size)
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
        self._controls = controls
        self._overlay.add_widget(controls)

        self._loupe.opacity = 1 if self._loupe_on else 0
        self._loupe.disabled = not self._loupe_on
        Clock.schedule_once(lambda dt: self._center_loupe(), 0)

    def _refresh_cards(self):
        self._card_host.clear_widgets()
        self._card_host.height = dp(0)
        msg = self._session.friendly_message()
        if msg:
            card = PastelCard(
                title=msg,
                subtitle="Allow camera access or try again. Details are in Settings → Debug → View recent log.",
                palette="sky",
                auto_height=True,
                size_hint_y=None,
            )
            self._card_host.add_widget(card)
            row = BoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(48),
                spacing=dp(8),
            )
            retry = PrimaryButton(text="Retry")
            retry.on_press_cb = lambda *_: self._retry_camera()
            row.add_widget(retry)
            settings = PrimaryButton(text="Open settings")
            settings.on_press_cb = lambda *_: open_settings_camera()
            row.add_widget(settings)
            self._card_host.add_widget(row)
            self._card_host.height = dp(220)
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
            self._card_host.height = dp(200)

    def _center_loupe(self, *_a):
        """Place loupe at preview center, above the control stack."""
        d = self._loupe.width or dp(140)
        top = self._card_host.y if self._card_host.height > 0 else self._overlay.top - dp(56)
        bot = self._controls.top if hasattr(self, "_controls") else self._overlay.y + dp(160)
        cy = (top + bot) / 2.0
        cx = self._root.center_x
        self._loupe.pos = (cx - d / 2, cy - d / 2)
        self._loupe.place_pill_inside(self._stage, prefer_below=True)

    def _go(self, name: str):
        if self.manager:
            self.manager.current = name

    def _retry_camera(self):
        self._session.reset()
        self._error_code = None
        self._refresh_cards()
        self._start_camera()

    # --- camera loop -----------------------------------------------------

    def _start_camera(self):
        def _after_perm(ok: bool):
            Clock.schedule_once(lambda dt: self._on_perm(ok), 0)

        request_camera_permission(_after_perm)

    def _on_perm(self, ok: bool):
        self._session.on_permission(ok)
        self._refresh_cards()
        if not ok:
            return

        if self._source is not None:
            try:
                self._source.stop()
            except Exception:
                pass
            self._source = None

        self._source = create_frame_source()
        # Android Preview must live under a widget parent
        if hasattr(self._source, "attach_host"):
            self._source.attach_host(self._root)
        if hasattr(self._source, "set_first_frame_cb"):
            self._source.set_first_frame_cb(
                lambda w, h: self._session.on_first_frame(w, h)
            )

        started = False
        try:
            started = bool(self._source.start())
        except Exception:
            log.exception("camera_event start_exception")
            started = False

        if not started:
            reason = getattr(self._source, "last_error", None) or "start_failed"
            if is_android():
                # Never fall back to synthetic frames on a real phone
                self._session.on_start_result(False, reason)
                self._refresh_cards()
                self._set_status(self._session.friendly_message() or "Camera failed to start")
                return
            # Desktop only: webcam missing → labeled test pattern
            log.warning("camera_event desktop_webcam_failed — synthetic test pattern")
            self._source = FakeFrameSource()
            self._source.start()
            self._session.on_start_result(True)
            self._set_test_pattern_visible(True)
            self._set_status("Test pattern (no webcam)")
        else:
            self._session.on_start_result(True)
            synthetic = bool(getattr(self._source, "is_synthetic", False))
            self._set_test_pattern_visible(synthetic)
            if synthetic:
                self._set_status("Test pattern")

        self._pending_frame = None
        self._blit_scheduled = False
        if self._poll_ev is not None:
            self._poll_ev.cancel()
        # Poll faster than display; blit is latest-frame-wins on Clock
        self._poll_ev = Clock.schedule_interval(self._tick, 1.0 / 30.0)

    def _set_test_pattern_visible(self, visible: bool):
        if hasattr(self, "_test_pattern_lbl"):
            self._test_pattern_lbl.opacity = 1 if visible else 0

    def _stop_camera(self):
        if self._poll_ev is not None:
            self._poll_ev.cancel()
            self._poll_ev = None
        if self._source is not None:
            try:
                self._source.stop()
            except Exception:
                log.exception("camera_event stop_exception")
            self._source = None
        self._session.on_stop()
        self._pending_frame = None
        self._blit_scheduled = False
        self._set_test_pattern_visible(False)

    def _apply_preview_matrix(self):
        """Recompute mat3 from mode + strength and push to the GPU uniform."""
        cvd = self._profile.type if self._profile is not None else None
        mat = matrix_for_mode(
            self._mode, cvd_type=cvd, severity=float(self._preview_severity)
        )
        if hasattr(self, "_stage"):
            self._stage.set_color_matrix(mat)

    def _tick(self, _dt):
        if self._frozen or self._source is None:
            return
        t0 = time.perf_counter()
        frame = self._source.read_latest()
        if frame is None:
            return
        # Latest-frame-wins: overwrite pending; schedule at most one blit
        self._pending_frame = frame
        self._t_recv_ms += (time.perf_counter() - t0) * 1000.0
        fs = getattr(self._source, "frame_size", (0, 0)) or (0, 0)
        self._frame_w, self._frame_h = int(fs[0]), int(fs[1])
        if not self._blit_scheduled:
            self._blit_scheduled = True
            Clock.schedule_once(self._blit_pending, 0)

    def _blit_pending(self, _dt=None):
        self._blit_scheduled = False
        frame = self._pending_frame
        self._pending_frame = None
        if frame is None or self._frozen:
            return
        t0 = time.perf_counter()
        try:
            original = downscale_live(frame, LIVE_LONGEST)
        except Exception:
            log.exception("frame downscale failed")
            return
        self._latest_original = original
        # Upload raw only — GPU mat3 does Corrected / Simulation
        self._stage.set_rgb(original)
        upload = self._stage.last_upload_ms()
        draw_ms = (time.perf_counter() - t0) * 1000.0
        self._t_upload_ms += upload
        self._t_draw_ms += max(0.0, draw_ms - upload)
        self._t_n += 1
        self._note_fps()
        if self._loupe_on:
            self._update_loupe(force_name=False)

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
                if show and self._t_n > 0:
                    n = max(1, self._t_n)
                    self._fps_lbl.text = (
                        f"{self._fps_value:.0f} fps · "
                        f"r{self._t_recv_ms / n:.1f}/"
                        f"u{self._t_upload_ms / n:.1f}/"
                        f"d{self._t_draw_ms / n:.1f} ms"
                    )
                elif show:
                    self._fps_lbl.text = (
                        f"{self._fps_value:.0f} fps · {self._frame_w}×{self._frame_h}"
                    )
                else:
                    self._fps_lbl.text = ""
        if now - self._t_log_t0 >= 5.0 and self._t_n > 0:
            n = self._t_n
            log.info(
                "camera_timing fps=%.1f recv_ms=%.2f upload_ms=%.2f draw_ms=%.2f "
                "python_ms=%.2f size=%sx%s n=%s",
                self._fps_value,
                self._t_recv_ms / n,
                self._t_upload_ms / n,
                self._t_draw_ms / n,
                (self._t_recv_ms + self._t_upload_ms + self._t_draw_ms) / n,
                self._frame_w,
                self._frame_h,
                n,
            )
            self._t_recv_ms = 0.0
            self._t_upload_ms = 0.0
            self._t_draw_ms = 0.0
            self._t_n = 0
            self._t_log_t0 = now

    # --- loupe -----------------------------------------------------------

    def _toggle_loupe(self):
        self.set_loupe_enabled(not self._loupe_on)

    def _on_loupe_move(self, *_a):
        self._loupe.place_pill_inside(self._stage, prefer_below=True)
        self._update_loupe(force_name=True)

    def _update_loupe(self, force_name: bool = False):
        if not self._loupe_on or self._latest_original is None:
            return
        gx, gy = self._loupe.glass_center()
        pix = self._stage.image_to_pixel(gx, gy)
        if pix is None:
            return
        cx, cy = pix
        # Zoom crop from the same CPU original frame (only when loupe is on)
        zoom_rgb = loupe_zoom_crop(self._latest_original, cx, cy, zoom=self._loupe.zoom)
        self._loupe.set_zoom_rgb(zoom_rgb)
        now = time.time()
        if not force_name and (now - self._loupe_name_t) < 0.2:
            return  # ~5 Hz color naming
        self._loupe_name_t = now
        try:
            name, med = name_loupe_color(self._latest_original, cx, cy)
            name = self._smoother.push(name)
            corr = None
            if self._mode == "corrected" and self._profile is not None:
                patch = med.reshape(1, 1, 3)
                corr = render_mode_rgb(
                    patch,
                    "corrected",
                    cvd_type=self._profile.type,
                    severity=self._preview_severity,
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
            self._apply_preview_matrix()
            return
        self._mode = mode
        self._apply_preview_matrix()

    def _on_severity(self, value: float):
        self._preview_severity = severity_for_slider(value)
        if hasattr(self, "_sev_value"):
            self._sev_value.text = f"{strength_percent(self._preview_severity)}"
        self._update_reset()
        # Instant: only recompute matrix + set uniform
        self._apply_preview_matrix()
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
        self._apply_preview_matrix()

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
        # Capture always runs CPU color math once (not the live GPU path)
        base = None
        if self._frozen and getattr(self, "_frozen_original", None) is not None:
            base = self._frozen_original
        elif self._latest_original is not None:
            base = self._latest_original
        elif self._stage.current_rgb() is not None:
            base = self._stage.current_rgb()
        if base is None:
            self._set_status("Nothing to capture yet")
            return
        self._set_status("Saving…")
        mode = self._mode
        sev = float(self._preview_severity)
        cvd = self._profile.type if self._profile is not None else None
        frame = base

        def _work():
            msg = "Couldn't save that photo"
            try:
                if mode == "original" or cvd is None:
                    out = frame
                else:
                    out = render_mode_rgb(frame, mode, cvd_type=cvd, severity=sev)
                msg = save_corrected_image(
                    out, preferred_name=f"ColorSight_Camera_{mode}", fmt="jpg"
                )
            except Exception as exc:
                log.exception("capture failed")
                text = str(exc).strip()
                if text and "/" not in text and "\\" not in text:
                    msg = text

            def _done(_dt=None):
                self._set_status(msg)

            Clock.schedule_once(_done, 0)

        threading.Thread(target=_work, daemon=True).start()
    def _flip(self):
        if self._source is not None:
            self._source.flip()

    def _set_status(self, text: str):
        if hasattr(self, "_status"):
            self._status.text = text or ""

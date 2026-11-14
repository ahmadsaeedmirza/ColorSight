"""Photos screen — gallery image correction with before/after preview."""

from __future__ import annotations

import logging
import threading

import numpy as np
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget

from colorsight.image_pipeline import (
    PREVIEW_LONGEST,
    build_comparison_card,
    load_rgb_uint8,
    render_mode_rgb,
    resize_longest,
    severity_for_slider,
)
from colorsight.photo_io import pick_image, save_corrected_image, share_image
from colorsight.screens.photo_widgets import (
    BeforeAfterViewer,
    LoadingShimmer,
    PhotoModeToolbar,
    PreviewSeverityBar,
    TextLinkButton,
)
from colorsight.storage import profile_path
from colorsight.theme.tokens import Colors, Fonts, Icons, Spacing
from colorsight.widgets import PastelCard, PrimaryButton, RoundIconButton

log = logging.getLogger(__name__)


class PhotosScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="photos", **kwargs)
        self._profile = None
        self._source_path: str | None = None
        self._full_rgb: np.ndarray | None = None
        self._preview_rgb: np.ndarray | None = None
        self._cache: dict[tuple[str, float], np.ndarray] = {}
        self._mode = "corrected"
        self._preview_severity = 0.5
        self._saved_severity = 0.5
        self._sev_ev = None
        self._busy = False
        self._status_clear = None
        self._root = BoxLayout(orientation="vertical")
        self.add_widget(self._root)
        self._build_shell()

    def on_pre_enter(self, *_args):
        self._reload_profile()
        self._rebuild_body()

    # --- profile ---------------------------------------------------------

    def _reload_profile(self):
        app = App.get_running_app()
        path = profile_path()
        profile = None
        if app is not None and getattr(app, "correction_profile", None) is not None:
            profile = app.correction_profile
        elif path.is_file():
            try:
                from core.profile import CorrectionProfile

                profile = CorrectionProfile.load(path)
                if app is not None:
                    app.correction_profile = profile
            except Exception as exc:  # noqa: BLE001
                log.warning("Failed to load correction profile: %s", exc)
                profile = None
        self._profile = profile
        if profile is not None:
            sev = severity_for_slider(float(profile.severity))
            self._saved_severity = sev
            self._preview_severity = sev

    def _sync_strength_ui(self):
        if hasattr(self, "_sev_bar"):
            self._sev_bar.set_value(self._preview_severity, notify=False)
        if hasattr(self, "_sev_value"):
            self._sev_value.text = f"{int(round(self._preview_severity * 100))}"
        self._update_reset_visibility()

    def _update_reset_visibility(self):
        if not hasattr(self, "_reset_btn"):
            return
        differs = abs(self._preview_severity - self._saved_severity) > 0.005
        self._reset_btn.opacity = 1 if differs else 0
        self._reset_btn.disabled = not differs
        self._reset_btn.height = dp(28) if differs else 0

    def _reset_strength(self, *_a):
        self._preview_severity = self._saved_severity
        self._sync_strength_ui()
        self._cache.clear()
        self._schedule_process()

    # --- chrome ----------------------------------------------------------

    def _build_shell(self):
        self._root.clear_widgets()
        header = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(52),
            padding=[dp(Spacing.screen_x), dp(Spacing.sm), dp(Spacing.screen_x), 0],
            spacing=dp(8),
        )
        back = RoundIconButton(icon=Icons.arrow_back, diameter=40)
        back.on_press_cb = lambda *_: self._go("home")
        header.add_widget(back)
        title = Label(
            text="Photos",
            font_name=Fonts.bold,
            font_size=dp(22),
            color=Colors.text,
            halign="left",
            valign="middle",
        )
        title.bind(size=lambda *_: setattr(title, "text_size", title.size))
        header.add_widget(title)
        self._root.add_widget(header)

        self._body = BoxLayout(
            orientation="vertical",
            padding=[
                dp(Spacing.screen_x),
                dp(Spacing.sm),
                dp(Spacing.screen_x),
                dp(Spacing.nav_clearance),
            ],
            spacing=dp(Spacing.sm),
        )
        self._root.add_widget(self._body)

    def _rebuild_body(self):
        self._body.clear_widgets()
        if self._profile is None:
            self._show_no_profile()
            return
        if self._preview_rgb is None:
            self._show_empty_pick()
            return
        self._show_viewer()

    def _go(self, name: str):
        if self.manager:
            self.manager.transition.direction = "right" if name == "home" else "left"
            self.manager.current = name
            parent = self.manager.parent
            if hasattr(parent, "set_nav_active"):
                parent.set_nav_active(name)

    # --- empty states ----------------------------------------------------

    def _show_no_profile(self):
        card = PastelCard(
            title="Take the color test first",
            subtitle="Take the color test first so we can correct photos for your eyes",
            palette="pink",
            auto_height=True,
            size_hint_y=None,
        )
        self._body.add_widget(card)
        btn = PrimaryButton(text="Go to Vision Test")
        btn.on_press_cb = lambda *_: self._go("test")
        self._body.add_widget(btn)
        self._body.add_widget(Widget())

    def _show_empty_pick(self):
        card = PastelCard(
            title="Choose a photo",
            subtitle="Pick a JPG, PNG, or WebP from your gallery. We'll correct it for your eyes.",
            palette="pink",
            auto_height=True,
            size_hint_y=None,
        )
        self._body.add_widget(card)
        btn = PrimaryButton(text="Choose a photo")
        btn.on_press_cb = lambda *_: self._pick()
        self._body.add_widget(btn)
        tip = Label(
            text="Your saved profile stays unchanged while you preview.",
            font_name=Fonts.regular,
            font_size=dp(12),
            color=Colors.text_muted,
            size_hint_y=None,
            height=dp(28),
        )
        self._body.add_widget(tip)
        self._body.add_widget(Widget())

    # --- viewer ----------------------------------------------------------

    def _show_viewer(self):
        self._viewer = BeforeAfterViewer(size_hint=(1, 1))
        self._viewer.split = 0.5
        self._body.add_widget(self._viewer)

        self._shimmer = LoadingShimmer()
        self._body.add_widget(self._shimmer)

        # Strength row
        strength_hdr = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(22),
            spacing=dp(8),
        )
        strength_hdr.add_widget(
            Label(
                text="Strength",
                font_name=Fonts.semibold,
                font_size=dp(13),
                color=Colors.text,
                size_hint=(None, 1),
                width=dp(72),
                halign="left",
                valign="middle",
            )
        )
        strength_hdr.add_widget(Widget())
        self._sev_value = Label(
            text=f"{int(round(self._preview_severity * 100))}",
            font_name=Fonts.semibold,
            font_size=dp(13),
            color=Colors.text,
            size_hint=(None, 1),
            width=dp(36),
        )
        strength_hdr.add_widget(self._sev_value)
        self._body.add_widget(strength_hdr)

        hint = Label(
            text="Starts at your test result. Move it to fine-tune the preview.",
            font_name=Fonts.regular,
            font_size=dp(11),
            color=Colors.text_muted,
            size_hint_y=None,
            height=dp(20),
            halign="left",
            valign="middle",
        )
        hint.bind(size=lambda *_: setattr(hint, "text_size", hint.size))
        self._body.add_widget(hint)

        self._sev_bar = PreviewSeverityBar(value=self._preview_severity)
        self._sev_bar.change_cb = self._on_severity
        self._body.add_widget(self._sev_bar)

        self._reset_btn = TextLinkButton(text="Reset to my result")
        self._reset_btn.bind(on_release=self._reset_strength)
        self._body.add_widget(self._reset_btn)
        self._update_reset_visibility()

        self._sim_hint = Label(
            text="Adjust the strength until it matches how you see it.",
            font_name=Fonts.regular,
            font_size=dp(11),
            color=Colors.text_muted,
            size_hint_y=None,
            height=dp(0),
            opacity=0,
            halign="left",
            valign="middle",
        )
        self._sim_hint.bind(size=lambda *_: setattr(self._sim_hint, "text_size", self._sim_hint.size))
        self._body.add_widget(self._sim_hint)

        self._toolbar = PhotoModeToolbar()
        self._toolbar.mode_cb = self._on_mode
        self._toolbar.save_cb = lambda: self._export_current(share=False)
        self._toolbar.share_cb = lambda: self._export_current(share=True)
        self._toolbar.mode = self._mode
        self._body.add_widget(self._toolbar)
        self._update_sim_hint()

        actions = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(48),
            spacing=dp(8),
        )
        change = PrimaryButton(text="Choose another")
        change.bg_color = (1, 1, 1, 1)
        change.text_color = Colors.text
        change.on_press_cb = lambda *_: self._pick()
        actions.add_widget(change)

        export = PrimaryButton(text="Export comparison")
        export.on_press_cb = lambda *_: self._export_comparison(share=False)
        actions.add_widget(export)
        self._body.add_widget(actions)

        self._status = Label(
            text="",
            font_name=Fonts.medium,
            font_size=dp(13),
            color=Colors.accent_blue,
            size_hint_y=None,
            height=dp(22),
        )
        self._body.add_widget(self._status)

        self._sync_strength_ui()
        self._push_viewer_images()

    def _update_sim_hint(self):
        if not hasattr(self, "_sim_hint"):
            return
        show = self._mode == "simulation"
        self._sim_hint.opacity = 1 if show else 0
        self._sim_hint.height = dp(20) if show else 0

    def _push_viewer_images(self):
        if self._preview_rgb is None or not hasattr(self, "_viewer"):
            return
        right = None
        if self._mode in ("corrected", "simulation"):
            right = self._cache_get(self._mode)
        if right is None and self._mode != "original":
            self._schedule_process()
            # Keep mode so divider intent is clear; use original as placeholder right
            # until cache fills (avoids silently looking like a no-op correction).
            self._viewer.set_images(self._preview_rgb, None, "original")
            return
        self._viewer.set_images(self._preview_rgb, right, self._mode)

    # --- pick / process --------------------------------------------------

    def _pick(self):
        pick_image(self._on_picked, on_error=self._on_pick_error)

    def _on_pick_error(self, msg: str):
        log.warning("pick error: %s", msg)
        Clock.schedule_once(lambda dt: self._set_status("Couldn't open the photo picker"), 0)

    def _on_picked(self, path: str | None):
        def _apply(_dt=None):
            if not path:
                return
            try:
                full = load_rgb_uint8(path)
            except Exception:  # noqa: BLE001
                log.exception("load failed")
                self._set_status("Couldn't read that image")
                return
            self._source_path = path
            self._full_rgb = full
            self._preview_rgb = resize_longest(full, PREVIEW_LONGEST)
            self._cache.clear()
            self._mode = "corrected"
            # Re-sync strength from saved profile whenever a new photo is loaded
            if self._profile is not None:
                self._preview_severity = severity_for_slider(float(self._profile.severity))
                self._saved_severity = self._preview_severity
            self._rebuild_body()
            self._schedule_process()

        Clock.schedule_once(_apply, 0)

    def _on_mode(self, mode: str):
        self._mode = mode
        self._update_sim_hint()
        self._push_viewer_images()

    def _on_severity(self, value: float):
        self._preview_severity = severity_for_slider(float(value))
        if hasattr(self, "_sev_value"):
            self._sev_value.text = f"{int(round(self._preview_severity * 100))}"
        self._update_reset_visibility()
        # Drop caches that do not match the new strength
        key_sev = round(self._preview_severity, 3)
        self._cache = {k: v for k, v in self._cache.items() if abs(k[1] - key_sev) < 1e-6}
        if self._sev_ev is not None:
            self._sev_ev.cancel()
        self._sev_ev = Clock.schedule_once(lambda dt: self._schedule_process(), 0.10)

    def _cache_key(self, kind: str) -> tuple[str, float]:
        return (kind, round(self._preview_severity, 3))

    def _cache_get(self, kind: str) -> np.ndarray | None:
        return self._cache.get(self._cache_key(kind))

    def _schedule_process(self):
        if self._preview_rgb is None or self._profile is None:
            return
        need = []
        if self._cache_get("corrected") is None:
            need.append("corrected")
        if self._cache_get("simulation") is None:
            need.append("simulation")
        if not need:
            self._push_viewer_images()
            return
        self._busy = True
        if hasattr(self, "_shimmer"):
            self._shimmer.start()
        preview = self._preview_rgb.copy()
        sev = float(self._preview_severity)
        cvd = self._profile.type
        kinds = list(need)

        def _work():
            out: dict[str, np.ndarray] = {}
            try:
                for kind in kinds:
                    out[kind] = render_mode_rgb(preview, kind, cvd_type=cvd, severity=sev)
            except Exception:
                log.exception("preview process failed")
                out = {}

            def _done(_dt=None):
                for k, arr in out.items():
                    self._cache[(k, round(sev, 3))] = arr
                self._busy = False
                if hasattr(self, "_shimmer"):
                    self._shimmer.stop()
                self._push_viewer_images()

            Clock.schedule_once(_done, 0)

        threading.Thread(target=_work, daemon=True).start()

    # --- save / share / comparison ---------------------------------------

    def _export_current(self, *, share: bool):
        if self._full_rgb is None or self._profile is None:
            return
        if self._busy:
            self._set_status("Still preparing preview…")
            return
        self._set_status("Sharing…" if share else "Saving…")
        if hasattr(self, "_shimmer"):
            self._shimmer.start()
        full = self._full_rgb
        sev = float(self._preview_severity)
        cvd = self._profile.type
        mode = self._mode
        prefix = {"original": "Original", "corrected": "Corrected", "simulation": "Simulation"}.get(
            mode, "ColorSight"
        )

        def _work():
            msg = "Couldn't save that photo"
            try:
                rgb = render_mode_rgb(full, mode, cvd_type=cvd, severity=sev)
                name = f"ColorSight_{prefix}"
                if share:
                    msg = share_image(rgb, preferred_name=name, fmt="jpg")
                else:
                    msg = save_corrected_image(rgb, preferred_name=name, fmt="jpg")
            except Exception:
                log.exception("export failed")

            def _done(_dt=None):
                if hasattr(self, "_shimmer"):
                    self._shimmer.stop()
                self._set_status(msg)

            Clock.schedule_once(_done, 0)

        threading.Thread(target=_work, daemon=True).start()

    def _export_comparison(self, *, share: bool):
        if self._full_rgb is None or self._profile is None:
            return
        if self._busy:
            self._set_status("Still preparing preview…")
            return
        self._set_status("Sharing…" if share else "Saving…")
        if hasattr(self, "_shimmer"):
            self._shimmer.start()
        full = self._full_rgb
        sev = float(self._preview_severity)
        cvd = self._profile.type

        def _work():
            msg = "Couldn't save that photo"
            try:
                sim = render_mode_rgb(full, "simulation", cvd_type=cvd, severity=sev)
                card = build_comparison_card(full, sim)
                name = "ColorSight_HowISeeIt"
                if share:
                    msg = share_image(card, preferred_name=name, fmt="jpg")
                else:
                    msg = save_corrected_image(card, preferred_name=name, fmt="jpg")
            except Exception:
                log.exception("comparison export failed")

            def _done(_dt=None):
                if hasattr(self, "_shimmer"):
                    self._shimmer.stop()
                self._set_status(msg)

            Clock.schedule_once(_done, 0)

        threading.Thread(target=_work, daemon=True).start()

    def _set_status(self, text: str):
        if hasattr(self, "_status"):
            self._status.text = text
        if self._status_clear is not None:
            self._status_clear.cancel()
        sticky = any(k in text.lower() for k in ("gallery", "share sheet"))
        if text and not sticky:
            self._status_clear = Clock.schedule_once(
                lambda dt: setattr(self._status, "text", "") if hasattr(self, "_status") else None,
                3.5,
            )

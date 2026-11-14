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

from colorsight.image_pipeline import PREVIEW_LONGEST, load_rgb_uint8, resize_longest
from colorsight.photo_io import pick_image, save_corrected_image
from colorsight.screens.photo_widgets import (
    BeforeAfterViewer,
    LoadingShimmer,
    PhotoModeToolbar,
    PreviewSeverityBar,
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
            self._preview_severity = float(profile.severity)

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
        self._body.add_widget(self._viewer)

        self._shimmer = LoadingShimmer()
        self._body.add_widget(self._shimmer)

        sev_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(44),
            spacing=dp(8),
        )
        sev_lbl = Label(
            text="Severity",
            font_name=Fonts.medium,
            font_size=dp(13),
            color=Colors.text_muted,
            size_hint=(None, 1),
            width=dp(72),
            halign="left",
            valign="middle",
        )
        sev_lbl.bind(size=lambda *_: setattr(sev_lbl, "text_size", sev_lbl.size))
        sev_row.add_widget(sev_lbl)
        self._sev_bar = PreviewSeverityBar(value=self._preview_severity)
        self._sev_bar.change_cb = self._on_severity
        sev_row.add_widget(self._sev_bar)
        self._sev_value = Label(
            text=f"{int(round(self._preview_severity * 100))}",
            font_name=Fonts.semibold,
            font_size=dp(13),
            color=Colors.text,
            size_hint=(None, 1),
            width=dp(36),
        )
        sev_row.add_widget(self._sev_value)
        self._body.add_widget(sev_row)

        self._toolbar = PhotoModeToolbar()
        self._toolbar.mode_cb = self._on_mode
        self._toolbar.save_cb = self._on_save
        # Assign mode after mode_cb so the first sync does not call a missing handler
        self._toolbar.mode = self._mode
        self._body.add_widget(self._toolbar)

        change = PrimaryButton(text="Choose another photo")
        change.bg_color = (1, 1, 1, 1)
        change.text_color = Colors.text
        change.on_press_cb = lambda *_: self._pick()
        self._body.add_widget(change)

        self._status = Label(
            text="",
            font_name=Fonts.medium,
            font_size=dp(13),
            color=Colors.accent_blue,
            size_hint_y=None,
            height=dp(22),
        )
        self._body.add_widget(self._status)

        self._push_viewer_images()

    def _push_viewer_images(self):
        if self._preview_rgb is None:
            return
        right = None
        if self._mode == "corrected":
            right = self._cache_get("corrected")
        elif self._mode == "simulation":
            right = self._cache_get("simulation")
        if right is None and self._mode != "original":
            self._schedule_process()
            self._viewer.set_images(self._preview_rgb, self._preview_rgb, "original")
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
            except Exception as exc:  # noqa: BLE001
                log.exception("load failed")
                self._set_status("Couldn't read that image")
                return
            self._source_path = path
            self._full_rgb = full
            self._preview_rgb = resize_longest(full, PREVIEW_LONGEST)
            self._cache.clear()
            self._mode = "corrected"
            self._rebuild_body()
            self._schedule_process()

        Clock.schedule_once(_apply, 0)

    def _on_mode(self, mode: str):
        self._mode = mode
        self._push_viewer_images()

    def _on_severity(self, value: float):
        self._preview_severity = float(value)
        if hasattr(self, "_sev_value"):
            self._sev_value.text = f"{int(round(value * 100))}"
        # Invalidate severity-dependent cache entries
        self._cache = {k: v for k, v in self._cache.items() if abs(k[1] - value) < 1e-6}
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
        # Always ensure current mode is ready; cache both for instant toggle
        if not need and self._mode != "original":
            self._push_viewer_images()
            return
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
            from core.engine import apply_correction, apply_simulation
            from core.profile import CorrectionProfile

            out: dict[str, np.ndarray] = {}
            try:
                if "corrected" in kinds:
                    tmp = CorrectionProfile.create(cvd, sev)
                    out["corrected"] = apply_correction(preview, tmp)
                if "simulation" in kinds:
                    out["simulation"] = apply_simulation(preview, cvd, sev)
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

    # --- save ------------------------------------------------------------

    def _on_save(self):
        if self._full_rgb is None or self._profile is None:
            return
        if self._busy:
            self._set_status("Still preparing preview…")
            return
        self._set_status("Saving…")
        if hasattr(self, "_shimmer"):
            self._shimmer.start()
        full = self._full_rgb
        sev = float(self._preview_severity)
        cvd = self._profile.type

        def _work():
            from core.engine import apply_correction
            from core.profile import CorrectionProfile

            msg = "Couldn't save that photo"
            try:
                tmp = CorrectionProfile.create(cvd, sev)
                corrected = apply_correction(full, tmp)
                msg = save_corrected_image(corrected, fmt="jpg")
            except Exception:
                log.exception("save failed")

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
        if text and "gallery" not in text.lower():
            self._status_clear = Clock.schedule_once(
                lambda dt: setattr(self._status, "text", "") if hasattr(self, "_status") else None,
                3.5,
            )

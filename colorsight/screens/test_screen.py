"""Color vision screening — checklist → Trivector CCT → hue arrange → results."""

from __future__ import annotations

import logging

import numpy as np
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from core import (
    NORMAL_CUTOFF,
    TrivectorSession,
    apply_simulation,
    hue_tile_colors,
    score_trivector,
    severity_label,
)
from colorsight.theme.tokens import Colors, Fonts, Icons, Spacing
from colorsight.widgets import PastelCard, PrimaryButton, RoundIconButton
from colorsight.screens.test_widgets import (
    ArrowPad,
    AxisBars,
    HueStrip,
    PillProgressBar,
    SeverityBar,
    numpy_to_texture,
)

log = logging.getLogger("colorsight")

TRIAL_TIMEOUT_S = 6.0
STIM_SIZE = 256
DISPLAY_DP = 190  # ~30 mm Landolt C at phone DPI


class TestScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="test", **kwargs)
        self._phase = "intro"
        self._session: TrivectorSession | None = None
        self._trial = None
        self._result = None
        self._hue_strip = None
        self._stim_image = None
        self._progress = None
        self._timeout_ev = None
        self._mode = "phone"
        self._body = BoxLayout(orientation="vertical")
        self.add_widget(self._body)
        self.bind(on_pre_enter=self._on_enter)
        self._show_checklist()

    def _on_enter(self, *_a):
        if self._phase in ("intro", "checklist", "results"):
            self._show_checklist()

    def _clear(self):
        self._cancel_timeout()
        self._body.clear_widgets()

    def _cancel_timeout(self):
        if self._timeout_ev is not None:
            self._timeout_ev.cancel()
            self._timeout_ev = None

    def _header(self, title: str, show_back=True):
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(44))
        if show_back:
            btn = RoundIconButton(icon=Icons.arrow_back, diameter=40)
            btn.bg_color = Colors.surface
            btn.icon_color = Colors.text
            btn.on_press_cb = lambda *_: self._go_home()
            row.add_widget(btn)
        title_lbl = Label(
            text=title,
            font_name=Fonts.bold,
            font_size=dp(20),
            color=Colors.text,
            halign="left",
            valign="middle",
        )
        title_lbl.bind(size=lambda *_: setattr(title_lbl, "text_size", title_lbl.size))
        row.add_widget(title_lbl)
        return row

    def _go_home(self, *_a):
        self._phase = "checklist"
        self._cancel_timeout()
        if self.manager:
            self.manager.current = "home"

    def _padded_scroll(self, *children):
        scroll = ScrollView(do_scroll_x=False, bar_width=0)
        content = BoxLayout(
            orientation="vertical",
            padding=[
                dp(Spacing.screen_x),
                dp(Spacing.md),
                dp(Spacing.screen_x),
                dp(Spacing.nav_clearance),
            ],
            spacing=dp(Spacing.md),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))
        for c in children:
            content.add_widget(c)
        scroll.add_widget(content)
        return scroll

    # ── Pre-test checklist ─────────────────────────────────────────────
    def _show_checklist(self):
        self._phase = "checklist"
        self._clear()
        card = PastelCard(
            title="Before you start",
            subtitle=(
                "Set brightness high. Turn off night mode, blue-light filters, "
                "and dark-mode color tints. Hold the phone about 40 cm away in "
                "normal room light. Wear your usual glasses."
            ),
            palette="yellow",
            size_hint_y=None,
            height=dp(180),
            interactive=False,
        )
        about = PastelCard(
            title="Cambridge-style Trivector",
            subtitle=(
                "You'll judge the gap in a Landolt C on three color axes "
                "(~24–40 trials). Then a short hue sort. Screening only — "
                "not a medical diagnosis. Screen colors vary by phone."
            ),
            palette="mint",
            size_hint_y=None,
            height=dp(160),
            interactive=False,
        )
        start = PrimaryButton(text="Start test")
        start.bg_color = Colors.accent_blue
        start.on_press_cb = lambda *_: self._start_trivector()
        self._body.add_widget(
            self._padded_scroll(
                self._header("Vision Test"),
                card,
                about,
                start,
            )
        )

    def _start_trivector(self):
        self._clear()
        wait = Label(
            text="Preparing trials…",
            font_name=Fonts.medium,
            font_size=dp(16),
            color=Colors.text_muted,
        )
        self._body.add_widget(wait)
        Clock.schedule_once(lambda dt: self._begin_trivector(), 0.05)

    def _begin_trivector(self):
        self._session = TrivectorSession(mode=self._mode, seed=42)
        self._result = None
        self._show_trial()

    # ── Trivector trials ───────────────────────────────────────────────
    def _show_trial(self):
        self._phase = "trivector"
        self._clear()
        assert self._session is not None
        if self._session.finished:
            self._show_hue()
            return

        trial = self._session.next_trial(size=STIM_SIZE)
        if trial is None:
            self._show_hue()
            return
        self._trial = trial

        progress = PillProgressBar(progress=self._session.progress)
        self._progress = progress
        step = Label(
            text=f"Trial  ·  {trial.axis} axis",
            font_name=Fonts.semibold,
            font_size=dp(14),
            color=Colors.text_muted,
            size_hint_y=None,
            height=dp(22),
            halign="left",
        )
        step.bind(size=lambda *_: setattr(step, "text_size", step.size))

        stim_img = Image(size_hint_y=None, height=dp(DISPLAY_DP), fit_mode="contain")
        stim_img.texture = numpy_to_texture(trial.stimulus.image)
        self._stim_image = stim_img

        prompt = Label(
            text="Which way does the gap open?",
            font_name=Fonts.bold,
            font_size=dp(18),
            color=Colors.text,
            size_hint_y=None,
            height=dp(28),
            halign="left",
        )
        prompt.bind(size=lambda *_: setattr(prompt, "text_size", prompt.size))

        pad = ArrowPad(on_orient=self._on_orient, on_cant_see=self._on_cant_see)

        self._body.add_widget(
            self._padded_scroll(
                self._header("Vision Test"),
                step,
                progress,
                stim_img,
                prompt,
                pad,
            )
        )
        self._timeout_ev = Clock.schedule_once(
            lambda dt: self._on_cant_see(), TRIAL_TIMEOUT_S
        )

    def _on_orient(self, orient: str):
        self._commit(orient)

    def _on_cant_see(self, *_a):
        self._commit(None)

    def _commit(self, response: str | None):
        self._cancel_timeout()
        if self._session is None or self._trial is None:
            return
        if self._phase != "trivector":
            return
        self._session.answer(self._trial, response)
        self._trial = None
        self._show_trial()

    # ── Hue arrangement ────────────────────────────────────────────────
    def _show_hue(self):
        self._phase = "hue"
        self._clear()
        colors = hue_tile_colors(7)
        intro = PastelCard(
            title="Hue arrangement",
            subtitle="Tap two tiles to swap them. Arrange colors from red → violet (rainbow order).",
            palette="lavender",
            size_hint_y=None,
            height=dp(130),
            interactive=False,
        )
        self._hue_strip = HueStrip(colors)
        self._hue_strip.shuffle(np.random.default_rng(11))

        done = PrimaryButton(text="Continue to results")
        done.bg_color = Colors.accent_blue
        done.on_press_cb = lambda *_: self._finish()

        progress = PillProgressBar(progress=0.92)
        self._body.add_widget(
            self._padded_scroll(
                self._header("Almost done"),
                progress,
                intro,
                self._hue_strip,
                Widget(size_hint_y=None, height=dp(8)),
                done,
            )
        )

    def _finish(self):
        assert self._session is not None
        order = self._hue_strip.order if self._hue_strip else list(range(7))
        self._result = score_trivector(self._session, hue_order=order)
        self._show_results()

    # ── Results ────────────────────────────────────────────────────────
    def _show_results(self):
        self._phase = "results"
        self._clear()
        r = self._result
        assert r is not None

        sev_pct = int(round(r.severity * 100))
        sev_lbl = severity_label(r.severity) if not r.is_normal else "none"
        if r.is_inconclusive:
            palette = "lavender"
            sub = f"Could not clearly classify  ·  Severity {sev_lbl} ({sev_pct})"
        elif r.is_normal:
            palette = "mint"
            sub = f"Severity {sev_lbl}  ·  {sev_pct}/100"
        else:
            palette = "peach"
            sub = f"Severity {sev_lbl}  ·  {sev_pct}/100"

        result_card = PastelCard(
            title=r.label,
            subtitle=sub,
            palette=palette,
            size_hint_y=None,
            height=dp(120),
            interactive=False,
        )

        sev_title = Label(
            text="Severity",
            font_name=Fonts.semibold,
            font_size=dp(14),
            color=Colors.text_muted,
            size_hint_y=None,
            height=dp(22),
            halign="left",
        )
        sev_title.bind(size=lambda *_: setattr(sev_title, "text_size", sev_title.size))
        sev_bar = SeverityBar(value=r.severity)

        axis_title = Label(
            text="Axis thresholds (protan / deutan / tritan)",
            font_name=Fonts.semibold,
            font_size=dp(14),
            color=Colors.text_muted,
            size_hint_y=None,
            height=dp(22),
            halign="left",
        )
        axis_title.bind(size=lambda *_: setattr(axis_title, "text_size", axis_title.size))
        axis_bars = AxisBars(thresholds=r.thresholds, cutoffs=NORMAL_CUTOFF)

        disclaimer = PastelCard(
            title="Not a medical diagnosis",
            subtitle=(
                "ColorSight is a screening tool only. Results can vary with phone "
                "calibration, brightness, and ambient light. See an eye-care professional "
                "for a clinical assessment."
            ),
            palette="yellow",
            size_hint_y=None,
            height=dp(150),
            interactive=False,
        )

        demo_title = Label(
            text="Before / after simulation",
            font_name=Fonts.bold,
            font_size=dp(16),
            color=Colors.text,
            size_hint_y=None,
            height=dp(28),
            halign="left",
        )
        demo_title.bind(size=lambda *_: setattr(demo_title, "text_size", demo_title.size))
        demo = self._demo_pair(r)

        save = PrimaryButton(text="Save my profile")
        save.bg_color = Colors.accent_blue
        save.on_press_cb = self._save_profile

        again = PrimaryButton(text="Retake test")
        again.bg_color = Colors.surface
        again.text_color = Colors.text
        again.on_press_cb = lambda *_: self._show_checklist()

        self._save_status = Label(
            text="",
            font_name=Fonts.medium,
            font_size=dp(13),
            color=Colors.text_muted,
            size_hint_y=None,
            height=dp(22),
        )

        self._body.add_widget(
            self._padded_scroll(
                self._header("Your results"),
                result_card,
                sev_title,
                sev_bar,
                axis_title,
                axis_bars,
                disclaimer,
                demo_title,
                demo,
                save,
                self._save_status,
                again,
            )
        )

    def _make_swatch_rgb(self, width: int, height: int = 72) -> np.ndarray:
        w = max(6, int(width))
        h = int(height)
        demo = np.zeros((h, w, 3), dtype=np.uint8)
        bands = [
            (220, 40, 40),
            (40, 180, 70),
            (40, 90, 220),
            (230, 200, 40),
            (180, 50, 180),
            (40, 180, 180),
        ]
        n = len(bands)
        for i, col in enumerate(bands):
            start = (i * w) // n
            end = ((i + 1) * w) // n
            demo[:, start:end] = col
        return demo

    def _demo_pair(self, result) -> BoxLayout:
        row = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None, height=dp(180))

        def _attach(title: str, kind: str):
            lbl = Label(
                text=title,
                font_name=Fonts.medium,
                font_size=dp(12),
                color=Colors.text_muted,
                size_hint_y=None,
                height=dp(18),
                halign="left",
            )
            lbl.bind(size=lambda *_ , L=lbl: setattr(L, "text_size", L.size))
            img = Image(size_hint_y=None, height=dp(64), fit_mode="fill")

            def _fill(*_a, image=img, which=kind):
                w = max(64, int(image.width) if image.width > 1 else 320)
                demo = self._make_swatch_rgb(w, 72)
                if which == "sim" and not result.is_normal and not result.is_inconclusive:
                    arr = apply_simulation(demo, result.classification, result.severity)
                elif which == "sim" and result.is_inconclusive:
                    arr = apply_simulation(demo, "deuteranopia", max(0.3, result.severity))
                else:
                    arr = demo
                image.texture = numpy_to_texture(arr)

            img.bind(size=_fill)
            Clock.schedule_once(lambda dt: _fill(), 0)
            row.add_widget(lbl)
            row.add_widget(img)

        _attach("Original", "orig")
        _attach("As simulated for your result", "sim")
        return row

    def _save_profile(self, *_a):
        if self._result is None:
            return
        from colorsight.storage import profile_path

        profile = self._result.to_profile()
        path = profile_path()
        profile.save(path)
        app = App.get_running_app()
        if app is not None:
            app.correction_profile = profile
        log.info("Correction profile saved to %s", path)
        self._save_status.text = "Your color profile has been saved"
        self._save_status.color = Colors.accent_blue

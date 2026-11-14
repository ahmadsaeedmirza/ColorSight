"""Color vision screening test — intro → plates → hue arrange → results."""

from __future__ import annotations

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
    DEFAULT_BATTERY,
    apply_simulation,
    generate_battery,
    hue_tile_colors,
    make_answers,
    score_screening,
)
from colorsight.storage import profile_path
from colorsight.theme.tokens import Colors, Fonts, Icons, Spacing
from colorsight.widgets import PastelCard, PrimaryButton, RoundIconButton
from colorsight.screens.test_widgets import HueStrip, Numpad, PillProgressBar, numpy_to_texture


class TestScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="test", **kwargs)
        self._phase = "intro"
        self._battery = []
        self._index = 0
        self._responses: list = []
        self._answer_buf = ""
        self._hue_strip = None
        self._result = None
        self._plate_image = None
        self._answer_label = None
        self._progress = None
        self._body = BoxLayout(orientation="vertical")
        self.add_widget(self._body)
        self.bind(on_pre_enter=self._on_enter)
        self._show_intro()

    def _on_enter(self, *_a):
        # Reset to intro each time user opens Test (unless mid-flow — keep mid-flow)
        if self._phase in ("intro", "results"):
            self._show_intro()

    def _clear(self):
        self._body.clear_widgets()

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
        self._phase = "intro"
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

    # ── Intro ──────────────────────────────────────────────────────────
    def _show_intro(self):
        self._phase = "intro"
        self._clear()
        card = PastelCard(
            title="About this screening",
            subtitle=(
                "You'll see 14 original color plates (not medical Ishihara prints), "
                "then sort a short rainbow. Results estimate a correction profile — "
                "not a clinical diagnosis. Screen colors vary by phone."
            ),
            palette="yellow",
            size_hint_y=None,
            height=dp(170),
            interactive=False,
        )
        tips = PastelCard(
            title="Tips",
            subtitle="Sit in normal room light. Hold the phone ~40 cm away. Answer what you see — guessing is OK.",
            palette="mint",
            size_hint_y=None,
            height=dp(120),
            interactive=False,
        )
        start = PrimaryButton(text="Start test")
        start.bg_color = Colors.accent_blue
        start.on_press_cb = lambda *_: self._start_test()
        self._body.add_widget(
            self._padded_scroll(
                self._header("Vision Test"),
                card,
                tips,
                start,
            )
        )

    def _start_test(self):
        # Generate plates (may take a moment) — defer one frame for UI
        self._clear()
        wait = Label(
            text="Preparing plates…",
            font_name=Fonts.medium,
            font_size=dp(16),
            color=Colors.text_muted,
        )
        self._body.add_widget(wait)
        Clock.schedule_once(lambda dt: self._begin_plates(), 0.05)

    def _begin_plates(self):
        self._battery = generate_battery(DEFAULT_BATTERY, size=360, seed=42)
        self._index = 0
        self._responses = []
        self._answer_buf = ""
        self._show_plate()

    # ── Plates ─────────────────────────────────────────────────────────
    def _show_plate(self):
        self._phase = "plate"
        self._clear()
        self._answer_buf = ""
        total = len(self._battery)
        rendered = self._battery[self._index]
        spec, img = rendered.spec, rendered.image

        progress = PillProgressBar(progress=(self._index) / total)
        self._progress = progress
        step = Label(
            text=f"Plate {self._index + 1} of {total}",
            font_name=Fonts.semibold,
            font_size=dp(14),
            color=Colors.text_muted,
            size_hint_y=None,
            height=dp(22),
            halign="left",
        )
        step.bind(size=lambda *_: setattr(step, "text_size", step.size))

        plate_img = Image(size_hint_y=None, height=dp(260), fit_mode="contain")
        plate_img.texture = numpy_to_texture(img)
        self._plate_image = plate_img

        prompt = Label(
            text="What number do you see?",
            font_name=Fonts.bold,
            font_size=dp(18),
            color=Colors.text,
            size_hint_y=None,
            height=dp(28),
            halign="left",
        )
        prompt.bind(size=lambda *_: setattr(prompt, "text_size", prompt.size))

        self._answer_label = Label(
            text="—",
            font_name=Fonts.bold,
            font_size=dp(28),
            color=Colors.text,
            size_hint_y=None,
            height=dp(36),
        )

        pad = Numpad(
            on_digit=self._on_digit,
            on_clear=self._on_clear,
            on_cant_see=self._on_cant_see,
            on_submit=self._on_submit_answer,
        )

        self._body.add_widget(
            self._padded_scroll(
                self._header("Vision Test"),
                step,
                progress,
                plate_img,
                prompt,
                self._answer_label,
                pad,
            )
        )

    def _on_digit(self, n: int):
        if len(self._answer_buf) >= 1:
            self._answer_buf = str(n)
        else:
            self._answer_buf += str(n)
        self._answer_label.text = self._answer_buf

    def _on_clear(self):
        self._answer_buf = ""
        self._answer_label.text = "—"

    def _on_cant_see(self):
        self._commit(None)

    def _on_submit_answer(self):
        if not self._answer_buf:
            return
        self._commit(int(self._answer_buf))

    def _commit(self, value: int | None):
        self._responses.append(value)
        self._index += 1
        if self._index >= len(self._battery):
            self._show_hue()
        else:
            self._show_plate()

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
        specs = [p.spec for p in self._battery]
        answers = make_answers(specs, self._responses)
        order = self._hue_strip.order if self._hue_strip else list(range(7))
        self._result = score_screening(answers, hue_order=order)
        self._show_results()

    # ── Results ────────────────────────────────────────────────────────
    def _show_results(self):
        self._phase = "results"
        self._clear()
        r = self._result

        sev_pct = int(round(r.severity * 100))
        if r.is_inconclusive:
            palette = "lavender"
            sub = f"Could not clearly classify  ·  Matched normal on {r.plate_correct}/{r.plate_total}"
        elif r.is_normal:
            palette = "mint"
            sub = f"Estimated severity {sev_pct}%  ·  Plates {r.plate_correct}/{r.plate_total}"
        else:
            palette = "peach"
            sub = f"Estimated severity {sev_pct}%  ·  Plates {r.plate_correct}/{r.plate_total}"
        result_card = PastelCard(
            title=r.label,
            subtitle=sub,
            palette=palette,
            size_hint_y=None,
            height=dp(120),
            interactive=False,
        )

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
        again.on_press_cb = lambda *_: self._show_intro()

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
                disclaimer,
                demo_title,
                demo,
                save,
                self._save_status,
                again,
            )
        )

    def _make_swatch_rgb(self, width: int, height: int = 72) -> np.ndarray:
        """Full-width band swatch with no leftover black column."""
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
        profile = self._result.to_profile()
        path = profile_path()
        profile.save(path)
        app = App.get_running_app()
        if app is not None:
            app.correction_profile = profile
        # Friendly copy only — path stays in logs/docs
        import logging

        logging.getLogger("colorsight").info("Correction profile saved to %s", path)
        self._save_status.text = "Your color profile has been saved"
        self._save_status.color = Colors.accent_blue

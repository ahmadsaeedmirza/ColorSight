"""Profile screen — saved correction, fine-tune (only place that overwrites profile)."""

from __future__ import annotations

import logging
from datetime import datetime

import numpy as np
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from colorsight.image_pipeline import severity_for_slider, strength_percent
from colorsight.screens.confirm_sheet import ConfirmSheet
from colorsight.screens.photo_widgets import PreviewSeverityBar, TextLinkButton, rgb_to_texture
from colorsight.screens.test_widgets import AxisBars, SeverityBar, numpy_to_texture
from colorsight.storage import profile_path
from colorsight.theme.tokens import Colors, Fonts, Icons, Spacing
from colorsight.widgets import PastelCard, PrimaryButton, RoundIconButton
from core.engine import apply_simulation
from core.trivector import severity_label

log = logging.getLogger(__name__)

_TYPE_WORDS = {
    "protanopia": "Protan (red-weak)",
    "deuteranopia": "Deutan (green-weak)",
    "tritanopia": "Tritan (blue-yellow)",
    "normal": "Typical color vision",
    "inconclusive": "Inconclusive result",
}


def profile_plain_label(profile) -> str:
    if getattr(profile, "label", None):
        return str(profile.label)
    return _TYPE_WORDS.get(profile.type.value, profile.type.value)


def _demo_swatch(width: int, height: int = 64) -> np.ndarray:
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
        demo[:, (i * w) // n : ((i + 1) * w) // n] = col
    return demo


class ProfileScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="profile", **kwargs)
        self._profile = None
        self._tune_sev = 0.5
        self._root = BoxLayout(orientation="vertical")
        self.add_widget(self._root)
        self._build_shell()

    def on_pre_enter(self, *_a):
        self._reload()
        self._rebuild()

    def _reload(self):
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
                log.warning("profile load failed: %s", exc)
        self._profile = profile
        if profile is not None:
            self._tune_sev = severity_for_slider(float(profile.severity))

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
            text="Profile",
            font_name=Fonts.bold,
            font_size=dp(22),
            color=Colors.text,
            halign="left",
            valign="middle",
        )
        title.bind(size=lambda *_: setattr(title, "text_size", title.size))
        header.add_widget(title)
        self._root.add_widget(header)
        self._body_host = BoxLayout(orientation="vertical", size_hint=(1, 1))
        self._root.add_widget(self._body_host)

    def _rebuild(self):
        self._body_host.clear_widgets()
        scroll = ScrollView(do_scroll_x=False, bar_width=0)
        content = BoxLayout(
            orientation="vertical",
            padding=[
                dp(Spacing.screen_x),
                dp(Spacing.sm),
                dp(Spacing.screen_x),
                dp(Spacing.nav_clearance),
            ],
            spacing=dp(Spacing.md),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))

        if self._profile is None:
            content.add_widget(
                PastelCard(
                    title="No profile yet",
                    subtitle="Take the color test so we can personalize Photos and Camera for your eyes.",
                    palette="peach",
                    auto_height=True,
                    size_hint_y=None,
                )
            )
            btn = PrimaryButton(text="Take the color test")
            btn.on_press_cb = lambda *_: self._go("test")
            content.add_widget(btn)
        else:
            self._fill_profile(content)

        scroll.add_widget(content)
        self._body_host.add_widget(scroll)

    def _fill_profile(self, content: BoxLayout):
        p = self._profile
        assert p is not None
        plain = profile_plain_label(p)
        sev_lbl = severity_label(float(p.severity))
        pct = strength_percent(float(p.severity))
        measured = p.measured_at or "Date not recorded"

        hero = PastelCard(
            title=plain,
            subtitle=f"{sev_lbl.capitalize()} · {pct} / 100\nMeasured {measured}",
            palette="peach",
            auto_height=True,
            size_hint_y=None,
        )
        content.add_widget(hero)

        content.add_widget(
            Label(
                text="Severity",
                font_name=Fonts.semibold,
                font_size=dp(14),
                color=Colors.text,
                size_hint_y=None,
                height=dp(22),
                halign="left",
            )
        )
        content.add_widget(SeverityBar(value=float(p.severity)))

        if isinstance(p.thresholds, dict) and p.thresholds:
            content.add_widget(
                Label(
                    text="Axis thresholds",
                    font_name=Fonts.semibold,
                    font_size=dp(14),
                    color=Colors.text,
                    size_hint_y=None,
                    height=dp(22),
                    halign="left",
                )
            )
            content.add_widget(AxisBars(thresholds=p.thresholds))

        content.add_widget(
            Label(
                text="How colors look to you",
                font_name=Fonts.semibold,
                font_size=dp(14),
                color=Colors.text,
                size_hint_y=None,
                height=dp(22),
                halign="left",
            )
        )
        content.add_widget(self._swatch_strip(p))

        retake = PrimaryButton(text="Retake the test")
        retake.on_press_cb = lambda *_: self._go("test")
        content.add_widget(retake)

        # Fine-tune section
        content.add_widget(
            PastelCard(
                title="Fine-tune my severity",
                subtitle="Preview only until you tap Save. This is the only place that overwrites your saved profile.",
                palette="lavender",
                auto_height=True,
                size_hint_y=None,
            )
        )
        self._tune_bar = PreviewSeverityBar(value=self._tune_sev)
        self._tune_bar.change_cb = self._on_tune
        content.add_widget(self._tune_bar)
        self._tune_lbl = Label(
            text=f"Preview {strength_percent(self._tune_sev)} / 100",
            font_name=Fonts.medium,
            font_size=dp(13),
            color=Colors.text_muted,
            size_hint_y=None,
            height=dp(22),
        )
        content.add_widget(self._tune_lbl)
        self._tune_img = KivyImage(size_hint_y=None, height=dp(72), fit_mode="fill")
        content.add_widget(self._tune_img)
        Clock.schedule_once(lambda dt: self._refresh_tune_swatch(), 0)

        save = PrimaryButton(text="Save fine-tuned profile")
        save.on_press_cb = lambda *_: self._confirm_save_tune()
        content.add_widget(save)

        reset = TextLinkButton(text="Reset to test result")
        reset.bind(on_release=lambda *_: self._reset_to_test())
        content.add_widget(reset)

        clear = PrimaryButton(text="Clear my profile")
        clear.bg_color = (0.92, 0.88, 0.88, 1)
        clear.text_color = (0.55, 0.15, 0.2, 1)
        clear.on_press_cb = lambda *_: self._confirm_clear()
        content.add_widget(clear)

        self._status = Label(
            text="",
            font_name=Fonts.medium,
            font_size=dp(13),
            color=Colors.accent_blue,
            size_hint_y=None,
            height=dp(22),
        )
        content.add_widget(self._status)

    def _swatch_strip(self, profile) -> BoxLayout:
        row = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None, height=dp(170))

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
            img = KivyImage(size_hint_y=None, height=dp(56), fit_mode="fill")

            def _fill(*_a, image=img, which=kind):
                w = max(64, int(image.width) if image.width > 1 else 280)
                demo = _demo_swatch(w, 56)
                if which == "sim":
                    arr = apply_simulation(demo, profile.type, float(profile.severity))
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

    def _on_tune(self, value: float):
        self._tune_sev = severity_for_slider(value)
        if hasattr(self, "_tune_lbl"):
            self._tune_lbl.text = f"Preview {strength_percent(self._tune_sev)} / 100"
        self._refresh_tune_swatch()

    def _refresh_tune_swatch(self):
        if not hasattr(self, "_tune_img") or self._profile is None:
            return
        w = max(64, int(self._tune_img.width) if self._tune_img.width > 1 else 280)
        demo = _demo_swatch(w, 72)
        arr = apply_simulation(demo, self._profile.type, self._tune_sev)
        self._tune_img.texture = rgb_to_texture(arr)

    def _reset_to_test(self, *_a):
        if self._profile is None:
            return
        base = self._profile.test_severity
        if base is None:
            base = self._profile.severity
        self._tune_sev = severity_for_slider(float(base))
        if hasattr(self, "_tune_bar"):
            self._tune_bar.set_value(self._tune_sev, notify=False)
        self._on_tune(self._tune_sev)

    def _confirm_save_tune(self):
        sheet = ConfirmSheet(
            title="Save fine-tuned profile?",
            message="This updates your saved correction for Photos and Camera. Your test result severity is kept as a reset point.",
            confirm_text="Save",
            confirm_cb=self._do_save_tune,
        )
        self.add_widget(sheet)

    def _do_save_tune(self):
        if self._profile is None:
            return
        from core.profile import CorrectionProfile

        test_sev = self._profile.test_severity
        if test_sev is None:
            test_sev = float(self._profile.severity)
        updated = CorrectionProfile.create(
            self._profile.type,
            self._tune_sev,
            measured_at=self._profile.measured_at or datetime.now().strftime("%Y-%m-%d"),
            label=self._profile.label or profile_plain_label(self._profile),
            thresholds=self._profile.thresholds,
            test_severity=test_sev,
        )
        path = profile_path()
        updated.save(path)
        app = App.get_running_app()
        if app is not None:
            app.correction_profile = updated
        self._profile = updated
        if hasattr(self, "_status"):
            self._status.text = "Your color profile has been updated"
        self._rebuild()

    def _confirm_clear(self):
        sheet = ConfirmSheet(
            title="Clear my profile?",
            message="Photos and Camera will stop using personalized correction until you take the test again.",
            confirm_text="Clear",
            danger=True,
            confirm_cb=self._do_clear,
        )
        self.add_widget(sheet)

    def _do_clear(self):
        path = profile_path()
        if path.is_file():
            path.unlink()
        app = App.get_running_app()
        if app is not None:
            app.correction_profile = None
        self._profile = None
        self._rebuild()

    def _go(self, name: str):
        if self.manager:
            self.manager.transition.direction = "right" if name == "home" else "left"
            self.manager.current = name

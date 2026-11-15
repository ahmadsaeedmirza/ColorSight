"""Welcome / onboarding — first run leads to the color test."""

from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget

from colorsight.prefs import mark_onboarding_done
from colorsight.theme.tokens import Colors, Fonts, Icons, Radii, Spacing
from colorsight.widgets import PastelCard, PrimaryButton, RoundIconButton


class WelcomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(name="welcome", **kwargs)
        self._build()

    def apply_theme(self):
        self._build()

    def _finish(self, target: str = "test"):
        mark_onboarding_done()
        if self.manager:
            self.manager.transition.direction = "left"
            self.manager.current = target
            parent = self.manager.parent
            if hasattr(parent, "set_nav_active"):
                parent.set_nav_active(target)

    def _build(self):
        scroll = ScrollView(do_scroll_x=False, bar_width=0, size_hint=(1, 1))
        content = BoxLayout(
            orientation="vertical",
            padding=[
                dp(Spacing.screen_x),
                dp(Spacing.safe_top),
                dp(Spacing.screen_x),
                dp(Spacing.xl),
            ],
            spacing=dp(Spacing.md),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))

        title = Label(
            text="ColorSight",
            font_name=Fonts.bold,
            font_size=dp(40),
            color=Colors.text,
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(52),
            shorten=True,
            shorten_from="right",
            max_lines=1,
        )
        title.bind(size=lambda *_: setattr(title, "text_size", title.size))
        content.add_widget(title)

        subtitle = Label(
            text=(
                "See colors more clearly — start with a short "
                "vision check, then correct photos and live video."
            ),
            font_name=Fonts.regular,
            font_size=dp(15),
            color=Colors.text_muted,
            halign="left",
            valign="top",
            size_hint_y=None,
            height=dp(56),
        )

        def _fit_sub(*_a):
            subtitle.text_size = (max(1, subtitle.width), None)
            subtitle.texture_update()
            subtitle.height = max(dp(40), subtitle.texture_size[1] + dp(4))

        subtitle.bind(size=_fit_sub, texture_size=_fit_sub)
        content.add_widget(subtitle)

        cta = PrimaryButton(text="Start with the color test")
        cta.on_press_cb = lambda *_: self._finish("test")
        content.add_widget(cta)

        tip = Label(
            text="You can explore Home anytime — the arrow skips to the toolkit.",
            font_name=Fonts.regular,
            font_size=dp(12),
            color=Colors.text_muted,
            size_hint_y=None,
            height=dp(36),
            halign="left",
            valign="top",
        )

        def _fit_tip(*_a):
            tip.text_size = (max(1, tip.width), None)
            tip.texture_update()
            tip.height = max(dp(28), tip.texture_size[1] + dp(4))

        tip.bind(size=_fit_tip, texture_size=_fit_tip)
        content.add_widget(tip)

        # Arrow CTA — below tip so tip never collides with card accent dots
        skip_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(56))
        skip_row.add_widget(Widget())
        arrow = RoundIconButton(icon=Icons.arrow_forward, diameter=48)
        arrow.on_press_cb = lambda *_: self._finish("home")
        skip_row.add_widget(arrow)
        content.add_widget(skip_row)

        content.add_widget(Widget(size_hint_y=None, height=dp(Spacing.sm)))

        cards = [
            ("Vision Test", "Find your color vision profile", "yellow"),
            ("Photos", "Correct images from your gallery", "pink"),
            ("Live Camera", "Real-time corrected preview", "sky"),
            ("Magnifier Lens", "Zoom in and name the color", "mint"),
        ]
        for title_t, sub, palette in cards:
            content.add_widget(
                PastelCard(
                    title=title_t,
                    subtitle=sub,
                    palette=palette,
                    size_hint_y=None,
                    auto_height=True,
                    radius=Radii.card_lg,
                )
            )

        scroll.add_widget(content)
        self.add_widget(scroll)

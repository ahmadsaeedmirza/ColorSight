"""System bar / cutout insets → Spacing.safe_top / safe_bottom (dp)."""

from __future__ import annotations

import logging
import os

from kivy.metrics import Metrics
from kivy.utils import platform

from colorsight.theme.tokens import Spacing

log = logging.getLogger("colorsight")

# Debug overrides (dp). Phone-sim sets these; clear with None.
_debug_top: float | None = None
_debug_bottom: float | None = None

_BASE_NAV_CLEARANCE = 120


def set_debug_insets(top_dp: float | None, bottom_dp: float | None) -> None:
    """Override insets for desktop phone-sim / tests (None = clear)."""
    global _debug_top, _debug_bottom
    _debug_top = top_dp
    _debug_bottom = bottom_dp
    refresh_safe_insets()


def refresh_safe_insets() -> tuple[float, float]:
    """Read platform insets, write Spacing.safe_* / screen_top / nav_clearance."""
    top_dp, bottom_dp = _read_insets_dp()
    # Desktop / missing: at least 16 dp top so headers never kiss the edge
    top_dp = max(16.0, float(top_dp))
    bottom_dp = max(0.0, float(bottom_dp))
    Spacing.safe_top = top_dp
    Spacing.safe_bottom = bottom_dp
    Spacing.screen_top = top_dp
    Spacing.nav_clearance = _BASE_NAV_CLEARANCE + bottom_dp
    log.info("safe_insets top=%.1f bottom=%.1f dp", top_dp, bottom_dp)
    return top_dp, bottom_dp


def _read_insets_dp() -> tuple[float, float]:
    env_top = os.environ.get("COLORSIGHT_INSET_TOP")
    env_bot = os.environ.get("COLORSIGHT_INSET_BOTTOM")
    if env_top is not None or env_bot is not None:
        try:
            t = float(env_top) if env_top is not None else 16.0
            b = float(env_bot) if env_bot is not None else 0.0
            return t, b
        except ValueError:
            pass
    if _debug_top is not None or _debug_bottom is not None:
        return (
            16.0 if _debug_top is None else float(_debug_top),
            0.0 if _debug_bottom is None else float(_debug_bottom),
        )
    if platform != "android":
        return 16.0, 0.0
    try:
        return _android_insets_dp()
    except Exception as exc:
        log.warning("safe_insets android probe failed: %s", exc)
        return 16.0, 0.0


def _android_insets_dp() -> tuple[float, float]:
    from jnius import autoclass  # type: ignore

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    activity = PythonActivity.mActivity
    dens = float(Metrics.density) or 1.0
    top_px = 0
    bottom_px = 0

    try:
        view = activity.getWindow().getDecorView().getRootView()
        insets = view.getRootWindowInsets()
        if insets is not None:
            try:
                # API 30+
                WindowInsets = autoclass("android.view.WindowInsets")
                Type = autoclass("android.view.WindowInsets$Type")
                combined = Type.systemBars() | Type.displayCutout()
                bars = insets.getInsets(combined)
                top_px = int(bars.top)
                bottom_px = int(bars.bottom)
            except Exception:
                # Older API
                top_px = int(insets.getSystemWindowInsetTop())
                bottom_px = int(insets.getSystemWindowInsetBottom())
    except Exception as exc:
        log.debug("WindowInsets unavailable: %s", exc)

    if top_px <= 0:
        try:
            res = activity.getResources()
            rid = res.getIdentifier("status_bar_height", "dimen", "android")
            if rid > 0:
                top_px = int(res.getDimensionPixelSize(rid))
        except Exception:
            pass

    return top_px / dens, bottom_px / dens

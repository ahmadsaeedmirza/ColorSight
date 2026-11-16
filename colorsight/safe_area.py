"""System bar / cutout insets → Spacing.safe_top / safe_bottom (dp)."""

from __future__ import annotations

import logging
import math
import os

from kivy.metrics import Metrics
from kivy.utils import platform

from colorsight.theme.tokens import Spacing

log = logging.getLogger("colorsight")

# Debug overrides (dp). Phone-sim sets these; clear with None.
_debug_top: float | None = None
_debug_bottom: float | None = None

_BASE_NAV_CLEARANCE = 120

# Sane clamps (dp). Absurd Android/px mix-ups must not push UI off-screen.
_DEFAULT_TOP = 28.0
_DEFAULT_BOTTOM = 16.0
_MAX_TOP = 80.0
_MAX_BOTTOM = 48.0


def set_debug_insets(top_dp: float | None, bottom_dp: float | None) -> None:
    """Override insets for desktop phone-sim / tests (None = clear)."""
    global _debug_top, _debug_bottom
    _debug_top = top_dp
    _debug_bottom = bottom_dp
    refresh_safe_insets()


def clamp_inset(value: float, *, kind: str) -> float:
    """Clamp / sanitize a single inset. Invalid → platform defaults."""
    default = _DEFAULT_TOP if kind == "top" else _DEFAULT_BOTTOM
    hi = _MAX_TOP if kind == "top" else _MAX_BOTTOM
    lo = 0.0
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(v) or math.isinf(v) or v < 0:
        return default
    # Values that look like raw pixels on a mid-range phone (>> dp range)
    if v > hi * 3:
        return default
    return max(lo, min(hi, v))


def refresh_safe_insets() -> tuple[float, float]:
    """Read platform insets, write Spacing.safe_* / screen_top / nav_clearance."""
    try:
        top_raw, bottom_raw = _read_insets_dp()
    except Exception as exc:
        log.warning("safe_insets read failed: %s — using defaults", exc)
        top_raw, bottom_raw = _DEFAULT_TOP, _DEFAULT_BOTTOM

    top_dp = clamp_inset(top_raw, kind="top")
    bottom_dp = clamp_inset(bottom_raw, kind="bottom")
    # Desktop / missing: at least a little top padding so headers clear the edge
    if platform != "android" and top_dp < 16.0:
        top_dp = max(16.0, top_dp)

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
            t = float(env_top) if env_top is not None else _DEFAULT_TOP
            b = float(env_bot) if env_bot is not None else _DEFAULT_BOTTOM
            return t, b
        except ValueError:
            pass
    if _debug_top is not None or _debug_bottom is not None:
        return (
            _DEFAULT_TOP if _debug_top is None else float(_debug_top),
            _DEFAULT_BOTTOM if _debug_bottom is None else float(_debug_bottom),
        )
    if platform != "android":
        return 16.0, 0.0
    try:
        return _android_insets_dp()
    except Exception as exc:
        log.warning("safe_insets android probe failed: %s", exc)
        return _DEFAULT_TOP, _DEFAULT_BOTTOM


def _android_insets_dp() -> tuple[float, float]:
    """Every pyjnius call wrapped — failure → defaults."""
    try:
        from jnius import autoclass  # type: ignore
    except Exception as exc:
        log.warning("safe_insets: jnius unavailable: %s", exc)
        return _DEFAULT_TOP, _DEFAULT_BOTTOM

    try:
        dens = float(Metrics.density) or 1.0
    except Exception:
        dens = 1.0

    top_px = 0
    bottom_px = 0
    try:
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = PythonActivity.mActivity
        if activity is None:
            return _DEFAULT_TOP, _DEFAULT_BOTTOM
        try:
            view = activity.getWindow().getDecorView().getRootView()
            insets = view.getRootWindowInsets()
            if insets is not None:
                try:
                    Type = autoclass("android.view.WindowInsets$Type")
                    combined = Type.systemBars() | Type.displayCutout()
                    bars = insets.getInsets(combined)
                    top_px = int(bars.top)
                    bottom_px = int(bars.bottom)
                except Exception:
                    try:
                        top_px = int(insets.getSystemWindowInsetTop())
                        bottom_px = int(insets.getSystemWindowInsetBottom())
                    except Exception as exc:
                        log.debug("legacy insets failed: %s", exc)
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
    except Exception as exc:
        log.warning("safe_insets android jnius failed: %s", exc)
        return _DEFAULT_TOP, _DEFAULT_BOTTOM

    try:
        return top_px / dens, bottom_px / dens
    except Exception:
        return _DEFAULT_TOP, _DEFAULT_BOTTOM

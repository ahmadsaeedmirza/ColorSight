"""Startup breadcrumbs + layout probes (flush every line so a crash keeps the trail)."""

from __future__ import annotations

import logging
import time
from typing import Any

log = logging.getLogger("colorsight")

_t0 = time.perf_counter()
_last = _t0
_first_frame_drawn = False
_startup_exc_count = 0
_startup_deadline = 0.0


def reset_startup_clock() -> None:
    global _t0, _last, _first_frame_drawn, _startup_exc_count, _startup_deadline
    _t0 = time.perf_counter()
    _last = _t0
    _first_frame_drawn = False
    _startup_exc_count = 0
    _startup_deadline = _t0 + 5.0


def mark_first_frame() -> None:
    global _first_frame_drawn
    _first_frame_drawn = True


def first_frame_drawn() -> bool:
    return _first_frame_drawn


def note_startup_exception() -> int:
    global _startup_exc_count
    now = time.perf_counter()
    if now <= _startup_deadline or _startup_deadline == 0.0:
        if _startup_deadline == 0.0:
            # build() may call this before reset — count anyway in first 5s of process
            pass
        _startup_exc_count += 1
    return _startup_exc_count


def startup_exc_count() -> int:
    return _startup_exc_count


def breadcrumb(stage: str, detail: str = "") -> None:
    """One-line startup breadcrumb; flush handlers so the line survives a crash."""
    global _last
    now = time.perf_counter()
    dt_ms = (now - _last) * 1000.0
    total_ms = (now - _t0) * 1000.0
    _last = now
    msg = f"startup:{stage} +{dt_ms:.1f}ms total={total_ms:.1f}ms"
    if detail:
        msg = f"{msg} {detail}"
    try:
        log.info(msg)
        _flush_log()
    except Exception:
        try:
            print(msg, flush=True)
        except Exception:
            pass


def _flush_log() -> None:
    root = logging.getLogger("colorsight")
    for h in list(root.handlers):
        try:
            h.flush()
        except Exception:
            pass
    for name in ("colorsight", "colorsight.theme"):
        for h in list(logging.getLogger(name).handlers):
            try:
                h.flush()
            except Exception:
                pass


def describe_widget(w: Any) -> str:
    if w is None:
        return "None"
    try:
        n = getattr(w, "name", None) or type(w).__name__
        return (
            f"{n} size=({float(w.width):.1f},{float(w.height):.1f}) "
            f"pos=({float(w.x):.1f},{float(w.y):.1f}) "
            f"opacity={float(getattr(w, 'opacity', 1)):.2f} "
            f"children={len(getattr(w, 'children', []) or [])}"
        )
    except Exception as exc:
        return f"{type(w).__name__} (describe failed: {exc})"


def layout_looks_broken(root: Any) -> tuple[bool, str]:
    """Return (broken, reason) for empty / zero-size / off-screen / invisible UI.

    A 100×100 screen on a phone-sized root looks like a black/empty app — treat
    that as broken (legacy default widget size stuck after Window resize).
    """
    try:
        if root is None:
            return True, "root is None"
        kids = getattr(root, "children", None) or []
        if len(kids) == 0:
            return True, "root has no children"
        rw = float(getattr(root, "width", 0) or 0)
        rh = float(getattr(root, "height", 0) or 0)
        if rw <= 1 or rh <= 1:
            return True, f"root size too small ({describe_widget(root)})"
        sm = getattr(root, "sm", None)
        if sm is not None:
            if float(sm.width) <= 1 or float(sm.height) <= 1:
                return True, f"ScreenManager size invalid ({describe_widget(sm)})"
            try:
                cur = sm.get_screen(sm.current)
            except Exception:
                cur = None
            if cur is None:
                return True, f"current screen missing (current={getattr(sm, 'current', None)!r})"
            cw = float(cur.width)
            ch = float(cur.height)
            if cw <= 1 or ch <= 1:
                return True, f"current screen size invalid ({describe_widget(cur)})"
            # Stuck at Kivy default 100×100 (or otherwise tiny vs the window)
            if rw >= 200 and rh >= 200 and (cw < rw * 0.5 or ch < rh * 0.5):
                return True, (
                    f"current screen much smaller than root "
                    f"({describe_widget(cur)} vs root {rw:.0f}x{rh:.0f})"
                )
            if float(getattr(cur, "opacity", 1)) <= 0.01:
                return True, f"current screen opacity 0 ({describe_widget(cur)})"
            if cur.x > rw or cur.y > rh or (cur.x + cw) < 0 or (cur.y + ch) < 0:
                return True, f"current screen outside window ({describe_widget(cur)})"
        return False, ""
    except Exception as exc:
        return True, f"layout probe failed: {exc}"

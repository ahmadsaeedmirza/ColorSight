"""Headless desktop flow: trivector session (scripted) → hue → score → profile."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core import (  # noqa: E402
    TrivectorSession,
    hue_tile_colors,
    score_trivector,
)


def main() -> None:
    session = TrivectorSession(mode="phone", seed=42)
    # Scripted alternating answers to finish quickly
    flip = True
    safety = 0
    while not session.finished and safety < 120:
        safety += 1
        trial = session.next_trial(size=128)
        if trial is None:
            break
        resp = trial.orientation if flip else None
        flip = not flip
        session.answer(trial, resp)

    order = list(range(7))
    # mild shuffle
    order[0], order[1] = order[1], order[0]
    result = score_trivector(session, hue_order=order)
    profile = result.to_profile()
    print(
        "FLOW_OK",
        result.classification,
        f"sev={result.severity:.2f}",
        f"label={result.severity_label}",
        f"thr={result.thresholds}",
        f"profile={profile.type.value}/{profile.severity:.2f}",
        f"trials={len(session.history)}",
    )


if __name__ == "__main__":
    main()

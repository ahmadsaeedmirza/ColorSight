"""Cambridge Colour Test (Trivector) — staircase, gamut, model-observer calibration."""

from __future__ import annotations

import unittest

import numpy as np

from core import CVDType
from core.trivector import (
    AXES,
    NORMAL_CUTOFF,
    ORIENTATIONS,
    STAIRCASE_MODES,
    TrivectorSession,
    background_rgb,
    build_calibration,
    chromaticity_at,
    classify_thresholds,
    get_calibration,
    in_srgb_gamut,
    max_in_gamut_d,
    render_landolt_stimulus,
    run_model_session,
    run_scripted_staircase,
    threshold_to_severity,
    uv_to_xyz,
    BG_Y,
)


def _axis_for_type(cvd: str) -> str:
    return {
        CVDType.PROTANOPIA.value: "protan",
        CVDType.DEUTERANOPIA.value: "deutan",
        CVDType.TRITANOPIA.value: "tritan",
    }[cvd]


class TestTrivectorCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Build calibration once (model observer) — required for severity mapping
        cls.curves = build_calibration([0.0, 0.3, 0.5, 0.7, 1.0])
        cls.confusion: dict[tuple[str, float], tuple[str, float]] = {}

    def test_gamut_all_axes(self):
        failures = []
        for axis in AXES:
            d_max = max_in_gamut_d(axis)
            self.assertGreater(d_max, 0.02, f"[{axis}] max in-gamut d too small: {d_max}")
            for d in np.linspace(0.0, d_max, 12):
                xyz, rgb = chromaticity_at(axis, float(d))
                if not in_srgb_gamut(xyz, eps=1e-3):
                    failures.append(f"[{axis}] d={d:.4f} out of gamut xyz={xyz} rgb={rgb}")
                if np.any(rgb < -1e-3) or np.any(rgb > 1.0 + 1e-3):
                    failures.append(f"[{axis}] d={d:.4f} rgb out of range {rgb}")
            # Background
            bg = background_rgb()
            if np.any(bg < 0) or np.any(bg > 1):
                failures.append(f"background rgb out of range {bg}")
        if failures:
            self.fail("Gamut failures:\n" + "\n".join(failures))

    def test_luminance_distributions_match(self):
        failures = []
        for axis in AXES:
            stim = render_landolt_stimulus(axis, 0.03, "up", size=192, seed=7)
            yt, yb = stim.target_ys, stim.background_ys
            if yt.size < 5 or yb.size < 5:
                failures.append(f"[{axis}] too few dots fig={yt.size} gnd={yb.size}")
                continue
            # Same generative distribution → means/std close
            if abs(float(yt.mean()) - float(yb.mean())) > 0.04:
                failures.append(
                    f"[{axis}] Y mean mismatch target={yt.mean():.3f} bg={yb.mean():.3f}"
                )
            if abs(float(yt.std()) - float(yb.std())) > 0.05:
                failures.append(
                    f"[{axis}] Y std mismatch target={yt.std():.3f} bg={yb.std():.3f}"
                )
            # Both drawn from [0.82, 1.18] * BG_Y
            lo, hi = BG_Y * 0.82 - 1e-6, BG_Y * 1.18 + 1e-6
            if yt.min() < lo or yt.max() > hi or yb.min() < lo or yb.max() > hi:
                failures.append(f"[{axis}] Y outside shared jitter band")
        if failures:
            self.fail("Luminance cue failures:\n" + "\n".join(failures))

    def test_scripted_staircase_converges(self):
        failures = []
        for true_t in (0.012, 0.028, 0.045):
            est = run_scripted_staircase(true_t, axis="protan", mode="phone", seed=11)
            if abs(est - true_t) > 0.012:
                failures.append(f"true={true_t:.3f} est={est:.3f} (tol 0.012)")
        if failures:
            self.fail("Staircase convergence failures:\n" + "\n".join(failures))

    def _thresholds_for(self, cvd: str, sev: float) -> dict[str, float]:
        """CCT-like threshold pattern from Machado calibration knots.

        Matching axis uses the calibrated thr(severity); other axes stay at the
        normal (sev=0) knot — isolates type/severity mapping from RG crosstalk
        that Machado applies to both protan and deutan axes.
        """
        from core.trivector import get_calibration

        cal = get_calibration()
        thr = {a: cal[a][0][0] for a in AXES}
        axis = _axis_for_type(cvd)
        xs = [k[0] for k in cal[axis]]
        ys = [k[1] for k in cal[axis]]
        # invert: severity -> threshold via interp on swapped axes
        thr[axis] = float(np.interp(sev, ys, xs))
        return thr

    def test_normal_observer_classified_normal(self):
        from core.trivector import classify_thresholds

        for cvd in (
            CVDType.PROTANOPIA.value,
            CVDType.DEUTERANOPIA.value,
            CVDType.TRITANOPIA.value,
        ):
            thr = self._thresholds_for(cvd, 0.0)
            result = classify_thresholds(thr)
            self.assertEqual(
                result.classification,
                "normal",
                f"severity=0 under {cvd} -> {result.classification} thr={thr}",
            )

    def test_type_and_severity_accuracy(self):
        from core.trivector import classify_thresholds

        failures = []
        matrix_rows = []
        for cvd in (
            CVDType.PROTANOPIA.value,
            CVDType.DEUTERANOPIA.value,
            CVDType.TRITANOPIA.value,
        ):
            for sev in (0.3, 0.5, 0.7, 1.0):
                thr = self._thresholds_for(cvd, sev)
                result = classify_thresholds(thr)
                self.confusion[(cvd, sev)] = (result.classification, result.severity)
                matrix_rows.append(
                    f"{cvd}@{sev:.1f} -> {result.classification} sev={result.severity:.2f} thr={thr}"
                )
                if result.classification != cvd:
                    failures.append(
                        f"[{cvd}@{sev}] classified {result.classification} thr={thr}"
                    )
                if abs(result.severity - sev) > 0.15:
                    failures.append(
                        f"[{cvd}@{sev}] severity {result.severity:.2f} outside +/-0.15"
                    )
        TestTrivectorCore._matrix_lines = matrix_rows
        if failures:
            self.fail(
                "Type/severity accuracy failures:\n"
                + "\n".join(failures)
                + "\n\nMatrix:\n"
                + "\n".join(matrix_rows)
            )

    def test_thresholds_increase_monotonically(self):
        failures = []
        for cvd in (
            CVDType.PROTANOPIA.value,
            CVDType.DEUTERANOPIA.value,
            CVDType.TRITANOPIA.value,
        ):
            axis = _axis_for_type(cvd)
            prev = -1.0
            for sev in (0.0, 0.3, 0.5, 0.7, 1.0):
                knots = get_calibration()[axis]
                t = None
                for kt, ks in knots:
                    if abs(ks - sev) < 1e-6:
                        t = kt
                        break
                if t is None:
                    from core.trivector import estimate_threshold_binary

                    t = estimate_threshold_binary(axis, cvd, sev, seed=5)
                if t + 1e-6 < prev:
                    failures.append(f"[{cvd}] thr@{sev}={t:.4f} < prev={prev:.4f}")
                prev = t
        if failures:
            self.fail("Monotonicity failures:\n" + "\n".join(failures))

    def test_machado_matching_axis_rises(self):
        """Raw Machado binary-search: matching axis thr rises with severity."""
        from core.trivector import estimate_threshold_binary

        failures = []
        for cvd in (
            CVDType.PROTANOPIA.value,
            CVDType.DEUTERANOPIA.value,
            CVDType.TRITANOPIA.value,
        ):
            axis = _axis_for_type(cvd)
            t0 = estimate_threshold_binary(axis, cvd, 0.0, seed=3)
            t1 = estimate_threshold_binary(axis, cvd, 1.0, seed=3 + 100)
            if t1 <= t0 * 1.2:
                failures.append(f"[{cvd}] matching {axis} thr0={t0:.4f} thr1={t1:.4f}")
        if failures:
            self.fail("Machado matching-axis failures:\n" + "\n".join(failures))

    def test_mild_never_wrong_type(self):
        from core.trivector import classify_thresholds

        failures = []
        for cvd in (
            CVDType.PROTANOPIA.value,
            CVDType.DEUTERANOPIA.value,
            CVDType.TRITANOPIA.value,
        ):
            for sev in (0.0, 0.1, 0.2):
                thr = self._thresholds_for(cvd, sev)
                result = classify_thresholds(thr)
                wrong = {
                    CVDType.PROTANOPIA.value,
                    CVDType.DEUTERANOPIA.value,
                    CVDType.TRITANOPIA.value,
                } - {cvd}
                if result.classification in wrong:
                    failures.append(
                        f"[{cvd}@{sev}] wrongly typed as {result.classification} thr={thr}"
                    )
                if result.classification == cvd and result.severity > 0.35:
                    failures.append(
                        f"[{cvd}@{sev}] severity {result.severity:.2f} too high for mild"
                    )
                if result.classification not in ("normal", cvd, "inconclusive"):
                    failures.append(f"[{cvd}@{sev}] unexpected {result.classification}")
        if failures:
            self.fail("Mild-case failures:\n" + "\n".join(failures))

    def test_classify_cutoffs(self):
        r = classify_thresholds({"protan": 0.005, "deutan": 0.005, "tritan": 0.008})
        self.assertEqual(r.classification, "normal")
        r = classify_thresholds({"protan": 0.05, "deutan": 0.012, "tritan": 0.01})
        self.assertEqual(r.classification, CVDType.PROTANOPIA.value)
        r = classify_thresholds({"protan": 0.012, "deutan": 0.05, "tritan": 0.01})
        self.assertEqual(r.classification, CVDType.DEUTERANOPIA.value)
        r = classify_thresholds({"protan": 0.008, "deutan": 0.008, "tritan": 0.04})
        self.assertEqual(r.classification, CVDType.TRITANOPIA.value)

    def test_session_finishes(self):
        session = TrivectorSession(mode="phone", seed=1)
        # Scripted: always correct → thresholds collapse, still need reversals
        # Alternate correct/wrong to force reversals quickly
        flip = False
        safety = 0
        while not session.finished and safety < 120:
            safety += 1
            trial = session.next_trial(size=64)
            self.assertIsNotNone(trial)
            resp = trial.orientation if flip else None
            flip = not flip
            session.answer(trial, resp)
        self.assertTrue(session.finished)
        thr = session.thresholds()
        for a in AXES:
            self.assertIn(a, thr)
            self.assertGreater(thr[a], 0.0)

    def test_modes_configured(self):
        self.assertEqual(STAIRCASE_MODES["phone"]["reversals"], 8)
        self.assertEqual(STAIRCASE_MODES["full"]["reversals"], 11)


if __name__ == "__main__":
    unittest.main()

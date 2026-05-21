"""Pulse detection methods (PULSE-126).

One classical, deterministic, evidence-emitting detector per `analytic.method`
declared in decision packs. v0.1 ships `dwell_z_score_vs_screen_baseline`
(the cell-1/cell-10 method); `multi_back_press` and `abandon_before_submit`
follow.

Each method reads the ordered canonical event sequence, computes a statistic
against the rolling per-screen baseline, and returns a MethodResult. The
discriminator (cell-10 suppression) is applied downstream in detect.py.
"""

from __future__ import annotations

from pulse.detection.detect import (
    MethodResult,
    ScreenBaseline,
    Session,
    elapsed_seconds,
    normal_cdf,
    ordered_events,
    register_method,
)

# error_type → FrictionBench root_cause enum (template / release / timing /
# cohort / none). v0.1 heuristic mapping — refined when cause-attribution is
# calibrated against the FrictionBench cause axis.
_ERROR_TYPE_TO_CAUSE = {
    "validation_error": "template",
    "data_load_failed": "timing",
    "account_authorization_lost": "release",
}


def _infer_cause(error_type: str | None) -> str | None:
    if error_type is None:
        return None
    return _ERROR_TYPE_TO_CAUSE.get(error_type, "template")


@register_method("dwell_z_score_vs_screen_baseline")
def dwell_z_score_vs_screen_baseline(
    session: Session, analytic: dict, baseline: ScreenBaseline
) -> MethodResult:
    """Fire when post-error dwell is anomalously long vs the screen baseline.

    Trigger (from the pack's `analytic.trigger`):
      - `requires_prior_event`: an error of this error_type must precede the dwell
      - `p_value_threshold`: fire when the one-sided upper-tail p-value < threshold

    Reads the ordered event sequence: finds the required prior error, then the
    next `dwell` event, z-scores its duration against the rolling baseline.
    Confidence = P(friction) = Φ(z) (upper tail). No qualifying dwell-after-error,
    or a degenerate baseline → no fire, low confidence.
    """
    trigger = analytic.get("trigger", {})
    required_prior = trigger.get("requires_prior_event")
    p_threshold = float(trigger.get("p_value_threshold", 0.01))

    events = ordered_events(session)
    t0 = events[0].get("event", {}).get("event_ts") if events else None

    seen_required_error = False
    matched_error_type: str | None = None
    error_count = 0
    dwell_seconds: float | None = None
    dwell_ts: str | None = None

    for e in events:
        ev = e.get("event", {})
        etype = ev.get("event_type")
        payload = ev.get("payload", {}) or {}
        if etype == "error":
            error_count += 1
            err = payload.get("error_type")
            # required_prior None → any error qualifies; else exact match
            if required_prior is None or err == required_prior:
                seen_required_error = True
                matched_error_type = err
        elif etype == "dwell" and seen_required_error and dwell_seconds is None:
            dwell_seconds = float(payload.get("duration_seconds", 0.0))
            dwell_ts = ev.get("event_ts")

    base_evidence = {
        "dwell_time_seconds": dwell_seconds,
        "error_event_count": error_count,
        "error_type": matched_error_type,
        "baseline_mean": baseline.mean,
        "baseline_std": baseline.std,
        "baseline_n_sessions": baseline.n_sessions,
    }

    # No qualifying dwell-after-error, or unusable baseline → abstain.
    if dwell_seconds is None or baseline.std <= 0.0:
        return MethodResult(
            fire_candidate=False,
            confidence=0.0,
            root_cause=None,
            time_to_detect_seconds=None,
            evidence={**base_evidence, "reason": "no_qualifying_dwell_or_baseline"},
        )

    z = (dwell_seconds - baseline.mean) / baseline.std
    p_value = 1.0 - normal_cdf(z)          # upper tail: long dwell = friction
    confidence = normal_cdf(z)             # P(friction)
    fire = p_value < p_threshold

    return MethodResult(
        fire_candidate=fire,
        confidence=confidence,
        root_cause=_infer_cause(matched_error_type),
        time_to_detect_seconds=elapsed_seconds(t0, dwell_ts),
        evidence={**base_evidence, "z_score": round(z, 4), "p_value": round(p_value, 6)},
    )

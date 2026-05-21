"""Tests for the Pulse detection runtime (PULSE-126).

Proves the first vertical slice end-to-end:
- the `dwell_z_score_vs_screen_baseline` method fires on a cell-1-style positive
- the negative-class discriminator suppresses a cell-10-style session (the
  load-bearing negative: long dwell = interest, not friction)
- a below-threshold dwell does not fire
- detections are reproducible (incl. inputs_hash)
- the emitted detection scores well via the FrictionBench reference scorer
"""

from __future__ import annotations

import pytest

from pulse.detection import (
    DETECTION_RUNTIME_VERSION,
    Detection,
    ScreenBaseline,
    Session,
    get_method,
    registered_methods,
    run_detection,
)
from pulse.frictionbench.scoring.score import score_detection


# ── fixtures ────────────────────────────────────────────────────────────────


def _event(seq: int, etype: str, screen: str, ts: str, payload: dict | None = None) -> dict:
    return {
        "context": {"sequence_no": seq, "screen_id": screen},
        "event": {"event_type": etype, "event_ts": ts, "payload": payload or {}},
    }


def _cell1_hypothesis() -> dict:
    """loans.apply.step3 × dwell_after_error — engineered POSITIVE."""
    return {
        "screen_id": "loans.apply.step3",
        "signature_id": "dwell_after_error",
        "analytic": {
            "method": "dwell_z_score_vs_screen_baseline",
            "trigger": {
                "requires_prior_event": "validation_error",
                "dwell_window_seconds": 60,
                "p_value_threshold": 0.01,
            },
            "baseline_source": "rolling_28d_same_screen",
        },
        "cohort_axes": ["age_band"],
        "negative_class_discriminator": None,
    }


def _cell10_hypothesis() -> dict:
    """investments.premier.portfolio.overview × dwell_after_error — engineered
    NEGATIVE. Long dwell after an error, BUT engagement signals mark it as
    deliberate review, not friction. The discriminator must suppress."""
    return {
        "screen_id": "investments.premier.portfolio.overview",
        "signature_id": "dwell_after_error",
        "analytic": {
            "method": "dwell_z_score_vs_screen_baseline",
            "trigger": {
                "requires_prior_event": "validation_error",
                "dwell_window_seconds": 60,
                "p_value_threshold": 0.01,
            },
            "baseline_source": "rolling_28d_same_screen",
        },
        "cohort_axes": ["client_tier"],
        "negative_class_discriminator": {
            "suppression_signals": [
                {"signal": "scroll_depth_pct", "threshold": 60, "direction": "above"},
                {"signal": "chart_drilldowns_in_session", "threshold": 2, "direction": "above_or_equal"},
                {"signal": "return_within_7_days", "threshold": True, "direction": "equals"},
            ],
        },
    }


def _loans_baseline() -> ScreenBaseline:
    return ScreenBaseline("loans.apply.step3", "dwell_seconds", mean=20.0, std=5.0, n_sessions=300)


def _investments_baseline() -> ScreenBaseline:
    return ScreenBaseline(
        "investments.premier.portfolio.overview", "dwell_seconds",
        mean=25.0, std=8.0, n_sessions=300,
    )


def _positive_session() -> Session:
    """Validation error then a 60s dwell — z = 8 vs the loans baseline."""
    return Session(
        session_id="sess-pos-1",
        screen_id="loans.apply.step3",
        cohort_tags=("over_50",),
        events=(
            _event(1, "screen_view", "loans.apply.step3", "2026-05-21T10:00:00Z"),
            _event(2, "error", "loans.apply.step3", "2026-05-21T10:00:05Z",
                   {"error_type": "validation_error"}),
            _event(3, "dwell", "loans.apply.step3", "2026-05-21T10:00:13Z",
                   {"duration_seconds": 60.0}),
        ),
        features={},
    )


def _cell10_session() -> Session:
    """70s dwell after a validation error (would fire) BUT engagement signals
    present → discriminator suppresses."""
    return Session(
        session_id="sess-neg-10",
        screen_id="investments.premier.portfolio.overview",
        cohort_tags=("premier",),
        events=(
            _event(1, "screen_view", "investments.premier.portfolio.overview", "2026-05-21T11:00:00Z"),
            _event(2, "error", "investments.premier.portfolio.overview", "2026-05-21T11:00:04Z",
                   {"error_type": "validation_error"}),
            _event(3, "dwell", "investments.premier.portfolio.overview", "2026-05-21T11:00:10Z",
                   {"duration_seconds": 70.0}),
        ),
        features={
            "scroll_depth_pct": 75,
            "chart_drilldowns_in_session": 3,
            "return_within_7_days": True,
        },
    )


def _short_dwell_session() -> Session:
    """8s dwell — below baseline, must not fire."""
    return Session(
        session_id="sess-short",
        screen_id="loans.apply.step3",
        cohort_tags=("under_30",),
        events=(
            _event(1, "error", "loans.apply.step3", "2026-05-21T10:00:00Z",
                   {"error_type": "validation_error"}),
            _event(2, "dwell", "loans.apply.step3", "2026-05-21T10:00:03Z",
                   {"duration_seconds": 8.0}),
        ),
        features={},
    )


# ── registry ──────────────────────────────────────────────────────────────────


def test_method_registered() -> None:
    assert "dwell_z_score_vs_screen_baseline" in registered_methods()
    assert callable(get_method("dwell_z_score_vs_screen_baseline"))


def test_unknown_method_raises() -> None:
    with pytest.raises(ValueError, match="unknown analytic.method"):
        get_method("does_not_exist")


# ── positive cell fires ─────────────────────────────────────────────────────


def test_positive_cell_fires() -> None:
    d = run_detection(
        hypothesis=_cell1_hypothesis(), session=_positive_session(), baseline=_loans_baseline()
    )
    assert d.fired is True
    assert d.signature_id == "dwell_after_error"
    assert d.screen_id == "loans.apply.step3"
    assert d.root_cause == "template"               # validation_error → template
    assert d.confidence is not None and d.confidence > 0.99   # z=8 → ~1.0
    assert d.cohort_tags == ("over_50",)
    assert d.time_to_detect_seconds == 13.0
    assert d.evidence["dwell_time_seconds"] == 60.0
    assert d.runtime_version == DETECTION_RUNTIME_VERSION
    assert d.suppressed_by == ()


def test_positive_detection_scores_well_on_frictionbench() -> None:
    d = run_detection(
        hypothesis=_cell1_hypothesis(), session=_positive_session(), baseline=_loans_baseline()
    )
    ground_truth = {
        "screen_id": "loans.apply.step3",
        "signature_id": "dwell_after_error",
        "should_fire": True,
        "root_cause": "template",
        "cohort_tags": ["over_50"],
        "confidence_target": 0.9,
    }
    score = score_detection(d.to_scoring_dict(), ground_truth)
    assert score.screen == 1.0
    assert score.signature == 1.0
    assert score.cohort == 1.0
    assert score.cause == 1.0
    assert score.aggregate > 0.95


# ── cell-10 negative is suppressed ──────────────────────────────────────────


def test_cell10_negative_is_suppressed() -> None:
    d = run_detection(
        hypothesis=_cell10_hypothesis(), session=_cell10_session(), baseline=_investments_baseline()
    )
    assert d.fired is False
    assert d.signature_id is None             # abstain
    assert d.root_cause is None
    assert d.confidence is not None and d.confidence <= 0.10   # collapsed
    assert set(d.suppressed_by) == {
        "scroll_depth_pct", "chart_drilldowns_in_session", "return_within_7_days"
    }


def test_cell10_abstain_scores_well_on_frictionbench() -> None:
    d = run_detection(
        hypothesis=_cell10_hypothesis(), session=_cell10_session(), baseline=_investments_baseline()
    )
    ground_truth = {
        "screen_id": "investments.premier.portfolio.overview",
        "signature_id": "none",
        "should_fire": False,
        "root_cause": "none",
        "cohort_tags": [],
    }
    score = score_detection(d.to_scoring_dict(), ground_truth)
    assert score.signature == 1.0    # correctly abstained
    assert score.cause == 1.0
    assert score.cohort == 1.0
    assert score.calibration > 0.95  # low confidence on a true negative
    assert score.aggregate > 0.95


# ── below-threshold does not fire ───────────────────────────────────────────


def test_short_dwell_does_not_fire() -> None:
    d = run_detection(
        hypothesis=_cell1_hypothesis(), session=_short_dwell_session(), baseline=_loans_baseline()
    )
    assert d.fired is False
    assert d.signature_id is None
    assert d.confidence is not None and d.confidence < 0.05   # 8s vs mean 20 → low


def test_no_qualifying_dwell_does_not_fire() -> None:
    """A session with no error-then-dwell sequence abstains cleanly."""
    session = Session(
        session_id="sess-nodwell",
        screen_id="loans.apply.step3",
        cohort_tags=(),
        events=(_event(1, "screen_view", "loans.apply.step3", "2026-05-21T10:00:00Z"),),
        features={},
    )
    d = run_detection(hypothesis=_cell1_hypothesis(), session=session, baseline=_loans_baseline())
    assert d.fired is False
    assert d.confidence == 0.0


# ── reproducibility ─────────────────────────────────────────────────────────


def test_same_inputs_produce_identical_detection() -> None:
    a = run_detection(hypothesis=_cell1_hypothesis(), session=_positive_session(), baseline=_loans_baseline())
    b = run_detection(hypothesis=_cell1_hypothesis(), session=_positive_session(), baseline=_loans_baseline())
    assert a == b
    assert a.inputs_hash == b.inputs_hash


def test_changing_dwell_changes_hash() -> None:
    a = run_detection(hypothesis=_cell1_hypothesis(), session=_positive_session(), baseline=_loans_baseline())
    b = run_detection(hypothesis=_cell1_hypothesis(), session=_short_dwell_session(), baseline=_loans_baseline())
    assert a.inputs_hash != b.inputs_hash

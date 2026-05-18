"""Tests for the Pulse Value methodology v0 (PULSE-101).

Key invariants (parallel to Risk's test_risk_score.py):
- tier-words enum is a closed set
- score_value() is pure: same inputs → identical ValueScore (incl. hash)
- methodology_version is stamped in every output
- adjustments are monotonic (only push tier up, never down)
- Value methodology + bank_policy integrate end-to-end
"""

from __future__ import annotations

import pytest

from pulse.contracts import validate_bank_policy
from pulse.value import (
    ValueMetrics,
    ValueScore,
    ValueShape,
    load_methodology,
    score_value,
)


def _good_bank_policy() -> dict:
    cfg = {
        "version": "0.1.0",
        "deployment_id": "deploy-test-001",
        "escalation_thresholds": {
            "affected_customers_7d_window": 500,
            "vulnerable_cohort_overrep_floor": 1.25,
        },
        "policy_areas": [],
        "vulnerable_cohort_extensions": [],
    }
    validate_bank_policy(cfg)
    return cfg


def _nominal_shape() -> ValueShape:
    return ValueShape(
        signature_id="lazy_scroll",
        journey_category="behavioural_noise",
        screen_class="marketing_page",
        severity="P2",
    )


def _quiet_metrics() -> ValueMetrics:
    return ValueMetrics(
        affected_customers_7d=15,
        avg_events_per_affected_user=1.1,
        vulnerable_cohort_share=0.05,
        counterfactual_baseline_pct=0.05,
    )


# --- tier-words closure ------------------------------------------------------


def test_tier_words_is_closed_enum_of_four() -> None:
    methodology = load_methodology()
    assert methodology["tier_words"] == [
        "NOMINAL",
        "WATCH",
        "SIGNIFICANT",
        "COMMERCIAL-OPPORTUNITY",
    ]


def test_max_tier_matches_tier_words_length() -> None:
    methodology = load_methodology()
    assert methodology["max_tier"] == len(methodology["tier_words"]) - 1


def test_every_returned_tier_is_in_the_enum() -> None:
    """Sweep: every reachable combination returns a tier-word from the enum."""
    methodology = load_methodology()
    valid_words = set(methodology["tier_words"])
    for severity in ("P0", "P1", "P2"):
        shape = ValueShape("any", "behavioural_noise", "any", severity)
        for affected in (0, 9999):
            for freq in (1.0, 10.0):
                for share in (0.0, 0.9):
                    for baseline in (0.0, 0.9):
                        metrics = ValueMetrics(
                            affected_customers_7d=affected,
                            avg_events_per_affected_user=freq,
                            vulnerable_cohort_share=share,
                            counterfactual_baseline_pct=baseline,
                        )
                        score = score_value(
                            shape=shape, metrics=metrics, bank_policy=_good_bank_policy()
                        )
                        assert score.tier in valid_words


# --- base tier from severity -------------------------------------------------


@pytest.mark.parametrize(
    "severity,expected_tier",
    [
        ("P0", "SIGNIFICANT"),
        ("P1", "WATCH"),
        ("P2", "NOMINAL"),
    ],
)
def test_base_tier_from_severity_alone(severity: str, expected_tier: str) -> None:
    shape = ValueShape("any", "behavioural_noise", "any", severity)
    metrics = ValueMetrics(0, 1.0, 0.0, 0.0)
    score = score_value(shape=shape, metrics=metrics, bank_policy=_good_bank_policy())
    assert score.tier == expected_tier
    assert score.adjustments_applied == ()


def test_unknown_severity_raises() -> None:
    shape = ValueShape("any", "behavioural_noise", "any", "P9")
    with pytest.raises(ValueError, match="severity"):
        score_value(shape=shape, metrics=_quiet_metrics(), bank_policy=_good_bank_policy())


# --- individual adjustments fire correctly -----------------------------------


def test_large_affected_population_fires_at_threshold() -> None:
    """Inclusive at the threshold."""
    shape = _nominal_shape()
    metrics = ValueMetrics(
        affected_customers_7d=500,  # equals threshold
        avg_events_per_affected_user=1.0,
        vulnerable_cohort_share=0.0,
        counterfactual_baseline_pct=0.0,
    )
    score = score_value(shape=shape, metrics=metrics, bank_policy=_good_bank_policy())
    assert "large_affected_population" in score.adjustments_applied
    assert score.tier == "WATCH"  # P2 base (0) + 1 = WATCH (1)


def test_high_frequency_per_user_fires() -> None:
    shape = _nominal_shape()
    metrics = ValueMetrics(
        affected_customers_7d=0,
        avg_events_per_affected_user=3.0,  # equals threshold
        vulnerable_cohort_share=0.0,
        counterfactual_baseline_pct=0.0,
    )
    score = score_value(shape=shape, metrics=metrics, bank_policy=_good_bank_policy())
    assert "high_frequency_per_user" in score.adjustments_applied


def test_vulnerable_cohort_concentrated_fires() -> None:
    shape = _nominal_shape()
    metrics = ValueMetrics(
        affected_customers_7d=0,
        avg_events_per_affected_user=1.0,
        vulnerable_cohort_share=0.4,  # equals threshold
        counterfactual_baseline_pct=0.0,
    )
    score = score_value(shape=shape, metrics=metrics, bank_policy=_good_bank_policy())
    assert "vulnerable_cohort_concentrated" in score.adjustments_applied


def test_large_counterfactual_baseline_fires() -> None:
    shape = _nominal_shape()
    metrics = ValueMetrics(
        affected_customers_7d=0,
        avg_events_per_affected_user=1.0,
        vulnerable_cohort_share=0.0,
        counterfactual_baseline_pct=0.25,  # equals threshold
    )
    score = score_value(shape=shape, metrics=metrics, bank_policy=_good_bank_policy())
    assert "large_counterfactual_baseline" in score.adjustments_applied


def test_adjustments_just_below_threshold_do_not_fire() -> None:
    shape = _nominal_shape()
    metrics = ValueMetrics(
        affected_customers_7d=499,
        avg_events_per_affected_user=2.999,
        vulnerable_cohort_share=0.399,
        counterfactual_baseline_pct=0.249,
    )
    score = score_value(shape=shape, metrics=metrics, bank_policy=_good_bank_policy())
    assert score.adjustments_applied == ()
    assert score.tier == "NOMINAL"


# --- monotonicity + clamping -------------------------------------------------


def test_p0_with_all_adjustments_clamps_at_top_tier() -> None:
    """The COMMERCIAL-OPPORTUNITY cell — P0 + every adjustment fires."""
    shape = ValueShape(
        signature_id="dwell_after_error",
        journey_category="choke_point",
        screen_class="credit_application",
        severity="P0",
    )
    metrics = ValueMetrics(
        affected_customers_7d=12500,
        avg_events_per_affected_user=3.5,
        vulnerable_cohort_share=0.55,
        counterfactual_baseline_pct=0.40,
    )
    score = score_value(shape=shape, metrics=metrics, bank_policy=_good_bank_policy())
    # P0 base (2) + 4 adjustments = 6, clamped to max_tier (3).
    assert score.tier == "COMMERCIAL-OPPORTUNITY"
    assert score.numeric_tier == 3
    assert set(score.adjustments_applied) == {
        "large_affected_population",
        "high_frequency_per_user",
        "vulnerable_cohort_concentrated",
        "large_counterfactual_baseline",
    }


def test_adjustments_are_monotonic() -> None:
    """Adding signal can only push the tier up, never down."""
    shape = ValueShape("sig", "context_loss", "credit_application", "P1")
    weak = ValueMetrics(0, 1.0, 0.0, 0.0)
    strong = ValueMetrics(99999, 10.0, 0.9, 0.9)
    weak_score = score_value(shape=shape, metrics=weak, bank_policy=_good_bank_policy())
    strong_score = score_value(shape=shape, metrics=strong, bank_policy=_good_bank_policy())
    assert strong_score.numeric_tier >= weak_score.numeric_tier


def test_p0_with_no_adjustments_stays_at_significant() -> None:
    """A P0 with quiet metrics is SIGNIFICANT, not COMMERCIAL-OPPORTUNITY —
    severity alone is not enough."""
    shape = ValueShape(
        signature_id="dwell_after_error",
        journey_category="choke_point",
        screen_class="credit_application",
        severity="P0",
    )
    metrics = ValueMetrics(20, 1.0, 0.1, 0.05)
    score = score_value(shape=shape, metrics=metrics, bank_policy=_good_bank_policy())
    assert score.tier == "SIGNIFICANT"
    assert score.adjustments_applied == ()


# --- determinism + audit footprint -------------------------------------------


def test_same_inputs_produce_identical_value_score() -> None:
    shape = ValueShape("sig", "context_loss", "credit_application", "P1")
    metrics = ValueMetrics(600, 3.1, 0.4, 0.3)
    policy = _good_bank_policy()
    a = score_value(shape=shape, metrics=metrics, bank_policy=policy)
    b = score_value(shape=shape, metrics=metrics, bank_policy=policy)
    assert a == b
    assert a.inputs_hash == b.inputs_hash


def test_changing_severity_changes_inputs_hash() -> None:
    shape_p2 = ValueShape("any", "behavioural_noise", "x", "P2")
    shape_p0 = ValueShape("any", "behavioural_noise", "x", "P0")
    a = score_value(shape=shape_p2, metrics=_quiet_metrics(), bank_policy=_good_bank_policy())
    b = score_value(shape=shape_p0, metrics=_quiet_metrics(), bank_policy=_good_bank_policy())
    assert a.inputs_hash != b.inputs_hash


def test_changing_deployment_id_changes_inputs_hash() -> None:
    policy_a = _good_bank_policy()
    policy_b = _good_bank_policy()
    policy_b["deployment_id"] = "deploy-test-002"
    a = score_value(shape=_nominal_shape(), metrics=_quiet_metrics(), bank_policy=policy_a)
    b = score_value(shape=_nominal_shape(), metrics=_quiet_metrics(), bank_policy=policy_b)
    assert a.inputs_hash != b.inputs_hash


def test_cosmetic_bank_policy_edit_does_not_change_hash() -> None:
    policy_a = _good_bank_policy()
    policy_b = _good_bank_policy()
    policy_b["policy_areas"] = [
        {
            "internal_name": "Cosmetic",
            "regulatory_taxonomy": "fca_consumer_duty_2.0",
            "regulatory_section": "PRIN 12",
        }
    ]
    a = score_value(shape=_nominal_shape(), metrics=_quiet_metrics(), bank_policy=policy_a)
    b = score_value(shape=_nominal_shape(), metrics=_quiet_metrics(), bank_policy=policy_b)
    assert a.inputs_hash == b.inputs_hash


def test_methodology_version_pinned_in_output() -> None:
    score = score_value(
        shape=_nominal_shape(), metrics=_quiet_metrics(), bank_policy=_good_bank_policy()
    )
    methodology = load_methodology()
    assert score.methodology_version == str(methodology["methodology_version"])
    assert score.methodology_version == "0.1.0"


def test_valuescore_as_dict_round_trip() -> None:
    score = score_value(
        shape=_nominal_shape(), metrics=_quiet_metrics(), bank_policy=_good_bank_policy()
    )
    d = score.as_dict()
    assert d["tier"] == score.tier
    assert d["methodology_version"] == score.methodology_version
    assert d["inputs_hash"] == score.inputs_hash


# --- cross-axis consistency with Risk ----------------------------------------


def test_shared_affected_population_threshold_with_risk() -> None:
    """Value and Risk both read affected_customers_7d_window from the
    bank policy — the bank commits to ONE number across both axes.
    This test asserts the cross-axis consistency at the threshold edge."""
    from pulse.risk import FrictionShape, ImpactMetrics, score_risk

    # At exactly the threshold, both axes' population-threshold
    # adjustments fire.
    affected_at_threshold = 500
    policy = _good_bank_policy()

    risk_shape = FrictionShape("sig", "behavioural_noise", "any_screen", "P2")
    risk_impact = ImpactMetrics(
        affected_customers_7d=affected_at_threshold,
        vulnerable_cohort_overrep_ratio=1.0,
    )
    risk_score = score_risk(shape=risk_shape, impact=risk_impact, bank_policy=policy)
    assert "affected_customers_threshold" in risk_score.adjustments_applied

    value_shape = ValueShape("sig", "behavioural_noise", "any_screen", "P2")
    value_metrics = ValueMetrics(
        affected_customers_7d=affected_at_threshold,
        avg_events_per_affected_user=1.0,
        vulnerable_cohort_share=0.0,
        counterfactual_baseline_pct=0.0,
    )
    value_score = score_value(shape=value_shape, metrics=value_metrics, bank_policy=policy)
    assert "large_affected_population" in value_score.adjustments_applied

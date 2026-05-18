"""Pulse Value methodology v0 — scoring function.

Pure function. Same inputs always produce the same Value score; the
methodology_version is pinned in every output for audit. Per the
canvas-as-discipline lock, Value is a COMPUTED canvas slot — packs
declare the friction signature shape and value-bearing observations;
the engine computes the tier.

Inputs:
- friction signature shape (signature_id, journey_category, screen_class, severity)
- detected value metrics (affected_customers_7d, avg_events_per_affected_user,
  vulnerable_cohort_share, counterfactual_baseline_pct)
- per-deployment bank_policy.yaml (escalation thresholds — shared with Risk
  for cross-axis consistency on the affected-population threshold)

Filed under PULSE-101.
"""

from __future__ import annotations

import functools
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

_METHODOLOGY_PATH = Path(__file__).parent / "value_methodology.yaml"


@dataclass(frozen=True)
class ValueScore:
    """Computed Value tier + audit footprint.

    `tier` is one of the methodology's closed enum (NOMINAL / WATCH /
    SIGNIFICANT / COMMERCIAL-OPPORTUNITY). `numeric_tier` is the
    underlying integer (0..3); useful for downstream sorting.

    `adjustments_applied` lists which methodology adjustment keys fired.
    `methodology_version` and `inputs_hash` together let any consumer
    reproduce or audit the score later."""

    tier: str
    numeric_tier: int
    base_tier: int
    adjustments_applied: tuple[str, ...]
    methodology_version: str
    inputs_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "numeric_tier": self.numeric_tier,
            "base_tier": self.base_tier,
            "adjustments_applied": list(self.adjustments_applied),
            "methodology_version": self.methodology_version,
            "inputs_hash": self.inputs_hash,
        }


@dataclass(frozen=True)
class ValueShape:
    """The friction signature coordinates Value scores against."""

    signature_id: str
    journey_category: str
    screen_class: str
    severity: str  # P0 / P1 / P2


@dataclass(frozen=True)
class ValueMetrics:
    """Detected value-bearing magnitudes the engine measured for this signature.

    Distinct from Risk's ImpactMetrics — Value asks a different question
    (how much would be unlocked by fixing this friction?) so the metrics
    differ even though some are derivable from the same underlying telemetry."""

    affected_customers_7d: int
    avg_events_per_affected_user: float
    vulnerable_cohort_share: float        # 0..1
    counterfactual_baseline_pct: float    # 0..1


@functools.lru_cache(maxsize=1)
def load_methodology() -> dict[str, Any]:
    with _METHODOLOGY_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def score_value(
    *,
    shape: ValueShape,
    metrics: ValueMetrics,
    bank_policy: dict[str, Any],
) -> ValueScore:
    """Compute Value tier. Pure function — same inputs → same ValueScore."""
    methodology = load_methodology()

    base_tier = _base_tier_from_severity(shape.severity, methodology)
    adjustments_applied: list[str] = []

    if _crosses_affected_population(metrics, bank_policy):
        adjustments_applied.append("large_affected_population")

    if _crosses_frequency_threshold(metrics, methodology):
        adjustments_applied.append("high_frequency_per_user")

    if _crosses_cohort_concentration(metrics, methodology):
        adjustments_applied.append("vulnerable_cohort_concentrated")

    if _crosses_counterfactual_baseline(metrics, methodology):
        adjustments_applied.append("large_counterfactual_baseline")

    numeric_tier = _apply_adjustments(base_tier, adjustments_applied, methodology)
    tier_word = methodology["tier_words"][numeric_tier]

    inputs_hash = _hash_inputs(shape, metrics, bank_policy)

    return ValueScore(
        tier=tier_word,
        numeric_tier=numeric_tier,
        base_tier=base_tier,
        adjustments_applied=tuple(adjustments_applied),
        methodology_version=str(methodology["methodology_version"]),
        inputs_hash=inputs_hash,
    )


# ── helpers ──────────────────────────────────────────────────────────────────


def _base_tier_from_severity(severity: str, methodology: dict[str, Any]) -> int:
    table = methodology["base_tier_by_severity"]
    if severity not in table:
        raise ValueError(
            f"severity must be one of {sorted(table)}, got {severity!r}"
        )
    return int(table[severity])


def _crosses_affected_population(
    metrics: ValueMetrics, bank_policy: dict[str, Any]
) -> bool:
    threshold = bank_policy["escalation_thresholds"]["affected_customers_7d_window"]
    return metrics.affected_customers_7d >= threshold


def _crosses_frequency_threshold(
    metrics: ValueMetrics, methodology: dict[str, Any]
) -> bool:
    threshold = methodology["adjustments"]["high_frequency_per_user"][
        "threshold_events_per_user"
    ]
    return metrics.avg_events_per_affected_user >= threshold


def _crosses_cohort_concentration(
    metrics: ValueMetrics, methodology: dict[str, Any]
) -> bool:
    threshold = methodology["adjustments"]["vulnerable_cohort_concentrated"][
        "threshold_cohort_share"
    ]
    return metrics.vulnerable_cohort_share >= threshold


def _crosses_counterfactual_baseline(
    metrics: ValueMetrics, methodology: dict[str, Any]
) -> bool:
    threshold = methodology["adjustments"]["large_counterfactual_baseline"][
        "threshold_baseline_pct"
    ]
    return metrics.counterfactual_baseline_pct >= threshold


def _apply_adjustments(
    base_tier: int, adjustments_applied: list[str], methodology: dict[str, Any]
) -> int:
    total = base_tier
    for key in adjustments_applied:
        total += int(methodology["adjustments"][key]["delta"])
    return min(int(methodology["max_tier"]), total)


def _hash_inputs(
    shape: ValueShape, metrics: ValueMetrics, bank_policy: dict[str, Any]
) -> str:
    payload = {
        "shape": {
            "signature_id": shape.signature_id,
            "journey_category": shape.journey_category,
            "screen_class": shape.screen_class,
            "severity": shape.severity,
        },
        "metrics": {
            "affected_customers_7d": metrics.affected_customers_7d,
            "avg_events_per_affected_user": metrics.avg_events_per_affected_user,
            "vulnerable_cohort_share": metrics.vulnerable_cohort_share,
            "counterfactual_baseline_pct": metrics.counterfactual_baseline_pct,
        },
        # Same partial-hashing posture as Risk: cosmetic policy edits
        # don't bust the audit trail.
        "bank_policy_thresholds": bank_policy.get("escalation_thresholds", {}),
        "bank_policy_deployment_id": bank_policy.get("deployment_id"),
    }
    serialised = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(serialised).hexdigest()

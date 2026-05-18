# Pulse Value — rubric (worked examples)

Machine-readable rubric: [`value_methodology.yaml`](./value_methodology.yaml).
Reference scorer: [`score.py`](./score.py). Methodology paper:
[`VALUE_DESIGN.md`](./VALUE_DESIGN.md).

Filed under [PULSE-101].

## Tier words (closed enum)

| Numeric | Word | Meaning |
|---|---|---|
| 0 | `NOMINAL` | minimal value at stake — no special prioritisation |
| 1 | `WATCH` | moderate signal worth monitoring |
| 2 | `SIGNIFICANT` | material commercial impact |
| 3 | `COMMERCIAL-OPPORTUNITY` | high-value pattern that warrants prioritised investment |

Extending the enum is a methodology-version change. The set is closed by
construction — a test asserts it.

## Worked examples

### Example 1 — P2 NOMINAL (no adjustments)

Low-severity friction, small affected population, low frequency, no
vulnerable-cohort concentration, small counterfactual baseline.

```
shape:   signature_id=lazy_scroll, journey_category=behavioural_noise,
         screen_class=marketing_page, severity=P2
metrics: affected_customers_7d=15, avg_events_per_affected_user=1.1,
         vulnerable_cohort_share=0.05, counterfactual_baseline_pct=0.05
policy:  affected_customers_7d_window=500
```

Base tier: `P2 → 0` (NOMINAL). No adjustments fire.
**Tier: NOMINAL.**

### Example 2 — P1 with high frequency → SIGNIFICANT

A medium-severity friction that customers encounter multiple times per
visit — a fix ends the recurring frustration.

```
shape:   signature_id=multi_back_press, journey_category=context_loss,
         screen_class=account_management, severity=P1
metrics: affected_customers_7d=100, avg_events_per_affected_user=4.2,
         vulnerable_cohort_share=0.1, counterfactual_baseline_pct=0.1
policy:  affected_customers_7d_window=500
```

Base tier: `P1 → 1` (WATCH). `high_frequency_per_user` fires (4.2 ≥ 3).
**Tier: SIGNIFICANT.** (1 + 1 = 2)

### Example 3 — P0 with all four adjustments → COMMERCIAL-OPPORTUNITY

High severity. Large affected population. High per-user frequency.
Vulnerable cohorts disproportionately affected. Large counterfactual.

```
shape:   signature_id=dwell_after_error, journey_category=choke_point,
         screen_class=credit_application, severity=P0
metrics: affected_customers_7d=12500, avg_events_per_affected_user=3.5,
         vulnerable_cohort_share=0.55, counterfactual_baseline_pct=0.40
policy:  affected_customers_7d_window=500
```

Base tier: `P0 → 2` (SIGNIFICANT).
Adjustments: all four fire. Sum: `2 + 4 = 6`. Clamped at `max_tier = 3`.
**Tier: COMMERCIAL-OPPORTUNITY.**

### Example 4 — P0 with no metric adjustments → SIGNIFICANT not COMMERCIAL-OPPORTUNITY

A P0 friction with small population, low frequency, no cohort
concentration, small counterfactual — the friction itself is severe,
but fixing it doesn't unlock material commercial volume.

```
shape:   signature_id=dwell_after_error, journey_category=choke_point,
         screen_class=credit_application, severity=P0
metrics: affected_customers_7d=20, avg_events_per_affected_user=1.0,
         vulnerable_cohort_share=0.1, counterfactual_baseline_pct=0.05
policy:  affected_customers_7d_window=500
```

Base tier: `P0 → 2` (SIGNIFICANT). No adjustments fire.
**Tier: SIGNIFICANT.**

This is the case worth understanding: a P0 friction can be `SIGNIFICANT`
on the Value axis without being `COMMERCIAL-OPPORTUNITY`. Severity and
commercial value are correlated but not identical — Value methodology
keeps the distinction visible.

### Example 5 — Same Risk inputs, different Value adjustments

The Risk axis would treat Example 4 above as `ESCALATE` (P0 base, no
regulatory match, no thresholds crossed, no Chronicle precedent). The
Value axis treats it as `SIGNIFICANT`. The 2×2 cell is
**(Risk=ESCALATE, Value=SIGNIFICANT)** → renders as **ACUTE** in the
downstream CLARK-style Action tier (high on both axes).

By contrast Example 2 above sits at (Risk=WATCH, Value=SIGNIFICANT) —
this is the kind of cell that produces a `COMMERCIAL-OPPORTUNITY`
Action tier downstream: worth fixing for the commercial unlock,
without crossing a regulatory line.

### Example 6 — Same inputs, same tier (determinism)

`score_value()` is a pure function. Calling it twice with the same
inputs returns `ValueScore` instances with identical `tier`,
`numeric_tier`, `methodology_version`, and `inputs_hash`. A test
asserts this round-trip — symmetric with Risk.

## Why thresholds are fixed in the methodology at v0

The three internal thresholds (`threshold_events_per_user=3`,
`threshold_cohort_share=0.4`, `threshold_baseline_pct=0.25`) live in
[`value_methodology.yaml`](./value_methodology.yaml) rather than in
[`pulse/contracts/bank_policy.yaml`](../contracts/bank_policy.yaml).
This is deliberate at v0:

- the methodology should be reproducible across deployments without
  per-bank tuning (CASP discipline)
- moving thresholds to `bank_policy.yaml` would let banks tune their
  way down to never crossing a tier — Value should resist that
  for the same reason Risk does

v0.2 may move some thresholds to per-deployment configuration once the
methodology has been observed in real deployments and the
single-population threshold (`affected_customers_7d_window`) has
proven workable as the cross-axis anchor.

## Why monotonic adjustments (vs continuous score)

Same answer as Risk: a closed tier-enum is easier to reason about and
brief on than a continuous score, and adjustment-only-up keeps the
audit-trail story simple ("this base tier, plus these adjustments,
clamped at the top"). The numeric tier (0..3) is exposed for
downstream sorting / 2×2 cell logic.

[PULSE-101]: https://cjipro.atlassian.net/browse/PULSE-101

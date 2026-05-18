# Pulse Value methodology v0 — design

CASP-style methodology paper. Published before any production Value score
runs against bank deployments. Mirrors the FrictionBench discipline of
publishing the rubric before the scores.

Filed under [PULSE-101]. Peer document: [`pulse/risk/RISK_DESIGN.md`](../risk/RISK_DESIGN.md).

## What Value is, in one sentence

Value is a **computed** canvas slot — not author-declared. The engine
takes the friction signature's coordinates, the detected value-bearing
metrics (population, frequency, cohort concentration, counterfactual
baseline), and the deployment's bank policy, and emits one of four
closed tier-words: `NOMINAL`, `WATCH`, `SIGNIFICANT`,
`COMMERCIAL-OPPORTUNITY`.

The Pulse Design Direction lock (2026-05-18) places Value as the peer of
Risk on the canvas Value × Risk 2×2. The combined output downstream is
the CLARK-style Action tier:

| Risk \ Value | NOMINAL / WATCH | SIGNIFICANT / COMMERCIAL-OPPORTUNITY |
|---|---|---|
| NOMINAL / WATCH | NOMINAL · WATCH | COMMERCIAL-OPPORTUNITY |
| ESCALATE / REGULATORY-FLAG | REGULATORY-FLAG | ACUTE |

Action-tier rendering belongs to the briefing surface (HOL-9), not this
methodology — the Value scorer outputs its own tier independently.

## Why Value is computed not declared

Same two reasons as Risk: **reproducibility** (a `methodology_version`
+ `inputs_hash` audit trail) and **per-deployment relevance** (bank-
specific population thresholds shouldn't be guessed by pack authors).

The Value axis also has a third reason particular to it:
**prioritisation conflicts of interest**. A pack author has an
incentive to declare their pack's value high; an engine-computed Value
removes that incentive. The bank's policy + the detected metrics
drive the tier — not the pack author's enthusiasm.

## Inputs

The scorer takes three input groups:

1. **ValueShape** — `signature_id`, `journey_category`, `screen_class`,
   `severity` (`P0` / `P1` / `P2`). The pack carries these via
   `hypothesis.yaml`. Identical structure to Risk's `FrictionShape` —
   the same shape feeds both methodologies.

2. **ValueMetrics** — `affected_customers_7d` (integer),
   `avg_events_per_affected_user` (float ≥ 0),
   `vulnerable_cohort_share` (float in [0, 1]),
   `counterfactual_baseline_pct` (float in [0, 1]). The engine
   measures these from telemetry.

3. **bank_policy** — the parsed
   [`pulse/contracts/bank_policy.yaml`](../contracts/bank_policy.yaml).
   Shares `escalation_thresholds.affected_customers_7d_window` with
   Risk — the bank commits to **one** population number that
   escalates both axes.

## Computation

Tier is computed as `min(COMMERCIAL-OPPORTUNITY, base_tier + Σ adjustments)`.

`base_tier` is a function of severity per
[`value_methodology.yaml`](./value_methodology.yaml). The mapping is
symmetric with Risk's:

| Severity | Base tier (numeric) | Base tier-word |
|---|---|---|
| P0 | 2 | SIGNIFICANT |
| P1 | 1 | WATCH |
| P2 | 0 | NOMINAL |

Four monotonic +1 adjustments stack and clamp at the top tier:

| Adjustment | Fires when |
|---|---|
| `large_affected_population` | `metrics.affected_customers_7d ≥ bank_policy.escalation_thresholds.affected_customers_7d_window` |
| `high_frequency_per_user` | `metrics.avg_events_per_affected_user ≥ 3` (threshold in methodology YAML) |
| `vulnerable_cohort_concentrated` | `metrics.vulnerable_cohort_share ≥ 0.4` (threshold in methodology YAML) |
| `large_counterfactual_baseline` | `metrics.counterfactual_baseline_pct ≥ 0.25` (threshold in methodology YAML) |

Adjustments are monotonic — they only push the tier up. Symmetric with
Risk's precautionary posture: severity already declared a floor; the
methodology never opts back down from it.

## Where Value and Risk diverge

Value and Risk share the friction shape, the bank policy, and the
P0/P1/P2 severity mapping. They differ in which **metrics** they
consume and which **questions** those metrics answer.

| Dimension | Risk asks | Value asks |
|---|---|---|
| Cohort | "is the cohort over-represented relative to baseline?" (fairness gate) | "does the friction concentrate on vulnerable cohorts?" (prioritisation gate) |
| Frequency | n/a | "would a fix end a recurring frustration vs a one-off?" |
| Counterfactual | n/a | "would a fix recover a large absolute volume of completions?" |
| Regulatory taxonomy | "does this cross a published regulatory expectation?" | n/a (Value doesn't read the regulatory taxonomy) |
| Chronicle | "has this signature converted to enforcement before?" | n/a (Value doesn't read Chronicle) |

The vulnerable-cohort axis is the trickiest divergence: same underlying
cohort data, different threshold semantics. Risk's `overrep_ratio`
asks whether the cohort is hit MORE than baseline (fairness signal);
Value's `cohort_share` asks whether vulnerable cohorts make up enough
of the affected population that fixing the friction would
disproportionately help them (prioritisation signal).

## Output

`ValueScore` (frozen dataclass) carries:
- `tier` (closed enum tier-word)
- `numeric_tier` (0..3)
- `base_tier` (for diff explanation)
- `adjustments_applied`
- `methodology_version` (pinned from `value_methodology.yaml`)
- `inputs_hash` (SHA-256 over the deployment-affecting inputs)

The audit footprint is symmetric with Risk's — both methodologies
reproduce identically from the same input bytes + methodology version.

## Things this methodology deliberately does NOT do

- **No reading the regulatory taxonomy** — Value is a commercial /
  prioritisation signal. Regulatory exposure is Risk's question, not
  Value's. Conflating the two would let regulator-favoured signatures
  monopolise the Value axis even when their fix has small commercial
  return.
- **No reading the Chronicle library** — Chronicle is a Risk-axis
  artefact (enforcement precedent), not a Value-axis one.
- **No revenue or basis-point estimation at v0** — the methodology
  is tier-based, not currency-based. v0.2 may add a `gbp_at_stake`
  scalar once the bank's commercial-impact model is in place; the
  v0.1 axis is intentionally cohort/population/frequency-based to
  ship without needing the bank's price book.
- **No LLM inference** — v1 is non-LLM runtime per the architectural
  lock.
- **No pack-author override** — packs declare the shape; the engine
  owns the tier.

## Versioning

`methodology_version` bumps on:

- any change to `tier_words` (adding / removing / renaming tiers)
- any change to `base_tier_by_severity` mappings
- any change to adjustment keys, thresholds, or `delta` values

Decision packs pin `required_pulse_version` in their metadata —
methodology-version changes surface as compatibility failures at load
time.

## v0.1 acknowledged limits

- **Linear adjustment stack** — same posture as Risk's v0.1; v0.2 may
  revisit if real deployments produce patterns that need interaction
  terms.
- **No revenue model at v0** — Value is tier-based, not money-based.
  See "deliberately does NOT do" above.
- **Threshold defaults are illustrative** — the
  `threshold_events_per_user=3`, `threshold_cohort_share=0.4`,
  `threshold_baseline_pct=0.25` defaults are reasonable starting
  points but warrant calibration against real telemetry before
  production use. v0.2 will likely move some thresholds to
  per-deployment `bank_policy.yaml` (the way
  `affected_customers_7d_window` already lives there).

[PULSE-101]: https://cjipro.atlassian.net/browse/PULSE-101

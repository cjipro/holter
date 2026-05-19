"""MLOps Console (HOL-6) — procurement-gate surface for ML eng + MRM.

Per HOL-6 spec (CLAUDE.md surface 4): mandatory before any live bank
deployment; built BEFORE any LLM_AUGMENTED synthesis is enabled in prod.

Four panes:
  1. DRIFT MONITORS — per FrictionBench cell × signature; time-series of
     detection rate / false-positive rate / accuracy gap
  2. FAIRNESS RE-CHECK — demographic_parity / equalised_odds /
     calibration_by_cohort over time, per template, per cohort dim
  3. LINEAGE VERIFIER — hash-chain health, broken-chain alerts,
     last-verified timestamp per pack
  4. SYNTHESIS-MODE GOVERNANCE — table of every pack with synthesis_mode
     (DETERMINISTIC / LLM_AUGMENTED), attestation status, reviewer + date

Critical mitigation — narrative layer (eats own dogfood):
  Every drift alert + fairness deviation MUST produce a deterministic
  one-paragraph narrative via the "What changed, for whom, with what
  evidence, what's the recommended response" template. Engine returns
  these later via pulse.synthesis.base.TemplateSynthesisProvider; stubbed
  here for design preview.

Out of scope: NO model training UI, NO notebook env, NO feature store browser.

Output: dist/preview/mlops/index.html
Serve:  py holter/preview/serve_mlops.py  (port 8506)
"""

from __future__ import annotations

import datetime as _dt
import sys
from html import escape as _e
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "dist" / "preview" / "mlops"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# HOL-35: import primitives from _shared, not from render_holter — so a
# broken Workspace import doesn't cascade to MLOps Console (Cannon's
# hand-carry concern). render_holter is no longer in the import path.
from holter.preview._shared import (  # noqa: E402
    discover_packs,
    get_pack_cell,
    short_hash,
    sparkline_svg,
    box_header,
    box_footer,
    render_box,
    body_lines,
    body_kpi_tiles,
    body_chip_strip,
    body_bars,
    body_action_primary,
    body_disclosure,
    body_quality_strip,
    body_primary_kpi,
    headline_tier_badge,
    headline_stat_card,
    headline_chip_strip,
    tooltip_token,
    render_glossary_panel,
    _ACTION_COLORS,
    _RISK_COLORS,
)

NOW = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ─────────────────────────────────────────────────────────────────────────────
# Stub data — engine returns these via pulse.frictionbench/convergence/lineage
# once those contracts are wired. Deterministic per pack-name hash.
# ─────────────────────────────────────────────────────────────────────────────

def drift_series_n(pack_name: str, n: int) -> list[int]:
    """Stub N-day detection-rate series. HOL-43 — variable length so the
    window scrubber can swap [7d][14d][30d] without re-fetching."""
    h = sum(ord(c) for c in pack_name)
    baseline = 40 + (h % 30)
    return [baseline + ((h + i * 5) % 19) - 9 for i in range(n)]


def cohort_drift_series_n(pack_name: str, cohort: str, n: int) -> list[int]:
    """HOL-43 — variable-length cohort series; mirrors cohort_drift_series."""
    h = sum(ord(c) for c in pack_name) + sum(ord(c) for c in cohort)
    baseline = 40 + (h % 30)
    swing = (h % 12) - 6
    return [baseline + ((h + i * (3 + cohort.count("-"))) % 19) - 9 + swing
            for i in range(n)]


def lineage_chain_ancestry(pack_name: str, sha: str) -> list[dict]:
    """HOL-43 — stub upstream ancestry chain for a pack's lineage hash.
    Closes O'Neil's 'hash is a string not a link' + Banin's 'no upstream
    pointer' R2 critique. Engine returns this via pulse.lineage in prod."""
    h = sum(ord(c) for c in pack_name)
    depth = 4 + (h % 3)
    pipelines = [
        "frictionbench.scoring", "convergence.cohort_split",
        "lineage.anchor_sealer", "pulse.synthesis.deterministic",
        "telemetry.taq_adapter", "schema.canonical_v2",
    ]
    chain = []
    for i in range(depth):
        ph = (h * 31 + i * 17) % 0xFFFFFFFF
        ds_suffix = (5 - i + (h % 4)) % 5 + 1
        chain.append({
            "sha":       f"sha-{ph:08x}_{(ph >> 4) & 0xFFFF:04x}",
            "pipeline":  pipelines[(h + i) % len(pipelines)],
            "dataset":   f"taq.session_2026{ds_suffix:02d}",
            "sealed_at": f"2026-05-{(19 - i * 3) % 28 + 1:02d}",
        })
    return chain


def drift_series(pack_name: str) -> list[int]:
    """Stub 14-day detection-rate series. Engine returns this via
    pulse.frictionbench.scoring once the contract is wired."""
    h = sum(ord(c) for c in pack_name)
    baseline = 40 + (h % 30)
    # Walk away from baseline by a tier-coupled drift amount
    return [baseline + ((h + i * 3) % 17) - 8 for i in range(14)]


# HOL-41 — cohort axes for disaggregated drift (O'Neil + Gigerenzer + Hubbard).
# Engine returns per-cohort series via pulse.frictionbench.scoring.cohort_breakdown
# once the contract is wired; stubbed deterministically per (pack, cohort).
_COHORT_LABELS = ["18-24", "25-54", "55+"]
_COHORT_COLORS = ["var(--red)", "var(--blue)", "var(--green)"]


def cohort_drift_series(pack_name: str, cohort: str) -> list[int]:
    """Stub 14-day detection-rate series per cohort. Different cohorts drift
    independently — important because cell-aggregated drift can hide a single
    subgroup bleeding (O'Neil's R1 critique)."""
    h = sum(ord(c) for c in pack_name) + sum(ord(c) for c in cohort)
    baseline = 40 + (h % 30)
    # Each cohort gets its own drift signature
    swing = (h % 12) - 6
    return [baseline + ((h + i * (3 + cohort.count("-"))) % 19) - 9 + swing
            for i in range(14)]


def multi_sparkline_svg(series_list: list[list[float]], colors: list[str],
                        width: int = 200, height: int = 36,
                        baseline: float | None = None,
                        baseline_color: str = "rgba(180,200,210,0.4)",
                        labels: list[str] | None = None) -> str:
    """Multi-series sparkline — N overlaid trend lines + optional baseline.

    HOL-41: replaces the single-series sparkline_svg in DRIFT pane to surface
    cohort-level drift. Each series gets its own color from `colors`. Baseline
    renders as a dashed horizontal line (cell-aggregated 30-day mean) so the
    reader has an anchor for "is this drifting away from baseline."
    """
    if not series_list or not series_list[0]:
        return ""
    # Y-axis range = union of all series + baseline
    all_y: list[float] = []
    for s in series_list:
        all_y.extend(s)
    if baseline is not None:
        all_y.append(baseline)
    vmin, vmax = min(all_y), max(all_y)
    span = (vmax - vmin) or 1.0
    n = len(series_list[0])
    step = width / max(n - 1, 1)

    polylines = []
    # HOL-43 — tag each polyline with data-cohort so the legend can solo on
    # hover (CSS-only dim of other lines)
    cohort_labels = labels or [""] * len(series_list)
    for series, color, label in zip(series_list, colors, cohort_labels):
        pts = " ".join(
            f"{i*step:.1f},{height - ((v - vmin) / span) * height:.1f}"
            for i, v in enumerate(series)
        )
        polylines.append(
            f'<polyline class="ms-line" data-cohort="{label}" '
            f'points="{pts}" fill="none" '
            f'stroke="{color}" stroke-width="1.4" opacity="0.85"/>'
        )

    baseline_svg = ""
    if baseline is not None:
        by = height - ((baseline - vmin) / span) * height
        baseline_svg = (
            f'<line x1="0" y1="{by:.1f}" x2="{width}" y2="{by:.1f}" '
            f'stroke="{baseline_color}" stroke-width="1" stroke-dasharray="2,3"/>'
        )

    # HOL-43 — invisible day-overlay rectangles carry <title> tooltips
    # showing per-day per-cohort values. Native browser tooltip; zero JS.
    day_rects = []
    if cohort_labels and labels:
        for i in range(n):
            day = n - i  # day_N = 1 is "today"
            x = max(0, i * step - step / 2)
            w = step
            tooltip_lines = [f"day -{n - 1 - i} (D{n - i})"]
            for series, label in zip(series_list, cohort_labels):
                if i < len(series):
                    tooltip_lines.append(f"{label}: {series[i]:.0f}")
            tooltip = " · ".join(tooltip_lines)
            day_rects.append(
                f'<rect class="ms-day" x="{x:.1f}" y="0" '
                f'width="{w:.1f}" height="{height}" '
                f'fill="transparent">'
                f'<title>{tooltip}</title>'
                f'</rect>'
            )

    return (
        f'<svg class="body-sparkline" viewBox="0 0 {width} {height}" '
        f'width="100%" height="{height}" preserveAspectRatio="none">'
        f'{baseline_svg}'
        f'{"".join(polylines)}'
        f'{"".join(day_rects)}'
        f'</svg>'
    )


def fairness_record(pack_name: str) -> dict:
    """Stub fairness metrics — engine returns via pulse.convergence."""
    h = sum(ord(c) for c in pack_name)
    return {
        "demographic_parity":      0.92 - (h % 11) * 0.01,
        "equalised_odds":          0.88 - (h % 13) * 0.01,
        "calibration_by_cohort":   0.94 - (h % 7)  * 0.01,
        "cohort_dims":             ["age_band", "gender", "ethnicity_band"],
        "deviation_alert":         (h % 17) > 13,
    }


def lineage_status(pack_name: str, sha: str) -> dict:
    """Stub lineage verification — engine returns via pulse.lineage."""
    h = sum(ord(c) for c in pack_name)
    broken = (h % 19) > 17  # ~10% of packs synthesised as broken
    return {
        "chain_status":   "BROKEN" if broken else "VERIFIED",
        "color":          "var(--red)" if broken else "var(--green)",
        "last_verified":  "2026-05-19 06:42 UTC" if not broken else "2026-05-17 14:08 UTC",
        "chain_depth":    4 + (h % 3),
        "anchor_sha":     sha,
    }


def synthesis_governance(pack_name: str) -> dict:
    """Stub synthesis-mode + attestation per pack."""
    h = sum(ord(c) for c in pack_name)
    is_llm = (h % 23) > 20  # ~13% of packs as LLM_AUGMENTED (gated)
    if is_llm:
        mode = "LLM_AUGMENTED"
        attestation = "self_declared"
        att_color = "var(--amber)"
    else:
        mode = "DETERMINISTIC"
        # ~20% of deterministic also land in attestation_pending — e.g.
        # newly-onboarded packs awaiting independent assessment. These
        # are the second class of rows MRM needs to act on.
        bucket = h % 3
        if bucket == 0:
            attestation = "attestation_pending"
            att_color = "var(--amber)"
        elif bucket == 1:
            attestation = "certified"
            att_color = "var(--green)"
        else:
            attestation = "independently_assessed"
            att_color = "var(--teal)"
    return {
        "synthesis_mode":  mode,
        "mode_color":      "var(--red)" if is_llm else "var(--green)",
        "attestation":     attestation,
        "att_color":       att_color,
        "reviewer":        "MRM-A · J. Patel" if (h % 3) else "MRM-B · S. Khan",
        "reviewed_date":   "2026-04-22" if (h % 5) else "2026-05-08",
        # HOL-42: PENDING rows get inline Attest/Challenge/Defer
        # affordances. Two flavours of "pending": (a) LLM_AUGMENTED
        # self_declared, (b) DETERMINISTIC attestation_pending. Rock's
        # R2 hard-gate fix: governance state needs governance affordance.
        "is_actionable":   attestation in ("self_declared", "attestation_pending"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Deterministic narrative layer — "What changed, for whom, with what evidence,
# what's the recommended response." Engine returns these via
# pulse.synthesis.base.TemplateSynthesisProvider; stubbed for design preview.
# ─────────────────────────────────────────────────────────────────────────────

def drift_narrative(pack_name: str, series: list[int]) -> str:
    """Generate a one-paragraph drift narrative — alert-fatigue mitigation."""
    today, week_ago = series[-1], series[-8]
    delta = today - week_ago
    direction = "rose" if delta > 0 else ("fell" if delta < 0 else "held")
    return (
        f"<strong>What changed:</strong> detection rate {direction} "
        f"{abs(delta)}pp over the last 7 days (now {today}). "
        f"<strong>For whom:</strong> the {_e(pack_name)[:40]} pack's "
        f"cell-level detection model. "
        f"<strong>Evidence:</strong> 14-day sparkline + cohort-weighted "
        f"baseline comparison. "
        f"<strong>Response:</strong> "
        f"{'recalibrate threshold; new bank-altitude check' if abs(delta) > 5 else 'continue monitoring — within bounds'}."
    )


# HOL-40 — severity gradient: 4 tiers control narrative rendering.
# Materiality thresholds per pane keep narratives information-rich when present.

def render_severity_narrative(severity: str, body_html: str) -> str:
    """Render a narrative at the right visual weight for its severity.

    NOMINAL  → single status token (no narrative)
    WATCH    → compact muted summary
    ESCALATE → full 4-clause block (default; current behaviour)
    ACUTE    → full block + red rail + ACUTE prefix, non-suppressible

    Raskin's R1 rule: if every state transition generates the same paragraph
    shape, the medium trains people to ignore it.
    """
    sev = severity.lower()
    if sev == "nominal":
        return (
            f'<div class="mlops-narrative mlops-narrative--nominal">'
            f'▬ NOMINAL · no action required'
            f'</div>'
        )
    cls = {
        "watch":    "mlops-narrative mlops-narrative--watch",
        "escalate": "mlops-narrative mlops-narrative--escalate",
        "acute":    "mlops-narrative mlops-narrative--acute",
    }.get(sev, "mlops-narrative")
    return f'<div class="{cls}">{body_html}</div>'


def classify_drift_severity(worst_delta: int) -> str:
    """Materiality thresholds per ticket: |delta| < 2 NOMINAL / 2-5 WATCH /
    5-10 ESCALATE / >10 ACUTE."""
    a = abs(worst_delta)
    if a < 2:   return "NOMINAL"
    if a <= 5:  return "WATCH"
    if a <= 10: return "ESCALATE"
    return "ACUTE"


def classify_fairness_severity(n_deviations: int) -> str:
    if n_deviations == 0: return "NOMINAL"
    if n_deviations == 1: return "WATCH"
    if n_deviations <= 3: return "ESCALATE"
    return "ACUTE"


def classify_lineage_severity(n_broken: int) -> str:
    if n_broken == 0: return "NOMINAL"
    if n_broken == 1: return "ESCALATE"
    return "ACUTE"


def classify_synthesis_severity(n_llm: int) -> str:
    """LLM_AUGMENTED in prod is the v1 immutability gate violation —
    ESCALATE/ACUTE depending on count."""
    if n_llm == 0: return "NOMINAL"
    if n_llm == 1: return "ESCALATE"
    return "ACUTE"


def classify_row_severity_drift(delta: int) -> str:
    """Per-row drift severity for HOL-45 filter. Same thresholds as
    classify_drift_severity but applied to a single row's delta."""
    return classify_drift_severity(delta)


def attestation_severity(attestation: str) -> str:
    """HOL-45 — per-row severity for SYNTHESIS filter. PENDING covers both
    self_declared and attestation_pending; everything else is NOMINAL."""
    if attestation in ("self_declared", "attestation_pending"):
        return "PENDING"
    return "NOMINAL"


# HOL-45 — threshold rule explanations. Keyed by severity OR by metric name.
# Surfaced via native `title` on the badge or fairness number. Plain-language
# so a non-statistician can decode (Gigerenzer's R1 + R2 ask).
THRESHOLD_RULES: dict[str, str] = {
    # Drift severity rules
    "DRIFT_NOMINAL":  "Drift NOMINAL = |delta| < 2pp (no material change)",
    "DRIFT_WATCH":    "Drift WATCH = 2-5pp delta (observe; no action required)",
    "DRIFT_ESCALATE": "Drift ESCALATE = 5-10pp delta (review baseline; flag for next cycle)",
    "DRIFT_ACUTE":    "Drift ACUTE = |delta| >= 10pp (recalibrate threshold; hold deployment)",
    # Lineage severity rules
    "LINEAGE_NOMINAL":  "Lineage NOMINAL = 0 broken chains (all hashes verified)",
    "LINEAGE_ESCALATE": "Lineage ESCALATE = 1 broken chain (re-seal; review anchor source)",
    "LINEAGE_ACUTE":    "Lineage ACUTE = 2+ broken chains (halt promotions; trace propagation)",
    # Synthesis severity rules
    "SYNTHESIS_NOMINAL":  "Synthesis NOMINAL = 0 LLM_AUGMENTED in prod path",
    "SYNTHESIS_ESCALATE": "Synthesis ESCALATE = 1 LLM_AUGMENTED pack flagged (v1 gate violation)",
    "SYNTHESIS_ACUTE":    "Synthesis ACUTE = 2+ LLM_AUGMENTED packs (governance backlog)",
    # Status rules
    "VERIFIED": "VERIFIED = chain hash matches anchor; no tampering detected",
    "BROKEN":   "BROKEN = chain hash mismatch; lineage integrity compromised",
    "STABLE":   "STABLE = chain depth and parents unchanged over last 24h",
    # Attestation rules
    "self_declared":          "self_declared = pack author asserted compliance; independent assessment required",
    "attestation_pending":    "attestation_pending = newly-onboarded pack awaiting MRM sign-off",
    "independently_assessed": "independently_assessed = second reviewer confirmed; not yet certified",
    "certified":              "certified = sealed for prod; quarterly recertification due",
    # Fairness metric rules
    "demographic_parity":  ("demographic_parity ∈ [0,1]; 1 = perfectly equal selection rates across cohorts. "
                            "Floor 0.85 = 15pp tolerance. Below floor = ACUTE."),
    "equalised_odds":      ("equalised_odds ∈ [0,1]; 1 = equal TPR and FPR across cohorts. "
                            "Floor 0.80 = 20pp tolerance. Below floor = ACUTE."),
    "calibration_by_cohort": ("calibration_by_cohort ∈ [0,1]; 1 = predicted probability matches observed rate "
                              "per cohort. Floor 0.90."),
}


def render_filter_strip(scope: str, options: list[tuple[str, str]],
                        default: str = "all") -> str:
    """HOL-45 — pane-scoped severity filter strip. Each button has
    data-filter-scope=<pane> + data-filter-value=<severity>. JS handler
    hides rows in the same scope whose data-severity doesn't match."""
    btns = "".join(
        f'<button class="pane-filter-btn" data-filter-scope="{scope}" '
        f'data-filter-value="{val}" '
        f'{"data-active=\"true\"" if val == default else ""} '
        f'type="button">{_e(label)}</button>'
        for val, label in options
    )
    return (
        f'<div class="pane-filter-strip" data-filter-scope="{scope}">'
        f'<span class="pane-filter-label">filter</span>{btns}'
        f'</div>'
    )


def fairness_narrative(pack_name: str, fair: dict) -> str:
    """One-paragraph fairness narrative for the deviation alert."""
    worst_metric, worst_value = min(
        [("demographic parity", fair["demographic_parity"]),
         ("equalised odds",     fair["equalised_odds"]),
         ("calibration",        fair["calibration_by_cohort"])],
        key=lambda x: x[1],
    )
    return (
        f"<strong>What changed:</strong> {worst_metric} dropped to "
        f"{worst_value:.2f} (floor 0.85). "
        f"<strong>For whom:</strong> {_e(' · '.join(fair['cohort_dims']))} cohorts. "
        f"<strong>Evidence:</strong> sliding-window over last 30 days; "
        f"deviation persists across re-runs. "
        f"<strong>Response:</strong> "
        f"{'hold deployment; MRM re-review' if fair['deviation_alert'] else 'no action — within tolerance'}."
    )


# ─────────────────────────────────────────────────────────────────────────────
# CSS — MIL briefing aesthetic + a small MLOps-specific addition for the
# governance table
# ─────────────────────────────────────────────────────────────────────────────

CSS_EXTRA = """
.mlops-page { padding: 24px; display: flex; flex-direction: column; gap: 16px; }
.mlops-masthead {
  display: flex; align-items: baseline; justify-content: space-between;
  border-bottom: 1px solid var(--border);
  padding-bottom: 10px;
}
.mlops-masthead-title {
  font-family: var(--mono); font-size: 12px; font-weight: 800;
  letter-spacing: 2.4px; text-transform: uppercase;
  color: var(--text-3);
}
.mlops-masthead-dateline {
  font-family: var(--mono); font-size: 11px; color: var(--text-3);
  letter-spacing: 1.2px; text-transform: uppercase;
}

/* 4 panes — same locked box discipline as Workspace, 2-col grid on wide,
   1-col on narrow. */
.mlops-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}
@media (max-width: 1100px) { .mlops-grid { grid-template-columns: 1fr; } }

/* Governance table */
.govern-table { width: 100%; border-collapse: collapse;
                font-family: var(--mono); font-size: 10px; }
.govern-table th { text-align: left; padding: 4px 6px;
                   color: var(--text-3); letter-spacing: 0.7px;
                   text-transform: uppercase;
                   border-bottom: 1px solid var(--border); }
.govern-table td { padding: 4px 6px; color: var(--text-2);
                   border-bottom: 1px solid var(--card-2); }
.govern-table tr:last-child td { border-bottom: 0; }
.govern-badge {
  font-family: var(--mono); font-weight: 800; font-size: 9px;
  letter-spacing: 0.8px;
  padding: 1px 6px;
  border: 1px solid currentColor;
  border-radius: 2px;
}

/* Drift sparkline cell — used in the per-cell mini-grid */
.drift-cell { display: flex; align-items: center; gap: 8px;
              padding: 4px 0; font-family: var(--mono); font-size: 10px; }
.drift-cell-label { color: var(--text-2); flex: 0 0 165px; white-space: nowrap;
                    overflow: hidden; text-overflow: ellipsis; }
/* HOL-41: bigger sparkline so 14 days are readable (was 90px → now 200px) */
.drift-cell-spark { flex: 1 1 200px; min-width: 200px; }
.drift-cell-val { color: var(--text); font-weight: 700; width: 50px;
                  text-align: right; flex: 0 0 50px; }
/* HOL-41: cohort legend at top of DRIFT pane */
.drift-legend { display: flex; align-items: center; gap: 12px;
                font-family: var(--mono); font-size: 9px;
                letter-spacing: 1.2px; text-transform: uppercase;
                color: var(--text-3); padding: 2px 0 6px;
                border-bottom: 1px dashed var(--border); margin-bottom: 6px; }
.drift-legend-label { color: var(--text-3); }
.drift-legend-swatch { display: inline-flex; align-items: center; gap: 4px; }
.drift-legend-dot { width: 10px; height: 2px; display: inline-block; }
.drift-legend-baseline { display: inline-flex; align-items: center; gap: 4px;
                         margin-left: auto; }
.drift-legend-baseline-line { width: 14px; height: 1px; border-top: 1px dashed var(--text-3); }

/* Narrative block — distinct from regular body lines */
.mlops-narrative {
  background: var(--card-elev);
  border-left: 3px solid var(--blue);
  padding: 10px 12px;
  font-size: 11px; line-height: 1.55;
  color: var(--text);
}
.mlops-narrative strong { color: var(--text); }

/* HOL-40 — severity gradient on narratives. Uniform paragraphs at uniform
   weight will train reviewers to skip them (Raskin's R1 critique). 4 tiers
   of visual weight match 4 tiers of actionability. */
.mlops-narrative--nominal {
  background: transparent;
  border-left-color: var(--text-3);
  padding: 4px 12px;
  font-size: 10px; color: var(--text-3);
  font-family: var(--mono); letter-spacing: 1px; text-transform: uppercase;
}
.mlops-narrative--watch {
  background: var(--card-2);
  border-left-color: var(--amber);
  padding: 6px 12px;
  font-size: 11px; color: var(--text-2);
}
.mlops-narrative--escalate {
  /* current default styling; explicit class for clarity */
  background: var(--card-elev);
  border-left-color: var(--amber);
}
.mlops-narrative--acute {
  background: var(--card-elev);
  border-left-width: 4px;
  border-left-color: var(--red);
  box-shadow: 0 0 0 1px rgba(230, 51, 51, 0.25);
  /* Non-suppressible — no opacity drop, no collapse */
}
.mlops-narrative--acute::before {
  content: "▲ ACUTE · ";
  font-family: var(--mono); font-weight: 800;
  letter-spacing: 1.4px; color: var(--red);
}

/* HOL-39 — drill-through coupling: clicking a cell-id link highlights
   every matching cell-row across all 4 panes simultaneously. */
.cell-link {
  color: inherit;
  text-decoration: none;
  border-bottom: 1px dotted currentColor;
  cursor: pointer;
}
.cell-link:hover { color: var(--blue); }
.cell-row {
  transition: background 120ms ease, box-shadow 120ms ease;
  border-radius: 2px;
  padding-left: 4px; margin-left: -4px;
}
.cell-row-highlighted {
  background: rgba(0, 183, 245, 0.12);
  box-shadow: inset 3px 0 0 var(--blue);
}
.govern-table tr.cell-row-highlighted td {
  background: rgba(0, 183, 245, 0.12);
}
.govern-table tr.cell-row-highlighted td:first-child {
  box-shadow: inset 3px 0 0 var(--blue);
}

/* HOL-42 — Attest/Challenge/Defer affordance on PENDING SYNTHESIS rows.
   Rock's R2 hard-gate critique: governance state without governance affordance
   is not a defensible surface. These 3 buttons let MRM record a decision
   from the screen (in-session log; engine wiring is PULSE's job). */
.govern-actions {
  display: inline-flex; gap: 4px; align-items: center;
}
.govern-action-btn {
  font-family: var(--mono); font-size: 9px; font-weight: 700;
  letter-spacing: 0.6px; text-transform: uppercase;
  padding: 2px 6px;
  background: transparent;
  color: var(--text-2);
  border: 1px solid var(--border);
  border-radius: 2px;
  cursor: pointer;
  transition: all 100ms ease;
}
.govern-action-btn:hover {
  border-color: var(--text-2);
  color: var(--text);
  background: var(--card-2);
}
.govern-action-btn--attest:hover  { border-color: var(--green); color: var(--green); }
.govern-action-btn--challenge:hover { border-color: var(--amber); color: var(--amber); }
.govern-action-btn--defer:hover   { border-color: var(--text-3); color: var(--text-3); }
.govern-actions-none {
  font-family: var(--mono); color: var(--text-3); font-size: 9px;
}
/* Resolved row state — replaces buttons with the recorded decision */
.govern-row--resolved {
  opacity: 0.65;
}
.govern-row--resolved td:first-child a.cell-link {
  text-decoration: line-through;
}
.govern-resolved-badge {
  font-family: var(--mono); font-weight: 800; font-size: 9px;
  letter-spacing: 0.8px; padding: 1px 6px;
  border-radius: 2px;
}
.govern-resolved-badge--attested   { color: var(--green); border: 1px solid var(--green); }
.govern-resolved-badge--challenged { color: var(--amber); border: 1px solid var(--amber); }
.govern-resolved-badge--deferred   { color: var(--text-3); border: 1px solid var(--text-3); }
/* Session log tray below the governance table */
.govern-session-log {
  margin-top: 8px;
  padding: 6px 10px;
  background: var(--card-2);
  border-left: 2px solid var(--text-3);
  font-family: var(--mono); font-size: 9px;
  color: var(--text-3); letter-spacing: 0.6px;
  text-transform: uppercase;
}
.govern-session-log--active {
  border-left-color: var(--blue);
  color: var(--text-2);
}
.govern-session-log-count { color: var(--blue); font-weight: 800; }

/* HOL-43 — Interrogable sparkline + lineage hash links + window scrubber.
   Victor/Hubbard/Banin/O'Neil R2 ask: the surface lets you reach into
   the data. Three affordances, one gesture. */

/* (b) Window scrubber [7d][14d][30d] above DRIFT sparklines */
.window-scrubber {
  display: inline-flex; gap: 4px; align-items: center;
  margin-left: auto;
  font-family: var(--mono); font-size: 9px;
}
.window-scrubber-label { color: var(--text-3); letter-spacing: 0.6px;
                         text-transform: uppercase; }
.window-scrubber-btn {
  font-family: var(--mono); font-size: 9px; font-weight: 700;
  letter-spacing: 0.6px;
  padding: 1px 6px;
  background: transparent;
  color: var(--text-3);
  border: 1px solid var(--border);
  border-radius: 2px;
  cursor: pointer;
  transition: all 100ms ease;
}
.window-scrubber-btn:hover { color: var(--text); border-color: var(--text-2); }
.window-scrubber-btn[data-active="true"] {
  background: rgba(0, 183, 245, 0.15);
  color: var(--blue); border-color: var(--blue);
}

/* SVG window switching: show one, hide the other two */
.drift-cell-spark svg[data-window] { display: none; }
body:not([data-window]) .drift-cell-spark svg[data-window="14d"],
body[data-window="7d"]  .drift-cell-spark svg[data-window="7d"],
body[data-window="14d"] .drift-cell-spark svg[data-window="14d"],
body[data-window="30d"] .drift-cell-spark svg[data-window="30d"] {
  display: block;
}

/* Day-stamp legend below the scrubber */
.drift-window-stamp { color: var(--text-3); font-family: var(--mono);
                      font-size: 9px; letter-spacing: 0.6px;
                      margin-left: 8px; }

/* (a) Cohort solo — hovering legend swatch dims other lines */
.drift-legend-swatch[data-cohort] { cursor: pointer; }
.drift-cell-spark svg .ms-line { transition: opacity 120ms ease; }
.drift-legend:hover .drift-legend-swatch:not(:hover) { opacity: 0.4; }
.drift-legend:has(.drift-legend-swatch[data-cohort="18-24"]:hover)
  ~ .drift-cell .drift-cell-spark svg .ms-line:not([data-cohort="18-24"]) {
  opacity: 0.15;
}
.drift-legend:has(.drift-legend-swatch[data-cohort="25-54"]:hover)
  ~ .drift-cell .drift-cell-spark svg .ms-line:not([data-cohort="25-54"]) {
  opacity: 0.15;
}
.drift-legend:has(.drift-legend-swatch[data-cohort="55+"]:hover)
  ~ .drift-cell .drift-cell-spark svg .ms-line:not([data-cohort="55+"]) {
  opacity: 0.15;
}

/* (c) Lineage hash-as-link + click-to-expand chain */
.hash-link {
  color: var(--text-2);
  text-decoration: none;
  border-bottom: 1px dotted var(--text-3);
  cursor: pointer;
}
.hash-link:hover { color: var(--blue); border-bottom-color: var(--blue); }
.hash-chain {
  display: none;
  margin: 4px 0 8px 18px;
  padding: 6px 10px;
  background: var(--card-2);
  border-left: 2px solid var(--blue);
  font-family: var(--mono); font-size: 9px;
  color: var(--text-2);
}
.hash-chain--open { display: block; }
.hash-chain-row { display: flex; gap: 10px; padding: 1px 0;
                  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hash-chain-sha { color: var(--text-2); flex: 0 0 145px; }
.hash-chain-pipeline { color: var(--blue); flex: 0 0 170px; }
.hash-chain-dataset { color: var(--text-3); flex: 1 1 auto; }
.hash-chain-date { color: var(--text-3); flex: 0 0 75px;
                   text-align: right; }
.hash-chain-arrow { color: var(--text-3); opacity: 0.6;
                    padding: 1px 0 3px 0; }

/* HOL-44 — Top-of-page decision frame. Young's R2 ask: "I land on this page
   and don't know what I'm supposed to do. The 4 panes feel like 4 separate
   status checks." Replaces the bare procurement-gate masthead. */
.mlops-decision-frame {
  background: var(--card-elev);
  border: 1px solid var(--border);
  border-left: 4px solid var(--blue);
  border-radius: 4px;
  padding: 14px 18px;
  display: grid;
  grid-template-columns: 1fr auto;
  grid-template-rows: auto auto;
  gap: 10px 24px;
  align-items: center;
}
.mlops-decision-frame--acute   { border-left-color: var(--red); }
.mlops-decision-frame--escalate{ border-left-color: var(--amber); }

.mlops-decision-trigger {
  grid-column: 1;
  font-size: 13px; line-height: 1.45;
  color: var(--text);
}
.mlops-decision-trigger-tag {
  display: inline-block; padding: 1px 6px;
  font-family: var(--mono); font-size: 9px; font-weight: 800;
  letter-spacing: 0.8px;
  border: 1px solid currentColor; border-radius: 2px;
  margin-right: 6px;
}
.mlops-decision-trigger-pack {
  font-family: var(--mono); font-size: 11px;
  color: var(--text); background: var(--card-2);
  padding: 1px 5px; border-radius: 2px;
}

.mlops-decision-actions {
  grid-column: 2;
  display: inline-flex; gap: 6px;
}
.mlops-decision-btn {
  font-family: var(--mono); font-size: 10px; font-weight: 700;
  letter-spacing: 0.8px; text-transform: uppercase;
  padding: 6px 12px;
  background: transparent;
  color: var(--text-2);
  border: 1px solid var(--border);
  border-radius: 3px;
  cursor: pointer;
  transition: all 100ms ease;
  white-space: nowrap;
}
.mlops-decision-btn:hover {
  border-color: var(--text-2); color: var(--text);
  background: var(--card-2);
}
.mlops-decision-btn--approve:hover   { border-color: var(--green); color: var(--green); }
.mlops-decision-btn--committee:hover { border-color: var(--amber); color: var(--amber); }
.mlops-decision-btn--retrain:hover   { border-color: var(--red); color: var(--red); }

.mlops-decision-session {
  grid-column: 1 / 3;
  display: flex; gap: 16px; align-items: center;
  padding-top: 8px; border-top: 1px dashed var(--border);
  font-family: var(--mono); font-size: 9px;
  color: var(--text-3); letter-spacing: 0.7px; text-transform: uppercase;
}
.mlops-decision-session-reviewer { color: var(--text-2); }
.mlops-decision-session-count { color: var(--blue); font-weight: 800; }
.mlops-decision-session-confirm {
  margin-left: auto;
  color: var(--green); font-weight: 800;
  opacity: 0; transition: opacity 200ms ease;
}
.mlops-decision-session-confirm--shown { opacity: 1; }

/* Demote old masthead — only date strip remains (top-right, slim) */
.mlops-masthead { display: none; }
.mlops-dateline {
  font-family: var(--mono); font-size: 9px; color: var(--text-3);
  letter-spacing: 1.2px; text-transform: uppercase;
  text-align: right; margin-top: -8px;
}

/* HOL-45 — Filter/sort + threshold transparency. Burt: "moment a reviewer
   wants to see 'only ACUTE rows' the surface is gravel." Gigerenzer:
   "0.85 GINI needs a stats card the surface doesn't provide." */

/* (a) Filter strip — sits at the top of each filterable pane body */
.pane-filter-strip {
  display: flex; gap: 4px; align-items: center;
  padding: 4px 0 8px 0;
  border-bottom: 1px dashed var(--border);
  margin-bottom: 6px;
  font-family: var(--mono); font-size: 9px;
}
.pane-filter-label { color: var(--text-3); letter-spacing: 0.6px;
                     text-transform: uppercase; margin-right: 4px; }
.pane-filter-btn {
  font-family: var(--mono); font-size: 9px; font-weight: 700;
  letter-spacing: 0.6px;
  padding: 1px 6px;
  background: transparent;
  color: var(--text-3);
  border: 1px solid var(--border);
  border-radius: 2px;
  cursor: pointer;
  transition: all 100ms ease;
}
.pane-filter-btn:hover { color: var(--text); border-color: var(--text-2); }
.pane-filter-btn[data-active="true"] {
  background: rgba(0, 183, 245, 0.15);
  color: var(--blue); border-color: var(--blue);
}
.pane-row-hidden { display: none !important; }

/* (b) Sortable column headers in SYNTHESIS table */
.govern-table th.sortable {
  cursor: pointer; user-select: none;
  position: relative; padding-right: 14px;
}
.govern-table th.sortable:hover { color: var(--text-2); }
.govern-table th.sortable::after {
  content: " ↕"; opacity: 0.4; font-size: 9px;
}
.govern-table th.sortable[data-sort="asc"]::after  { content: " ↑"; opacity: 1;
                                                     color: var(--blue); }
.govern-table th.sortable[data-sort="desc"]::after { content: " ↓"; opacity: 1;
                                                     color: var(--blue); }

/* (c) Threshold tooltip — leverage native title; styled cursor hint */
.threshold-token {
  cursor: help;
  border-bottom: 1px dotted var(--text-3);
}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Pane renderers — each pane is one box obeying the 4-layer discipline
# ─────────────────────────────────────────────────────────────────────────────

def render_drift_pane(packs: list[dict]) -> str:
    """Pane 1 — DRIFT MONITORS. Per-cell COHORT-DISAGGREGATED sparklines
    (HOL-41) — multiple lines per row showing each age-band's trend so
    O'Neil's single-subgroup-bleeding case is visible at a glance."""
    # HOL-41 cohort legend (top of body) + HOL-43 cohort-solo data-cohort attr
    legend_swatches = "".join(
        f'<span class="drift-legend-swatch" data-cohort="{_e(label)}">'
        f'<span class="drift-legend-dot" style="background:{c};"></span>'
        f'<span>{_e(label)}</span>'
        f'</span>'
        for label, c in zip(_COHORT_LABELS, _COHORT_COLORS)
    )
    # HOL-43 — window scrubber + cohort legend share the top strip
    scrubber_html = (
        f'<div class="window-scrubber">'
        f'<span class="window-scrubber-label">window</span>'
        f'<button class="window-scrubber-btn" data-window="7d" type="button">7d</button>'
        f'<button class="window-scrubber-btn" data-window="14d" type="button" '
        f'data-active="true">14d</button>'
        f'<button class="window-scrubber-btn" data-window="30d" type="button">30d</button>'
        f'</div>'
    )
    legend_html = (
        f'<div class="drift-legend">'
        f'<span class="drift-legend-label">age_band</span>'
        f'{legend_swatches}'
        f'<span class="drift-legend-baseline">'
        f'<span class="drift-legend-baseline-line"></span>'
        f'<span>30-day baseline</span>'
        f'</span>'
        f'{scrubber_html}'
        f'</div>'
    )

    drift_rows = []
    worst_delta = 0
    worst_pack = None
    for p in packs[:5]:  # 5 rows fit cleanly with the bigger sparkline
        cell_series = drift_series(p["meta"]["pack_name"])
        today, week_ago = cell_series[-1], cell_series[-8]
        delta = today - week_ago
        color = "var(--red)" if abs(delta) > 5 else (
                 "var(--amber)" if abs(delta) > 2 else "var(--green)")
        if abs(delta) > abs(worst_delta):
            worst_delta = delta
            worst_pack = p
        h = p["hypothesis"] or {}
        cell = _e(str(h.get("cell_id", "?")))
        sig = _e(h.get("signature_id", "—").replace("_", " "))
        # HOL-41: per-cohort series + cell-aggregated baseline
        # HOL-43: render 3 windows ([7d][14d][30d]); CSS toggles which
        # is visible based on body[data-window]. Default 14d.
        baseline_30d = sum(cell_series) / len(cell_series)
        spark_parts = []
        for win_n, win_label in [(7, "7d"), (14, "14d"), (30, "30d")]:
            cs_list = [
                cohort_drift_series_n(p["meta"]["pack_name"], cohort, win_n)
                for cohort in _COHORT_LABELS
            ]
            svg = multi_sparkline_svg(
                cs_list, _COHORT_COLORS,
                width=240, height=28, baseline=baseline_30d,
                labels=_COHORT_LABELS,
            )
            # Inject the data-window attribute into the SVG root tag
            svg_tagged = svg.replace(
                '<svg class="body-sparkline"',
                f'<svg class="body-sparkline" data-window="{win_label}"',
                1,
            )
            spark_parts.append(svg_tagged)
        spark = "".join(spark_parts)
        # HOL-39: cell-id is now a click-target; row carries data-cell-id
        # HOL-45: per-row severity for filter + delta value carries threshold tooltip
        row_sev = classify_row_severity_drift(delta)
        delta_tooltip = THRESHOLD_RULES.get(f"DRIFT_{row_sev}", "")
        drift_rows.append(
            f'<div class="drift-cell cell-row pane-filterable" '
            f'data-cell-id="{cell}" data-severity="{row_sev}" '
            f'data-filter-scope="drift">'
            f'<span class="drift-cell-label">'
            f'<a class="cell-link" href="#cell-{cell}" data-cell-id="{cell}">cell {cell}</a>'
            f' · {sig}</span>'
            f'<span class="drift-cell-spark">{spark}</span>'
            f'<span class="drift-cell-val threshold-token" '
            f'style="color:{color};" title="{_e(delta_tooltip)}">'
            f'{delta:+d}pp</span>'
            f'</div>'
        )

    # HOL-40 — narrative severity gradient driven by worst-cell delta
    drift_sev = classify_drift_severity(worst_delta)
    narrative = ""
    if worst_pack:
        series = drift_series(worst_pack["meta"]["pack_name"])
        narrative = render_severity_narrative(
            drift_sev,
            drift_narrative(worst_pack["meta"]["pack_name"], series),
        )
    elif drift_sev == "NOMINAL":
        narrative = render_severity_narrative("NOMINAL", "")

    # HOL-45 — pane filter strip
    drift_filter = render_filter_strip(
        scope="drift",
        options=[("all", "ALL"), ("ACUTE", "ACUTE only"),
                 ("ESCALATE", "≥ESCALATE"), ("WATCH", "≥WATCH")],
    )

    return render_box(
        header=box_header("DRIFT MONITORS", "14-day window"),
        accent_color="var(--blue)",
        headline=headline_stat_card(
            label="WORST-CELL DELTA · 7-DAY",
            value=f"{worst_delta:+d}pp",
            delta=f"on cell {(worst_pack['hypothesis'] or {}).get('cell_id','?') if worst_pack else '—'}",
            traj="↗ DRIFTING" if abs(worst_delta) > 5 else "→ STABLE",
            meta_left=f"{len(packs)} cells monitored",
            meta_right=NOW,
            progress_pct=min(100, abs(worst_delta) * 10),
        ),
        body=drift_filter + legend_html + "".join(drift_rows) + narrative,
        footer=box_footer(
            "frictionbench v0.1", NOW, live=True,
            note="Drift baselines from pulse.frictionbench.scoring",
        ),
    )


def render_fairness_pane(packs: list[dict]) -> str:
    """Pane 2 — FAIRNESS RE-CHECK. Per-pack metrics + worst-pack narrative.

    HOL-46 — Raskin's R1+R2 carryover: "FAIRNESS RE-CHECK still leads with
    three competing numbers at equal visual weight. Pick one." Header now
    rebuilt with a single dominant primary KPI (worst equalised-odds) and
    PASS/FAIL counts demoted to supporting annotation. Gigerenzer's "0.85
    GINI requires a stats card" closed via threshold tooltip on the
    primary value.
    """
    FLOOR = 0.85
    fair_records = [(p, fairness_record(p["meta"]["pack_name"])) for p in packs]
    alerts = [(p, f) for p, f in fair_records if f["deviation_alert"]]
    n_alerts = len(alerts)
    worst_pack, worst_fair = (alerts[0] if alerts else fair_records[0])

    # Per-metric distribution (count of packs below 0.85 floor)
    below_dp = sum(1 for _, f in fair_records if f["demographic_parity"] < FLOOR)
    below_eo = sum(1 for _, f in fair_records if f["equalised_odds"] < FLOOR)
    below_cc = sum(1 for _, f in fair_records if f["calibration_by_cohort"] < FLOOR)

    # HOL-40 — severity driven by deviation count
    fair_sev = classify_fairness_severity(n_alerts)
    narrative = render_severity_narrative(
        fair_sev,
        fairness_narrative(worst_pack["meta"]["pack_name"], worst_fair),
    )

    # HOL-46 — primary KPI = worst pack's equalised-odds (the floor-breach
    # signal). Single dominant number; PASS/FAIL counts move into meta_left
    # at the demoted supporting weight provided by headline_stat_card.
    worst_eo = min(f["equalised_odds"] for _, f in fair_records)
    n_pass = sum(1 for _, f in fair_records if f["equalised_odds"] >= FLOOR)
    n_fail = len(fair_records) - n_pass
    eo_delta = worst_eo - FLOOR  # negative = below floor
    delta_color = "var(--red)" if eo_delta < 0 else "var(--green)"
    delta_arrow = "↓" if eo_delta < 0 else "↑"
    delta_str = (
        f'<span style="color:{delta_color};" class="threshold-token" '
        f'title="{_e(THRESHOLD_RULES["equalised_odds"])}">'
        f'{delta_arrow} {eo_delta:+.2f} vs {FLOOR:.2f} floor</span>'
    )
    traj_str = "↘ BELOW FLOOR" if eo_delta < 0 else "→ WITHIN FLOOR"
    meta_left_str = (
        f'<span style="color:var(--green); font-weight:700;">{n_pass} passing</span>'
        f' · '
        f'<span style="color:var(--red); font-weight:700;">{n_fail} fail</span>'
        f' · across {len(packs)} packs'
    )

    return render_box(
        header=box_header("FAIRNESS RE-CHECK", "30-day window"),
        accent_color="var(--amber)" if n_alerts else "var(--green)",
        # HOL-46 — primary stat card replaces the 3-chip equal-weight strip
        headline=headline_stat_card(
            label="WORST EQUALISED-ODDS",
            value=f"{worst_eo:.2f}",
            delta=delta_str,
            traj=traj_str,
            meta_left=meta_left_str,
            meta_right=NOW,
            progress_pct=int(worst_eo * 100),
        ),
        body=body_kpi_tiles([
            (f"{below_dp}/{len(packs)}", "DEM PARITY",  "below floor",
             "var(--red)" if below_dp else "var(--green)"),
            (f"{below_eo}/{len(packs)}", "EQ ODDS",     "below floor",
             "var(--red)" if below_eo else "var(--green)"),
            (f"{below_cc}/{len(packs)}", "CALIBRATION", "below floor",
             "var(--red)" if below_cc else "var(--green)"),
        ]) + narrative + body_lines([
            ("Methods registry: pulse.convergence — demographic_parity, "
             "equalised_odds, calibration_by_cohort", "var(--text-3)"),
        ]),
        footer=box_footer(
            "convergence v0.1", NOW, live=True,
            note=f"Re-evaluation every 30 days · cohort axes: age_band · gender · ethnicity_band",
        ),
    )


def render_lineage_pane(packs: list[dict]) -> str:
    """Pane 3 — LINEAGE VERIFIER. Hash-chain health + broken alerts."""
    rows = [(p, lineage_status(p["meta"]["pack_name"], p["sha256"])) for p in packs]
    broken = [(p, ls) for p, ls in rows if ls["chain_status"] == "BROKEN"]
    n_broken = len(broken)
    n_verified = len(packs) - n_broken
    chain_health_pct = int(100 * n_verified / max(len(packs), 1))

    # Worst pack (first broken, or just first if none broken)
    detail_rows = []
    for p, ls in rows[:5]:
        h = p["hypothesis"] or {}
        cell = _e(str(h.get("cell_id", "?")))
        sha_short = _e(short_hash(p["sha256"]))
        # HOL-39: cell-id is a click-target; row carries data-cell-id
        # HOL-43: hash is a click-target; expands chain ancestry inline
        ancestry = lineage_chain_ancestry(p["meta"]["pack_name"], p["sha256"])
        chain_rows = []
        for i, anc in enumerate(ancestry):
            arrow = ('<span class="hash-chain-arrow">↑ parent</span>'
                     if i < len(ancestry) - 1 else
                     '<span class="hash-chain-arrow">root</span>')
            chain_rows.append(
                f'<div class="hash-chain-row">'
                f'<span class="hash-chain-sha">{_e(anc["sha"])}</span>'
                f'<span class="hash-chain-pipeline">{_e(anc["pipeline"])}</span>'
                f'<span class="hash-chain-dataset">{_e(anc["dataset"])}</span>'
                f'<span class="hash-chain-date">{_e(anc["sealed_at"])}</span>'
                f'</div>'
                f'<div class="hash-chain-row">{arrow}</div>'
            )
        chain_html = (
            f'<div class="hash-chain" data-chain-for="{cell}">'
            f'{"".join(chain_rows)}'
            f'</div>'
        )
        # HOL-45: per-row severity (BROKEN→ACUTE, VERIFIED→NOMINAL) +
        # threshold tooltip on the chain_status badge
        row_sev = "ACUTE" if ls["chain_status"] == "BROKEN" else "NOMINAL"
        status_tip = THRESHOLD_RULES.get(ls["chain_status"], "")
        detail_rows.append(
            f'<div class="drift-cell cell-row pane-filterable" '
            f'data-cell-id="{cell}" data-severity="{row_sev}" '
            f'data-filter-scope="lineage">'
            f'<span class="drift-cell-label">'
            f'<a class="cell-link" href="#cell-{cell}" data-cell-id="{cell}">cell {cell}</a>'
            f' · <a class="hash-link" href="#" data-chain-toggle="{cell}" '
            f'title="Expand upstream chain">sha:{sha_short}</a></span>'
            f'<span class="govern-badge threshold-token" '
            f'style="color:{ls["color"]};" title="{_e(status_tip)}">'
            f'{ls["chain_status"]}</span>'
            f'<span class="drift-cell-val" style="color:var(--text-3); width:auto; '
            f'text-align:right; font-size:9px;">depth {ls["chain_depth"]}</span>'
            f'</div>'
            f'{chain_html}'
        )

    # HOL-45 — pane filter strip
    lineage_filter = render_filter_strip(
        scope="lineage",
        options=[("all", "ALL"), ("ACUTE", "BROKEN only"),
                 ("NOMINAL", "VERIFIED only")],
    )

    return render_box(
        header=box_header("LINEAGE VERIFIER", "hash-chain integrity"),
        accent_color="var(--red)" if n_broken else "var(--green)",
        headline=headline_stat_card(
            label="CHAIN HEALTH",
            value=f"{n_verified}/{len(packs)}",
            delta=f"{n_broken} broken" if n_broken else "all chains verified",
            traj="↘ DEGRADED" if n_broken else "→ STABLE",
            meta_left="hash-anchored · regulator-defensible",
            meta_right=NOW,
            progress_pct=chain_health_pct,
        ),
        # HOL-40 — severity driven by BROKEN count (0 → NOMINAL → single-token render)
        body=lineage_filter + "".join(detail_rows) + render_severity_narrative(
            classify_lineage_severity(n_broken),
            (f'<strong>What changed:</strong> {n_broken} pack chain'
             f'{"s" if n_broken != 1 else ""} reported BROKEN. '
             f'<strong>For whom:</strong> any reviewer or regulator querying '
             f'these packs gets a chain-integrity failure. '
             f'<strong>Evidence:</strong> lineage_verifier.verify() output. '
             f'<strong>Response:</strong> trace + reseal chain anchors before next promotion.'),
        ),
        footer=box_footer(
            "lineage v0.1", NOW, live=True,
            note="pulse.lineage verifier · synthesis-pending packs excluded",
        ),
    )


def render_synthesis_pane(packs: list[dict]) -> str:
    """Pane 4 — SYNTHESIS-MODE GOVERNANCE. Per-pack table of synthesis-mode +
    attestation status. Critical before any LLM_AUGMENTED prod enable."""
    rows = [(p, synthesis_governance(p["meta"]["pack_name"])) for p in packs]
    n_llm = sum(1 for _, g in rows if g["synthesis_mode"] == "LLM_AUGMENTED")
    n_det = len(packs) - n_llm
    n_certified = sum(1 for _, g in rows if g["attestation"] == "certified")

    table_rows = []
    n_actionable = 0
    for p, g in rows[:6]:
        h = p["hypothesis"] or {}
        cell = _e(str(h.get("cell_id", "?")))
        # HOL-42: PENDING rows get inline action cluster; resolved rows
        # show "—". JS swaps the row state in-session when buttons are clicked.
        if g["is_actionable"]:
            n_actionable += 1
            actions_cell = (
                f'<td><span class="govern-actions" data-cell-id="{cell}">'
                f'<button class="govern-action-btn govern-action-btn--attest" '
                f'data-action="attest" data-cell-id="{cell}" type="button">Attest</button>'
                f'<button class="govern-action-btn govern-action-btn--challenge" '
                f'data-action="challenge" data-cell-id="{cell}" type="button">Challenge</button>'
                f'<button class="govern-action-btn govern-action-btn--defer" '
                f'data-action="defer" data-cell-id="{cell}" type="button">Defer</button>'
                f'</span></td>'
            )
        else:
            actions_cell = '<td><span class="govern-actions-none">—</span></td>'
        # HOL-39: row carries data-cell-id; cell column is the click-target
        # HOL-45: per-row severity for filter + threshold tooltip on attestation
        row_sev = attestation_severity(g["attestation"])
        att_tip = THRESHOLD_RULES.get(g["attestation"], "")
        mode_tip = THRESHOLD_RULES.get(g["synthesis_mode"], "")  # may be empty
        table_rows.append(
            f'<tr class="cell-row pane-filterable" data-cell-id="{cell}" '
            f'data-row-state="pending" data-severity="{row_sev}" '
            f'data-filter-scope="synthesis" '
            f'data-sort-cell="{cell}" '
            f'data-sort-mode="{_e(g["synthesis_mode"])}" '
            f'data-sort-attestation="{_e(g["attestation"])}" '
            f'data-sort-reviewed="{_e(g["reviewed_date"])}">'
            f'<td><a class="cell-link" href="#cell-{cell}" data-cell-id="{cell}">cell {cell}</a></td>'
            f'<td><span class="govern-badge threshold-token" '
            f'style="color:{g["mode_color"]};" title="{_e(mode_tip)}">'
            f'{g["synthesis_mode"]}</span></td>'
            f'<td><span class="govern-badge threshold-token" '
            f'style="color:{g["att_color"]};" title="{_e(att_tip)}">'
            f'{g["attestation"]}</span></td>'
            f'<td>{_e(g["reviewer"])}</td>'
            f'<td>{_e(g["reviewed_date"])}</td>'
            f'{actions_cell}'
            f'</tr>'
        )
    # HOL-45 — sortable column headers; data-sort-key matches the
    # data-sort-* attrs on rows, JS handler reorders tbody children.
    table_html = (
        '<table class="govern-table" data-sortable-table="synthesis">'
        '<thead><tr>'
        '<th class="sortable" data-sort-key="cell">cell</th>'
        '<th class="sortable" data-sort-key="mode">mode</th>'
        '<th class="sortable" data-sort-key="attestation">attestation</th>'
        '<th>reviewer</th>'
        '<th class="sortable" data-sort-key="reviewed">reviewed</th>'
        '<th>actions</th>'
        '</tr></thead>'
        f'<tbody>{"".join(table_rows)}</tbody>'
        '</table>'
        # HOL-42: session log tray — JS updates count + last action
        f'<div class="govern-session-log" id="govern-session-log" '
        f'data-pending="{n_actionable}">'
        f'session log · 0 decisions recorded · '
        f'<span class="govern-session-log-count">{n_actionable}</span> pending'
        f'</div>'
    )

    # HOL-40 — severity driven by LLM_AUGMENTED count
    gate_note = render_severity_narrative(
        classify_synthesis_severity(n_llm),
        (f'<strong>v1 immutability gate:</strong> {n_llm} LLM_AUGMENTED pack'
         f'{"s" if n_llm != 1 else ""} flagged. Per pulse/synthesis/SYNTHESIS_DESIGN.md '
         f'the v1 gate refuses synthesis_mode: llm_augmented in decision packs. '
         f'<strong>Response:</strong> '
         f'hold packs out of prod; route through governance review before enabling.')
    )

    # HOL-45 — pane filter strip for SYNTHESIS
    synth_filter = render_filter_strip(
        scope="synthesis",
        options=[("all", "ALL"), ("PENDING", "PENDING only")],
    )

    return render_box(
        header=box_header("SYNTHESIS GOVERNANCE", "per-pack attestation"),
        accent_color="var(--green)" if n_llm == 0 else "var(--amber)",
        headline=headline_chip_strip([
            (str(n_det),       "DETERMINISTIC", "var(--green)"),
            (str(n_llm),       "LLM_AUGMENTED", "var(--red)"),
            (str(n_certified), "CERTIFIED",     "var(--teal)"),
        ]),
        body=synth_filter + table_html + gate_note,
        footer=box_footer(
            "synthesis v0.1", NOW, live=True,
            note=f"All packs declare synthesis_mode · attestation pinned per review",
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Top nav + masthead (same identity strip as Workspace + Home)
# ─────────────────────────────────────────────────────────────────────────────

def render_topnav() -> str:
    return f"""
<header class="home-topnav">
  <span class="brand-logo">CJI&nbsp;PULSE</span>
  <span class="topnav-spacer"></span>
  <button class="topnav-icon" type="button" title="Search packs (/)">⌕</button>
  <button class="topnav-icon" type="button" title="Notifications">🔔</button>
  <details class="topnav-glossary">
    <summary class="topnav-icon topnav-glossary-trigger" title="Status glossary (full token dictionary)">Aa</summary>
    <div class="topnav-glossary-panel">
      <div class="topnav-glossary-panel-header">STATUS GLOSSARY</div>
      <div>{render_glossary_panel()}</div>
    </div>
  </details>
  <button class="topnav-icon" type="button" title="Canvas guide">?</button>
  <button class="topnav-icon" type="button" title="Settings">⚙</button>
  <button class="topnav-avatar" type="button" title="Hussain Ahmed">HA</button>
</header>"""


def render_masthead() -> str:
    """Deprecated by HOL-44 — kept for back-compat; CSS hides it. Date
    strip moved into render_decision_frame() top-right corner."""
    today = _dt.date.today().strftime("%A · %d %b %Y")
    return f'<div class="mlops-masthead">MLOps Console · {today} · {NOW}</div>'


def render_decision_frame(packs: list[dict]) -> str:
    """HOL-44 — Top-of-page decision frame. Replaces the bare procurement-gate
    masthead with a Young/Burt/Rock-aligned "why you are here today" framing.

    Composition (matches ticket acceptance):
      - Trigger sentence — computed from worst-cell drift + flagged count
      - Decision frame — 3-button cluster [Approve 14d / Committee / Retrain]
      - Session badge — reviewer + session start + decisions logged
    """
    # Compute trigger from drift (worst-cell pack)
    worst_delta = 0
    worst_pack = None
    for p in packs[:5]:
        cs = drift_series(p["meta"]["pack_name"])
        delta = cs[-1] - cs[-8]
        if abs(delta) > abs(worst_delta):
            worst_delta = delta
            worst_pack = p

    sev = classify_drift_severity(worst_delta)  # NOMINAL/WATCH/ESCALATE/ACUTE
    sev_color = {
        "ACUTE":    "var(--red)",
        "ESCALATE": "var(--amber)",
        "WATCH":    "var(--amber)",
        "NOMINAL":  "var(--green)",
    }[sev]
    frame_mod = f"mlops-decision-frame--{sev.lower()}" if sev in ("ACUTE", "ESCALATE") else ""

    pack_name = worst_pack["meta"]["pack_name"] if worst_pack else "—"
    cell_id = (worst_pack["hypothesis"] or {}).get("cell_id", "?") if worst_pack else "?"

    # Count cohorts below floor across all packs (matches FAIRNESS pane logic)
    cohorts_below = 0
    for p in packs:
        f_ = fairness_record(p["meta"]["pack_name"])
        if f_["equalised_odds"] < 0.85:
            cohorts_below += 1

    trigger = (
        f'<span class="mlops-decision-trigger-tag" style="color:{sev_color};">{sev}</span>'
        f'Model <span class="mlops-decision-trigger-pack">{_e(pack_name)}</span> '
        f'manual re-check flagged <strong>{sev}</strong> — '
        f'drift {worst_delta:+d}pp on cell {_e(str(cell_id))} · '
        f'{cohorts_below}/{len(packs)} cohorts below equalised-odds floor.'
    )

    today = _dt.date.today().strftime("%a · %d %b")
    session_start = NOW

    return f'''
<div class="mlops-decision-frame {frame_mod}">
  <div class="mlops-decision-trigger">{trigger}</div>
  <div class="mlops-decision-actions">
    <button class="mlops-decision-btn mlops-decision-btn--approve"
            data-decision="approve_14d" type="button">Approve for prod · 14d</button>
    <button class="mlops-decision-btn mlops-decision-btn--committee"
            data-decision="route_committee" type="button">Route to committee</button>
    <button class="mlops-decision-btn mlops-decision-btn--retrain"
            data-decision="request_retrain" type="button">Request retraining</button>
  </div>
  <div class="mlops-decision-session">
    <span>reviewer · <span class="mlops-decision-session-reviewer">HA · Hussain Ahmed</span></span>
    <span>session · {today} · started {session_start}</span>
    <span>decisions · <span class="mlops-decision-session-count" id="mlops-decision-count">0</span></span>
    <span class="mlops-decision-session-confirm" id="mlops-decision-confirm"></span>
  </div>
</div>
<div class="mlops-dateline">MLOps Console · {today} · {session_start}</div>'''


# ─────────────────────────────────────────────────────────────────────────────
# Page composition
# ─────────────────────────────────────────────────────────────────────────────

def render_page() -> str:
    packs = discover_packs()

    panes = (
        render_drift_pane(packs)
        + render_fairness_pane(packs)
        + render_lineage_pane(packs)
        + render_synthesis_pane(packs)
    )

    # HOL-35: CSS now lives in _shared (was in render_holter). MLOps no
    # longer imports anything from render_holter — Cannon's condition met.
    from holter.preview._shared import CSS as WORKSPACE_CSS

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>MLOps Console — procurement gate</title>
<style>{WORKSPACE_CSS}{CSS_EXTRA}</style>
</head>
<body>
{render_topnav()}
<main class="mlops-page">
{render_decision_frame(packs)}
<div class="mlops-grid">{panes}</div>
</main>
<script>
// HOL-39 — drill-through coupling: clicking a cell-id link toggles
// .cell-row-highlighted on EVERY .cell-row[data-cell-id="N"] across all
// 4 panes simultaneously. Vanilla JS, no library, ~15 lines.
(function () {{
  function clearAll() {{
    document.querySelectorAll('.cell-row-highlighted')
      .forEach(el => el.classList.remove('cell-row-highlighted'));
  }}
  function highlight(cellId) {{
    document.querySelectorAll('.cell-row[data-cell-id="' + cellId + '"]')
      .forEach(el => el.classList.add('cell-row-highlighted'));
  }}
  document.querySelectorAll('.cell-link').forEach(link => {{
    link.addEventListener('click', function (ev) {{
      ev.preventDefault();
      const cellId = this.getAttribute('data-cell-id');
      const wasHighlighted = document.querySelector(
        '.cell-row.cell-row-highlighted[data-cell-id="' + cellId + '"]'
      );
      clearAll();
      if (!wasHighlighted) highlight(cellId);
    }});
  }});
  // Click anywhere else clears highlight
  document.addEventListener('click', function (ev) {{
    if (!ev.target.closest('.cell-link') && !ev.target.closest('.cell-row')) {{
      clearAll();
    }}
  }});
}})();

// HOL-42 — Attest / Challenge / Defer affordance. In-session event log;
// engine wiring is PULSE's job, this surface renders the affordance + the
// in-session state change so a reviewer can record a governance decision.
window.holterEventLog = window.holterEventLog || [];

(function () {{
  const REVIEWER = 'HA';  // session reviewer initials (top-nav avatar)

  function recordAction(cellId, action, reason) {{
    const event = {{
      cell_id: cellId,
      action: action,
      reason: reason || null,
      reviewer: REVIEWER,
      timestamp: new Date().toISOString(),
    }};
    window.holterEventLog.push(event);
    console.log('[holter-event]', event);
    return event;
  }}

  function resolveRow(cellId, action) {{
    const row = document.querySelector(
      '.govern-table tr.cell-row[data-cell-id="' + cellId + '"]'
    );
    if (!row) return;
    row.setAttribute('data-row-state', action);
    row.classList.add('govern-row--resolved');
    const actionsCell = row.querySelector('td:last-child');
    if (actionsCell) {{
      actionsCell.innerHTML = '<span class="govern-resolved-badge ' +
        'govern-resolved-badge--' + action + 'ed">' +
        action.toUpperCase() + 'ED</span>';
    }}
  }}

  function updateSessionLog() {{
    const log = document.getElementById('govern-session-log');
    if (!log) return;
    const n = window.holterEventLog.length;
    const initialPending = parseInt(log.getAttribute('data-pending'), 10);
    const stillPending = Math.max(0, initialPending - n);
    const last = n ? window.holterEventLog[n - 1] : null;
    if (n === 0) {{
      log.innerHTML = 'session log · 0 decisions recorded · ' +
        '<span class="govern-session-log-count">' + initialPending +
        '</span> pending';
    }} else {{
      log.classList.add('govern-session-log--active');
      log.innerHTML = 'session log · ' +
        '<span class="govern-session-log-count">' + n + '</span> recorded · ' +
        stillPending + ' pending · last: cell ' + last.cell_id + ' ' +
        last.action.toUpperCase() +
        (last.reason ? ' (' + last.reason.slice(0, 30) + ')' : '');
    }}
  }}

  document.querySelectorAll('.govern-action-btn').forEach(btn => {{
    btn.addEventListener('click', function (ev) {{
      ev.preventDefault();
      ev.stopPropagation();
      const cellId = this.getAttribute('data-cell-id');
      const action = this.getAttribute('data-action');
      let reason = null;
      if (action === 'challenge') {{
        reason = window.prompt(
          'Challenge cell ' + cellId + ' — reason (cohort scope + concern):'
        );
        if (reason === null) return;  // user cancelled
      }}
      recordAction(cellId, action, reason);
      resolveRow(cellId, action);
      updateSessionLog();
    }});
  }});
}})();

// HOL-43 — Window scrubber [7d][14d][30d] + lineage hash click-to-expand
// chain ancestry. Three affordances, one gesture (reach into the data).
(function () {{
  // (b) Window scrubber: sets body[data-window]; CSS hides/shows the
  // matching sparkline SVG variant. Default 14d.
  document.body.setAttribute('data-window', '14d');
  document.querySelectorAll('.window-scrubber-btn').forEach(btn => {{
    btn.addEventListener('click', function (ev) {{
      ev.preventDefault();
      const win = this.getAttribute('data-window');
      document.body.setAttribute('data-window', win);
      document.querySelectorAll('.window-scrubber-btn').forEach(b =>
        b.setAttribute('data-active', b === this ? 'true' : 'false')
      );
    }});
  }});

  // (c) Hash click-to-expand: toggles .hash-chain--open on the matching
  // chain block. Cell-id key avoids opening the wrong chain in cases
  // where two rows somehow share a cell.
  document.querySelectorAll('a.hash-link[data-chain-toggle]').forEach(link => {{
    link.addEventListener('click', function (ev) {{
      ev.preventDefault();
      ev.stopPropagation();
      const cellId = this.getAttribute('data-chain-toggle');
      const chain = this.closest('.holter-box').querySelector(
        '.hash-chain[data-chain-for="' + cellId + '"]'
      );
      if (chain) chain.classList.toggle('hash-chain--open');
    }});
  }});
}})();

// HOL-44 — Top-of-page decision frame. Three model-scope decisions:
// Approve 14d / Route to committee / Request retraining. Writes the
// same window.holterEventLog used by HOL-42 (scope: 'model' vs cell-N).
(function () {{
  const countEl = document.getElementById('mlops-decision-count');
  const confirmEl = document.getElementById('mlops-decision-confirm');
  let modelDecisions = 0;

  function flashConfirm(text) {{
    if (!confirmEl) return;
    confirmEl.textContent = '✓ ' + text;
    confirmEl.classList.add('mlops-decision-session-confirm--shown');
    setTimeout(() => {{
      confirmEl.classList.remove('mlops-decision-session-confirm--shown');
    }}, 2400);
  }}

  document.querySelectorAll('.mlops-decision-btn').forEach(btn => {{
    btn.addEventListener('click', function (ev) {{
      ev.preventDefault();
      const decision = this.getAttribute('data-decision');
      window.holterEventLog = window.holterEventLog || [];
      window.holterEventLog.push({{
        scope: 'model',
        decision: decision,
        reviewer: 'HA',
        timestamp: new Date().toISOString(),
      }});
      modelDecisions += 1;
      if (countEl) countEl.textContent = modelDecisions;
      flashConfirm(decision.replace(/_/g, ' '));
      console.log('[holter-event]', window.holterEventLog[window.holterEventLog.length - 1]);
    }});
  }});
}})();

// HOL-45 — pane-scoped severity filter + sortable SYNTHESIS columns.
// Filter: pane-filter-btn click sets active filter for that scope; hides
//   .pane-filterable[data-filter-scope=X] rows whose data-severity doesn't
//   pass the rule (ALL passes everything; ESCALATE passes ESCALATE+ACUTE).
// Sort: click a th.sortable to toggle asc/desc on data-sort-(key) attrs.
(function () {{
  const severityRank = {{ NOMINAL: 0, WATCH: 1, ESCALATE: 2, ACUTE: 3, PENDING: 1 }};

  function passesFilter(rowSev, filterVal) {{
    if (filterVal === 'all') return true;
    if (filterVal === 'PENDING') return rowSev === 'PENDING';
    // For severity filters: row passes if its severity is >= filter level
    const rs = severityRank[rowSev]; const fs = severityRank[filterVal];
    if (rs === undefined || fs === undefined) return rowSev === filterVal;
    return rs >= fs;
  }}

  function applyFilter(scope, filterVal) {{
    document.querySelectorAll(
      '.pane-filterable[data-filter-scope="' + scope + '"]'
    ).forEach(row => {{
      const rowSev = row.getAttribute('data-severity') || 'NOMINAL';
      row.classList.toggle('pane-row-hidden', !passesFilter(rowSev, filterVal));
    }});
  }}

  document.querySelectorAll('.pane-filter-btn').forEach(btn => {{
    btn.addEventListener('click', function (ev) {{
      ev.preventDefault();
      const scope = this.getAttribute('data-filter-scope');
      const val = this.getAttribute('data-filter-value');
      // Toggle active state for the scope's button group
      document.querySelectorAll(
        '.pane-filter-btn[data-filter-scope="' + scope + '"]'
      ).forEach(b => b.setAttribute(
        'data-active', b === this ? 'true' : 'false'
      ));
      applyFilter(scope, val);
    }});
  }});

  // Sort: synthesis table columns
  document.querySelectorAll('th.sortable[data-sort-key]').forEach(th => {{
    th.addEventListener('click', function (ev) {{
      ev.preventDefault();
      const table = this.closest('table');
      const key = this.getAttribute('data-sort-key');
      const current = this.getAttribute('data-sort');
      const next = current === 'asc' ? 'desc' : 'asc';
      // Reset other headers
      table.querySelectorAll('th.sortable').forEach(t =>
        t.removeAttribute('data-sort')
      );
      this.setAttribute('data-sort', next);
      // Reorder tbody
      const tbody = table.querySelector('tbody');
      const rows = Array.from(tbody.querySelectorAll('tr'));
      rows.sort((a, b) => {{
        const va = a.getAttribute('data-sort-' + key) || '';
        const vb = b.getAttribute('data-sort-' + key) || '';
        // Numeric if both parse as numbers
        const na = parseFloat(va); const nb = parseFloat(vb);
        const numeric = !isNaN(na) && !isNaN(nb);
        const cmp = numeric ? (na - nb) : va.localeCompare(vb);
        return next === 'asc' ? cmp : -cmp;
      }});
      rows.forEach(r => tbody.appendChild(r));
    }});
  }});
}})();
</script>
</body>
</html>
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "index.html"
    html = render_page()
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out}  ({len(html):,} bytes)")


if __name__ == "__main__":
    main()

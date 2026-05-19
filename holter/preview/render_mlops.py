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
                        baseline_color: str = "rgba(180,200,210,0.4)") -> str:
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
    for series, color in zip(series_list, colors):
        pts = " ".join(
            f"{i*step:.1f},{height - ((v - vmin) / span) * height:.1f}"
            for i, v in enumerate(series)
        )
        polylines.append(
            f'<polyline points="{pts}" fill="none" '
            f'stroke="{color}" stroke-width="1.4" opacity="0.85"/>'
        )

    baseline_svg = ""
    if baseline is not None:
        by = height - ((baseline - vmin) / span) * height
        baseline_svg = (
            f'<line x1="0" y1="{by:.1f}" x2="{width}" y2="{by:.1f}" '
            f'stroke="{baseline_color}" stroke-width="1" stroke-dasharray="2,3"/>'
        )

    return (
        f'<svg class="body-sparkline" viewBox="0 0 {width} {height}" '
        f'width="100%" height="{height}" preserveAspectRatio="none">'
        f'{baseline_svg}'
        f'{"".join(polylines)}'
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
        attestation = "independently_assessed" if (h % 5) else "certified"
        att_color = "var(--green)" if attestation == "certified" else "var(--teal)"
    return {
        "synthesis_mode":  mode,
        "mode_color":      "var(--red)" if is_llm else "var(--green)",
        "attestation":     attestation,
        "att_color":       att_color,
        "reviewer":        "MRM-A · J. Patel" if (h % 3) else "MRM-B · S. Khan",
        "reviewed_date":   "2026-04-22" if (h % 5) else "2026-05-08",
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
"""


# ─────────────────────────────────────────────────────────────────────────────
# Pane renderers — each pane is one box obeying the 4-layer discipline
# ─────────────────────────────────────────────────────────────────────────────

def render_drift_pane(packs: list[dict]) -> str:
    """Pane 1 — DRIFT MONITORS. Per-cell COHORT-DISAGGREGATED sparklines
    (HOL-41) — multiple lines per row showing each age-band's trend so
    O'Neil's single-subgroup-bleeding case is visible at a glance."""
    # HOL-41 cohort legend (top of body)
    legend_swatches = "".join(
        f'<span class="drift-legend-swatch">'
        f'<span class="drift-legend-dot" style="background:{c};"></span>'
        f'<span>{_e(label)}</span>'
        f'</span>'
        for label, c in zip(_COHORT_LABELS, _COHORT_COLORS)
    )
    legend_html = (
        f'<div class="drift-legend">'
        f'<span class="drift-legend-label">age_band</span>'
        f'{legend_swatches}'
        f'<span class="drift-legend-baseline">'
        f'<span class="drift-legend-baseline-line"></span>'
        f'<span>30-day baseline</span>'
        f'</span>'
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
        # HOL-41: per-cohort 14-day series + cell-aggregated baseline
        cohort_series_list = [
            cohort_drift_series(p["meta"]["pack_name"], cohort)
            for cohort in _COHORT_LABELS
        ]
        baseline_30d = sum(cell_series) / len(cell_series)
        spark = multi_sparkline_svg(
            cohort_series_list, _COHORT_COLORS,
            width=240, height=28, baseline=baseline_30d,
        )
        drift_rows.append(
            f'<div class="drift-cell">'
            f'<span class="drift-cell-label">cell {cell} · {sig}</span>'
            f'<span class="drift-cell-spark">{spark}</span>'
            f'<span class="drift-cell-val" style="color:{color};">'
            f'{delta:+d}pp</span>'
            f'</div>'
        )

    narrative = ""
    if worst_pack:
        series = drift_series(worst_pack["meta"]["pack_name"])
        narrative = (
            f'<div class="mlops-narrative">'
            f'{drift_narrative(worst_pack["meta"]["pack_name"], series)}'
            f'</div>'
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
        body=legend_html + "".join(drift_rows) + narrative,
        footer=box_footer(
            "frictionbench v0.1", NOW, live=True,
            note="Drift baselines from pulse.frictionbench.scoring",
        ),
    )


def render_fairness_pane(packs: list[dict]) -> str:
    """Pane 2 — FAIRNESS RE-CHECK. Per-pack metrics + worst-pack narrative."""
    fair_records = [(p, fairness_record(p["meta"]["pack_name"])) for p in packs]
    alerts = [(p, f) for p, f in fair_records if f["deviation_alert"]]
    n_alerts = len(alerts)
    worst_pack, worst_fair = (alerts[0] if alerts else fair_records[0])

    # Per-metric distribution (count of packs below 0.85 floor)
    below_dp = sum(1 for _, f in fair_records if f["demographic_parity"] < 0.85)
    below_eo = sum(1 for _, f in fair_records if f["equalised_odds"] < 0.85)
    below_cc = sum(1 for _, f in fair_records if f["calibration_by_cohort"] < 0.85)

    narrative = (
        f'<div class="mlops-narrative">'
        f'{fairness_narrative(worst_pack["meta"]["pack_name"], worst_fair)}'
        f'</div>'
    )

    return render_box(
        header=box_header("FAIRNESS RE-CHECK", "30-day window"),
        accent_color="var(--amber)" if n_alerts else "var(--green)",
        headline=headline_chip_strip([
            (str(n_alerts),       "DEVIATIONS",   "var(--red)" if n_alerts else "var(--text-3)"),
            (str(len(packs)),     "PACKS",        "var(--blue)"),
            ("0.85",              "FLOOR",        "var(--green)"),
        ]),
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
        detail_rows.append(
            f'<div class="drift-cell">'
            f'<span class="drift-cell-label">cell {cell} · sha:{sha_short}</span>'
            f'<span class="govern-badge" style="color:{ls["color"]};">'
            f'{ls["chain_status"]}</span>'
            f'<span class="drift-cell-val" style="color:var(--text-3); width:auto; '
            f'text-align:right; font-size:9px;">depth {ls["chain_depth"]}</span>'
            f'</div>'
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
        body="".join(detail_rows) + (
            f'<div class="mlops-narrative">'
            f'<strong>What changed:</strong> {n_broken} pack chain'
            f'{"s" if n_broken != 1 else ""} reported BROKEN. '
            f'<strong>For whom:</strong> any reviewer or regulator querying '
            f'these packs gets a chain-integrity failure. '
            f'<strong>Evidence:</strong> lineage_verifier.verify() output. '
            f'<strong>Response:</strong> '
            f'{"trace + reseal chain anchors before next promotion" if n_broken else "no action — all chains green"}.'
            f'</div>'
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
    for p, g in rows[:6]:
        h = p["hypothesis"] or {}
        cell = _e(str(h.get("cell_id", "?")))
        table_rows.append(
            f'<tr>'
            f'<td>cell {cell}</td>'
            f'<td><span class="govern-badge" style="color:{g["mode_color"]};">'
            f'{g["synthesis_mode"]}</span></td>'
            f'<td><span class="govern-badge" style="color:{g["att_color"]};">'
            f'{g["attestation"]}</span></td>'
            f'<td>{_e(g["reviewer"])}</td>'
            f'<td>{_e(g["reviewed_date"])}</td>'
            f'</tr>'
        )
    table_html = (
        '<table class="govern-table">'
        '<thead><tr>'
        '<th>cell</th><th>mode</th><th>attestation</th>'
        '<th>reviewer</th><th>reviewed</th>'
        '</tr></thead>'
        f'<tbody>{"".join(table_rows)}</tbody>'
        '</table>'
    )

    # Engine v1 immutability gate: LLM_AUGMENTED refused in decision packs
    # per CLAUDE.md (Pulse Design Direction). Surface that explicitly.
    gate_note = (
        f'<div class="mlops-narrative">'
        f'<strong>v1 immutability gate:</strong> {n_llm} LLM_AUGMENTED pack'
        f'{"s" if n_llm != 1 else ""} flagged. Per pulse/synthesis/SYNTHESIS_DESIGN.md '
        f'the v1 gate refuses synthesis_mode: llm_augmented in decision packs. '
        f'<strong>Response:</strong> '
        f'{"hold packs out of prod; route through governance review before enabling" if n_llm else "no action — all packs DETERMINISTIC"}.'
        f'</div>'
    )

    return render_box(
        header=box_header("SYNTHESIS GOVERNANCE", "per-pack attestation"),
        accent_color="var(--green)" if n_llm == 0 else "var(--amber)",
        headline=headline_chip_strip([
            (str(n_det),       "DETERMINISTIC", "var(--green)"),
            (str(n_llm),       "LLM_AUGMENTED", "var(--red)"),
            (str(n_certified), "CERTIFIED",     "var(--teal)"),
        ]),
        body=table_html + gate_note,
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
    today = _dt.date.today().strftime("%A · %d %b %Y")
    return f"""
<div class="mlops-masthead">
  <div class="mlops-masthead-title">MLOps Console — procurement gate</div>
  <div class="mlops-masthead-dateline">{today} · {NOW}</div>
</div>"""


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
{render_masthead()}
<div class="mlops-grid">{panes}</div>
</main>
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

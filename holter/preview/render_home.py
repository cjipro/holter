"""Pulse Home (HOL-4) — first-30-seconds entry feed for all roles.

Per HOL-4 spec: news-portal aesthetic, 3-7 heterogeneous cards, NO KPI
tiles, NO trend charts, NO personalisation, NO sidebar navigation. The
job of this surface is "what changed since I last looked" — cards link
out to the Workspace (HOL-3, :8504) for investigation.

Card categories (per HOL-4 spec):
  (a) FLAGGED — signals with recommended investigation templates
  (b) AWAITING REVIEW — completed investigations needing sign-off
  (c) MLOPS — model-ops alerts (drift, calibration, etc.)

Data sources:
  - FLAGGED cards: discover_packs() + get_pack_cell() filtered to
    ACUTE / REGULATORY-FLAG / COMMERCIAL-OPPORTUNITY action tiers
  - AWAITING REVIEW: stubbed (no review-state contract in engine yet)
  - MLOPS: stubbed (Surface 4 not yet built)

Output: dist/preview/home/index.html
Serve:  py holter/preview/serve_home.py  (port 8505)
"""

from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "dist" / "preview" / "home"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# Reuse Workspace helpers — same data fabric, different presentation
from holter.preview.render_holter import (  # noqa: E402
    discover_packs,
    get_pack_cell,
    headline_pack,
    short_hash,
    _ACTION_COLORS,
    STATUS_GLOSSARY,
    tooltip_token,
    render_glossary_panel,
)

NOW = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ─────────────────────────────────────────────────────────────────────────────
# Data shaping — pulls flagged signals from the pack registry
# ─────────────────────────────────────────────────────────────────────────────

_TIER_RANK = {
    "ACUTE":                    0,
    "REGULATORY-FLAG":          1,
    "COMMERCIAL-OPPORTUNITY":   2,
    "WATCH":                    3,
    "NOMINAL":                  4,
    "NEEDS_MORE_DATA":          5,
}


def collect_flagged_signals(packs: list[dict]) -> list[dict]:
    """All packs sorted by Action tier severity, highest-first."""
    out = []
    for p in packs:
        cs = get_pack_cell(p["meta"]["pack_name"])
        if cs is None:
            continue
        out.append({
            "pack": p,
            "cell_score": cs,
            "tier": cs.action_tier,
            "rank": _TIER_RANK.get(cs.action_tier, 99),
            "journey": cs.journey_id,
        })
    out.sort(key=lambda r: r["rank"])
    return out


def select_flagged_grid(flagged: list[dict], hero: dict, n: int = 3) -> list[dict]:
    """HOL-25: deduplicate FLAGGED grid against hero's journey.

    Selection logic:
      1. Exclude the hero pack itself
      2. Prefer breadth-first by journey (one card per journey before doubling up)
      3. Among same-journey candidates, take the highest-severity one
      4. Hero's journey can still appear ONCE if there are too few other journeys
    """
    hero_pack_name = hero["pack"]["meta"]["pack_name"]
    hero_journey = hero["journey"]
    seen_journeys: set[str] = set()
    out: list[dict] = []

    # Pass 1: highest-severity card from each non-hero journey
    for sig in flagged:
        if sig["pack"]["meta"]["pack_name"] == hero_pack_name:
            continue
        if sig["journey"] == hero_journey:
            continue
        if sig["journey"] in seen_journeys:
            continue
        seen_journeys.add(sig["journey"])
        out.append(sig)
        if len(out) >= n:
            return out

    # Pass 2: fill remaining slots with any unseen card (still skipping hero pack)
    for sig in flagged:
        if sig["pack"]["meta"]["pack_name"] == hero_pack_name:
            continue
        if sig in out:
            continue
        out.append(sig)
        if len(out) >= n:
            return out

    return out


# HOL-25 — de-templated card summaries. Keyed by (signature, diagnosis); each
# combo carries 1-2 distinct sentence patterns so cards on the same journey
# read as distinct stories.
_CARD_SUMMARY_TEMPLATES: dict[tuple[str, str], list[str]] = {
    ("abandon_before_submit", "BOTH"): [
        "High-intent sessions reach the form's last field then leave — both the "
        "journey design and the in-flow support layer need attention.",
        "Late-stage abandonment driven by both the form itself and the absence "
        "of contextual help. Two-front fix.",
    ],
    ("abandon_before_submit", "JOURNEY_PROBLEM"): [
        "Sessions reach the form's last field then leave. Fix the journey design — "
        "assistance doesn't recover this kind of abandonment.",
    ],
    ("abandon_before_submit", "SUPPORT_PROBLEM"): [
        "Sessions abandon at the submission step but accept assistance when offered. "
        "Strengthen the in-flow support layer; the journey itself is sound.",
    ],
    ("abandon_before_submit", "INCONCLUSIVE"): [
        "Abandonment signal fires at the submission step. Engine can't yet separate "
        "journey-design causes from support-gap causes — collect more control sessions.",
    ],
    ("dwell_after_error", "BOTH"): [
        "Sessions stall after a validation error — both the error message itself "
        "and the inline help around it need work.",
        "Post-error dwell exceeds baseline on both the message wording and the "
        "absence of in-context recovery affordance.",
    ],
    ("dwell_after_error", "JOURNEY_PROBLEM"): [
        "Sessions stall after a validation error. The error message itself is the "
        "friction — fix the journey, not the support around it.",
    ],
    ("dwell_after_error", "SUPPORT_PROBLEM"): [
        "Sessions stall after a validation error but recover when assisted. "
        "Deploy in-context support at the moment the error fires.",
    ],
    ("dwell_after_error", "INCONCLUSIVE"): [
        "Post-error dwell detected. Engine can't yet attribute the friction to "
        "journey or support — collect more data before deciding.",
    ],
    ("multi_back_press", "BOTH"): [
        "Sessions backtrack repeatedly within a single screen — both the form "
        "flow and the help context need rework.",
    ],
    ("multi_back_press", "JOURNEY_PROBLEM"): [
        "Repeated back-presses signal users searching for fields they already left. "
        "The journey order is the friction — assistance doesn't fix navigation.",
    ],
    ("multi_back_press", "SUPPORT_PROBLEM"): [
        "Sessions show repeated back-navigation; assistance reduces it. "
        "Surface contextual help at the screens with highest re-entry.",
    ],
    ("multi_back_press", "INCONCLUSIVE"): [
        "Multi-back-press signal fires. Engine can't tell if this is journey "
        "navigation or unclear support — need more sessions.",
    ],
}


def summary_for(signature: str, diagnosis: str, pack_name: str) -> str:
    """HOL-25 — varied per-card prose. Falls back to engine recommendation."""
    templates = _CARD_SUMMARY_TEMPLATES.get((signature, diagnosis), [])
    if not templates:
        return ""  # caller falls back to placement_recommendation
    # Deterministic selection by pack-name hash so a given pack always shows the
    # same template (stable across reloads), but varies across the registry.
    idx = sum(ord(c) for c in pack_name) % len(templates)
    return templates[idx]


# ─────────────────────────────────────────────────────────────────────────────
# HOL-24 — per-card delta layer (stubs; engine returns these later)
# ─────────────────────────────────────────────────────────────────────────────

_DELTA_TIMES = ["2h ago", "6h ago", "yesterday", "3 days ago", "last week"]
_DELTA_CHANGES = [
    ("→ new",                          "var(--blue)"),
    ("↑ escalated from WATCH",         "var(--amber)"),
    ("↑ escalated from REGULATORY-FLAG", "var(--red)"),
    ("↑ escalated from COMMERCIAL-OPP", "var(--amber)"),
    ("→ existing",                     "var(--text-3)"),
    ("↓ de-escalated from ACUTE",      "var(--green)"),
]
_DELTA_CONFIDENCE = [
    ("HIGH",   "0.91", "var(--green)"),
    ("HIGH",   "0.88", "var(--green)"),
    ("MEDIUM", "0.74", "var(--amber)"),
    ("MEDIUM", "0.69", "var(--amber)"),
    ("LOW",    "0.62", "var(--red)"),
    ("LOW",    "0.55", "var(--red)"),
]


def card_delta(pack_name: str) -> dict:
    """Deterministic stub delta values for a pack. Engine returns these
    on the verdict object once pulse.workspace.feed_for(role) lands."""
    h = sum(ord(c) for c in pack_name)
    time_str = _DELTA_TIMES[h % len(_DELTA_TIMES)]
    change_str, change_color = _DELTA_CHANGES[(h // 3) % len(_DELTA_CHANGES)]
    conf_label, conf_score, conf_color = _DELTA_CONFIDENCE[(h // 7) % len(_DELTA_CONFIDENCE)]
    n_findings = 1 + (h % 7)
    return {
        "time": time_str,
        "change": change_str,
        "change_color": change_color,
        "conf_label": conf_label,
        "conf_score": conf_score,
        "conf_color": conf_color,
        "n_findings": n_findings,
    }


def render_confidence_chip(delta: dict) -> str:
    """Small chip next to the tier badge — engine confidence in the verdict."""
    return (
        f'<span class="confidence-chip" '
        f'style="color:{delta["conf_color"]};border-color:{delta["conf_color"]};" '
        f'data-tooltip="Engine confidence in this verdict — drivers visible in Workspace (HOL-19).">'
        f'{delta["conf_label"]} {delta["conf_score"]}'
        f'</span>'
    )


def render_delta_strip(delta: dict, preview_text: str = "") -> str:
    """One-line meta strip: time-since-surfaced · tier-change · preview."""
    preview_html = f'<span>· {preview_text}</span>' if preview_text else ""
    return (
        f'<div class="delta-strip">'
        f'<span>surfaced {delta["time"]}</span>'
        f'<span style="color:{delta["change_color"]};">· {delta["change"]}</span>'
        f'{preview_html}'
        f'</div>'
    )


# Stub data for AWAITING REVIEW and MLOPS — placeholders until engine
# returns review-state and MLOps surface ships
_STUB_AWAITING_REVIEW = [
    {
        "title": "International beneficiary setup · validation-error friction",
        "summary": ("Investigation pack closed by automated detector. "
                    "Reviewer needed for fairness sign-off — affected sessions "
                    "skew toward non-English-language-preference cohort."),
        "owner": "Compliance · UK Banking",
        "submitted": "4h ago",
        "pack_hint": "international_beneficiary_setup__dwell_after_error",
    },
]

_STUB_MLOPS_ALERTS = [
    {
        "title": "Diagnosis methodology — control-arm sample size drifted below threshold",
        "summary": ("Cell 10 (investments premier portfolio overview) "
                    "control arm dropped to n=540, below the 600 floor. "
                    "Verdict will mark NEEDS_MORE_DATA until backfill."),
        "severity": "WATCH",
        "raised": "1h ago",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# CSS — news-portal aesthetic (distinct from Workspace box discipline)
# ─────────────────────────────────────────────────────────────────────────────

CSS = """
:root {
  --bg:         #000810;
  --bg-strip:   #001020;
  --card-2:     #001828;
  --card:       #002A3F;
  --card-elev:  #002E47;
  --border:     #003A5C;
  --blue:       #00B7F5;
  --teal:       #4FE5C2;
  --green:      #4FE583;
  --amber:      #FFB84A;
  --red:        #FF5A6E;
  --live:       #4FE583;
  --text:       #DAE6EE;
  --text-2:     #94A8B6;
  --text-3:     #607080;
  --mono:       'JetBrains Mono', 'Fira Code', 'SF Mono', Consolas, monospace;
  --sans:       'Inter', 'SF Pro Text', system-ui, sans-serif;
  --serif:      'Source Serif Pro', Georgia, serif;
}

* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  background: var(--bg); color: var(--text);
  font-family: var(--sans);
  font-size: 14px; line-height: 1.5;
  min-height: 100vh;
}
a { color: var(--blue); text-decoration: none; }

/* ── Top nav (shared identity strip with Workspace) ─────────────────────── */
.home-topnav {
  height: 48px;
  background: var(--bg-strip);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 14px;
  padding: 0 24px;
  position: sticky; top: 0; z-index: 100;
}
.brand-logo {
  font-family: var(--mono);
  font-size: 13px; font-weight: 800;
  letter-spacing: 2px;
  color: var(--blue);
  text-shadow: 0 0 12px rgba(0,183,245,0.4);
}
.topnav-spacer { flex: 1; }
.topnav-icon, .topnav-avatar {
  background: transparent; border: 1px solid var(--border);
  color: var(--text-2); border-radius: 50%;
  width: 30px; height: 30px;
  display: inline-flex; align-items: center; justify-content: center;
  cursor: pointer; font-size: 13px;
}
.topnav-icon:hover, .topnav-avatar:hover { color: var(--text); background: var(--card); }
.topnav-avatar {
  font-family: var(--mono); font-size: 10px; font-weight: 800;
  background: var(--card); color: var(--blue);
}

/* HOL-16 glossary panel — copied from Workspace for consistency */
.topnav-glossary { position: relative; }
.topnav-glossary > summary.topnav-glossary-trigger {
  list-style: none; cursor: pointer;
  font-family: var(--mono); font-size: 13px; font-weight: 700;
}
.topnav-glossary > summary::-webkit-details-marker { display: none; }
.topnav-glossary-panel {
  position: absolute; top: calc(100% + 4px); right: 0;
  background: var(--card-2); border: 1px solid var(--blue);
  width: 520px; max-height: 72vh;
  overflow-y: auto;
  box-shadow: 0 8px 24px rgba(0,0,0,0.7);
  z-index: 220; padding: 14px 16px;
}
.topnav-glossary-panel-header {
  font-size: 10px; font-weight: 800;
  letter-spacing: 1.8px; color: var(--blue);
  text-transform: uppercase;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 10px;
}
.glossary-section { margin-bottom: 14px; }
.glossary-section-label {
  font-size: 9px; font-weight: 800; letter-spacing: 1.4px;
  color: var(--text-3); text-transform: uppercase;
  padding-bottom: 4px; margin-bottom: 6px;
  border-bottom: 1px dashed var(--border);
}
.glossary-item {
  display: grid; grid-template-columns: 150px 1fr; gap: 12px;
  padding: 4px 0; font-size: 10px;
}
.glossary-token { font-family: var(--mono); font-weight: 700; color: var(--text); }
.glossary-def { color: var(--text-2); line-height: 1.45; }

/* ── Page layout ───────────────────────────────────────────────────────── */
.home-main {
  max-width: 1240px;
  margin: 0 auto;
  padding: 32px 24px 64px;
  display: flex; flex-direction: column;
  gap: 28px;
}

/* Page-level dateline + masthead (news portal feel) */
.home-masthead {
  display: flex; align-items: baseline; justify-content: space-between;
  border-bottom: 1px solid var(--border);
  padding-bottom: 14px;
}
.home-masthead-title {
  font-family: var(--serif);
  font-size: 24px; font-weight: 700;
  color: var(--text);
  letter-spacing: 0.2px;
}
.home-masthead-dateline {
  font-family: var(--mono);
  font-size: 11px; color: var(--text-3);
  letter-spacing: 1.2px; text-transform: uppercase;
}

/* ── Section label (FLAGGED / AWAITING REVIEW / MLOPS) ─────────────────── */
.section-label {
  display: flex; align-items: center; gap: 10px;
  font-family: var(--mono);
  font-size: 10px; font-weight: 800;
  letter-spacing: 2px; text-transform: uppercase;
  color: var(--text-3);
  padding-bottom: 2px;
}
.section-label::after {
  content: ""; flex: 1; height: 1px;
  background: var(--border);
  margin-left: 6px;
}
.section-label-count {
  font-family: var(--mono);
  color: var(--text-2);
  font-weight: 700;
  background: var(--card-2);
  padding: 2px 8px; border-radius: 2px;
  font-size: 10px; letter-spacing: 0.5px;
}

/* ── HERO card (full-width, top of feed, highest-severity signal) ──────── */
.hero-card {
  background: var(--card);
  border: 1px solid var(--border);
  border-left: 4px solid var(--red);  /* overridden inline per tier */
  padding: 24px 28px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 24px;
  align-items: start;
}
.hero-card-meta {
  display: flex; align-items: center; gap: 10px;
  font-family: var(--mono); font-size: 10px;
  letter-spacing: 1.4px; text-transform: uppercase;
  color: var(--text-3);
  margin-bottom: 10px;
}
.hero-card-tier-badge {
  font-family: var(--mono); font-weight: 800;
  letter-spacing: 1.4px; font-size: 10px;
  padding: 3px 8px;
  border: 1px solid currentColor;
  border-radius: 2px;
}
.hero-card-headline {
  font-family: var(--serif);
  font-size: 28px; font-weight: 700;
  color: var(--text);
  line-height: 1.25;
  margin: 6px 0 10px;
}
.hero-card-summary {
  font-size: 14px; color: var(--text-2);
  line-height: 1.6;
  max-width: 720px;
}
.hero-card-foot {
  display: flex; align-items: center; gap: 16px;
  margin-top: 16px;
  font-family: var(--mono); font-size: 10px; color: var(--text-3);
  letter-spacing: 0.5px;
}
.hero-card-cta {
  align-self: end;
  background: var(--blue);
  color: var(--bg);
  font-family: var(--mono); font-weight: 800; letter-spacing: 1.2px;
  font-size: 11px;
  padding: 10px 18px;
  border: 0; border-radius: 2px;
  cursor: pointer;
  text-decoration: none;
  white-space: nowrap;
}
.hero-card-cta:hover { background: var(--teal); color: var(--bg); }

/* ── FEED grid — secondary cards ───────────────────────────────────────── */
.feed-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}
@media (max-width: 1100px) { .feed-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 700px)  { .feed-grid { grid-template-columns: 1fr; } }

.feed-card {
  background: var(--card-2);
  border: 1px solid var(--border);
  border-left: 3px solid var(--border);
  padding: 16px 18px;
  display: flex; flex-direction: column;
  gap: 8px;
  min-height: 220px;
}
.feed-card-meta {
  display: flex; align-items: center; gap: 8px;
  font-family: var(--mono); font-size: 9px;
  letter-spacing: 1.4px; text-transform: uppercase;
  color: var(--text-3);
}
.feed-card-tag {
  font-family: var(--mono); font-weight: 800; font-size: 9px;
  letter-spacing: 1.4px;
  padding: 2px 7px;
  border: 1px solid currentColor;
  border-radius: 2px;
}
.feed-card-tier-badge {
  font-family: var(--mono); font-weight: 800;
  font-size: 9px; letter-spacing: 1.4px;
  padding: 2px 6px;
  border: 1px solid currentColor;
  border-radius: 2px;
  margin-left: auto;
}
.feed-card-headline {
  font-family: var(--serif);
  font-size: 16px; font-weight: 600;
  color: var(--text);
  line-height: 1.3;
  margin: 4px 0;
}
.feed-card-summary {
  font-size: 12px; color: var(--text-2);
  line-height: 1.5;
  flex: 1;
}
.feed-card-foot {
  display: flex; align-items: center; gap: 12px;
  padding-top: 8px;
  margin-top: 8px;
  border-top: 1px solid var(--border);
  font-family: var(--mono); font-size: 9px; color: var(--text-3);
  letter-spacing: 0.5px;
}
.feed-card-cta {
  margin-left: auto;
  color: var(--blue);
  font-family: var(--mono); font-weight: 700; font-size: 10px;
  letter-spacing: 1px;
  text-decoration: none;
}
.feed-card-cta:hover { color: var(--teal); }

/* HOL-24 — confidence chip + delta strip */
.confidence-chip {
  font-family: var(--mono); font-weight: 800;
  font-size: 9px; letter-spacing: 1px;
  padding: 2px 7px;
  border: 1px solid currentColor;
  border-radius: 2px;
}
.delta-strip {
  display: flex; align-items: center; gap: 6px;
  font-family: var(--mono); font-size: 10px;
  letter-spacing: 0.4px;
  color: var(--text-3);
  margin-top: 6px;
}
.delta-strip > span { white-space: nowrap; }

/* Hover tooltip — reused pattern from Workspace */
[data-tooltip] { position: relative; }
[data-tooltip]:hover::after {
  content: attr(data-tooltip);
  position: absolute; bottom: 100%; left: 50%;
  transform: translateX(-50%);
  margin-bottom: 6px;
  background: var(--card-2); color: var(--text);
  border: 1px solid var(--blue);
  padding: 8px 10px; border-radius: 2px;
  font-size: 11px; line-height: 1.5;
  white-space: normal; width: max-content; max-width: 320px;
  z-index: 200;
  box-shadow: 0 4px 12px rgba(0,0,0,0.6);
  pointer-events: none;
}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Rendering helpers
# ─────────────────────────────────────────────────────────────────────────────

def screen_short(screen_id: str) -> str:
    parts = (screen_id or "").split(".")
    if len(parts) >= 3:
        return f"{parts[0]} · {parts[-2]} · {parts[-1]}"
    return screen_id


def render_topnav() -> str:
    """Same identity strip as Workspace — CJI PULSE logo + utility cluster."""
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
<div class="home-masthead">
  <div class="home-masthead-title">Pulse Home — what changed</div>
  <div class="home-masthead-dateline">{today} · {NOW}</div>
</div>"""


def render_hero(top_signal: dict) -> str:
    """The top-of-feed urgency card — highest-severity flagged signal."""
    pack = top_signal["pack"]
    cs   = top_signal["cell_score"]
    tier = cs.action_tier
    color = _ACTION_COLORS.get(tier, "var(--amber)")
    journey = cs.journey_id.replace("_", " · ")
    signature = cs.signature_id.replace("_", " ")
    # Headline reads as news. Diagnosis becomes the "why" prefix.
    _DIAG_PREFIX = {
        "SUPPORT_PROBLEM": "Support gap detected",
        "JOURNEY_PROBLEM": "Journey design gap detected",
        "BOTH":            "Journey and support gaps both detected",
        "INCONCLUSIVE":    "Friction detected, attribution unclear",
    }
    diag_prefix = _DIAG_PREFIX.get(cs.diagnosis.diagnosis, "Friction detected")
    headline = f"{diag_prefix} on {journey.title()}"
    # HOL-25 — use de-templated summary (varied per signature × diagnosis),
    # falling back to engine recommendation if no template matches.
    varied_summary = summary_for(cs.signature_id, cs.diagnosis.diagnosis,
                                  pack["meta"]["pack_name"])
    summary = (
        f'<strong>Signature:</strong> {signature}. '
        f'{varied_summary or cs.placement_recommendation}'
    )
    # HOL-25 — slug breadcrumb killed. Provenance moves to a hover-tooltip
    # on the INVESTIGATE → CTA so a curious reader can still verify lineage.
    sha = short_hash(pack["sha256"])
    provenance_tooltip = (
        f"pack: {pack['meta']['pack_name']} · sha256:{sha} · "
        f"verdict v0 · DuckDB-backed (PULSE)"
    ).replace('"', "&quot;")
    # HOL-24 — delta meta: confidence chip + time-since-surfaced + tier-change + click preview
    delta = card_delta(pack["meta"]["pack_name"])
    preview_text = f"{delta['n_findings']} sub-findings · open in Workspace"
    return f"""
<a class="hero-card" style="border-left-color:{color}; text-decoration:none; color:inherit;"
   href="http://localhost:8504/" target="_blank">
  <div>
    <div class="hero-card-meta">
      <span class="hero-card-tier-badge" style="color:{color};">
        {tooltip_token("action", tier)}
      </span>
      {render_confidence_chip(delta)}
      <span>FLAGGED · {journey}</span>
    </div>
    <div class="hero-card-headline">{headline}</div>
    <div class="hero-card-summary">{summary}</div>
    {render_delta_strip(delta, preview_text)}
  </div>
  <span class="hero-card-cta" data-tooltip="{provenance_tooltip}">INVESTIGATE →</span>
</a>"""


def render_feed_card(*, tag: str, tag_color: str, headline: str, summary: str,
                     tier: str | None = None, tier_dim: str = "action",
                     meta_left: str = "", meta_right: str = "",
                     cta_label: str = "OPEN →", accent: str = "var(--border)",
                     delta: dict | None = None, preview_text: str = "") -> str:
    """Generic feed card — reused for FLAGGED, AWAITING REVIEW, MLOPS.

    HOL-24: optional `delta` adds confidence chip beside tier badge AND
    a delta strip (time-since-surfaced + tier-change + preview) below
    the summary. `preview_text` is the "X sub-findings · ..." pre-click hint.
    """
    tier_html = ""
    if tier:
        tier_color = _ACTION_COLORS.get(tier, "var(--amber)")
        tier_html = (
            f'<span class="feed-card-tier-badge" style="color:{tier_color};">'
            f'{tooltip_token(tier_dim, tier)}</span>'
        )
    confidence_html = render_confidence_chip(delta) if delta else ""
    delta_html = render_delta_strip(delta, preview_text) if delta else ""
    return f"""
<a class="feed-card" style="border-left-color:{accent}; text-decoration:none; color:inherit;"
   href="http://localhost:8504/" target="_blank">
  <div class="feed-card-meta">
    <span class="feed-card-tag" style="color:{tag_color};">{tag}</span>
    {confidence_html}
    {tier_html}
  </div>
  <div class="feed-card-headline">{headline}</div>
  <div class="feed-card-summary">{summary}</div>
  {delta_html}
  <div class="feed-card-foot">
    <span>{meta_left}</span>
    <span>{meta_right}</span>
    <span class="feed-card-cta">{cta_label}</span>
  </div>
</a>"""


def render_flagged_feed(flagged: list[dict], hero: dict) -> str:
    """3-card grid of next-most-urgent signals (after the hero).

    HOL-25 — uses select_flagged_grid() to deduplicate against the hero's
    journey and prefer breadth across journeys, and per-card varied summary
    so the cards don't read as the same recommendation pasted three times.
    """
    grid = select_flagged_grid(flagged, hero, n=3)
    cards = []
    for sig in grid:
        pack = sig["pack"]
        cs = sig["cell_score"]
        tier = cs.action_tier
        accent = _ACTION_COLORS.get(tier, "var(--amber)")
        journey = cs.journey_id.replace("_", " · ").title()
        signature = cs.signature_id.replace("_", " ")
        varied = summary_for(cs.signature_id, cs.diagnosis.diagnosis,
                              pack["meta"]["pack_name"])
        summary = varied or cs.placement_recommendation
        if len(summary) > 180:
            summary = summary[:177] + "…"
        delta = card_delta(pack["meta"]["pack_name"])
        preview = f"{delta['n_findings']} sub-findings"
        cards.append(render_feed_card(
            tag="FLAGGED",
            tag_color="var(--red)" if tier == "ACUTE" else "var(--amber)",
            headline=f"{journey} — {signature}",
            summary=summary,
            tier=tier,
            tier_dim="action",
            meta_left=f"sha:{short_hash(pack['sha256'])}",
            meta_right=NOW,
            cta_label="INVESTIGATE →",
            accent=accent,
            delta=delta,
            preview_text=preview,
        ))
    if not cards:
        return ""
    remaining = max(0, len(flagged) - 1 - len(cards))
    count_label = f"{remaining} more in pipeline" if remaining else "all surfaced"
    return f"""
<section>
  <div class="section-label">
    Flagged signals
    <span class="section-label-count">{count_label}</span>
  </div>
  <div class="feed-grid">{"".join(cards)}</div>
</section>"""


def render_awaiting_review(items: list[dict]) -> str:
    if not items:
        return ""
    cards = []
    for it in items:
        # HOL-24 — synthetic delta for stub items (consistent shape, unique seed)
        delta = card_delta(it.get("pack_hint", it["title"]))
        cards.append(render_feed_card(
            tag="AWAITING REVIEW",
            tag_color="var(--teal)",
            headline=it["title"],
            summary=it["summary"],
            meta_left=f"owner: {it['owner']}",
            meta_right=f"closed {it['submitted']}",
            cta_label="REVIEW →",
            accent="var(--teal)",
            delta=delta,
            preview_text="1 reviewer assigned · fairness sign-off required",
        ))
    return f"""
<section>
  <div class="section-label">
    Awaiting review
    <span class="section-label-count">{len(items)}</span>
  </div>
  <div class="feed-grid">{"".join(cards)}</div>
</section>"""


def render_mlops_alerts(items: list[dict]) -> str:
    if not items:
        return ""
    cards = []
    for it in items:
        sev_color = "var(--amber)" if it["severity"] == "WATCH" else "var(--red)"
        delta = card_delta(it["title"])
        cards.append(render_feed_card(
            tag="MLOPS",
            tag_color=sev_color,
            headline=it["title"],
            summary=it["summary"],
            tier=it["severity"],
            tier_dim="risk",
            meta_left=f"raised {it['raised']}",
            meta_right="MLOps Console (HOL-6 pending)",
            cta_label="ACKNOWLEDGE →",
            accent=sev_color,
            delta=delta,
            preview_text="affects 1 cell · auto-resolves on backfill",
        ))
    return f"""
<section>
  <div class="section-label">
    MLOps alerts
    <span class="section-label-count">{len(items)}</span>
  </div>
  <div class="feed-grid">{"".join(cards)}</div>
</section>"""


# ─────────────────────────────────────────────────────────────────────────────
# Page composition
# ─────────────────────────────────────────────────────────────────────────────

def render_page() -> str:
    packs = discover_packs()
    flagged = collect_flagged_signals(packs)

    sections = []
    if flagged:
        hero = flagged[0]
        sections.append(render_hero(hero))
        sections.append(render_flagged_feed(flagged, hero))
    sections.append(render_awaiting_review(_STUB_AWAITING_REVIEW))
    sections.append(render_mlops_alerts(_STUB_MLOPS_ALERTS))

    body = "".join(sections)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Pulse Home — what changed</title>
<style>{CSS}</style>
</head>
<body>
{render_topnav()}
<main class="home-main">
{render_masthead()}
{body}
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

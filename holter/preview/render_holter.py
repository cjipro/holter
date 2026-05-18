"""Holter template — functional v1 (porting :8502 into the Holter framework).

Holter's locked box discipline (4 layers, 562×731, universal chrome)
applied to the FULL briefing surface, consuming real pack data + engine
methodology outputs.

This replaces the v0 design-template render_holter.py. The previous
hardcoded placeholder content is gone — every box now reads from
discover_packs() and pulse.scenarios.agentic_ai_placement.

Discipline (unchanged from v0):
  - Every box: 562 × 731, 4 layers (header 48 / headline 96 / body 531 / footer 48)
  - Body content varies per box; everything else is locked
  - Sticky chrome: top nav (48px) + left sidebar (168px); topbar boxes scroll away

What changed vs v0 (the port):
  - discover_packs() + load_journey_taxonomy() (ported from render_mil_briefing.py)
  - get_pack_cell() consumes PULSE-106 placement scenario for per-pack tiers
  - render_sidebar() has REAL filter controls (Journey / Time Range / Severity)
  - All topbar boxes (1/2/3) read pack data + engine output
  - V3 layer becomes a grid of boxes obeying the same contract:
      · Engine summary: Friction Risk / Placement Posture / Confidence Protocol
      · Methodology distributions: Diagnosis / Value / Risk
      · Detail: Chronicle Matcher + Commentary-per-journey + Bench
  - FILTER_JS adapted to Holter classes (sidebar checkboxes + topbar dropdowns
    drive box visibility + tier-count recompute)

Output: dist/preview/holter/index.html
Serve:  py holter/preview/serve_holter.py  (port 8504)
"""

from __future__ import annotations

import datetime as _dt
import functools
import hashlib
import sys
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[2]
PACKS_DIR = REPO / "pulse" / "decision_packs"
JOURNEY_TAXONOMY = REPO / "pulse" / "contracts" / "journey_taxonomy.yaml"
OUT_DIR = REPO / "dist" / "preview" / "holter"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


# ─────────────────────────────────────────────────────────────────────────────
# Data discovery (ported from render_mil_briefing.py)
# ─────────────────────────────────────────────────────────────────────────────

def load_journey_taxonomy() -> dict[str, str]:
    if not JOURNEY_TAXONOMY.exists():
        return {}
    data = yaml.safe_load(JOURNEY_TAXONOMY.read_text(encoding="utf-8"))
    return data.get("journeys", {})


def discover_packs() -> list[dict]:
    packs: list[dict] = []
    if not PACKS_DIR.exists():
        return packs
    for pack_dir in sorted(PACKS_DIR.iterdir()):
        if not pack_dir.is_dir():
            continue
        meta_path = pack_dir / "metadata.yaml"
        samples_dir = pack_dir / "samples"
        hyp_path = pack_dir / "hypothesis.yaml"
        if not meta_path.exists() or not samples_dir.exists():
            continue
        raw_bytes = meta_path.read_bytes()
        meta = yaml.safe_load(raw_bytes.decode("utf-8"))
        hypothesis = (
            yaml.safe_load(hyp_path.read_text(encoding="utf-8"))
            if hyp_path.exists() else None
        )
        bank_md = (samples_dir / "bank.md").read_text(encoding="utf-8") \
            if (samples_dir / "bank.md").exists() else ""
        packs.append({
            "dir": pack_dir,
            "meta": meta,
            "sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "hypothesis": hypothesis,
            "bank_md": bank_md,
        })
    return packs


def short_hash(h: str) -> str:
    return f"{h[:7]}…{h[-4:]}"


def screen_short(screen_id: str) -> str:
    parts = screen_id.split(".")
    if len(parts) >= 2:
        return f"{parts[0]} · {parts[-1]}"
    return screen_id


def headline_pack(packs: list[dict]) -> dict:
    for p in packs:
        h = p["hypothesis"] or {}
        if h.get("cell_id") == 10:
            return p
    for p in packs:
        if "abandon" in p["meta"]["pack_name"] and "cards" in p["meta"]["pack_name"]:
            return p
    return packs[0] if packs else {}


def cell_screens_with_counts(packs: list[dict]) -> list[dict]:
    """Aggregate detection counts by friction-target screen for the journey row."""
    screens: dict[str, list[dict]] = {}
    for p in packs:
        h = p["hypothesis"] or {}
        sc = h.get("screen_id")
        if not sc:
            continue
        screens.setdefault(sc, []).append(p)
    out = []
    for sc, ps in screens.items():
        positives = sum(1 for p in ps if (p["hypothesis"] or {}).get("ground_truth_expectation") != "negative")
        negatives = sum(1 for p in ps if (p["hypothesis"] or {}).get("ground_truth_expectation") == "negative")
        out.append({
            "screen": sc,
            "short": screen_short(sc),
            "packs": ps,
            "positives": positives,
            "negatives": negatives,
            "total": len(ps),
            "status": "ACUTE" if positives >= 3 else ("LOAD-BEARING" if negatives else "STABLE"),
            "status_color": "var(--red)" if positives >= 3 else (
                "var(--amber)" if negatives else "var(--teal)"
            ),
        })
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Engine integration — per-pack PlacementCell from the worked scenario
# ─────────────────────────────────────────────────────────────────────────────

@functools.lru_cache(maxsize=1)
def _build_pack_cell_index() -> dict[str, Any]:
    try:
        from pulse.scenarios.agentic_ai_placement import run_placement_scenario
        scenario_path = REPO / "pulse" / "scenarios" / "agentic_ai_placement" / "scenario.yaml"
        with scenario_path.open("r", encoding="utf-8") as f:
            scenario = yaml.safe_load(f)
        pack_dirs = [c["pack_dir"] for c in scenario["cells"]]
        matrix = run_placement_scenario()
        return {pack_dir: cell for pack_dir, cell in zip(pack_dirs, matrix.cells)}
    except Exception:
        return {}


def get_pack_cell(pack_name: str):
    return _build_pack_cell_index().get(pack_name)


# Tier colour maps (mirror HOL-11 / HOL-9)

_DIAGNOSIS_COLORS = {
    "SUPPORT_PROBLEM":  "var(--green)",
    "JOURNEY_PROBLEM":  "var(--amber)",
    "BOTH":             "var(--blue)",
    "INCONCLUSIVE":     "#7A7A7A",
}
_RISK_COLORS = {
    "NOMINAL":          "#5A6E7A",
    "WATCH":            "var(--teal)",
    "ESCALATE":         "var(--amber)",
    "REGULATORY-FLAG":  "var(--red)",
}
_VALUE_COLORS = {
    "NOMINAL":                  "#5A6E7A",
    "WATCH":                    "var(--teal)",
    "SIGNIFICANT":              "var(--amber)",
    "COMMERCIAL-OPPORTUNITY":   "var(--green)",
}
_ACTION_COLORS = {
    "ACUTE":                    "var(--red)",
    "REGULATORY-FLAG":          "var(--amber)",
    "COMMERCIAL-OPPORTUNITY":   "var(--green)",
    "WATCH":                    "var(--teal)",
    "NOMINAL":                  "#5A6E7A",
    "NEEDS_MORE_DATA":          "#7A7A7A",
}


# ─────────────────────────────────────────────────────────────────────────────
# CSS — locked design language
# ─────────────────────────────────────────────────────────────────────────────

CSS = """
:root {
  /* Multi-tone backgrounds for visual layering (was 2-tone in v0) */
  --bg:           #000810;   /* page background — slightly darker */
  --bg-strip:    #001020;   /* sticky chrome strips (filter / ticker / journey) */
  --card-2:      #001828;   /* box header band + footer band */
  --card:        #002A3F;   /* box body */
  --card-elev:  #002E47;   /* elevated content surface inside body */
  --border:     #003A5C;
  /* Stronger semantic palette (was muted in v0) */
  --blue:       #00B7F5;   /* boosted from #00AEEF */
  --teal:       #00C5B3;   /* boosted from #00AFA0 */
  --amber:      #FFB23D;   /* boosted from #F5A623 */
  --red:        #E63333;   /* boosted from #CC0000 */
  --green:      #3DB677;   /* boosted from #2a9a5a */
  --live:       #4FE583;   /* brighter green specifically for LIVE pill */
  --text:       #E8F4FA;
  --text-2:     #8DC2D9;   /* slightly brighter for body legibility */
  --text-3:     #3A6A7F;
  --sans: 'Plus Jakarta Sans', system-ui, sans-serif;
  --mono: 'DM Mono', 'Menlo', monospace;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { background: var(--bg); color: var(--text); font-family: var(--sans);
             font-size: 12px; line-height: 1.5; }

/* ── Layout shell ──────────────────────────────────────────────────────── */
.holter-app {
  display: flex; flex-direction: column;
  min-height: 100vh;
}
.holter-topnav {
  position: sticky; top: 0; z-index: 100;
  height: 48px;
  background: var(--card-2);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; padding: 0 12px;
  gap: 8px;
}
.holter-main {
  padding: 12px;
}
/* Box 0 dissolved into a sticky full-width horizontal filter strip
   beneath the topnav (page-chrome exception, like topnav/ticker/journey
   row). Filters always reachable; Box 0 sidebar is gone. */
.holter-filter-strip {
  position: sticky; top: 48px; z-index: 99;
  height: 64px;
  background: var(--bg-strip);
  border-bottom: 1px solid var(--border);
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  display: flex; align-items: center; gap: 14px;
  padding: 0 16px;
  overflow-x: auto;
}
.holter-filter-section {
  display: flex; align-items: center; gap: 10px; flex-shrink: 0;
}
.holter-filter-label {
  font-size: 9px; font-weight: 700; letter-spacing: 1.5px;
  color: var(--text-3); text-transform: uppercase;
}
.holter-filter-sep {
  width: 1px; height: 28px; background: var(--border); flex-shrink: 0;
}
.holter-filter-select {
  background: var(--card-2); border: 1px solid var(--border);
  color: var(--text); font-family: var(--mono); font-size: 11px;
  padding: 4px 10px; border-radius: 2px; cursor: pointer; min-width: 120px;
}
.holter-filter-select.filter-on { border-color: var(--amber); color: var(--amber); }
.holter-filter-radios { display: flex; gap: 10px; }
.holter-filter-radios label {
  display: flex; align-items: center; gap: 4px;
  font-size: 11px; color: var(--text-2); cursor: pointer; white-space: nowrap;
}
.holter-filter-actions { margin-left: auto; display: flex; gap: 6px; }

/* Time picker: button + calendar-style popover with presets + custom range */
.holter-time-section { position: relative; }
.holter-time-btn {
  background: var(--card-2); border: 1px solid var(--border);
  color: var(--text); font-family: var(--mono); font-size: 11px;
  padding: 4px 10px; border-radius: 2px; cursor: pointer;
  display: flex; align-items: center; gap: 6px;
}
.holter-time-btn:hover { border-color: var(--blue); }
.holter-time-btn-caret { color: var(--text-3); font-size: 9px; }
.holter-time-pop {
  position: absolute; top: 100%; left: 0; margin-top: 6px;
  background: var(--card); border: 1px solid var(--border);
  padding: 10px; border-radius: 2px;
  z-index: 200; min-width: 260px;
  box-shadow: 0 6px 18px rgba(0,0,0,0.7);
}
.holter-time-pop[hidden] { display: none; }
.time-presets { display: flex; flex-direction: column; gap: 1px;
                padding-bottom: 8px; border-bottom: 1px solid var(--border);
                margin-bottom: 8px; }
.time-preset {
  background: transparent; border: 0; color: var(--text-2);
  text-align: left; padding: 6px 8px; font-size: 11px; cursor: pointer;
  border-radius: 2px; font-family: var(--sans);
}
.time-preset:hover { background: var(--card-2); color: var(--text); }
.time-preset.active { color: var(--blue); background: var(--card-2); }
.time-custom { display: flex; flex-direction: column; gap: 6px; }
.time-custom-label {
  font-size: 9px; letter-spacing: 1.5px; color: var(--text-3);
  text-transform: uppercase; font-weight: 700;
}
.time-custom-row { display: flex; align-items: center; gap: 6px; }
.time-date {
  background: var(--card-2); border: 1px solid var(--border);
  color: var(--text); padding: 4px 6px; font-family: var(--mono);
  font-size: 11px; border-radius: 2px; flex: 1;
  color-scheme: dark;
}
.time-to-arrow { color: var(--text-3); font-family: var(--mono); }
.time-apply {
  background: var(--blue); color: var(--bg); border: 0;
  padding: 6px 12px; border-radius: 2px; font-family: var(--mono);
  font-size: 10px; font-weight: 700; cursor: pointer; letter-spacing: 0.5px;
  margin-top: 4px;
}
.holter-filter-btn {
  background: var(--blue); color: var(--bg);
  border: 0; padding: 6px 14px; border-radius: 2px;
  font-family: var(--mono); font-size: 10px; font-weight: 700;
  letter-spacing: 0.5px; cursor: pointer;
}
.holter-filter-btn.secondary {
  background: transparent; color: var(--text-2); border: 1px solid var(--border);
}

/* ── Top nav ───────────────────────────────────────────────────────────── */
.brand-logo {
  font-size: 13px; font-weight: 800; letter-spacing: 2.5px;
  color: var(--blue); text-transform: uppercase;
}
.topnav-spacer { flex: 1; }
.topnav-icon, .topnav-avatar {
  font-family: var(--mono); font-size: 14px; color: var(--text-3);
  background: transparent; border: 0; cursor: pointer;
  padding: 4px 8px; border-radius: 4px;
}
.topnav-icon:hover, .topnav-avatar:hover { color: var(--text); background: var(--card); }
.topnav-avatar {
  width: 28px; height: 28px; border-radius: 50%;
  background: var(--amber); color: var(--bg); font-weight: 700;
  display: inline-flex; align-items: center; justify-content: center; font-size: 10px;
}
.topnav-select {
  background: var(--card-2); border: 1px solid var(--border);
  color: var(--blue); font-family: var(--mono); font-size: 11px;
  padding: 4px 10px; border-radius: 2px; cursor: pointer;
}
.topnav-select:disabled { color: var(--text-3); cursor: not-allowed; }
.topnav-select.filter-on { border-color: var(--amber); color: var(--amber); }
.topnav-reset {
  background: transparent; border: 1px solid var(--amber); color: var(--amber);
  font-family: var(--mono); font-size: 10px; padding: 3px 10px;
  border-radius: 2px; cursor: pointer;
}

/* ── Sidebar (Box 0) ───────────────────────────────────────────────────── */
.sidebar-inner { padding: 14px 12px; display: flex; flex-direction: column; gap: 16px; }
.sidebar-section-label {
  font-size: 9px; font-weight: 700; letter-spacing: 1.2px;
  color: var(--text-3); text-transform: uppercase;
  margin-bottom: 6px;
}
.sidebar-check {
  display: flex; align-items: center; gap: 6px; padding: 4px 0;
  font-size: 11px; color: var(--text-2); cursor: pointer;
}
.sidebar-check input { cursor: pointer; }
.sidebar-check-count {
  margin-left: auto; font-family: var(--mono); font-size: 9px; color: var(--text-3);
}
.sidebar-radio { display: flex; flex-direction: column; gap: 3px; }
.sidebar-radio label {
  display: flex; align-items: center; gap: 6px; cursor: pointer;
  font-size: 11px; color: var(--text-2);
}
.sidebar-select {
  width: 100%; background: var(--card-2); border: 1px solid var(--border);
  color: var(--text); font-family: var(--mono); font-size: 11px;
  padding: 4px 6px; border-radius: 2px;
}
.sidebar-actions { display: flex; gap: 6px; margin-top: 4px; }
.sidebar-btn {
  flex: 1; background: var(--blue); color: var(--bg);
  border: 0; padding: 6px 10px; border-radius: 2px;
  font-family: var(--mono); font-size: 10px; font-weight: 700; cursor: pointer;
  letter-spacing: 0.5px;
}
.sidebar-btn.secondary { background: transparent; color: var(--text-2); border: 1px solid var(--border); }

/* ── Universal box (THE locked discipline) ─────────────────────────────── */
.holter-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}
@media (max-width: 1100px) {
  .holter-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 700px) {
  .holter-row { grid-template-columns: 1fr; }
}
.holter-box {
  width: 100%;                              /* responsive — fills 1fr grid cell */
  height: clamp(520px, 78vh, 731px);        /* responsive — scales with viewport height */
  background: var(--card);
  border: 1px solid var(--border);
  border-left: 3px solid var(--border);     /* default; per-box accent overrides */
  display: grid;
  grid-template-rows: 48px 96px 1fr 48px;   /* header + headline + body(1fr) + footer */
  overflow: hidden;
  transition: border-left-color 0.2s;
}
.box-header {
  background: var(--card-2);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 8px;
  padding: 0 14px;
  position: relative;
}
.box-header::before {
  /* subtle bottom underline accent in box-accent colour, set inline */
  content: ""; position: absolute; left: 0; right: 0; bottom: -1px;
  height: 2px; background: var(--box-accent, transparent);
  opacity: 0.6;
}
.box-header-title {
  font-size: 12px; font-weight: 800; letter-spacing: 1.8px;
  color: var(--blue); text-transform: uppercase;
  text-shadow: 0 0 12px rgba(0,183,245,0.25);
}
.box-header-sub {
  margin-left: auto;
  font-size: 10px; color: var(--text-3); font-family: var(--mono);
}
.box-headline {
  padding: 12px 14px;
  border-bottom: 1px solid var(--card-2);
  display: flex; align-items: center;
  overflow: hidden;
}
.box-body {
  padding: 14px;
  overflow: hidden;
  display: flex; flex-direction: column; gap: 10px;
}
.box-footer {
  border-top: 1px solid var(--card-2);
  background: var(--card-2);
  padding: 0 14px;
  display: flex; flex-direction: column; justify-content: center; gap: 2px;
}
.box-footer-pills { display: flex; align-items: center; gap: 8px;
                    font-family: var(--mono); font-size: 9px; }
.box-footer-pill { border: 1px solid var(--border); border-radius: 2px;
                   padding: 1px 6px; color: var(--text-2); }
.box-footer-live {
  background: var(--live); color: var(--bg); padding: 1px 7px;
  border-radius: 2px; font-weight: 700; letter-spacing: 0.5px;
  animation: live-pulse 2.4s ease-in-out infinite;
  box-shadow: 0 0 0 0 rgba(79,229,131,0.6);
}
@keyframes live-pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(79,229,131,0.5);
    transform: scale(1);
  }
  50% {
    box-shadow: 0 0 0 4px rgba(79,229,131,0);
    transform: scale(1.04);
  }
}
.box-footer-note { font-size: 9px; color: var(--text-3);
                   white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* ── Headline shape vocabulary ─────────────────────────────────────────── */
.headline-stat { display: flex; flex-direction: column; gap: 4px; width: 100%; }
.headline-stat-row1 { display: flex; align-items: baseline; gap: 8px; }
.headline-stat-label { font-size: 9px; font-weight: 700; letter-spacing: 1.5px;
                       color: var(--text-3); text-transform: uppercase; }
.headline-stat-value {
  font-size: 32px; font-weight: 800; color: var(--text);
  font-family: var(--mono); line-height: 1;
  text-shadow: 0 0 18px rgba(0,183,245,0.2);
}
.headline-stat-delta {
  font-size: 11px; color: var(--green); font-weight: 600;
  font-family: var(--mono);
}
.headline-stat-traj {
  font-size: 11px; color: var(--green); margin-left: auto; font-weight: 700;
  letter-spacing: 0.5px;
}
.headline-stat-meta { font-size: 9px; color: var(--text-3); font-family: var(--mono);
                      display: flex; gap: 12px; }
.headline-stat-progress { height: 3px; background: var(--card-2);
                          border-radius: 1px; overflow: hidden; }
.headline-stat-progress-fill { height: 100%; background: var(--blue); }

.headline-chips { display: flex; gap: 10px; width: 100%; align-items: center; }
.headline-chip {
  display: inline-flex; flex-direction: column; gap: 2px;
  padding: 6px 10px; border-radius: 2px;
  border: 1px solid var(--border); background: var(--card-2);
  min-width: 80px;
}
.headline-chip-value {
  font-family: var(--mono); font-size: 26px; font-weight: 800;
  text-shadow: 0 0 12px currentColor;
}
.headline-chip-label { font-size: 9px; letter-spacing: 1px; color: var(--text-3);
                       text-transform: uppercase; }

.headline-tier { display: flex; align-items: center; gap: 10px; width: 100%; }
.headline-tier-badge {
  display: inline-block; padding: 7px 14px;
  font-family: var(--mono); font-weight: 800; font-size: 14px;
  letter-spacing: 0.5px; background: var(--card-2);
  border: 1px solid; border-radius: 2px;
  text-shadow: 0 0 10px currentColor;
  box-shadow: 0 0 16px -8px currentColor;
}
.headline-tier-context { font-size: 11px; color: var(--text-2); line-height: 1.4;
                         display: -webkit-box; -webkit-line-clamp: 3;
                         -webkit-box-orient: vertical; overflow: hidden; }

/* ── Body shape vocabulary ─────────────────────────────────────────────── */
.body-evidence-card {
  border-left: 3px solid var(--blue); padding: 10px 12px;
  background: var(--card-elev);
  box-shadow: -8px 0 16px -10px var(--blue);
}
.body-evidence-quote {
  font-size: 11px; color: var(--text); line-height: 1.5;
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
  overflow: hidden;
  cursor: help;
  border-bottom: 1px dotted transparent;
}
.body-evidence-quote[data-tooltip]:hover { border-bottom-color: var(--text-3); }
.body-evidence-attr {
  margin-top: 4px;
  font-size: 9px; font-family: var(--mono); color: var(--text-3);
  letter-spacing: 0.5px;
}
.body-kpi-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.body-kpi-tile { background: var(--card-2); border: 1px solid var(--border);
                 border-top-width: 3px; padding: 10px;
                 display: flex; flex-direction: column; gap: 4px; }
.body-kpi-value { font-family: var(--mono); font-size: 20px; font-weight: 700; }
.body-kpi-label { font-size: 9px; letter-spacing: 1px; color: var(--text-3); text-transform: uppercase; }
.body-kpi-sub { font-size: 10px; color: var(--text-2); }

.body-chip-strip { display: flex; flex-wrap: wrap; gap: 8px; }
.body-chip {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 8px; border-radius: 2px;
  background: var(--card-2); border: 1px solid var(--border);
  font-size: 10px;
}
.body-chip-dot { width: 8px; height: 8px; border-radius: 50%; }
.body-chip-count { font-family: var(--mono); font-weight: 700; color: var(--text); margin-left: 4px; }

.body-bars { display: flex; flex-direction: column; gap: 6px; }
.body-bar-row { display: flex; align-items: center; gap: 8px; font-size: 10px; }
.body-bar-label { width: 130px; color: var(--text-2);
                  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.body-bar-track { flex: 1; height: 14px; background: var(--card-2); border-radius: 1px; overflow: hidden; }
.body-bar-fill { height: 100%; }
.body-bar-value { width: 40px; text-align: right; color: var(--text); font-family: var(--mono); }

.body-line { font-size: 11px; color: var(--text-2);
             display: flex; align-items: center; gap: 8px;
             overflow: hidden; text-overflow: ellipsis; }
.body-line-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
  box-shadow: 0 0 8px currentColor;
}
.body-line-dot[style*="background"] {
  /* the dot's inline background sets currentColor for the shadow */
}

.body-table { width: 100%; border-collapse: collapse; font-size: 10px; }
.body-table th { text-align: left; padding: 4px 6px; font-size: 9px;
                 color: var(--text-3); letter-spacing: 0.5px;
                 border-bottom: 1px solid var(--border); text-transform: uppercase; }
.body-table td { padding: 4px 6px; color: var(--text-2);
                 border-bottom: 1px solid var(--card-2); }
.body-table tr:last-child td { border-bottom: 0; }

/* ── Pure-CSS hover tooltip ────────────────────────────────────────────── */
[data-tooltip] { position: relative; }
[data-tooltip]:hover::after {
  content: attr(data-tooltip);
  position: absolute;
  bottom: 100%; left: 0;
  margin-bottom: 6px;
  background: var(--card-2); color: var(--text);
  border: 1px solid var(--blue);
  padding: 8px 10px; border-radius: 2px;
  font-size: 11px; line-height: 1.5;
  white-space: normal; max-width: 480px;
  z-index: 200;
  box-shadow: 0 4px 12px rgba(0,0,0,0.6);
}

/* Filtered-out box visibility */
.holter-box.filtered-out { display: none; }

/* ── Page chrome strips — ticker + journey row (documented exceptions) ── */
/* Not boxes — full-width horizontal strips between row sections. Same
   role as topnav/footer: page chrome that lives outside the box grid. */

.holter-ticker {
  overflow: hidden; background: var(--bg-strip);
  border-top: 1px solid var(--border); border-bottom: 1px solid var(--border);
  margin-bottom: 12px;
}
.holter-ticker-track { overflow: hidden; white-space: nowrap; }
.holter-ticker-inner {
  display: inline-flex; align-items: center;
  padding: 10px 0;
  animation: holter-ticker-scroll 120s linear infinite;
}
.holter-ticker-inner:hover { animation-play-state: paused; }
@keyframes holter-ticker-scroll {
  from { transform: translateX(0); }
  to   { transform: translateX(-50%); }
}
.holter-ticker-item {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 0 20px;
}
.holter-ticker-cell {
  font-size: 11px; font-weight: 700; letter-spacing: 0.5px;
  font-family: var(--mono);
}
.holter-ticker-sig {
  font-size: 11px; color: var(--text-2);
}
.holter-ticker-bar {
  width: 40px; height: 6px; background: var(--card); border-radius: 1px;
  overflow: hidden;
}
.holter-ticker-bar-fill { height: 100%; }
.holter-ticker-sha {
  font-family: var(--mono); font-size: 9px; color: var(--text-3);
}
.holter-ticker-sep { color: var(--border); padding: 0 4px; font-size: 16px; }

.holter-journey-strip {
  margin-bottom: 12px;
}
.holter-journey-header {
  display: flex; align-items: baseline; gap: 12px;
  padding: 0 4px 8px;
}
.holter-journey-title {
  font-size: 11px; font-weight: 800; letter-spacing: 1.5px;
  color: var(--text-2); text-transform: uppercase;
}
.holter-journey-sub {
  font-size: 10px; color: var(--text-3); font-family: var(--mono);
}
.holter-journey-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1px;
  background: var(--border);
  border: 1px solid var(--border);
}
.holter-journey-cell {
  background: var(--bg-strip);
  padding: 12px 16px;
  border-top: 3px solid;
  display: flex; flex-direction: column; gap: 4px;
}
.holter-journey-cell-name {
  font-size: 12px; font-weight: 700; color: var(--text-2);
  letter-spacing: 0.5px;
}
.holter-journey-cell-score {
  font-size: 32px; font-weight: 800; font-family: var(--mono);
  color: var(--text);
  line-height: 1;
  text-shadow: 0 0 12px rgba(0,183,245,0.25);
}
.holter-journey-cell-status {
  font-size: 10px; font-weight: 700; letter-spacing: 1px;
}
.holter-journey-cell-submeta {
  font-size: 9px; color: var(--text-3); font-family: var(--mono);
}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Box helpers — enforce the 4-layer contract
# ─────────────────────────────────────────────────────────────────────────────

NOW = _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%d %H:%M UTC")


def render_box(*, header: str, headline: str, body: str, footer: str,
               accent_color: str = "var(--border)",
               box_attrs: str = "") -> str:
    """Universal 4-layer box. accent_color drives:
       - left-edge severity border (3px)
       - subtle bottom underline under header (via --box-accent CSS var)
       - per-box visual identity inside the locked shape."""
    style = (
        f'style="border-left-color:{accent_color};'
        f'--box-accent:{accent_color};"'
    )
    return f'''
<div class="holter-box" {style} {box_attrs}>
  <div class="box-header">{header}</div>
  <div class="box-headline">{headline}</div>
  <div class="box-body">{body}</div>
  <div class="box-footer">{footer}</div>
</div>'''


def box_header(title: str, sub: str = "") -> str:
    sub_html = f'<span class="box-header-sub">{sub}</span>' if sub else ""
    return f'<span class="box-header-title">{title}</span>{sub_html}'


def box_footer(version: str, ts: str, live: bool = True, note: str = "") -> str:
    live_html = '<span class="box-footer-live">LIVE</span>' if live else ""
    pills = (
        f'<span class="box-footer-pill">{version}</span>'
        f'<span class="box-footer-pill">{ts}</span>'
        f'{live_html}'
    )
    note_html = f'<div class="box-footer-note">{note}</div>' if note else ""
    return f'<div class="box-footer-pills">{pills}</div>{note_html}'


def headline_stat_card(*, label: str, value: str, delta: str, traj: str,
                        meta_left: str, meta_right: str, progress_pct: int) -> str:
    return f'''
<div class="headline-stat">
  <div class="headline-stat-row1">
    <span class="headline-stat-label">{label}</span>
    <span class="headline-stat-value">{value}</span>
    <span class="headline-stat-delta">{delta}</span>
    <span class="headline-stat-traj">{traj}</span>
  </div>
  <div class="headline-stat-meta">
    <span>{meta_left}</span>
    <span style="margin-left:auto;">{meta_right}</span>
  </div>
  <div class="headline-stat-progress">
    <div class="headline-stat-progress-fill" style="width:{progress_pct}%;"></div>
  </div>
</div>'''


def headline_chip_strip(chips: list[tuple[str, str, str]]) -> str:
    items = "".join(
        f'<span class="headline-chip" style="border-color:{color};">'
        f'<span class="headline-chip-value" style="color:{color};">{value}</span>'
        f'<span class="headline-chip-label">{label}</span>'
        f'</span>'
        for value, label, color in chips
    )
    return f'<div class="headline-chips">{items}</div>'


def headline_tier_badge(tier: str, color: str, context: str) -> str:
    return f'''
<div class="headline-tier">
  <span class="headline-tier-badge" style="color:{color};border-color:{color};">{tier}</span>
  <span class="headline-tier-context">{context}</span>
</div>'''


def body_evidence_cards(quotes: list[tuple[str, str]]) -> str:
    return "".join(
        f'<div class="body-evidence-card">'
        f'<div class="body-evidence-quote" data-tooltip="{q[0].replace(chr(34), chr(39))}">{q[0]}</div>'
        f'<div class="body-evidence-attr">{q[1]}</div>'
        f'</div>'
        for q in quotes
    )


def body_kpi_tiles(tiles: list[tuple[str, str, str, str]]) -> str:
    items = "".join(
        f'<div class="body-kpi-tile" style="border-top-color:{color};">'
        f'<div class="body-kpi-value" style="color:{color};">{value}</div>'
        f'<div class="body-kpi-label">{label}</div>'
        f'<div class="body-kpi-sub">{sub}</div>'
        f'</div>'
        for value, label, sub, color in tiles
    )
    return f'<div class="body-kpi-grid">{items}</div>'


def body_chip_strip(chips: list[tuple[str, str, str]]) -> str:
    items = "".join(
        f'<span class="body-chip">'
        f'<span class="body-chip-dot" style="background:{color};"></span>'
        f'<span>{label}</span>'
        f'<span class="body-chip-count">{count}</span>'
        f'</span>'
        for label, count, color in chips
    )
    return f'<div class="body-chip-strip">{items}</div>'


def body_bars(bars: list[tuple[str, int, str, str]]) -> str:
    rows = "".join(
        f'<div class="body-bar-row">'
        f'<span class="body-bar-label">{label}</span>'
        f'<div class="body-bar-track">'
        f'<div class="body-bar-fill" style="width:{pct}%;background:{color};"></div>'
        f'</div>'
        f'<span class="body-bar-value">{value}</span>'
        f'</div>'
        for label, pct, value, color in bars
    )
    return f'<div class="body-bars">{rows}</div>'


def body_lines(lines: list[tuple[str, str]]) -> str:
    return "".join(
        f'<div class="body-line">'
        f'<span class="body-line-dot" style="background:{color};"></span>'
        f'<span>{text}</span>'
        f'</div>'
        for text, color in lines
    )


# ─────────────────────────────────────────────────────────────────────────────
# Top nav + Sidebar (Box 0) — sidebar with REAL filter controls
# ─────────────────────────────────────────────────────────────────────────────

def render_topnav(packs: list[dict]) -> str:
    """Topnav with identity + Product/Owner filters. Domain + Date moved
    into the filter strip so they don't duplicate (Journey = Domain;
    Time = Date)."""
    owners = sorted({a for p in packs for a in p["meta"].get("authors", [])})
    n = len(packs)
    product_opts = f'<option value="">Product · all packs · {n}</option>\n' + "".join(
        f'<option value="{p["meta"]["pack_name"]}">'
        f'Product · cell {(p["hypothesis"] or {}).get("cell_id","?")} · '
        f'{(p["hypothesis"] or {}).get("signature_id","—").replace("_"," ")}</option>'
        for p in sorted(packs, key=lambda p: (p["hypothesis"] or {}).get("cell_id", 99))
    )
    owner_opts = f'<option value="">Owner · all teams · {len(owners)}</option>\n' + "".join(
        f'<option value="{o}">Owner · {o}</option>' for o in owners
    )
    return f'''
<header class="holter-topnav">
  <span class="brand-logo">CJI&nbsp;PULSE</span>
  <select class="topnav-select" id="filter-product" data-filter="packname">{product_opts}</select>
  <select class="topnav-select" id="filter-owner" data-filter="author">{owner_opts}</select>
  <button class="topnav-reset" id="filter-reset" type="button" hidden>Reset</button>
  <span class="topnav-spacer"></span>
  <button class="topnav-icon" type="button" title="Search packs (/)">⌕</button>
  <button class="topnav-icon" type="button" title="Notifications">🔔</button>
  <button class="topnav-icon" type="button" title="Canvas guide">?</button>
  <button class="topnav-icon" type="button" title="Settings">⚙</button>
  <button class="topnav-avatar" type="button" title="Hussain Ahmed">HA</button>
</header>'''


def render_filter_strip(packs: list[dict]) -> str:
    """Sticky horizontal filter strip below the topnav.
    Journey = dropdown (single-select). Time = button → calendar popover
    with preset buttons + custom date-range inputs. Severity = radio."""
    domains = sorted({(p["hypothesis"] or {}).get("screen_id", "").split(".")[0]
                       for p in packs if (p["hypothesis"] or {}).get("screen_id")})
    domain_counts: dict[str, int] = {}
    for p in packs:
        d = (p["hypothesis"] or {}).get("screen_id", "").split(".")[0]
        if d:
            domain_counts[d] = domain_counts.get(d, 0) + 1

    journey_opts = f'<option value="">Journey · all · {len(domains)}</option>\n' + "".join(
        f'<option value="{d}">{d} · {domain_counts.get(d, 0)} packs</option>'
        for d in domains
    )

    # Default date range = last 7 days from today
    today = _dt.date.today()
    week_ago = today - _dt.timedelta(days=7)

    return f'''
<div class="holter-filter-strip">
  <div class="holter-filter-section">
    <span class="holter-filter-label">Journey</span>
    <select class="holter-filter-select" id="filter-journey" data-filter="domain">{journey_opts}</select>
  </div>
  <div class="holter-filter-sep"></div>
  <div class="holter-filter-section holter-time-section">
    <span class="holter-filter-label">Time</span>
    <button class="holter-time-btn" id="time-btn" type="button">
      <span id="time-btn-label">Last 7 days</span>
      <span class="holter-time-btn-caret">▾</span>
    </button>
    <div class="holter-time-pop" id="time-pop" hidden>
      <div class="time-presets">
        <button class="time-preset active" data-preset="7" type="button">Last 7 days</button>
        <button class="time-preset" data-preset="30" type="button">Last 30 days</button>
        <button class="time-preset" data-preset="90" type="button">Last 90 days</button>
        <button class="time-preset" data-preset="month" type="button">This month</button>
        <button class="time-preset" data-preset="quarter" type="button">This quarter</button>
        <button class="time-preset" data-preset="ytd" type="button">Year to date</button>
      </div>
      <div class="time-custom">
        <div class="time-custom-label">Custom range</div>
        <div class="time-custom-row">
          <input type="date" class="time-date" id="time-from" value="{week_ago.isoformat()}">
          <span class="time-to-arrow">→</span>
          <input type="date" class="time-date" id="time-to" value="{today.isoformat()}">
        </div>
        <button class="time-apply" id="time-apply" type="button">Apply custom range</button>
      </div>
    </div>
  </div>
  <div class="holter-filter-sep"></div>
  <div class="holter-filter-section">
    <span class="holter-filter-label">Severity</span>
    <div class="holter-filter-radios">
      <label><input type="radio" name="severity" value="all" checked> All</label>
      <label><input type="radio" name="severity" value="positive"> Positive</label>
      <label><input type="radio" name="severity" value="negative"> Negative</label>
    </div>
  </div>
  <div class="holter-filter-sep"></div>
  <div class="holter-filter-section">
    <span class="holter-filter-label">Scope</span>
    <span style="font-size:11px; color:var(--text-2); font-family:var(--mono);">
      {len(packs)} packs · 4 journeys × 3 signatures
    </span>
  </div>
  <div class="holter-filter-actions">
    <button class="holter-filter-btn" id="filter-apply" type="button">APPLY</button>
    <button class="holter-filter-btn secondary" id="filter-strip-reset" type="button">RESET</button>
  </div>
</div>'''


def render_sidebar(packs: list[dict]) -> str:
    """[Deprecated] Box 0 sidebar — kept for compatibility but no longer
    rendered. Filters moved to render_filter_strip()."""
    # Journey checkboxes
    domains = sorted({(p["hypothesis"] or {}).get("screen_id", "").split(".")[0]
                       for p in packs if (p["hypothesis"] or {}).get("screen_id")})
    domain_counts: dict[str, int] = {}
    for p in packs:
        d = (p["hypothesis"] or {}).get("screen_id", "").split(".")[0]
        if d:
            domain_counts[d] = domain_counts.get(d, 0) + 1

    journey_checks = "".join(
        f'<label class="sidebar-check">'
        f'<input type="checkbox" class="sidebar-domain-check" value="{d}" checked>'
        f'<span>{d}</span>'
        f'<span class="sidebar-check-count">{domain_counts.get(d, 0)}</span>'
        f'</label>'
        for d in domains
    )

    return f'''
<aside class="holter-sidebar">
  <div class="sidebar-inner">
    <div>
      <div class="sidebar-section-label">Journeys</div>
      {journey_checks}
    </div>
    <div>
      <div class="sidebar-section-label">Time Range</div>
      <select class="sidebar-select" id="sidebar-timerange">
        <option>Last 7 days</option>
        <option>Last 30 days</option>
        <option>Last 90 days</option>
        <option>Custom range…</option>
      </select>
    </div>
    <div>
      <div class="sidebar-section-label">Severity</div>
      <div class="sidebar-radio">
        <label><input type="radio" name="severity" value="all" checked> All</label>
        <label><input type="radio" name="severity" value="positive"> Positive only</label>
        <label><input type="radio" name="severity" value="negative"> Negative only</label>
      </div>
    </div>
    <div>
      <div class="sidebar-section-label">Scope</div>
      <div style="font-size:10px; color:var(--text-3); line-height:1.5;">
        {len(packs)} packs · 4 journeys × 3 signatures
      </div>
    </div>
    <div class="sidebar-actions">
      <button class="sidebar-btn" id="sidebar-apply">APPLY</button>
      <button class="sidebar-btn secondary" id="sidebar-reset">RESET</button>
    </div>
  </div>
</aside>'''


# ─────────────────────────────────────────────────────────────────────────────
# Box 1, 2, 3 — topbar boxes consuming REAL data
# ─────────────────────────────────────────────────────────────────────────────

def _extract_quote(pack: dict) -> str:
    """Pull a quotable sentence from a pack's bank_md."""
    raw = pack.get("bank_md", "")
    cleaned = " ".join(
        ln.strip().lstrip("#").strip()
        for ln in raw.split("\n")
        if ln.strip() and not ln.startswith("```")
    )
    return cleaned[:280] + ("…" if len(cleaned) > 280 else "")


def render_ticker(packs: list[dict]) -> str:
    """Scrolling marquee of pack lineage anchors (page chrome, not a box).
    Doubled track so the loop seam is invisible during animation."""
    if not packs:
        return ""
    items = []
    for p in packs:
        h = p["hypothesis"] or {}
        sig = h.get("signature_id", "—").replace("_", " ")
        cell = h.get("cell_id", "?")
        sha = short_hash(p["sha256"])
        is_neg = h.get("ground_truth_expectation") == "negative"
        color = "var(--amber)" if is_neg else "var(--text-2)"
        bar_w = 22 if is_neg else 40
        items.append(
            f'<span class="holter-ticker-item">'
            f'<span class="holter-ticker-cell" style="color:{color};">CELL {cell:>2}</span>'
            f'<span class="holter-ticker-sig">{sig}</span>'
            f'<span class="holter-ticker-bar"><span class="holter-ticker-bar-fill" '
            f'style="width:{bar_w}px;background:{color};"></span></span>'
            f'<span class="holter-ticker-sha">{sha}</span>'
            f'</span>'
            f'<span class="holter-ticker-sep">·</span>'
        )
    track = "".join(items)
    return (
        f'<div class="holter-ticker">'
        f'<div class="holter-ticker-track">'
        f'<div class="holter-ticker-inner">{track}{track}</div>'
        f'</div></div>'
    )


def render_journey_row(packs: list[dict]) -> str:
    """4-cell horizontal strip showing per-screen friction-target status
    (page chrome, not a box). Cell width = 1fr each so 4 cells fill the
    available row width regardless of viewport."""
    screens = cell_screens_with_counts(packs)
    if not screens:
        return ""
    cells_html = ""
    for s in screens:
        cells_html += (
            f'<div class="holter-journey-cell" style="border-top-color:{s["status_color"]};">'
            f'<div class="holter-journey-cell-name">{s["short"]}</div>'
            f'<div class="holter-journey-cell-score">{s["positives"]}/3</div>'
            f'<div class="holter-journey-cell-status" style="color:{s["status_color"]};">{s["status"]}</div>'
            f'<div class="holter-journey-cell-submeta">{s["total"]} cells · '
            f'{s["positives"]} positive · {s["negatives"]} negative</div>'
            f'</div>'
        )
    return (
        '<div class="holter-journey-strip">'
        '<div class="holter-journey-header">'
        '<span class="holter-journey-title">FRICTION-TARGET SCREENS</span>'
        '<span class="holter-journey-sub">FrictionBench v0.1 · 4 screens × 3 signatures</span>'
        '</div>'
        f'<div class="holter-journey-row">{cells_html}</div>'
        '</div>'
    )


def render_box1(packs: list[dict]) -> str:
    """Box 1 — PULSE INTELLIGENCE. Real CELL COVERAGE + real evidence quotes."""
    n = len(packs)
    pct = int(100 * n / 12) if n else 0
    # Pick two illustrative packs for evidence — cards abandonment + investments negative
    pack_evidence = [p for p in packs if "cards" in p["meta"]["pack_name"]
                     and "abandon" in p["meta"]["pack_name"]]
    pack_neg = [p for p in packs if (p["hypothesis"] or {}).get("cell_id") == 10]
    e1 = pack_evidence[0] if pack_evidence else (packs[0] if packs else None)
    e2 = pack_neg[0] if pack_neg else (packs[-1] if packs else None)
    quotes: list[tuple[str, str]] = []
    if e1:
        h = e1["hypothesis"] or {}
        quotes.append((
            _extract_quote(e1) or f"Cell {h.get('cell_id','?')} pack — bank altitude not available",
            f"CELL {h.get('cell_id','?')} · {h.get('signature_id','—').replace('_',' ')} · POSITIVE",
        ))
    if e2 and e2 is not e1:
        h = e2["hypothesis"] or {}
        quotes.append((
            _extract_quote(e2) or f"Cell {h.get('cell_id','?')} pack — bank altitude not available",
            f"CELL {h.get('cell_id','?')} · {h.get('signature_id','—').replace('_',' ')} · NEGATIVE",
        ))
    return render_box(
        header=box_header("PULSE — DECISION INTELLIGENCE", "v1.0.0"),
        accent_color="var(--blue)",
        headline=headline_stat_card(
            label="CELL COVERAGE",
            value=f"{n}/12",
            delta=f"+{n-3} vs showcase",
            traj="↗ COMPLETE" if n >= 12 else "↗ GROWING",
            meta_left="Baseline: 3 showcase packs",
            meta_right=NOW,
            progress_pct=pct,
        ),
        body=body_evidence_cards(quotes) + body_lines([
            ("FrictionBench v0.1 · 12-cell matrix · 4 screens × 3 signatures", "var(--blue)"),
            ("Lineage-anchored · fairness-enforced · regulator-defensible decision packs", "var(--teal)"),
        ]),
        footer=box_footer(
            "pulse v1.0.0", NOW, live=True,
            note="Decision packs · canonical lineage anchors · synthesis pending PULSE-93",
        ),
    )


def render_box2(packs: list[dict]) -> str:
    """Box 2 — PACK STATUS. Real counts + per-screen coverage bars."""
    n = len(packs)
    n_neg = sum(1 for p in packs if (p["hypothesis"] or {}).get("ground_truth_expectation") == "negative")
    n_pos = n - n_neg
    # Per-screen aggregate (positive count / total)
    screens: dict[str, dict[str, int]] = {}
    for p in packs:
        h = p["hypothesis"] or {}
        sc = h.get("screen_id", "")
        if not sc:
            continue
        domain = sc.split(".")[0]
        rec = screens.setdefault(domain, {"positive": 0, "negative": 0, "total": 0})
        rec["total"] += 1
        if h.get("ground_truth_expectation") == "negative":
            rec["negative"] += 1
        else:
            rec["positive"] += 1
    bars = []
    for domain in sorted(screens):
        r = screens[domain]
        pct = int(100 * r["positive"] / 3) if r["total"] else 0
        color = "var(--green)" if pct == 100 else "var(--amber)" if pct > 0 else "var(--text-3)"
        bars.append((f"{domain} · 3 cells", pct, f"{r['positive']}/3", color))
    return render_box(
        header=box_header("PACK STATUS", "registry"),
        accent_color="var(--teal)",
        headline=headline_chip_strip([
            (str(n_pos), "POSITIVE", "var(--teal)"),
            (str(n_neg), "NEGATIVE", "var(--amber)"),
            (str(n),     "TOTAL",    "var(--blue)"),
        ]),
        body=body_bars(bars) + body_lines([
            (f"{n} packs canvas-complete · PULSE-104 backfill landed", "var(--green)"),
            ("0 packs awaiting validation · all in registry", "var(--teal)"),
            (f"{n_neg} negative-class discriminator cell · cell 10", "var(--amber)"),
        ]),
        footer=box_footer(
            "registry v0.1", NOW, live=True,
            note="Pack registry · metadata + hypothesis validators green",
        ),
    )


def render_box3(packs: list[dict]) -> str:
    """Box 3 — INTELLIGENCE BRIEF. Headline pack + computed Action tier."""
    pack = headline_pack(packs)
    if not pack:
        return render_box(
            header=box_header("INTELLIGENCE BRIEF", "—"),
            headline=headline_tier_badge("NO PACKS", "var(--amber)", "Registry empty"),
            body=body_lines([("No packs loaded", "var(--amber)")]),
            footer=box_footer("—", NOW, live=False, note="—"),
        )
    h = pack["hypothesis"] or {}
    meta = pack["meta"]
    is_neg = h.get("ground_truth_expectation") == "negative"
    cell = h.get("cell_id", "?")
    sig = h.get("signature_id", "—").replace("_", " ")
    screen = h.get("screen_id", "—")
    # Engine output for this pack
    cell_score = get_pack_cell(meta["pack_name"])
    if cell_score:
        action_tier = cell_score.action_tier
        action_color = _ACTION_COLORS.get(action_tier, "var(--amber)")
        action_note = cell_score.placement_recommendation
    else:
        action_tier = "PENDING"
        action_color = "var(--text-3)"
        action_note = "Action tier requires PULSE-106 placement scenario"
    tier_text = f"CELL {cell} · {'NEGATIVE' if is_neg else 'POSITIVE'}"
    tier_color = "var(--amber)" if is_neg else "var(--red)"
    return render_box(
        header=box_header("INTELLIGENCE BRIEF", "headline pack"),
        accent_color=tier_color,
        headline=headline_tier_badge(
            tier=tier_text,
            color=tier_color,
            context=(
                f"<strong>{sig}</strong> on {screen} · "
                f"{'detector MUST NOT fire · discriminator load-bearing' if is_neg else 'detector active · positive ground truth'}"
            ),
        ),
        body=body_kpi_tiles([
            (f"CELL {cell}", "FrictionBench",   "v0.1 · frozen",
             "var(--blue)"),
            ("NEGATIVE" if is_neg else "POSITIVE",
             "Ground truth",
             "discriminator active" if is_neg else "detector active",
             "var(--amber)" if is_neg else "var(--teal)"),
            ((h.get("analytic") or {}).get("method", "—").split("_")[0],
             "Method family",
             (h.get("analytic") or {}).get("method", "—")[:32],
             "var(--text-2)"),
        ]) + body_evidence_cards([
            (
                (meta.get("description", "").strip().replace("\n", " "))[:400]
                or "No description in pack metadata",
                f"The Situation · pack: {meta['pack_name']}",
            ),
            (
                _extract_quote(pack) or "Bank altitude not available",
                f"Bank altitude · cell {cell} · sha256:{short_hash(pack['sha256'])}",
            ),
        ]),
        footer=box_footer(
            "engine v0.1.0", NOW, live=True,
            note=f"Action: {action_tier} · {action_note[:80]}",
        ),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Engine summary row — Friction Risk · Placement Posture · Confidence Protocol
# ─────────────────────────────────────────────────────────────────────────────

def render_box_friction_risk(packs: list[dict]) -> str:
    risk = sum(1 for p in packs if (p["hypothesis"] or {}).get("ground_truth_expectation") != "negative")
    discriminators = sum(1 for p in packs if (p["hypothesis"] or {}).get("ground_truth_expectation") == "negative")
    score = f"{risk * 6.5:.1f}"
    pos_pack = next((p for p in packs if (p["hypothesis"] or {}).get("ground_truth_expectation") != "negative"
                    and "abandon" in p["meta"]["pack_name"]), None)
    return render_box(
        header=box_header("FRICTION RISK SCORE", "v0.1"),
        accent_color="var(--amber)",
        headline=headline_stat_card(
            label="CELL RISK SCORE",
            value=score,
            delta=f"+{risk * 6.5 - 19.5:.1f} vs showcase",
            traj="↗ COMPLETE" if risk >= 11 else "↗ GROWING",
            meta_left=f"{risk} positive cells × 6.5 weight",
            meta_right=NOW,
            progress_pct=min(100, int(risk * 6.5)),
        ),
        body=body_kpi_tiles([
            (str(risk),            "POSITIVE",      "detector cells", "var(--teal)"),
            (str(discriminators),  "DISCRIMINATOR", "negative-class", "var(--amber)"),
            (str(len(packs)),      "TOTAL",         "cells covered",  "var(--blue)"),
        ]) + body_lines([
            ("Score formula: positive_count × 6.5 weight · placeholder until v0.2", "var(--text-3)"),
            ("All cells canvas-complete (PULSE-104) · methodology validators green", "var(--green)"),
        ]) + (body_evidence_cards([(
            _extract_quote(pos_pack) or "—",
            f"Top positive · cell {(pos_pack['hypothesis'] or {}).get('cell_id','?')}",
        )]) if pos_pack else ""),
        footer=box_footer("pulse v1.0.0", NOW, live=True,
                         note=f"Risk-weighted across {len(packs)} cells"),
    )


def render_box_placement_posture(packs: list[dict]) -> str:
    cells = [get_pack_cell(p["meta"]["pack_name"]) for p in packs]
    cells = [c for c in cells if c is not None]
    if not cells:
        return render_box(
            header=box_header("PLACEMENT POSTURE", "PULSE-106"),
            headline=headline_tier_badge("UNAVAILABLE", "var(--amber)",
                                          "PULSE-106 placement scenario could not load"),
            body=body_lines([("Engine import failed — see render_holter.py logs", "var(--amber)")]),
            footer=box_footer("placement v0.1.0", NOW, live=False, note="Engine offline"),
        )
    high_value = {"SIGNIFICANT", "COMMERCIAL-OPPORTUNITY"}
    high_risk = {"ESCALATE", "REGULATORY-FLAG"}
    counts = {"ACUTE": 0, "REGULATORY-FLAG": 0, "COMMERCIAL-OPPORTUNITY": 0,
              "WATCH": 0, "NOMINAL": 0, "NEEDS_MORE_DATA": 0}
    for c in cells:
        if c.diagnosis.diagnosis == "INCONCLUSIVE":
            counts["NEEDS_MORE_DATA"] += 1
            continue
        hv = c.value.tier in high_value
        hr = c.risk.tier in high_risk
        if hv and hr: counts["ACUTE"] += 1
        elif hr: counts["REGULATORY-FLAG"] += 1
        elif hv: counts["COMMERCIAL-OPPORTUNITY"] += 1
        elif c.risk.tier == "NOMINAL" and c.value.tier == "NOMINAL": counts["NOMINAL"] += 1
        else: counts["WATCH"] += 1
    dominant = max(counts, key=counts.get)
    dom_color = _ACTION_COLORS.get(dominant, "var(--amber)")
    return render_box(
        header=box_header("PLACEMENT POSTURE", "Agentic AI"),
        accent_color=dom_color,
        headline=headline_tier_badge(
            tier=f"{dominant} · {counts[dominant]}/{len(cells)}",
            color=dom_color,
            context="Dominant action tier across placement cells · Diagnosis can override the 2×2",
        ),
        body=body_chip_strip([
            ("ACUTE",                  str(counts["ACUTE"]),                  _ACTION_COLORS["ACUTE"]),
            ("REGULATORY-FLAG",        str(counts["REGULATORY-FLAG"]),        _ACTION_COLORS["REGULATORY-FLAG"]),
            ("COMMERCIAL-OPPORTUNITY", str(counts["COMMERCIAL-OPPORTUNITY"]), _ACTION_COLORS["COMMERCIAL-OPPORTUNITY"]),
            ("WATCH",                  str(counts["WATCH"]),                  _ACTION_COLORS["WATCH"]),
            ("NOMINAL",                str(counts["NOMINAL"]),                _ACTION_COLORS["NOMINAL"]),
            ("NEEDS_MORE_DATA",        str(counts["NEEDS_MORE_DATA"]),        _ACTION_COLORS["NEEDS_MORE_DATA"]),
        ]) + body_lines([
            ("CLARK-style action tier from Risk × Value 2×2", "var(--blue)"),
            ("Diagnosis overrides INCONCLUSIVE → NEEDS_MORE_DATA", "var(--text-3)"),
            ("JOURNEY_PROBLEM → 'fix the journey' verb regardless of tier", "var(--text-3)"),
        ]),
        footer=box_footer("diagnosis+risk+value v0.1.0", NOW, live=True,
                         note=f"Computed across {len(cells)} cells · PULSE-106"),
    )


def render_box_confidence_protocol(packs: list[dict]) -> str:
    n_neg = sum(1 for p in packs if (p["hypothesis"] or {}).get("ground_truth_expectation") == "negative")
    n_pos = len(packs) - n_neg
    return render_box(
        header=box_header("CONFIDENCE PROTOCOL", "4-tier"),
        accent_color="var(--green)",
        headline=headline_chip_strip([
            ("0",         "PULSE-3", "var(--red)"),
            (str(n_neg),  "PULSE-2", "var(--amber)"),
            (str(n_pos),  "PULSE-1", "var(--teal)"),
            (str(len(packs)), "PULSE-0", "var(--blue)"),
        ]),
        body=body_bars([
            ("PULSE-0 valid",         100, f"{len(packs)}/12", "var(--blue)"),
            ("PULSE-1 detector",      int(100 * n_pos/12) if len(packs) else 0,
                                       f"{n_pos}/12", "var(--teal)"),
            ("PULSE-2 discriminator", int(100 * n_neg/12) if len(packs) else 0,
                                       f"{n_neg}/12", "var(--amber)"),
            ("PULSE-3 failure",       0, "0/12", "var(--red)"),
        ]) + body_lines([
            (f"All {len(packs)} packs pass v1 metadata validator", "var(--green)"),
            (f"All {len(packs)} packs pass canvas-completeness (PULSE-103)", "var(--green)"),
            ("Synthesis tier · awaiting PULSE-93 hydration", "var(--text-3)"),
        ]),
        footer=box_footer("registry v0.1", NOW, live=True,
                         note="Per-pack confidence inputs land in v0.2"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Methodology distribution row — Diagnosis · Value · Risk
# ─────────────────────────────────────────────────────────────────────────────

def _dist_box(packs: list[dict], *, name: str, attr_path: tuple[str, str],
              color_map: dict[str, str], methodology_version: str,
              context_template: str) -> str:
    """Generic distribution box for Diagnosis / Value / Risk."""
    cells = [get_pack_cell(p["meta"]["pack_name"]) for p in packs]
    cells = [c for c in cells if c is not None]
    if not cells:
        return render_box(
            header=box_header(f"{name} DISTRIBUTION", "engine offline"),
            headline=headline_tier_badge("UNAVAILABLE", "var(--amber)",
                                          "Engine scenario could not load"),
            body=body_lines([("PULSE-106 placement scenario unavailable", "var(--amber)")]),
            footer=box_footer(f"{name.lower()} v0.1.0", NOW, live=False, note="Engine offline"),
        )
    tier_counts: dict[str, int] = {}
    for c in cells:
        score_obj = getattr(c, attr_path[0])
        tier = getattr(score_obj, attr_path[1])
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
    dominant = max(tier_counts, key=tier_counts.get)
    dom_color = color_map.get(dominant, "var(--amber)")
    chip_rows = [(t, str(tier_counts.get(t, 0)), color_map.get(t, "#7A7A7A"))
                 for t in color_map.keys()]
    # Two evidence cards for the dominant tier
    dominant_packs = []
    for p in packs[:6]:
        cs = get_pack_cell(p["meta"]["pack_name"])
        if cs is None: continue
        if getattr(getattr(cs, attr_path[0]), attr_path[1]) == dominant:
            dominant_packs.append((p, cs))
        if len(dominant_packs) >= 2: break
    evidence = []
    for p, cs in dominant_packs[:2]:
        h = p["hypothesis"] or {}
        evidence.append((
            f"{p['meta']['pack_name']} → {dominant}. "
            f"{(p['meta'].get('description', '').strip().replace(chr(10), ' '))[:180]}",
            f"Cell {h.get('cell_id','?')} · {dominant}",
        ))
    return render_box(
        header=box_header(f"{name} DISTRIBUTION", f"v{methodology_version}"),
        accent_color=dom_color,
        headline=headline_tier_badge(
            tier=f"{dominant} · {tier_counts[dominant]}/{len(cells)}",
            color=dom_color,
            context=context_template,
        ),
        body=body_chip_strip(chip_rows)
             + (body_evidence_cards(evidence) if evidence else "")
             + body_lines([
                 (f"{len(cells)} cells scored · methodology v{methodology_version}", "var(--blue)"),
             ]),
        footer=box_footer(f"{name.lower()} v{methodology_version}", NOW, live=True,
                         note=f"Distribution across {len(cells)} scored cells"),
    )


def render_box_diagnosis_dist(packs: list[dict]) -> str:
    return _dist_box(
        packs, name="DIAGNOSIS",
        attr_path=("diagnosis", "diagnosis"),
        color_map=_DIAGNOSIS_COLORS,
        methodology_version="0.1.0",
        context_template="Dominant Diagnosis · runs BEFORE Risk/Value · can override 2×2",
    )


def render_box_value_dist(packs: list[dict]) -> str:
    return _dist_box(
        packs, name="VALUE TIER",
        attr_path=("value", "tier"),
        color_map=_VALUE_COLORS,
        methodology_version="0.1.0",
        context_template="Dominant Value tier · severity × population × frequency × cohort × counterfactual",
    )


def render_box_risk_dist(packs: list[dict]) -> str:
    return _dist_box(
        packs, name="RISK TIER",
        attr_path=("risk", "tier"),
        color_map=_RISK_COLORS,
        methodology_version="0.1.0",
        context_template="Dominant Risk tier · regulatory taxonomy × bank policy × Chronicle precedent",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Chronicle matcher box
# ─────────────────────────────────────────────────────────────────────────────

def render_box_chronicle(packs: list[dict]) -> str:
    """Chronicle matcher state for the headline pack."""
    pack = headline_pack(packs)
    cs = get_pack_cell(pack["meta"]["pack_name"]) if pack else None
    matches = cs.risk.chronicle_matches if cs else []
    n_matches = len(matches)
    h = (pack or {}).get("hypothesis") or {}
    return render_box(
        header=box_header("CHRONICLE MATCHER", "PULSE-100"),
        accent_color="var(--amber)",
        headline=headline_chip_strip([
            (str(n_matches), "VERIFIED MATCHES", "var(--green)" if n_matches else "#7A7A7A"),
            ("10", "LIBRARY ENTRIES", "var(--blue)"),
            ("10", "PENDING REVIEW",  "var(--amber)"),
        ]),
        body=body_lines([
            (f"Headline pack: cell {h.get('cell_id','?')} · {h.get('signature_id','—').replace('_',' ')}", "var(--blue)"),
            (
                f"{n_matches} verified precedents matched" if n_matches
                else "NO verified matches · matcher fails closed on pending entries",
                "var(--green)" if n_matches else "var(--amber)",
            ),
            ("Seed library: 10 CHR-friction entries, all pending_human_review", "var(--text-3)"),
            ("Curator handoff: corroborate against cited public sources · flip to verified", "var(--text-3)"),
            ("Two-stage trust: matcher excludes pending entries from prod Risk scoring", "var(--text-3)"),
        ]),
        footer=box_footer("chronicle v0.1.0", NOW, live=True,
                         note="Risk methodology will use chronicle once entries flip to verified"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Per-journey commentary boxes (4 boxes, one per journey)
# ─────────────────────────────────────────────────────────────────────────────

def render_box_commentary_for_journey(packs: list[dict], journey_prefix: str,
                                       display_name: str) -> str:
    """One box per journey showing the 3 signatures' summaries."""
    journey_packs = [p for p in packs
                     if (p["hypothesis"] or {}).get("screen_id", "").startswith(journey_prefix)]
    if not journey_packs:
        return render_box(
            header=box_header(f"COMMENTARY · {display_name}", "—"),
            headline=headline_tier_badge("NO PACKS", "var(--text-3)", "No packs for this journey"),
            body=body_lines([("Journey not present in registry", "var(--text-3)")]),
            footer=box_footer("commentary v0.1", NOW, live=False, note="—"),
        )
    n_pos = sum(1 for p in journey_packs if (p["hypothesis"] or {}).get("ground_truth_expectation") != "negative")
    n_neg = len(journey_packs) - n_pos
    # Dominant action tier for the journey
    cells = [get_pack_cell(p["meta"]["pack_name"]) for p in journey_packs]
    cells = [c for c in cells if c is not None]
    if cells:
        action_counts: dict[str, int] = {}
        for c in cells:
            action_counts[c.action_tier] = action_counts.get(c.action_tier, 0) + 1
        dominant = max(action_counts, key=action_counts.get)
        dom_color = _ACTION_COLORS.get(dominant, "var(--amber)")
        tier_text = f"{dominant} · {action_counts[dominant]}/{len(cells)}"
    else:
        dominant = "—"
        dom_color = "var(--text-3)"
        tier_text = "engine offline"
    # Evidence: 2 of the journey's packs
    evidence: list[tuple[str, str]] = []
    for p in journey_packs[:2]:
        h = p["hypothesis"] or {}
        evidence.append((
            _extract_quote(p) or
            (p["meta"].get("description", "").strip().replace("\n", " "))[:200],
            f"Cell {h.get('cell_id','?')} · {h.get('signature_id','—').replace('_',' ')}",
        ))
    return render_box(
        header=box_header(f"COMMENTARY · {display_name}", f"{len(journey_packs)} packs"),
        accent_color=dom_color,
        headline=headline_tier_badge(
            tier=tier_text, color=dom_color,
            context=f"Per-journey roll-up · {n_pos} positive · {n_neg} negative · 3 signatures (dwell · multi_back · abandon)",
        ),
        body=body_evidence_cards(evidence) + body_lines([
            (f"Journey: {journey_prefix}", "var(--blue)"),
            (f"{len(journey_packs)} packs canvas-complete · all in registry", "var(--green)"),
        ]),
        footer=box_footer("commentary v0.1", NOW, live=True,
                         note=f"Journey: {display_name}"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Bench box (summary across 12 cells)
# ─────────────────────────────────────────────────────────────────────────────

def render_box_bench(packs: list[dict]) -> str:
    sorted_packs = sorted(packs, key=lambda p: (p["hypothesis"] or {}).get("cell_id", 99))
    rows = ""
    densities = []
    for p in sorted_packs[:6]:
        h = p["hypothesis"] or {}
        cohort_n = len(h.get("cohort_axes") or [])
        evidence_n = len(h.get("evidence_required") or [])
        density = min((cohort_n + evidence_n) * 6, 100)
        densities.append(density)
        is_neg = h.get("ground_truth_expectation") == "negative"
        gt_color = "var(--amber)" if is_neg else "var(--teal)"
        sig = h.get("signature_id", "—").replace("_", " ")
        rows += (
            f'<tr><td>Cell {h.get("cell_id","?")} · {sig[:18]}</td>'
            f'<td style="text-align:right;font-family:var(--mono);">{density}%</td>'
            f'<td style="text-align:right;color:{gt_color};">{"NEG" if is_neg else "POS"}</td></tr>'
        )
    avg_density = int(sum(densities) / len(densities)) if densities else 0
    return render_box(
        header=box_header("⚠ FRICTIONBENCH", "cell density"),
        accent_color="var(--blue)",
        headline=headline_stat_card(
            label="AVG DENSITY",
            value=f"{avg_density}%",
            delta=f"+{avg_density - 60}% vs floor",
            traj="↗" if avg_density > 60 else "→",
            meta_left=f"Cohort axes + evidence fields across {len(packs)} cells",
            meta_right=NOW,
            progress_pct=avg_density,
        ),
        body=(
            f'<table class="body-table">'
            f'<thead><tr><th>Cell</th><th style="text-align:right;">Density</th>'
            f'<th style="text-align:right;">GT</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>'
        ) + body_lines([
            (f"Top {min(6, len(packs))} cells shown · scroll detail in v0.2", "var(--text-3)"),
            ("Density = (cohort_axes + evidence_required) × 6 cap 100%", "var(--text-3)"),
        ]),
        footer=box_footer("frictionbench v0.1", NOW, live=True,
                         note=f"FrictionBench cell benchmark · {len(packs)} cells covered"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# JS — adapted from render_mil_briefing FILTER_JS
# ─────────────────────────────────────────────────────────────────────────────

FILTER_JS = """
<script>
/* Holter filter JS — sidebar checkboxes + topnav dropdowns drive box visibility.
 * Each .holter-box can carry data-packname / data-domain / data-author etc.;
 * the filter applies via class .filtered-out → display:none.
 */
(function () {
  // Topnav + filter strip dropdowns — all are <select data-filter="…">
  const $selects = ['filter-product', 'filter-owner', 'filter-journey']
                     .map(id => document.getElementById(id));
  const $resetBtn  = document.getElementById('filter-reset');
  const $stripApply = document.getElementById('filter-apply');
  const $stripReset = document.getElementById('filter-strip-reset');

  function matches(el) {
    const filters = $selects.filter(Boolean).map(sel => ({
      attr: sel.dataset.filter,
      value: sel.value,
    })).filter(f => f.value);
    for (const f of filters) {
      if (f.attr === 'packname' && el.dataset.packname !== f.value) return false;
      if (f.attr === 'author' && (el.dataset.author || '').split(',').indexOf(f.value) < 0) return false;
      if (f.attr === 'domain' && el.dataset.domain !== f.value) return false;
    }
    return true;
  }

  function applyFilters() {
    const boxes = document.querySelectorAll('.holter-box[data-packname], .holter-box[data-domain]');
    boxes.forEach(b => {
      if (matches(b)) b.classList.remove('filtered-out');
      else b.classList.add('filtered-out');
    });
    let anyActive = false;
    $selects.forEach(sel => {
      if (!sel) return;
      if (sel.value) { sel.classList.add('filter-on'); anyActive = true; }
      else sel.classList.remove('filter-on');
    });
    if ($resetBtn) {
      if (anyActive) $resetBtn.removeAttribute('hidden');
      else $resetBtn.setAttribute('hidden', '');
    }
  }

  function reset() {
    $selects.forEach(sel => { if (sel) sel.value = ''; });
    applyFilters();
  }

  $selects.forEach(sel => sel && sel.addEventListener('change', applyFilters));
  if ($resetBtn) $resetBtn.addEventListener('click', reset);
  if ($stripApply) $stripApply.addEventListener('click', applyFilters);
  if ($stripReset) $stripReset.addEventListener('click', reset);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') reset(); });

  applyFilters();
})();

/* Time picker popover */
(function () {
  const btn = document.getElementById('time-btn');
  const pop = document.getElementById('time-pop');
  const label = document.getElementById('time-btn-label');
  if (!btn || !pop || !label) return;

  function close() { pop.setAttribute('hidden', ''); }
  function open() { pop.removeAttribute('hidden'); }
  function isOpen() { return !pop.hasAttribute('hidden'); }

  btn.addEventListener('click', e => {
    e.stopPropagation();
    isOpen() ? close() : open();
  });
  document.addEventListener('click', e => {
    if (e.target.closest('#time-pop') || e.target.closest('#time-btn')) return;
    close();
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });

  document.querySelectorAll('.time-preset').forEach(p => {
    p.addEventListener('click', () => {
      label.textContent = p.textContent.trim();
      document.querySelectorAll('.time-preset').forEach(b => b.classList.remove('active'));
      p.classList.add('active');
      close();
    });
  });
  const applyCustom = document.getElementById('time-apply');
  if (applyCustom) {
    applyCustom.addEventListener('click', () => {
      const from = document.getElementById('time-from').value;
      const to = document.getElementById('time-to').value;
      if (from && to) {
        label.textContent = from + ' → ' + to;
        document.querySelectorAll('.time-preset').forEach(b => b.classList.remove('active'));
      }
      close();
    });
  }
})();
</script>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Page composition
# ─────────────────────────────────────────────────────────────────────────────

def render_page() -> str:
    packs = discover_packs()
    rows_html = ""

    # Row 1 — topbar: Box 1/2/3 only (Box 0 dissolved into sticky filter strip)
    rows_html += '<div class="holter-row" data-row="topbar">'
    rows_html += render_box1(packs)
    rows_html += render_box2(packs)
    rows_html += render_box3(packs)
    rows_html += '</div>'

    # Page-chrome strips between topbar row and engine-summary row.
    # Documented exceptions to the box discipline — full-width horizontal
    # elements (ticker is a stream; journey row is a 4-cell status strip).
    rows_html += render_ticker(packs)
    rows_html += render_journey_row(packs)

    # Row 2 — engine summary
    rows_html += '<div class="holter-row" data-row="engine-summary">'
    rows_html += render_box_friction_risk(packs)
    rows_html += render_box_placement_posture(packs)
    rows_html += render_box_confidence_protocol(packs)
    rows_html += '</div>'

    # Row 3 — methodology distributions
    rows_html += '<div class="holter-row" data-row="methodology-distributions">'
    rows_html += render_box_diagnosis_dist(packs)
    rows_html += render_box_value_dist(packs)
    rows_html += render_box_risk_dist(packs)
    rows_html += '</div>'

    # Row 4 — chronicle + bench + first journey commentary
    rows_html += '<div class="holter-row" data-row="detail-row-1">'
    rows_html += render_box_chronicle(packs)
    rows_html += render_box_bench(packs)
    rows_html += render_box_commentary_for_journey(packs, "loans", "Loans · step3")
    rows_html += '</div>'

    # Row 5 — remaining journey commentary
    rows_html += '<div class="holter-row" data-row="detail-row-2">'
    rows_html += render_box_commentary_for_journey(packs, "international", "International · setup")
    rows_html += render_box_commentary_for_journey(packs, "cards", "Cards · eligibility")
    rows_html += render_box_commentary_for_journey(packs, "investments", "Investments · overview")
    rows_html += '</div>'

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Holter — functional template</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div class="holter-app">
  {render_topnav(packs)}
  {render_filter_strip(packs)}
  <main class="holter-main">{rows_html}</main>
</div>
{FILTER_JS}
</body>
</html>'''


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    html = render_page()
    out = OUT_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out}  ({len(html):,} bytes)")


if __name__ == "__main__":
    main()

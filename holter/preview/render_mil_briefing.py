"""Render decision packs in the MIL Sonar V4 briefing template.

Per direction 2026-05-18: "follow MIL briefing template — use the EXACT same
template." This drops Streamlit and outputs static HTML matching the MIL Sonar
V4 layout (cjipro/mil_streamlit → mil/publish/output/index_v4.html), with
content sections re-keyed for Pulse decision packs:

  MIL Sonar concept               Pulse mapping
  ──────────────────────────────  ─────────────────────────────────────
  Barclays Sentiment score        Pack coverage score (12/12 cells)
  Quote cards                     Bank-altitude headlines from packs
  Issues Status box               Cell ground-truth distribution
  Journey list                    4 friction-target screens
  Intelligence Brief (Box 3)      Selected pack's Bank altitude
  Sentiment ticker                Pack lineage anchor ticker
  Journey Row                     4 friction-target screens with detection rate
  Journey cards (left col)        Per-pack cards ranked by severity
  Chronicle Failure Library       FrictionBench cell catalogue
  Active Inferences               Selected pack's hypothesis
  Signal Sources                  Cohort axes for selected pack
  Churn Risk Score                Friction risk score across packs
  Analyst Commentary              Per-pack risk/strength commentary
  Technical/Service Benchmark     FrictionBench cell scoring
  Intelligence Findings           Signal-altitude per-session evidence
  Clark Protocol                  Confidence tier tiles

CSS variables and class names are kept identical to the MIL template so the
visual treatment stays canonical.

Run with: py holter/preview/render_mil_briefing.py
Output:  dist/preview/index.html
"""

from __future__ import annotations

import datetime as _dt
import hashlib
from pathlib import Path
from typing import Any

import yaml

REPO = Path(__file__).resolve().parents[2]
PACKS_DIR = REPO / "pulse" / "decision_packs"
JOURNEY_TAXONOMY = REPO / "pulse" / "contracts" / "journey_taxonomy.yaml"
OUT_DIR = REPO / "dist" / "preview"


def load_journey_taxonomy() -> dict[str, str]:
    """Returns {journey_id: category} from pulse/contracts/journey_taxonomy.yaml."""
    if not JOURNEY_TAXONOMY.exists():
        return {}
    data = yaml.safe_load(JOURNEY_TAXONOMY.read_text(encoding="utf-8"))
    return data.get("journeys", {})


# ─────────────────────────────────────────────────────────────────────────────
# Load packs
# ─────────────────────────────────────────────────────────────────────────────

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
            "meta_raw": raw_bytes.decode("utf-8"),
            "sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "hypothesis": hypothesis,
            "bank_md": bank_md,
        })
    return packs


def short_hash(h: str) -> str:
    return f"{h[:12]}…{h[-4:]}"


def headline_pack(packs: list[dict]) -> dict:
    """Pick a load-bearing pack for the top-of-page briefing. Prefer the
    cell-10 negative if present (regulator-defensible discriminator); else
    the cards abandonment (largest opportunity cost in current samples)."""
    for p in packs:
        h = p["hypothesis"] or {}
        if h.get("cell_id") == 10:
            return p
    for p in packs:
        if "abandon_before_submit" in p["meta"]["pack_name"] and "cards" in p["meta"]["pack_name"]:
            return p
    return packs[0]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers for HTML fragments
# ─────────────────────────────────────────────────────────────────────────────

def screen_short(screen_id: str) -> str:
    """`loans.apply.step3` → `loans · step3` for compact display."""
    parts = screen_id.split(".")
    if len(parts) >= 2:
        return f"{parts[0]} · {parts[-1]}"
    return screen_id


def pack_severity(pack: dict) -> tuple[str, str, str]:
    """Return (badge_label, css_color_var, border_color)."""
    h = pack["hypothesis"] or {}
    gt = h.get("ground_truth_expectation", "positive")
    if gt == "negative":
        return ("NEGATIVE · LOAD-BEARING", "var(--amber)", "var(--amber)")
    return ("POSITIVE", "var(--red)", "var(--red)")


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
# HTML rendering
# ─────────────────────────────────────────────────────────────────────────────

CSS = """
:root {
  --bg: #00273D; --topbar-bg: #001E30; --ticker-bg: #001828; --journey-bg: #001E30;
  --summary-bg: #002030; --feed-bg: #00273D; --panel-bg: #001828; --card: #002A3F;
  --border: #003A5C; --blue: #00AEEF; --teal: #00AFA0; --amber: #F5A623;
  --red: #CC0000; --green: #2a9a5a;
  --text: #E8F4FA; --text-2: #7AACBF; --text-3: #4A7A8F; --muted: #3A6A7F;
  --mono: 'DM Mono', 'JetBrains Mono', monospace;
  --sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html, body {
  background: var(--bg); color: var(--text); font-family: var(--sans);
  font-size: 14px; line-height: 1.5; min-height: 100vh;
}
a { color: var(--blue); text-decoration: none; }

/* ── App top nav ────────────────────────────────────────────────
   Global chrome: CJI Pulse brand + canvas-header dropdowns + utility cluster.
   Sticky at top:0; topbar below it sticks at top:48px so both stay visible. */
.app-topnav {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; height: 48px;
  background: #000810;
  border-bottom: 1px solid var(--border);
  position: sticky; top: 0; z-index: 110;
  min-width: 0;
}
.topnav-brand { display: flex; align-items: baseline; gap: 12px; min-width: 0; }
.brand-logo {
  font-family: var(--sans); font-weight: 800; font-size: 18px;
  letter-spacing: 2.5px; color: var(--blue); text-transform: uppercase;
  white-space: nowrap;
}
.brand-tagline {
  font-family: var(--mono); font-size: 10.5px; color: var(--text-3);
  letter-spacing: 1.2px; text-transform: uppercase; white-space: nowrap;
}
.topnav-controls { display: flex; gap: 6px; align-items: center; min-width: 0; }
.topnav-select {
  background: transparent;
  border: 1px solid var(--border); border-radius: 4px;
  padding: 4px 22px 4px 10px;
  font-family: var(--mono); font-size: 11px; color: var(--text-2);
  min-width: 130px; appearance: none;
  background-image: url("data:image/svg+xml;charset=utf-8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 14 8' fill='%234A7A8F'><path d='M0 0l7 8 7-8z'/></svg>");
  background-repeat: no-repeat; background-position: right 8px center;
  background-size: 8px 6px; cursor: not-allowed; opacity: 0.85;
}
.topnav-select.active {
  cursor: pointer; opacity: 1;
  color: var(--text);
}
.topnav-select.active:hover { border-color: var(--blue); }
.topnav-select.active:focus { outline: none; border-color: var(--blue); }
.topnav-select.active.filter-on {
  border-color: var(--amber);
  color: var(--amber);
  background-image: url("data:image/svg+xml;charset=utf-8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 14 8' fill='%23F5A623'><path d='M0 0l7 8 7-8z'/></svg>");
}
.topnav-reset {
  background: transparent;
  border: 1px solid var(--border); border-radius: 4px;
  padding: 4px 10px;
  font-family: var(--mono); font-size: 11px;
  color: var(--text-3);
  cursor: pointer; text-transform: uppercase; letter-spacing: 0.8px;
  margin-left: 4px;
}
.topnav-reset:hover { color: var(--text); border-color: var(--text-3); }
.topnav-reset.active {
  color: var(--amber); border-color: var(--amber);
}
.topnav-select-label {
  font-family: var(--mono); font-size: 9px; color: var(--text-3);
  text-transform: uppercase; letter-spacing: 0.8px; margin-right: 4px;
}
.topnav-control-group { display: flex; align-items: center; gap: 2px; }
.topnav-utility { display: flex; gap: 12px; align-items: center; flex-shrink: 0; }
.topnav-icon {
  font-family: var(--mono); font-size: 14px; color: var(--text-3);
  cursor: pointer; padding: 4px 8px; border-radius: 4px;
  display: inline-flex; align-items: center; gap: 4px;
}
.topnav-icon:hover { color: var(--text); background: var(--card); }
.topnav-icon-badge {
  background: var(--red); color: #fff; border-radius: 8px;
  font-size: 9px; padding: 0 5px; font-weight: 700;
  min-width: 14px; text-align: center;
}
.topnav-avatar {
  font-family: var(--mono); font-size: 11px; font-weight: 700;
  color: var(--bg); background: var(--amber);
  width: 30px; height: 30px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%;
}
.topnav-divider {
  width: 1px; height: 22px; background: var(--border); margin: 0 4px;
}

/* topbar — Box0 is the first column (168px), then Box1/2/3 (1fr each).
   align-items: stretch on the grid + height: auto on boxes = all 4 share
   the row's tallest box's height. Sticky at top:48px to clear the topnav. */
.topbar {
  display: grid;
  grid-template-columns: 168px minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr);
  gap: 16px;
  padding: 16px 24px; background: var(--topbar-bg);
  border-bottom: 1px solid var(--border); position: sticky; top: 48px; z-index: 100;
  align-items: stretch;
  min-width: 0;
}
.topbar > * { min-width: 0; }
.topbar-box, .topbar-box-body, .topbar-box-header, .topbar-box-body * {
  min-width: 0;
  word-break: break-word;
  overflow-wrap: anywhere;
}
.topbar-box { background: #002A3F; border: 1px solid #003A5C; border-radius: 12px;
              overflow: hidden; display: flex; flex-direction: column; }
.topbar-box-header { padding: 10px 16px; border-bottom: 1px solid #003A5C;
                     display: flex; align-items: center; justify-content: space-between; }
.topbar-box-title { font-size: 13px; font-weight: 700; letter-spacing: 2px;
                    text-transform: uppercase; color: var(--text-2); }
.topbar-box-body { padding: 14px 16px; flex: 1; display: flex; flex-direction: column; gap: 10px; }
.topbar-logo { font-weight: 800; font-size: 17px; letter-spacing: 1.5px;
               color: var(--blue); margin-bottom: 2px; }

/* Box 1: brand + score card */
.topbar-sent-card { background: #002A3F; border: 1px solid #00AEEF; border-radius: 8px;
                    overflow: hidden; }
.sent-card-bar { height: 2px; background: linear-gradient(90deg, #00AEEF, #0080C0); }
.sent-card-inner { padding: 8px 14px; display: flex; flex-direction: column; gap: 3px; }
.sent-row-1 { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.sent-row-2 { display: flex; align-items: center; justify-content: space-between; }
.sent-card-label { font-size: 15px; font-weight: 700; letter-spacing: 2px;
                   color: #00AEEF; text-transform: uppercase; flex-shrink: 0; }
.sent-card-score { font-family: var(--mono); font-size: 36px; font-weight: 800;
                   color: #E8F4FA; line-height: 1; }
.sent-card-delta { font-family: var(--mono); font-size: 16px; font-weight: 600; }
.sent-card-traj { font-size: 10px; font-weight: 700; margin-left: auto; }
.sent-card-baseline { font-family: var(--mono); font-size: 10px; color: #4A7A8F; }
.sent-card-progress { height: 2px; background: #003A5C; border-radius: 1px; margin-top: 3px; }
.sent-progress-fill { height: 2px; background: linear-gradient(90deg, #00AEEF, #0080C0); }
.sent-card-ts { font-family: var(--mono); font-size: 10px; color: #3A6A7F; }
.brand-line { display: flex; align-items: flex-start; gap: 7px; font-size: 15px;
              font-weight: 400; color: var(--text-2); line-height: 1.4; }
.brand-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; margin-top: 3px; }
.brand-dot-blue { background: #00AEEF; box-shadow: 0 0 4px rgba(0,174,239,0.5); }
.brand-dot-teal { background: #00AFA0; box-shadow: 0 0 4px rgba(0,175,160,0.5); }
.topbar-pills { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 3px; }
.version-pill { font-family: var(--mono); font-size: 12px; color: var(--text-3);
                background: var(--card); border: 1px solid var(--border);
                padding: 2px 8px; border-radius: 4px; }
.live-dot { display: inline-flex; align-items: center; gap: 6px; font-size: 11px;
            color: var(--teal); font-weight: 600; letter-spacing: 0.05em; }
.live-dot::before { content: ''; width: 7px; height: 7px; background: var(--teal);
                    border-radius: 50%; animation: pulse 2s ease-in-out infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }

/* Box 2: pack status */
.issues-stat-row { display: flex; align-items: center; gap: 12px; }
.issues-stat-num { font-family: var(--mono); font-size: 40px; font-weight: 800;
                   line-height: 1; min-width: 52px; }
.issues-stat-label { font-size: 12px; font-weight: 700; letter-spacing: 1.5px;
                     color: var(--text-3); text-transform: uppercase; }
.issues-stat-sub { font-size: 13px; color: var(--text-2); margin-top: 2px; }
.issues-divider { height: 1px; background: #003A5C; margin: 4px 0; }
.journey-list-item { display: flex; align-items: center; justify-content: space-between;
                     padding: 5px 0; border-bottom: 1px solid #001E30; font-size: 14px; }
.journey-list-item:last-child { border-bottom: none; }
.journey-list-name { color: #7AACBF; font-weight: 600; }
.journey-list-right { display: flex; align-items: center; gap: 6px; }
.journey-list-score { font-family: var(--mono); font-size: 16px; font-weight: 700; }
.journey-list-meta { color: #4A7A8F; font-size: 11px; font-weight: 500; }
.journey-list-status { font-size: 10px; font-weight: 700; }

/* Box 3: intelligence brief (exec alert) */
.exec-alert-panel { background: #001828; border: 1px solid #CC0000; border-radius: 12px; }
.exec-alert-panel.nominal { border-color: #00AFA0; }
.preamble {
  padding: 10px 12px; background: #04131D; border: 1px solid #003A5C;
  border-left: 3px solid var(--amber); border-radius: 3px; margin-bottom: 14px;
  font-size: 12px; color: #E8F4FA; line-height: 1.55;
}
.preamble strong { color: #FFD580; }
.preamble-sub { color: #7AACBF; font-size: 11px; margin-top: 4px; }
.volume-strip { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.volume-card { flex: 1 1 140px; min-width: 140px; padding: 12px 14px;
               background: #001828; border: 1px solid #003A5C; border-radius: 4px; }
.volume-num { font-family: var(--mono); font-size: 24px; font-weight: 700;
              line-height: 1; margin-bottom: 6px; letter-spacing: 0.5px; }
.volume-lbl { font-size: 9px; color: #7AACBF; text-transform: uppercase;
              letter-spacing: 1.2px; margin-bottom: 4px; font-weight: 600; }
.volume-sub { font-size: 10px; color: #4A7A8F; font-family: var(--mono); }
.alert-section-label { font-size: 9px; color: #3A6A7F; text-transform: uppercase;
                       letter-spacing: 1px; margin-bottom: 5px; }
.alert-section-text { font-size: 12px; color: #C5DDE8; line-height: 1.65; }
.alert-quote { font-size: 11px; color: #4A7A8F; font-style: italic;
               border-left: 2px solid #003A5C; padding-left: 10px; margin: 10px 0 14px; }
.alert-section + .alert-section { margin-top: 14px; border-top: 1px solid #003A5C; padding-top: 14px; }
.clark-badge-wrap { margin-top: 14px; border-top: 1px solid #003A5C; padding-top: 14px; }
.clark-badge {
  display: inline-block; padding: 8px 14px; border-radius: 4px;
}
.clark-badge-tier { display: block; font-size: 11px; font-weight: 700;
                    letter-spacing: 1px; }
.clark-badge-action { display: block; font-size: 10px; color: #7AACBF;
                      margin-top: 4px; font-family: var(--mono); letter-spacing: 0.3px; }

/* Ticker */
.ticker-wrapper { overflow: hidden; background: var(--ticker-bg);
                  border-top: 1px solid var(--border); border-bottom: 1px solid var(--border);
                  padding: 11px 0; }
.ticker-track { overflow: hidden; white-space: nowrap; }
.ticker-inner { display: inline-flex; align-items: center;
                animation: ticker-scroll 60s linear infinite; }
.ticker-inner:hover { animation-play-state: paused; }
@keyframes ticker-scroll {
  0% { transform: translateX(0); } 100% { transform: translateX(-50%); }
}
.ticker-item { display: inline-flex; align-items: center; gap: 6px; padding: 0 20px; }
.ticker-name { font-size: 13px; font-weight: 600; color: var(--text-2); }
.ticker-score { font-family: var(--mono); font-size: 15px; font-weight: 700; color: var(--text); }
.ticker-delta { font-family: var(--mono); font-size: 10px; }
.ticker-sep { color: var(--border); padding: 0 4px; font-size: 18px; }
.mini-bar { display: inline-flex; align-items: center; width: 60px; height: 4px;
            background: var(--border); border-radius: 2px; overflow: hidden; }
.mini-bar-fill { height: 4px; border-radius: 2px; }

/* Journey row */
.journey-row-header { display: flex; align-items: baseline; flex-wrap: wrap;
                      padding: 10px 20px; border-top: 1px solid var(--border);
                      background: var(--journey-bg); gap: 6px 18px; }
.journey-row-title { font-size: 12px; font-weight: 800; color: var(--text-2);
                     letter-spacing: 1.8px; text-transform: uppercase; }
.journey-row-sub { font-size: 10px; color: #4A7A8F; font-family: var(--mono); }
.journey-row { display: flex; gap: 1px; background: var(--border);
               border-bottom: 2px solid var(--border); }
.journey-cell { flex: 1; padding: 10px 32px; background: var(--journey-bg);
                border-top: 3px solid var(--border); }
.journey-cell-name { font-size: 13px; font-weight: 700; color: var(--text-2);
                     letter-spacing: 1px; margin-bottom: 4px; text-transform: uppercase; }
.journey-cell-score { font-size: 30px; font-weight: 800; font-family: var(--mono);
                      margin-bottom: 4px; color: var(--text); }
.journey-cell-meta { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.journey-cell-submeta { font-size: 10px; color: #4A7A8F; font-family: var(--mono);
                        margin-top: 4px; letter-spacing: 0.3px; }
.journey-status-label { font-size: 10px; font-weight: 700; letter-spacing: 0.06em;
                        font-family: var(--mono); color: var(--text-3); }

/* Metrics strip */
.metrics-strip { display: flex; gap: 1px; background: var(--border);
                 border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); }
.metric-card { flex: 1; padding: 12px 32px; background: var(--summary-bg); }
.metric-value { font-size: 28px; font-weight: 800; font-family: var(--mono);
                line-height: 1; margin-bottom: 4px; }
.metric-label { font-size: 10px; font-weight: 700; letter-spacing: 1.5px;
                color: var(--text-3); text-transform: uppercase; }
.metric-sub { font-size: 12px; color: var(--text-2); margin-top: 2px; }

/* Body wrapper: left feed + right panel */
.body-wrapper { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 1px;
                background: var(--border); min-height: calc(100vh - 200px);
                min-width: 0; }
.body-wrapper > * { min-width: 0; }
.left-col { background: var(--feed-bg); padding: 18px 32px 24px;
            display: flex; flex-direction: column; gap: 16px; }
.right-col { background: var(--panel-bg); padding: 16px 18px;
             display: flex; flex-direction: column; gap: 16px; }

/* Journey cards (left col) */
.journey-card { background: var(--card); border: 1px solid var(--border);
                border-radius: 12px; padding: 16px 18px; display: flex;
                flex-direction: column; gap: 10px; }
.card-header { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.rank-num { font-family: var(--mono); font-size: 12px; font-weight: 800;
            color: var(--text-3); background: var(--border); width: 26px; height: 26px;
            border-radius: 7px; display: flex; align-items: center; justify-content: center; }
.journey-name { font-size: 16px; font-weight: 700; color: var(--text); flex: 1; }
.badge { font-size: 10px; font-weight: 700; letter-spacing: 1px;
         padding: 2px 10px; border-radius: 12px; }
.derived-note { font-size: 11px; font-family: var(--mono); color: var(--amber);
                background: rgba(245,166,35,0.08); padding: 3px 8px; border-radius: 12px;
                display: inline-block; align-self: flex-start; }
.verdict-label { font-size: 10px; font-weight: 700; letter-spacing: 2px;
                 color: var(--blue); text-transform: uppercase; }
.verdict-text { font-size: 13px; font-weight: 600; color: var(--text); line-height: 1.65; }
.version-delta-row { display: flex; align-items: center; gap: 12px; }
.version-label { font-family: var(--mono); font-size: 10px; font-weight: 700;
                 color: var(--blue); background: var(--border);
                 padding: 2px 6px; border-radius: 4px; }
.version-delta { font-family: var(--mono); font-size: 12px; font-weight: 500;
                 background: var(--border); padding: 2px 8px; border-radius: 4px; color: var(--text-2); }
.signal-counts { display: flex; gap: 8px; }
.sig-count { font-family: var(--mono); font-size: 11px; padding: 1px 6px; border-radius: 12px; }
.sig-p1 { background: rgba(204,0,0,0.15); color: #FF4444; border: 1px solid rgba(204,0,0,0.2); }
.sig-p2 { background: rgba(245,166,35,0.10); color: var(--amber); border: 1px solid rgba(245,166,35,0.2); }
.market-note { font-size: 11px; color: var(--muted); font-style: italic; }
.pack-chips { display: flex; gap: 6px; flex-wrap: wrap; }
.pack-chip { font-family: var(--mono); font-size: 10px; padding: 2px 8px;
             border-radius: 10px; background: rgba(0,174,239,0.08);
             color: var(--blue); border: 1px solid rgba(0,174,239,0.2); }
.pack-chip.fairness { background: rgba(245,166,35,0.08);
                       color: var(--amber); border-color: rgba(245,166,35,0.3); }
.pack-chip.negative { background: rgba(0,175,160,0.08);
                       color: var(--teal); border-color: rgba(0,175,160,0.3); }

/* Right panel */
.panel-section { display: flex; flex-direction: column; gap: 10px; }
.panel-title { font-size: 11px; font-weight: 700; letter-spacing: 2px;
               color: var(--blue); text-transform: uppercase;
               padding-bottom: 8px; border-bottom: 1px solid var(--border); }
.chronicle-card { background: var(--card); border: 1px solid var(--border);
                  border-radius: 8px; padding: 12px 14px;
                  display: flex; flex-direction: column; gap: 5px; }
.chronicle-header { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.chronicle-id { font-family: var(--mono); font-size: 11px; font-weight: 600; color: #8BBCCC; }
.chronicle-bank { font-size: 11px; font-weight: 600; color: #8BBCCC; flex: 1; }
.chronicle-date { font-size: 10px; color: var(--muted); font-family: var(--mono); }
.chronicle-type { font-size: 10px; color: #3A5A6F; }
.chronicle-impact { font-size: 11px; font-weight: 700; color: var(--amber); font-family: var(--mono); }
.chronicle-active { font-size: 9px; font-weight: 700; letter-spacing: 1px;
                    background: rgba(204,0,0,0.2); color: #FF6666;
                    padding: 1px 5px; border-radius: 8px; }
.chronicle-hold { font-size: 9px; font-weight: 700;
                  background: rgba(74,122,143,0.2); color: var(--text-3);
                  padding: 1px 5px; border-radius: 8px; }

.inference-card { background: var(--card); border: 1px solid var(--red);
                  border-radius: 12px; padding: 14px 16px;
                  display: flex; flex-direction: column; gap: 8px; }
.inference-header { display: flex; align-items: center; gap: 8px; }
.inference-label { font-size: 11px; font-weight: 800; letter-spacing: 2px;
                   color: var(--red); text-transform: uppercase; }
.severity-badge { font-size: 10px; font-weight: 700; padding: 1px 8px; border-radius: 12px; }
.severity-p0 { background: rgba(204,0,0,0.3); color: #FF4444; }
.severity-p1 { background: rgba(204,0,0,0.15); color: #FF6666; }
.severity-p2 { background: rgba(245,166,35,0.15); color: var(--amber); }
.inference-finding { font-size: 13px; font-weight: 700; color: var(--text); line-height: 1.5; }
.blind-spots { list-style: none; display: flex; flex-direction: column; gap: 4px; }
.blind-spot-item { font-size: 11px; color: #9AB0BA; line-height: 1.5;
                   padding-left: 12px; position: relative; }
.blind-spot-item::before { content: '·'; position: absolute; left: 4px;
                           color: var(--amber); font-weight: 700; }
.chronicle-anchor { font-family: var(--mono); font-size: 11px; color: var(--blue); }

.sources-grid { display: flex; flex-direction: column; gap: 4px; }
.source-item { display: flex; align-items: center; gap: 8px; padding: 5px 0;
               border-bottom: 1px solid var(--border); }
.source-item:last-child { border-bottom: none; }
.dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.dot-green { background: var(--teal); box-shadow: 0 0 4px rgba(0,175,160,0.6); }
.dot-amber { background: var(--amber); box-shadow: 0 0 4px rgba(245,166,35,0.5); }
.dot-grey { background: var(--border); }
.source-name { font-size: 11px; font-weight: 500; color: var(--muted); flex: 1; }
.source-weight { font-family: var(--mono); font-size: 11px; color: var(--text-3); }

/* V3 below-fold layer */
.v3-divider { border: none; border-top: 2px solid #003A5C; margin: 32px 0 0; }
.v3-outer { max-width: 1200px; margin: 0 auto; padding: 24px 16px 60px; }
.v3-label { font-size: 10px; color: #3A6A7F; text-transform: uppercase;
            letter-spacing: 1px; margin-bottom: 24px; }
.churn-header { display: flex; align-items: center; gap: 24px; flex-wrap: wrap; }
.churn-score-block { text-align: center; min-width: 110px; }
.churn-score-num { font-family: var(--mono); font-size: 48px; font-weight: 800; line-height: 1; }
.churn-score-lbl { font-size: 9px; color: #3A6A7F; text-transform: uppercase;
                   letter-spacing: 1px; margin-top: 4px; }
.churn-trend-block { display: flex; flex-direction: column; gap: 6px; }
.churn-trend-badge { display: inline-block; padding: 4px 10px; border-radius: 4px;
                     font-size: 11px; font-weight: 700; letter-spacing: 0.5px; }
.churn-meta { font-size: 11px; color: #4A7A8F; }
.churn-over-list { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
.churn-issue-pill { font-size: 10px; padding: 3px 8px; border-radius: 4px;
                    border: 1px solid #CC3333; color: #CC3333; background: #1A0810; }
.churn-issue-pill.strength { border-color: #00AFA0; color: #00AFA0; background: #00100E; }

.commentary-grid { display: flex; flex-direction: column; gap: 14px; }
.commentary-card { background: #001828; border: 1px solid #003A5C;
                   border-radius: 8px; padding: 16px 20px; }
.commentary-card.risk { border-left: 4px solid #CC3333; }
.commentary-card.strength { border-left: 4px solid #00AFA0; }
.commentary-card.negative { border-left: 4px solid var(--amber); }
.commentary-card-header { display: flex; align-items: center; gap: 10px;
                          margin-bottom: 10px; flex-wrap: wrap; }
.commentary-issue { font-size: 13px; font-weight: 700; color: #E8F4FA; }
.commentary-badge { font-size: 9px; padding: 2px 7px; border-radius: 3px;
                    font-weight: 700; letter-spacing: 0.5px; }
.commentary-badge.risk { background: #2A0808; color: #CC3333; border: 1px solid #CC3333; }
.commentary-badge.strength { background: #001810; color: #00AFA0; border: 1px solid #00AFA0; }
.commentary-badge.negative { background: #2A1200; color: var(--amber); border: 1px solid var(--amber); }
.commentary-stats { display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 10px; }
.commentary-stat { font-size: 10px; color: #3A6A7F; }
.commentary-stat span { font-family: var(--mono); color: #7AACBF; }
.commentary-prose { font-size: 12px; color: #C5DDE8; line-height: 1.65; margin-bottom: 10px; }
.commentary-quote { font-size: 11px; color: #4A7A8F; font-style: italic;
                    border-left: 2px solid #003A5C; padding-left: 10px; }

.bench-table { width: 100%; border-collapse: separate; border-spacing: 0 4px; }
.bench-row-head { font-size: 9px; color: #3A6A7F; text-transform: uppercase;
                  letter-spacing: 0.5px; padding: 4px 8px 8px; text-align: left; }
.bench-issue-row { background: #001828; }
.bench-issue-name { font-size: 11px; color: #C5DDE8; padding: 10px 8px 10px 12px;
                    min-width: 230px; }
.bench-bar-cell { padding: 6px 8px; min-width: 140px; }
.bench-bar-wrap { display: flex; align-items: center; gap: 6px; }
.bench-bar-bg { flex: 1; background: #002030; border-radius: 3px;
                height: 8px; max-width: 140px; }
.bench-bar-fill { height: 8px; border-radius: 3px; }
.bench-bar-pct { font-family: var(--mono); font-size: 10px; color: #7AACBF; min-width: 38px; }
.bench-gap-cell { font-family: var(--mono); font-size: 11px;
                  padding: 10px 8px; text-align: right; min-width: 60px; }
.bench-gap-positive { color: #CC3333; }
.bench-gap-negative { color: #00AFA0; }
.bench-gap-neutral { color: #4A7A8F; }
.bench-days-cell { font-size: 10px; color: #3A6A7F; padding: 10px 8px;
                   min-width: 70px; text-align: left; }

/* Clark Protocol tiles */
.clark-strip { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.clark-tile { flex: 1; min-width: 100px; background: #001828;
              border: 1px solid #003A5C; border-radius: 8px;
              padding: 12px; text-align: center; }
.clark-count { font-family: var(--mono); font-size: 24px; font-weight: 800; }
.clark-tier { font-size: 9px; color: #3A6A7F; text-transform: uppercase;
              letter-spacing: 1px; margin-top: 2px; }
.clark-label { font-size: 8px; color: #4A7A8F; }

/* footer */
.footer { background: var(--topbar-bg); border-top: 1px solid var(--border);
          padding: 16px 32px; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.footer-item { font-size: 11px; color: #2A5A6F; font-family: var(--mono); letter-spacing: 1px; }
.footer-sep { color: var(--border); }
.footer-sovereign { font-size: 11px; font-weight: 700; letter-spacing: 1px;
                    color: var(--blue); background: rgba(0,174,239,0.08);
                    padding: 2px 8px; border-radius: 8px; }

/* ── BOX 0 — first column of the topbar (controls placeholder).
   Inherits .topbar-box chrome via .sidebar.topbar-box so it visually
   matches box1/2/3. Internal sections scroll if box0 content overflows. */
body { overflow-x: hidden; }
.sidebar {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.sidebar-body { flex: 1; overflow-y: auto; }
.sidebar-head {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  background: #001828;
}
.sidebar-tag {
  font-family: var(--mono);
  font-size: 10px;
  color: var(--text-3);
  letter-spacing: 1.5px;
  text-transform: uppercase;
}
.sidebar-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--blue);
  letter-spacing: 2px;
  text-transform: uppercase;
  margin-top: 4px;
}
.sidebar-sub {
  font-size: 9px;
  color: var(--text-3);
  margin-top: 4px;
  line-height: 1.4;
  font-style: italic;
}
.sidebar-section {
  padding: 8px 14px;
  border-bottom: 1px solid #001E30;
}
.sidebar-section-label {
  font-family: var(--mono);
  font-size: 9px;
  font-weight: 700;
  color: var(--text-3);
  letter-spacing: 1.2px;
  text-transform: uppercase;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sidebar-section-label .badge {
  background: rgba(245,166,35,0.08);
  color: var(--amber);
  border: 1px solid rgba(245,166,35,0.3);
  padding: 1px 5px;
  border-radius: 8px;
  font-size: 8px;
  letter-spacing: 0.5px;
}
.sidebar-select {
  width: 100%;
  background: #001828;
  color: var(--text-2);
  border: 1px solid var(--border);
  padding: 6px 8px;
  font-family: var(--mono);
  font-size: 11px;
  border-radius: 4px;
  appearance: none;
  background-image: url("data:image/svg+xml;charset=utf-8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 14 8' fill='%234A7A8F'><path d='M0 0l7 8 7-8z'/></svg>");
  background-repeat: no-repeat;
  background-position: right 8px center;
  background-size: 8px 6px;
  padding-right: 22px;
}
.sidebar-select:focus { outline: none; border-color: var(--blue); }
.sidebar-multiselect {
  background: #001828;
  border: 1px solid var(--border);
  border-radius: 4px;
  max-height: 120px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.sidebar-multi-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  font-family: var(--mono);
  font-size: 10.5px;
  color: var(--text-2);
  border-bottom: 1px solid #001E30;
  cursor: pointer;
}
.sidebar-multi-item:last-child { border-bottom: none; }
.sidebar-multi-item:hover { background: #002A3F; color: var(--text); }
.sidebar-multi-item input {
  margin: 0;
  width: 11px;
  height: 11px;
  accent-color: var(--blue);
  cursor: pointer;
}
.sidebar-multi-item .cat-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  margin-left: auto;
  flex-shrink: 0;
}
.cat-choke_point { background: var(--red); }
.cat-context_loss { background: var(--amber); }
.cat-behavioural_noise { background: #B07A1F; }
.cat-regulator { background: var(--blue); }
.cat-infrastructure { background: var(--text-3); }

.sidebar-placeholder {
  font-family: var(--mono);
  font-size: 10px;
  color: var(--text-3);
  background: #001828;
  border: 1px dashed var(--border);
  border-radius: 4px;
  padding: 10px 12px;
  text-align: center;
  font-style: italic;
}
.sidebar-actions {
  margin-top: auto;
  padding: 12px 14px;
  border-top: 1px solid var(--border);
  background: #001828;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.sidebar-btn {
  font-family: var(--mono);
  font-size: 10.5px;
  letter-spacing: 0.6px;
  padding: 6px 8px;
  border-radius: 4px;
  text-align: center;
  text-transform: uppercase;
  cursor: pointer;
  border: 1px solid var(--border);
  background: #002030;
  color: var(--text-2);
}
.sidebar-btn.primary {
  background: rgba(0,174,239,0.12);
  border-color: var(--blue);
  color: var(--blue);
  font-weight: 700;
}
.sidebar-btn:hover { background: rgba(0,174,239,0.08); color: var(--text); }

@media (max-width: 1024px) {
  .topbar { grid-template-columns: 1fr; }
  .body-wrapper { grid-template-columns: 1fr; }
  .journey-row { flex-wrap: wrap; }
  .journey-cell { min-width: 45%; }
}
"""


def render_ticker(packs: list[dict]) -> str:
    """Scrolling ticker of pack lineage anchors."""
    items = []
    for p in packs:
        sig = (p["hypothesis"] or {}).get("signature_id", "—").replace("_", " ")
        cell = (p["hypothesis"] or {}).get("cell_id", "?")
        sha = short_hash(p["sha256"])
        gt = (p["hypothesis"] or {}).get("ground_truth_expectation", "positive")
        color = "#F5A623" if gt == "negative" else "#7AACBF"
        items.append(
            f'<span class="ticker-item">'
            f'<span class="ticker-name" style="color:{color};">CELL {cell:>2}</span>'
            f'<span class="ticker-score" style="font-size:11px;">{sig}</span>'
            f'<span class="mini-bar"><span class="mini-bar-fill" '
            f'style="width:{40 if gt!="negative" else 22}px;background:{color};"></span></span>'
            f'<span class="ticker-delta" style="color:#3A6A7F;">{sha}</span></span>'
            f'<span class="ticker-sep">·</span>'
        )
    track = "".join(items)
    return f'<div class="ticker-wrapper"><div class="ticker-track"><div class="ticker-inner">{track}{track}</div></div></div>'


def render_journey_row(screens: list[dict]) -> str:
    cells_html = ""
    for s in screens:
        score = 100 - (s["positives"] * 18)  # synthetic — higher positives = lower screen health
        cells_html += (
            f'<div class="journey-cell" style="border-top:3px solid {s["status_color"]};">'
            f'<div class="journey-cell-name">{s["short"]}</div>'
            f'<div class="journey-cell-score">{s["positives"]}/3</div>'
            f'<div class="journey-cell-meta">'
            f'<span class="journey-status-label" style="color:{s["status_color"]};">{s["status"]}</span>'
            f'</div>'
            f'<div class="journey-cell-submeta">{s["total"]} cells · '
            f'{s["positives"]} positive · {s["negatives"]} negative</div>'
            f'</div>'
        )
    header = (
        '<div class="journey-row-header">'
        '<span class="journey-row-title">FRICTION-TARGET SCREENS</span>'
        '<span class="journey-row-sub">FrictionBench v0.1 · 4 screens × 3 signatures</span>'
        '</div>'
    )
    return header + f'<div class="journey-row">{cells_html}</div>'


def render_journey_cards(packs: list[dict]) -> str:
    """Per-pack cards, ranked by ground-truth severity (negative first, then positive)."""
    sorted_packs = sorted(
        packs,
        key=lambda p: (
            0 if (p["hypothesis"] or {}).get("ground_truth_expectation") == "negative" else 1,
            (p["hypothesis"] or {}).get("cell_id", 99),
        ),
    )
    cards = ""
    for i, p in enumerate(sorted_packs, 1):
        meta = p["meta"]
        h = p["hypothesis"] or {}
        label, _, border = pack_severity(p)
        cell = h.get("cell_id", "?")
        screen = h.get("screen_id", "—")
        sig = h.get("signature_id", "—").replace("_", " ")
        analytic_method = (h.get("analytic") or {}).get("method", "—")
        fairness = (h.get("fairness") or {}).get("required_methods", [])
        chip_class = "negative" if "NEGATIVE" in label else ""
        chips = ""
        if fairness:
            chips += f'<span class="pack-chip fairness">FAIRNESS · {len(fairness)} methods</span>'
        chips += f'<span class="pack-chip">{analytic_method}</span>'
        if "NEGATIVE" in label:
            chips += '<span class="pack-chip negative">DISCRIMINATOR ACTIVE</span>'
        domain = screen.split(".")[0] if screen != "—" else ""
        authors = ",".join(meta.get("authors", []))
        gt = h.get("ground_truth_expectation", "")
        cards += f'''
<div class="journey-card pack-card"
     data-packname="{meta['pack_name']}"
     data-author="{authors}"
     data-domain="{domain}"
     data-screen="{screen}"
     data-signature="{h.get('signature_id', '')}"
     data-gt="{gt}"
     data-cell="{cell}"
     style="border-left:3px solid {border};">
  <div class="card-header">
    <span class="rank-num">#{i}</span>
    <span class="journey-name">Cell {cell} · {sig.title()}</span>
    <span class="badge" style="color:{border};background:{'#2a1500' if 'NEGATIVE' in label else '#2a0a0a'};">{label}</span>
  </div>
  <div class="derived-note">{screen}</div>
  <div class="verdict-label">Pack verdict</div>
  <div class="verdict-text">{meta.get("description","").strip().replace(chr(10), " ")[:220]}{"…" if len(meta.get("description","")) > 220 else ""}</div>
  <div class="version-delta-row">
    <span class="version-label">{meta["pack_name"]}</span>
    <code class="version-delta">v{meta["pack_version"]} · sha256:{short_hash(p["sha256"])}</code>
  </div>
  <div class="pack-chips">{chips}</div>
  <div class="market-note">Synthesis: {meta["synthesis_mode"]} · attestation: {(meta["compliance_attestations"] or [{}])[0].get("status", "—")} · {(meta["compliance_attestations"] or [{}])[0].get("name", "—")}</div>
</div>
'''
    return cards


def render_chronicle(packs: list[dict]) -> str:
    """FrictionBench cell catalogue in the chronicle slot."""
    cards = ""
    sorted_packs = sorted(packs, key=lambda p: (p["hypothesis"] or {}).get("cell_id", 99))
    for p in sorted_packs:
        h = p["hypothesis"] or {}
        cell = h.get("cell_id", "?")
        screen = h.get("screen_id", "—")
        sig = h.get("signature_id", "—").replace("_", " ")
        gt = h.get("ground_truth_expectation", "positive")
        if gt == "negative":
            badge = '<span class="chronicle-hold" style="background:rgba(245,166,35,0.2);color:#F5A623;">NEGATIVE · LOAD-BEARING</span>'
        else:
            badge = '<span class="chronicle-active">POSITIVE</span>'
        cards += f'''
<div class="chronicle-card">
  <div class="chronicle-header">
    <span class="chronicle-id">CELL-{cell:02}</span>
    <span class="chronicle-bank">{sig.title()}</span>
    {badge}
  </div>
  <div class="chronicle-type">{screen}</div>
  <div class="chronicle-impact">v{p["meta"]["pack_version"]} · {p["meta"]["pack_name"]}</div>
</div>'''
    return cards


def render_inference(pack: dict) -> str:
    """Currently-selected pack's hypothesis in the inference slot."""
    h = pack["hypothesis"] or {}
    analytic = h.get("analytic") or {}
    method = analytic.get("method", "—")
    trigger = analytic.get("trigger") or {}
    cohort_axes = h.get("cohort_axes") or []
    fairness = (h.get("fairness") or {}).get("required_methods", [])
    gt = h.get("ground_truth_expectation", "positive")
    sev = "P0" if gt == "negative" else "P1"
    sev_cls = "severity-p0" if gt == "negative" else "severity-p1"
    blind_spots_html = ""
    for cls in fairness:
        blind_spots_html += f'<li class="blind-spot-item">Fairness method enforced: {cls}</li>'
    if gt == "negative":
        blind_spots_html += '<li class="blind-spot-item">Discriminator MUST suppress fire — false positives are the failure mode</li>'
    return f'''
<div class="inference-card">
  <div class="inference-header">
    <span class="inference-label">ACTIVE HYPOTHESIS</span>
    <span class="severity-badge {sev_cls}">{sev}</span>
  </div>
  <div class="inference-finding">{method} · {h.get("question_class", "—")}</div>
  <ul class="blind-spots">
    {blind_spots_html}
    <li class="blind-spot-item">Cohort axes: {", ".join(cohort_axes) or "—"}</li>
  </ul>
  <div class="chronicle-anchor">CELL: {h.get("cell_id", "?")} · sha256:{short_hash(pack["sha256"])}</div>
</div>
'''


def render_sources(pack: dict) -> str:
    """Cohort axes in the signal sources slot."""
    h = pack["hypothesis"] or {}
    axes = h.get("cohort_axes") or []
    items = ""
    for a in axes:
        items += (
            f'<div class="source-item">'
            f'<span class="dot dot-green"></span>'
            f'<span class="source-name">{a}</span>'
            f'<span class="source-weight">enforced</span>'
            f'</div>'
        )
    if not items:
        items = '<div class="source-item"><span class="dot dot-grey"></span><span class="source-name">No cohort axes declared</span></div>'
    return items


def render_intelligence_brief(pack: dict, all_packs: list[dict]) -> str:
    """Box 3 — selected pack's Bank altitude rendered in MIL exec-alert format."""
    h = pack["hypothesis"] or {}
    meta = pack["meta"]
    cell = h.get("cell_id", "?")
    sig = h.get("signature_id", "—").replace("_", " ")
    screen = h.get("screen_id", "—")
    gt = h.get("ground_truth_expectation", "positive")
    is_negative = gt == "negative"

    # Strip markdown headings and code fences — box3 needs to stay compact.
    raw = pack["bank_md"]
    cleaned = " ".join(
        ln.strip().lstrip("#").strip()
        for ln in raw.split("\n")
        if ln.strip() and not ln.startswith("```")
    )
    bank_excerpt = cleaned[:280] + ("…" if len(cleaned) > 280 else "")

    # Synthetic volume strip metrics derived from the pack
    n_packs = len(all_packs)
    n_positive = sum(1 for p in all_packs if (p["hypothesis"] or {}).get("ground_truth_expectation") != "negative")
    n_negative = n_packs - n_positive

    badge_color = "var(--amber)" if is_negative else "#F5A623"
    tier = "PULSE-0 — DISCRIMINATOR REQUIRED" if is_negative else "PULSE-1 — DETECTOR ACTIVE"
    tier_action = "engineering · fairness review · before-fire suppression" if is_negative else "investigation routing · remediation · cohort review"

    return f'''
<div class="topbar-box exec-alert-panel{' nominal' if not is_negative else ''}">
  <div class="topbar-box-header" style="background:#001828;border-bottom:1px solid #003A5C;">
    <span class="topbar-box-title">INTELLIGENCE BRIEF</span>
    <span style="font-size:10px;color:#3A6A7F;">Pulse · cell {cell} · {sig.title()}</span>
  </div>
  <div class="topbar-box-body">
    <div class="preamble">
      <div><strong>{sig.title()}</strong> on {screen} is the active hypothesis — {"NEGATIVE ground truth (detector MUST NOT fire)" if is_negative else "POSITIVE ground truth, detector active"}, cell {cell} of 12 in FrictionBench v0.1.</div>
      <div class="preamble-sub">{n_positive} positive · {n_negative} negative · {n_packs} cells total · synthesis layer pending PULSE-93</div>
    </div>
    <div class="volume-strip">
      <div class="volume-card">
        <div class="volume-num" style="color:var(--blue);">CELL {cell}</div>
        <div class="volume-lbl">FrictionBench</div>
        <div class="volume-sub">v0.1 · frozen</div>
      </div>
      <div class="volume-card">
        <div class="volume-num" style="color:{'var(--amber)' if is_negative else 'var(--teal)'};">{gt.upper()}</div>
        <div class="volume-lbl">Ground truth</div>
        <div class="volume-sub">{"discriminator active" if is_negative else "detector active"}</div>
      </div>
      <div class="volume-card">
        <div class="volume-num" style="color:var(--text-2);">{(h.get("analytic") or {}).get("method", "—").split("_")[0]}</div>
        <div class="volume-lbl">Method family</div>
        <div class="volume-sub" style="font-size:9px;">{(h.get("analytic") or {}).get("method", "—")}</div>
      </div>
      <div class="volume-card">
        <div class="volume-num" style="color:var(--amber);font-size:14px;line-height:1.4;">sha256</div>
        <div class="volume-lbl">Lineage anchor</div>
        <div class="volume-sub">{short_hash(pack["sha256"])}</div>
      </div>
    </div>
    <div class="alert-section">
      <div class="alert-section-label">The Situation</div>
      <div class="alert-section-text">{meta.get("description", "").strip().replace(chr(10), " ")[:500]}</div>
    </div>
    <div class="alert-section">
      <div class="alert-section-label">Bank altitude (preview)</div>
      <div class="alert-section-text">{bank_excerpt}…</div>
    </div>
    <div class="clark-badge-wrap">
      <span class="clark-badge" style="background:{badge_color}22;border:1px solid {badge_color};">
        <span class="clark-badge-tier" style="color:{badge_color};">{tier}</span>
        <span class="clark-badge-action">{tier_action}</span>
      </span>
    </div>
  </div>
</div>
'''


def render_volume_brief_for_box1(packs: list[dict]) -> str:
    """Box 1: 2 sample quote cards from headline packs."""
    quote_packs = [p for p in packs if (p["hypothesis"] or {}).get("cell_id") in (9, 10)]
    if not quote_packs:
        quote_packs = packs[:2]
    cards = ""
    for p in quote_packs[:2]:
        h = p["hypothesis"] or {}
        sig = h.get("signature_id", "—").replace("_", " ")
        cell = h.get("cell_id", "?")
        # First line of bank.md, minus the heading
        lines = [ln for ln in p["bank_md"].split("\n") if ln.strip() and not ln.startswith("#")][:2]
        excerpt = " ".join(lines)[:200] + "…"
        gt = h.get("ground_truth_expectation", "positive")
        cards += (
            f'<div style="border:1px solid #003A5C;border-radius:8px;padding:10px 12px;'
            f'background:#001E2E;">'
            f'<div style="font-size:12px;color:#B8D4E0;font-style:italic;line-height:1.5;">'
            f'"{excerpt}"</div>'
            f'<div style="font-size:11px;color:#4A7A8F;margin-top:6px;letter-spacing:0.03em;">'
            f'CELL {cell} · {sig} · {gt.upper()}</div>'
            f'</div>'
        )
    return cards


def render_volume_brief_for_box2(packs: list[dict], screens: list[dict]) -> str:
    """Box 2 issues status with cell counts + screen list."""
    n_positive = sum(1 for p in packs if (p["hypothesis"] or {}).get("ground_truth_expectation") != "negative")
    n_negative = sum(1 for p in packs if (p["hypothesis"] or {}).get("ground_truth_expectation") == "negative")

    list_items = ""
    for s in screens:
        list_items += (
            f'<div class="journey-list-item">'
            f'<span class="journey-list-name">{s["short"]}</span>'
            f'<span class="journey-list-right">'
            f'<span class="journey-list-score" style="color:{s["status_color"]};">{s["positives"]}/3</span>'
            f'<span class="journey-list-meta">{s["total"]} cells</span>'
            f'<span class="journey-list-status" style="color:{s["status_color"]};">{s["status"]}</span>'
            f'</span></div>'
        )
    return f'''
<div class="topbar-box">
  <div class="topbar-box-header">
    <span class="topbar-box-title">PACK STATUS</span>
    <span style="font-size:10px;color:#3A6A7F;">FrictionBench v0.1 cell coverage</span>
  </div>
  <div class="topbar-box-body">
    <div class="issues-stat-row">
      <span class="issues-stat-num" style="color:var(--teal);" data-count="positive">{n_positive}</span>
      <div><div class="issues-stat-label">Positive</div><div class="issues-stat-sub">DETECTOR ACTIVE cells</div></div>
    </div>
    <div class="issues-stat-row">
      <span class="issues-stat-num" style="color:var(--amber);" data-count="negative">{n_negative}</span>
      <div><div class="issues-stat-label">Negative</div><div class="issues-stat-sub">LOAD-BEARING · discriminator MUST suppress</div></div>
    </div>
    <div class="issues-stat-row">
      <span class="issues-stat-num" style="color:var(--blue);" data-count="total">{len(packs)}</span>
      <div><div class="issues-stat-label">Total</div><div class="issues-stat-sub">cells covered</div></div>
    </div>
    <div class="issues-divider"></div>
    {list_items}
  </div>
</div>'''


def render_metrics_strip(packs: list[dict]) -> str:
    n_packs = len(packs)
    n_negative = sum(1 for p in packs if (p["hypothesis"] or {}).get("ground_truth_expectation") == "negative")
    fairness_enforced = sum(1 for p in packs if p["meta"].get("fairness_methods_required"))
    return f'''
<div class="metrics-strip">
  <div class="metric-card">
    <div class="metric-value" style="color:var(--teal);" data-count="metric-total">{n_packs}</div>
    <div class="metric-label">Cells covered</div>
    <div class="metric-sub" data-count="metric-total-sub">of 12 FrictionBench v0.1</div>
  </div>
  <div class="metric-card">
    <div class="metric-value" style="color:var(--amber);" data-count="metric-negative">{n_negative}</div>
    <div class="metric-label">Load-bearing negative</div>
    <div class="metric-sub">discriminator required</div>
  </div>
  <div class="metric-card">
    <div class="metric-value" style="color:var(--blue);" data-count="metric-fairness">{fairness_enforced}</div>
    <div class="metric-label">Fairness enforced</div>
    <div class="metric-sub">all packs (regulator-defensible)</div>
  </div>
</div>'''


def render_churn_block(packs: list[dict]) -> str:
    """V3 churn-risk-style block — adapt to friction risk score."""
    risk = sum(1 for p in packs if (p["hypothesis"] or {}).get("ground_truth_expectation") != "negative")
    discriminators = sum(1 for p in packs if (p["hypothesis"] or {}).get("negative_class_discriminator"))
    score = f"{risk * 6.5:.1f}"
    pos_pills = "".join(
        f'<span class="churn-issue-pill">{(p["hypothesis"] or {}).get("signature_id","—").replace("_"," ")} · cell {(p["hypothesis"] or {}).get("cell_id","?")}</span>'
        for p in packs if (p["hypothesis"] or {}).get("ground_truth_expectation") != "negative"
    )
    neg_pills = "".join(
        f'<span class="churn-issue-pill strength">{(p["hypothesis"] or {}).get("signature_id","—").replace("_"," ")} · cell {(p["hypothesis"] or {}).get("cell_id","?")} · discriminator</span>'
        for p in packs if (p["hypothesis"] or {}).get("ground_truth_expectation") == "negative"
    )
    return f'''
<div class="topbar-box">
  <div class="topbar-box-header">
    <span class="topbar-box-title">FRICTION RISK SCORE</span>
    <span style="font-size:10px;color:#3A6A7F;">Pulse · FrictionBench cell coverage · risk-weighted</span>
  </div>
  <div class="topbar-box-body">
    <div class="churn-header">
      <div class="churn-score-block">
        <div class="churn-score-num" style="color:var(--amber);">{score}</div>
        <div class="churn-score-lbl">Cell Risk Score</div>
      </div>
      <div class="churn-trend-block">
        <span class="churn-trend-badge" style="background:#002030;color:#7AACBF;border:1px solid #3A6A7F;">12-CELL COVERAGE</span>
        <div class="churn-meta">
          {risk} positive detector cells · {discriminators} negative-class discriminator cells
        </div>
      </div>
    </div>
    <div style="margin-top:12px;">
      <div style="font-size:9px;color:#3A6A7F;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">
        Positive cells — detector active
      </div>
      <div class="churn-over-list">{pos_pills}</div>
    </div>
    <div style="margin-top:10px;">
      <div style="font-size:9px;color:#3A6A7F;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">
        Negative cells — discriminator suppresses
      </div>
      <div class="churn-over-list">{neg_pills}</div>
    </div>
  </div>
</div>'''


def render_commentary_block(packs: list[dict]) -> str:
    """V3 analyst-commentary-style: one card per pack."""
    cards_html = ""
    sorted_packs = sorted(packs, key=lambda p: (p["hypothesis"] or {}).get("cell_id", 99))
    for p in sorted_packs:
        h = p["hypothesis"] or {}
        m = p["meta"]
        gt = h.get("ground_truth_expectation", "positive")
        cell = h.get("cell_id", "?")
        sig = h.get("signature_id", "—").replace("_", " ")
        screen = h.get("screen_id", "—")
        is_neg = gt == "negative"
        cls = "negative" if is_neg else "risk"
        badge_cls = "negative" if is_neg else "risk"
        badge_text = "NEGATIVE · LOAD-BEARING" if is_neg else "POSITIVE · DETECTOR ACTIVE"
        cards_html += f'''
<div class="commentary-card {cls}">
  <div class="commentary-card-header">
    <span class="commentary-issue">Cell {cell} · {sig.title()}</span>
    <span class="commentary-badge {badge_cls}">{badge_text}</span>
    <span class="commentary-badge sev-p{('0' if is_neg else '1')}">SIG · {(h.get("analytic") or {}).get("method","").split("_")[0].upper()}</span>
    <span style="font-size:9px;color:#3A6A7F;">{screen}</span>
  </div>
  <div class="commentary-stats">
    <div class="commentary-stat">Cohort axes <span>{len(h.get("cohort_axes") or [])}</span></div>
    <div class="commentary-stat">Fairness methods <span>{len((h.get("fairness") or {}).get("required_methods", []))}</span></div>
    <div class="commentary-stat">Evidence fields <span>{len(h.get("evidence_required") or [])}</span></div>
    <div class="commentary-stat">Remediation <span>{len(h.get("remediation_categories") or [])}</span></div>
  </div>
  <div class="commentary-prose">{m.get("description","").strip().replace(chr(10), " ")[:400]}</div>
</div>'''
    return f'''
<div class="topbar-box">
  <div class="topbar-box-header">
    <span class="topbar-box-title">PACK COMMENTARY</span>
    <span style="font-size:10px;color:#3A6A7F;">
      Per-cell hypothesis summary · {len(packs)} packs
    </span>
  </div>
  <div class="topbar-box-body">
    <div class="commentary-grid">{cards_html}</div>
  </div>
</div>'''


def render_bench_block(packs: list[dict]) -> str:
    """Pack benchmark table (mirror MIL benchmark)."""
    rows = ""
    sorted_packs = sorted(packs, key=lambda p: (p["hypothesis"] or {}).get("cell_id", 99))
    for p in sorted_packs:
        h = p["hypothesis"] or {}
        cell = h.get("cell_id", "?")
        sig = h.get("signature_id", "—").replace("_", " ")
        screen_s = screen_short(h.get("screen_id", "—"))
        gt = h.get("ground_truth_expectation", "positive")
        is_neg = gt == "negative"
        cohort_n = len(h.get("cohort_axes") or [])
        evidence_n = len(h.get("evidence_required") or [])
        # synthetic "rate" — count of fields as a proxy for hypothesis density
        density = min((cohort_n + evidence_n) * 6, 100)
        bar_color = "var(--amber)" if is_neg else "var(--blue)"
        rows += f'''
<tr class="bench-issue-row">
  <td class="bench-issue-name"><span style="color:{'#F5A623' if is_neg else '#CC0000'};font-size:8px;margin-right:2px;">●</span>Cell {cell} · {sig.title()}</td>
  <td class="bench-bar-cell">
    <div style="margin-bottom:3px;">
      <div style="font-size:8px;color:#3A6A7F;margin-bottom:2px;">Hypothesis density</div>
      <div class="bench-bar-wrap">
        <div class="bench-bar-bg">
          <div class="bench-bar-fill" style="width:{density}%;background:{bar_color};"></div>
        </div>
        <span class="bench-bar-pct" style="color:{bar_color};">{density}%</span>
      </div>
    </div>
  </td>
  <td class="bench-gap-cell {'bench-gap-positive' if is_neg else 'bench-gap-neutral'}">
    {gt.upper()}
  </td>
  <td class="bench-days-cell">{screen_s}</td>
</tr>'''
    return f'''
<div class="topbar-box">
  <div class="topbar-box-header">
    <span class="topbar-box-title">⚠ FRICTIONBENCH CELL BENCHMARK</span>
    <span style="font-size:10px;color:#3A6A7F;">All 12 cells · hypothesis density by cohort + evidence field count</span>
  </div>
  <div class="topbar-box-body">
    <table class="bench-table">
      <thead>
        <tr>
          <th class="bench-row-head">Cell</th>
          <th class="bench-row-head">Density</th>
          <th class="bench-row-head" style="text-align:right;">Ground Truth</th>
          <th class="bench-row-head">Screen</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</div>'''


FILTER_JS = """
<script>
/* HOL-10 phase 1 — top-nav filtering.
 * Reads Product / Owner / Domain dropdowns, hides non-matching .pack-card
 * elements, recomputes counts in box1 / box2 / metrics-strip, syncs URL
 * query params, and toggles the Reset button + dropdown styling.
 * No backend; pure client-side. State shareable via URL. */
(function () {
  const FILTERS = ['product', 'owner', 'domain'];
  const FILTER_TO_DATA = {
    product: 'packname',
    owner:   'author',
    domain:  'domain',
  };

  const $selects = FILTERS.map(f => document.getElementById('filter-' + f));
  const $resetBtn = document.getElementById('filter-reset');
  const $cards = Array.from(document.querySelectorAll('.pack-card'));

  function readURLState() {
    const params = new URLSearchParams(window.location.search);
    FILTERS.forEach((f, i) => {
      const v = params.get(f) || '';
      if ($selects[i]) $selects[i].value = v;
    });
  }

  function writeURLState() {
    const params = new URLSearchParams();
    FILTERS.forEach((f, i) => {
      const v = $selects[i] && $selects[i].value;
      if (v) params.set(f, v);
    });
    const qs = params.toString();
    const url = window.location.pathname + (qs ? '?' + qs : '');
    history.replaceState(null, '', url);
  }

  function matches(card) {
    for (let i = 0; i < FILTERS.length; i++) {
      const sel = $selects[i];
      if (!sel || !sel.value) continue;
      const dataKey = FILTER_TO_DATA[FILTERS[i]];
      const cardVal = card.dataset[dataKey] || '';
      if (FILTERS[i] === 'owner') {
        // multi-value field — comma-separated authors
        const authors = cardVal.split(',').map(s => s.trim());
        if (!authors.includes(sel.value)) return false;
      } else if (cardVal !== sel.value) {
        return false;
      }
    }
    return true;
  }

  function recomputeCounts(visibleCards) {
    let positive = 0, negative = 0, fairness = 0;
    visibleCards.forEach(c => {
      if (c.dataset.gt === 'negative') negative++;
      else positive++;
      // every pack in this dataset declares fairness_methods_required:true
      // we proxy via presence of the FAIRNESS chip on the card
      if (c.querySelector('.pack-chip.fairness')) fairness++;
    });
    const total = visibleCards.length;

    function setText(selector, value) {
      document.querySelectorAll(selector).forEach(el => { el.textContent = value; });
    }

    setText('[data-count="positive"]', positive);
    setText('[data-count="negative"]', negative);
    setText('[data-count="total"]', total);
    setText('[data-count="metric-total"]', total);
    setText('[data-count="metric-total-sub"]',
            total === 12 ? 'of 12 FrictionBench v0.1'
                         : 'of 12 FrictionBench v0.1 · ' + (12 - total) + ' filtered out');
    setText('[data-count="metric-negative"]', negative);
    setText('[data-count="metric-fairness"]', fairness);
    setText('[data-count="coverage-score"]', total + '/12');
    setText('[data-count="coverage-delta"]',
            total === 12 ? '+9 vs showcase'
                         : (total === 0 ? '— no packs in scope'
                                        : 'filtered (' + total + ' of 12)'));
  }

  function recomputeJourneyRow(visibleCards) {
    // Recompute journey-row scores: count visible cards per screen.
    const byScreen = {};
    visibleCards.forEach(c => {
      const dom = c.dataset.domain;
      if (!dom) return;
      if (!byScreen[dom]) byScreen[dom] = { positive: 0, negative: 0 };
      if (c.dataset.gt === 'negative') byScreen[dom].negative++;
      else byScreen[dom].positive++;
    });
    document.querySelectorAll('.journey-cell').forEach(cell => {
      const nameEl = cell.querySelector('.journey-cell-name');
      if (!nameEl) return;
      const dom = nameEl.textContent.trim().split(' ')[0];
      const counts = byScreen[dom] || { positive: 0, negative: 0 };
      const total = counts.positive + counts.negative;
      const scoreEl = cell.querySelector('.journey-cell-score');
      const submetaEl = cell.querySelector('.journey-cell-submeta');
      if (scoreEl) scoreEl.textContent = counts.positive + '/3';
      if (submetaEl) submetaEl.textContent =
        total + ' cells · ' + counts.positive + ' positive · ' + counts.negative + ' negative';
      cell.style.opacity = total === 0 ? '0.35' : '1';
    });
  }

  function applyFilters() {
    const visibleCards = [];
    $cards.forEach(card => {
      if (matches(card)) {
        card.style.display = '';
        visibleCards.push(card);
      } else {
        card.style.display = 'none';
      }
    });
    recomputeCounts(visibleCards);
    recomputeJourneyRow(visibleCards);

    // toggle visual on dropdowns + reset btn
    let anyActive = false;
    $selects.forEach(sel => {
      if (!sel) return;
      if (sel.value) { sel.classList.add('filter-on'); anyActive = true; }
      else sel.classList.remove('filter-on');
    });
    if ($resetBtn) {
      if (anyActive) $resetBtn.classList.add('active');
      else $resetBtn.classList.remove('active');
    }

    writeURLState();
  }

  function reset() {
    $selects.forEach(sel => { if (sel) sel.value = ''; });
    applyFilters();
  }

  // wire events
  $selects.forEach(sel => sel && sel.addEventListener('change', applyFilters));
  if ($resetBtn) $resetBtn.addEventListener('click', reset);
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') reset();
  });

  // on load: read URL state and apply
  readURLState();
  applyFilters();
})();
</script>
"""


def render_topnav(packs: list[dict]) -> str:
    """Global top nav — CJI Pulse brand + canvas-header dropdowns + utility cluster.

    HOL-10 phase 1: Product / Owner / Domain dropdowns are now functional —
    they filter the briefing content via the JS in `render_filter_js()`. Date
    is cosmetic (packs don't carry detection timestamps yet).

    Search / Notifications / Canvas-guide / Settings still placeholders (subsequent
    HOL-10 phases).
    """
    domains = sorted({(p["hypothesis"] or {}).get("screen_id", "").split(".")[0]
                       for p in packs if (p["hypothesis"] or {}).get("screen_id")})
    owners = sorted({a for p in packs for a in p["meta"].get("authors", [])})

    product_opts = '<option value="">all packs · {n}</option>\n'.format(n=len(packs))
    sorted_packs = sorted(packs, key=lambda p: (p["hypothesis"] or {}).get("cell_id", 99))
    for p in sorted_packs:
        h = p["hypothesis"] or {}
        cell = h.get("cell_id", "?")
        sig = h.get("signature_id", "—").replace("_", " ")
        product_opts += (
            f'<option value="{p["meta"]["pack_name"]}">'
            f'cell {cell} · {sig}</option>\n'
        )

    owner_opts = f'<option value="">all teams · {len(owners)}</option>\n'
    for o in owners:
        owner_opts += f'<option value="{o}">{o}</option>\n'

    domain_opts = f'<option value="">all journeys · {len(domains)}</option>\n'
    for d in domains:
        domain_opts += f'<option value="{d}">{d}</option>\n'

    return f'''
<header class="app-topnav">
  <div class="topnav-brand">
    <span class="brand-logo">CJI&nbsp;PULSE</span>
    <span class="brand-tagline">Decision Intelligence · briefing v0</span>
  </div>
  <div class="topnav-controls">
    <div class="topnav-control-group">
      <span class="topnav-select-label">Product</span>
      <select class="topnav-select active" id="filter-product" data-filter="packname">
        {product_opts}
      </select>
    </div>
    <div class="topnav-control-group">
      <span class="topnav-select-label">Owner</span>
      <select class="topnav-select active" id="filter-owner" data-filter="author">
        {owner_opts}
      </select>
    </div>
    <div class="topnav-control-group">
      <span class="topnav-select-label">Domain</span>
      <select class="topnav-select active" id="filter-domain" data-filter="domain">
        {domain_opts}
      </select>
    </div>
    <div class="topnav-control-group">
      <span class="topnav-select-label">Date</span>
      <select class="topnav-select" disabled title="Date filter — packs don't yet carry detection timestamps (HOL-10 phase later)">
        <option>last 7 days</option>
      </select>
    </div>
    <button class="topnav-reset" id="filter-reset" type="button" title="Reset filters (Esc)">Reset</button>
  </div>
  <div class="topnav-utility">
    <span class="topnav-icon" title="Search packs / journeys (HOL-10 phase 2)">⌕&nbsp;Search</span>
    <span class="topnav-divider"></span>
    <span class="topnav-icon" title="Notifications (HOL-10 phase 3)">
      🔔<span class="topnav-icon-badge">3</span>
    </span>
    <span class="topnav-icon" title="Help / Canvas guide (HOL-10 phase 3)">?</span>
    <span class="topnav-icon" title="Settings (HOL-10 phase 3)">⚙</span>
    <span class="topnav-divider"></span>
    <span class="topnav-avatar" title="Hussain Ahmed">HA</span>
  </div>
</header>
'''


def render_sidebar(packs: list[dict]) -> str:
    """Box 0 — left vertical sidebar with placeholder controls."""
    taxonomy = load_journey_taxonomy()  # {journey_id: category}
    # journeys present in at least one pack — pre-tick them in the multi-select
    covered_screens = {(p["hypothesis"] or {}).get("screen_id", "") for p in packs}
    covered_journeys = {s.split(".")[0] for s in covered_screens if s}

    # category dot legend order matches journey_taxonomy.yaml
    journey_items = ""
    for jid, cat in taxonomy.items():
        checked = "checked" if jid in covered_journeys else ""
        journey_items += (
            f'<label class="sidebar-multi-item" title="{cat}">'
            f'<input type="checkbox" {checked} disabled>'
            f'<span>{jid}</span>'
            f'<span class="cat-dot cat-{cat}"></span>'
            f'</label>'
        )

    return f'''
<aside class="topbar-box sidebar">
  <div class="topbar-box-header" style="background:#001828;">
    <span class="topbar-box-title" style="color:#7AACBF;">BOX 0 · CONTROLS</span>
    <span style="font-size:9px;color:#3A6A7F;">placeholder</span>
  </div>
  <div class="sidebar-body">
    <div class="sidebar-section">
      <div class="sidebar-section-label">
        Journey <span class="badge">{len(covered_journeys)} of {len(taxonomy)}</span>
      </div>
      <div class="sidebar-multiselect">{journey_items}</div>
    </div>
    <div class="sidebar-section">
      <div class="sidebar-section-label">Time period</div>
      <select class="sidebar-select" disabled>
        <option>Last 24 hours</option>
        <option selected>Last 7 days</option>
        <option>Last 30 days</option>
        <option>Last quarter</option>
        <option>Custom range…</option>
      </select>
    </div>
    <div class="sidebar-section">
      <div class="sidebar-section-label">ML model</div>
      <select class="sidebar-select" disabled>
        <option selected>deterministic · v1</option>
        <option disabled>llm_augmented · v2 (gated)</option>
      </select>
    </div>
    <div class="sidebar-section">
      <div class="sidebar-section-label">Reserved <span class="badge">future</span></div>
      <div style="display:flex;flex-direction:column;gap:4px;font-family:var(--mono);font-size:10px;color:var(--text-3);">
        <span>· cohort axis</span>
        <span>· confidence floor</span>
        <span>· fairness gate</span>
      </div>
    </div>
  </div>
  <div class="sidebar-actions">
    <button class="sidebar-btn primary" disabled>Apply</button>
    <button class="sidebar-btn" disabled>Reset</button>
  </div>
</aside>
'''


def render_clark_protocol(packs: list[dict]) -> str:
    n_positive = sum(1 for p in packs if (p["hypothesis"] or {}).get("ground_truth_expectation") != "negative")
    n_negative = sum(1 for p in packs if (p["hypothesis"] or {}).get("ground_truth_expectation") == "negative")
    return f'''
<div class="topbar-box">
  <div class="topbar-box-header">
    <span class="topbar-box-title">CONFIDENCE PROTOCOL</span>
    <span style="font-size:10px;color:#3A6A7F;">Pulse synthesis tier · 4-level escalation</span>
  </div>
  <div class="topbar-box-body">
    <div class="clark-strip">
      <div class="clark-tile" style="border-top-color:#CC3333;">
        <div class="clark-count" style="color:#CC3333;">0</div>
        <div class="clark-tier">PULSE-3</div>
        <div class="clark-label">CALIBRATION FAIL</div>
      </div>
      <div class="clark-tile" style="border-top-color:var(--amber);">
        <div class="clark-count" style="color:var(--amber);">{n_negative}</div>
        <div class="clark-tier">PULSE-2</div>
        <div class="clark-label">DISCRIMINATOR ACTIVE</div>
      </div>
      <div class="clark-tile" style="border-top-color:var(--teal);">
        <div class="clark-count" style="color:var(--teal);">{n_positive}</div>
        <div class="clark-tier">PULSE-1</div>
        <div class="clark-label">DETECTOR ACTIVE</div>
      </div>
      <div class="clark-tile" style="border-top-color:var(--blue);">
        <div class="clark-count" style="color:var(--blue);">{len(packs)}</div>
        <div class="clark-tier">PULSE-0</div>
        <div class="clark-label">REGISTRY-VALID</div>
      </div>
    </div>
    <div style="font-size:11px;color:#4A7A8F;padding:8px 0;">
      All {len(packs)} packs pass v1 metadata validator · all declare fairness_methods_required · attestation: self_declared · awaiting PULSE-93 synthesis hydration.
    </div>
  </div>
</div>'''


# ─────────────────────────────────────────────────────────────────────────────
# Page assembly
# ─────────────────────────────────────────────────────────────────────────────

def render_page(packs: list[dict]) -> str:
    headline = headline_pack(packs)
    screens = cell_screens_with_counts(packs)
    now = _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%d %H:%M UTC")

    # Box 1 — brand + sentiment-style "coverage" card + quote cards + footnote
    coverage_pct = int(len(packs) / 12 * 100)
    box1_html = f'''
<div class="topbar-box topbar-left">
  <div class="topbar-box-header" style="background:#001828;">
    <span class="topbar-logo">PULSE — DECISION INTELLIGENCE</span>
  </div>
  <div class="topbar-box-body" style="gap:8px;">
    <div class="topbar-sent-card">
      <div class="sent-card-bar"></div>
      <div class="sent-card-inner">
        <div class="sent-row-1">
          <span class="sent-card-label">CELL COVERAGE</span>
          <span class="sent-card-score" style="margin-left:auto;" data-count="coverage-score">{len(packs)}/12</span>
          <span class="sent-card-delta" style="color:var(--green);" data-count="coverage-delta">+{len(packs)-3} vs showcase</span>
          <span class="sent-card-traj" style="color:var(--green);" data-count="coverage-traj">↗ COMPLETE</span>
        </div>
        <div class="sent-row-2">
          <span class="sent-card-baseline">Baseline: 3 showcase packs</span>
          <span class="sent-card-ts">{now}</span>
        </div>
        <div class="sent-card-progress">
          <div class="sent-progress-fill" style="width:{coverage_pct}%;"></div>
        </div>
      </div>
    </div>
    <div style="display:flex;flex-direction:column;gap:8px;">
      {render_volume_brief_for_box1(packs)}
    </div>
    <div class="brand-line">
      <span class="brand-dot brand-dot-blue"></span>
      <span>FrictionBench v0.1 · 12-cell matrix · 4 screens × 3 signatures</span>
    </div>
    <div class="brand-line">
      <span class="brand-dot brand-dot-teal"></span>
      <span>Lineage-anchored, fairness-enforced, regulator-defensible decision packs</span>
    </div>
    <div class="topbar-pills" style="margin-top:auto;">
      <span class="version-pill">pulse v1.0.0</span>
      <span class="version-pill">{now}</span>
      <div class="live-dot">LIVE</div>
    </div>
    <div style="font-size:10px;color:#3A6A7F;line-height:1.4;">
      Decision packs · canonical lineage anchors · synthesis layer pending PULSE-93 hydration
    </div>
  </div>
</div>'''

    # Box 2 — pack status
    box2_html = render_volume_brief_for_box2(packs, screens)

    # Box 3 — intelligence brief for the headline pack
    box3_html = render_intelligence_brief(headline, packs)

    # Body
    body_html = f'''
{render_metrics_strip(packs)}
{render_journey_cards(packs)}
'''

    # Right panel
    right_html = f'''
<div class="panel-section">
  <div class="panel-title">CELL CATALOGUE — FrictionBench v0.1</div>
  {render_chronicle(packs)}
</div>
<div class="panel-section">
  <div class="panel-title">ACTIVE HYPOTHESIS</div>
  {render_inference(headline)}
</div>
<div class="panel-section">
  <div class="panel-title">Cohort Axes — {headline["meta"]["pack_name"][:32]}…</div>
  <div class="sources-grid">
    {render_sources(headline)}
  </div>
</div>'''

    # V3 below-fold intelligence layer
    v3_html = f'''
<hr class="v3-divider">
<div class="v3-outer">
  <div class="v3-label">
    Pulse Intelligence Layer &nbsp;·&nbsp; {now}
  </div>
  {render_churn_block(packs)}
  {render_commentary_block(packs)}
  {render_bench_block(packs)}
  {render_clark_protocol(packs)}
</div>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pulse — Decision-pack briefing (MIL-template-style)</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
{render_topnav(packs)}
<div class="topbar">
  {render_sidebar(packs)}
  {box1_html}
  {box2_html}
  {box3_html}
</div>
{render_ticker(packs)}
{render_journey_row(screens)}
<div class="body-wrapper">
  <div class="left-col">{body_html}</div>
  <div class="right-col">{right_html}</div>
</div>
{v3_html}
<div class="footer">
  <span class="footer-item">INFERENCE LOCAL</span>
  <span class="footer-sep">·</span>
  <span class="footer-item">PUBLISHED OUTPUT ONLY</span>
  <span class="footer-sep">·</span>
  <span class="footer-item">dist/preview/index.html</span>
  <span class="footer-sep">·</span>
  <span class="footer-item">pulse v1.0.0</span>
  <span class="footer-sep">·</span>
  <span class="footer-sovereign">SOVEREIGN</span>
  <span class="footer-sep">·</span>
  <span class="footer-item">Article Zero</span>
  <span class="footer-sep">·</span>
  <span class="footer-item">Generated {now}</span>
</div>
{FILTER_JS}
</body>
</html>
'''


def main() -> None:
    packs = discover_packs()
    print(f"Discovered {len(packs)} packs")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    html = render_page(packs)
    out_path = OUT_DIR / "index.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Wrote {out_path}  ({len(html):,} bytes)")


if __name__ == "__main__":
    main()

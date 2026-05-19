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
        })
    out.sort(key=lambda r: r["rank"])
    return out


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
    # Headline reads as news, not as engine output. Diagnosis becomes the
    # "why" prefix; signature is the "what was detected"; recommendation
    # follows below as the lede.
    _DIAG_PREFIX = {
        "SUPPORT_PROBLEM": "Support gap detected",
        "JOURNEY_PROBLEM": "Journey design gap detected",
        "BOTH":            "Journey and support gaps both detected",
        "INCONCLUSIVE":    "Friction detected, attribution unclear",
    }
    diag_prefix = _DIAG_PREFIX.get(cs.diagnosis.diagnosis, "Friction detected")
    headline = f"{diag_prefix} on {journey.title()}"
    summary = (
        f"<strong>Signature:</strong> {signature}. {cs.placement_recommendation}"
    )
    sha = short_hash(pack["sha256"])
    return f"""
<a class="hero-card" style="border-left-color:{color}; text-decoration:none; color:inherit;"
   href="http://localhost:8504/" target="_blank">
  <div>
    <div class="hero-card-meta">
      <span class="hero-card-tier-badge" style="color:{color};">
        {tooltip_token("action", tier)}
      </span>
      <span>FLAGGED · {journey}</span>
      <span>· {NOW}</span>
    </div>
    <div class="hero-card-headline">{headline}</div>
    <div class="hero-card-summary">{summary}</div>
    <div class="hero-card-foot">
      <span>pack: {pack["meta"]["pack_name"][:60]}</span>
      <span>· sha256:{sha}</span>
      <span>· verdict v0 · DuckDB-backed (PULSE)</span>
    </div>
  </div>
  <span class="hero-card-cta">INVESTIGATE →</span>
</a>"""


def render_feed_card(*, tag: str, tag_color: str, headline: str, summary: str,
                     tier: str | None = None, tier_dim: str = "action",
                     meta_left: str = "", meta_right: str = "",
                     cta_label: str = "OPEN →", accent: str = "var(--border)") -> str:
    """Generic feed card — reused for FLAGGED, AWAITING REVIEW, MLOPS."""
    tier_html = ""
    if tier:
        tier_color = _ACTION_COLORS.get(tier, "var(--amber)")
        tier_html = (
            f'<span class="feed-card-tier-badge" style="color:{tier_color};">'
            f'{tooltip_token(tier_dim, tier)}</span>'
        )
    return f"""
<a class="feed-card" style="border-left-color:{accent}; text-decoration:none; color:inherit;"
   href="http://localhost:8504/" target="_blank">
  <div class="feed-card-meta">
    <span class="feed-card-tag" style="color:{tag_color};">{tag}</span>
    {tier_html}
  </div>
  <div class="feed-card-headline">{headline}</div>
  <div class="feed-card-summary">{summary}</div>
  <div class="feed-card-foot">
    <span>{meta_left}</span>
    <span>{meta_right}</span>
    <span class="feed-card-cta">{cta_label}</span>
  </div>
</a>"""


def render_flagged_feed(flagged: list[dict]) -> str:
    """3-card grid of next-most-urgent signals (after the hero)."""
    cards = []
    for sig in flagged[1:4]:  # skip hero, show next 3
        pack = sig["pack"]
        cs = sig["cell_score"]
        tier = cs.action_tier
        accent = _ACTION_COLORS.get(tier, "var(--amber)")
        journey = cs.journey_id.replace("_", " · ").title()
        cards.append(render_feed_card(
            tag="FLAGGED",
            tag_color="var(--red)" if tier == "ACUTE" else "var(--amber)",
            headline=f"{journey} — {cs.signature_id.replace('_', ' ')}",
            summary=cs.placement_recommendation[:160] + ("…" if len(cs.placement_recommendation) > 160 else ""),
            tier=tier,
            tier_dim="action",
            meta_left=f"sha:{short_hash(pack['sha256'])}",
            meta_right=NOW,
            cta_label="INVESTIGATE →",
            accent=accent,
        ))
    if not cards:
        return ""
    return f"""
<section>
  <div class="section-label">
    Flagged signals
    <span class="section-label-count">{len(flagged) - 1} more in pipeline</span>
  </div>
  <div class="feed-grid">{"".join(cards)}</div>
</section>"""


def render_awaiting_review(items: list[dict]) -> str:
    if not items:
        return ""
    cards = []
    for it in items:
        cards.append(render_feed_card(
            tag="AWAITING REVIEW",
            tag_color="var(--teal)",
            headline=it["title"],
            summary=it["summary"],
            meta_left=f"owner: {it['owner']}",
            meta_right=f"closed {it['submitted']}",
            cta_label="REVIEW →",
            accent="var(--teal)",
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
        sections.append(render_hero(flagged[0]))
        sections.append(render_flagged_feed(flagged))
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

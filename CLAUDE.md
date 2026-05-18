# CLAUDE.md — Holter

This file provides guidance to Claude Code when working in this repository.

## Project Identity

- **Codename:** Holter (after Norman Holter, inventor of the wearable continuous ECG monitor, 1949)
- **Public product:** CJI Pulse — almost-real-time decision intelligence (one of four CJI products: Sonar / Reckoner / **Pulse** / Lever)
- **Importable Python package:** `pulse` — engine identity preserved; never `holter` in code
- **License:** Apache-2.0
- **Status:** scaffolded 2026-05-17 under PULSE-90; engine code (`pulse/`) currently lives in `cjipro/while-sleeping` pending migration

## Sister concerns

This repo lives alongside two others in the cjipro org. Each is a separate
git repo with its own dependency tree; they share `.env`, the Atlassian site,
and the GitHub org.

| Repo | Path | Role |
|---|---|---|
| `cjipro/mil_streamlit` (`while-sleeping`) | `C:\Users\hussa\while-sleeping` | MIL sovereign engine + Sonar publisher + Hodos seed. Hosts pulse/ pending migration here. |
| `cjipro/taq-app` | `C:\Users\hussa\taq-app` | Closed synthetic banking environment. Emits telemetry Pulse consumes via the crossing contract. |
| `cjipro/holter` (this repo) | `C:\Users\hussa\holter` | Pulse engine + UI build. |

## Boundary

- This repo holds engine code (`pulse/` after migration) + interface layer (TBD).
- Real-bank telemetry is processed on a **separate work machine**; this repo
  never sees production PII. Only the deny-list contract lives here.
- TAQ telemetry crosses via `cji_pulse_telemetry.yaml` (TAQ side, placeholder)
  ↔ `pulse/contracts/taq_contract.yaml` (Pulse side, active).
- Real-bank crossing has a complete deny-list (`pulse/contracts/real_bank_contract.yaml`)
  but placeholder field mappings; the mappings are filled separately on the
  work-machine side.

## Sister-concern operating rules

- **Shared `.env`:** read via relative path `../while-sleeping/.env`. Never
  duplicate secrets in this repo.
- **Shared Atlassian site:** `cjipro.atlassian.net` (Cloud ID `d9b829b8-66af-42de-bc53-a79515365742`).
- **Shared GitHub org:** `cjipro`.
- **Separate git history.** Cross-repo work crosses via documented contracts,
  not shared imports.

## Architectural locks (inherited from CJI / Pulse Design Direction)

- **Non-LLM runtime.** Classical ML + statistics + Jinja2 templates. Zero LLM
  inference in the runtime path. AI is dev-time only (Opus, DeepSeek, etc.).
  Enabling LLM-augmented synthesis in v2 requires a deliberate ship + governance
  review per `pulse/synthesis/SYNTHESIS_DESIGN.md` (the v1 immutability gate
  refuses `synthesis_mode: llm_augmented` in decision packs).
- **Naming discipline:** `taq` (synthetic) + `real_bank` (production) only.
  Never the real bank's name in OSS code, GitHub, or any travelling document.
  Mirrors MIL's P5 discipline.
- **Approved Python libraries only.** Python is locked to **3.11**. Every
  dependency added to this repo MUST be on the bank-env list at
  [`APPROVED_LIBRARIES.md`](APPROVED_LIBRARIES.md). If a package you want
  isn't on the list, find a substitute that is — or file a ticket proposing
  it before adding. Mirrored verbatim in
  `while-sleeping/APPROVED_LIBRARIES.md`; edit both together.
- **Hodos relationship:** Holter is one application repo. The general engine
  extraction target is Hodos (deferred per architecture panel 2026-04-30 PM).
  Patterns proven in Holter that generalise become candidates for the Hodos
  seed when extraction begins.
- **No phases, no timelines.** Work moves ticket-to-ticket on dependency-readiness
  (see `feedback_no_phases_jira_tickets.md` memory in while-sleeping).
- **No ship without ticket.** Every change in this repo requires a Jira ticket
  in PULSE first (see `feedback_no_ship_without_ticket.md` memory).

## Jira — TWO PROJECTS, ONE REPO

Per scrum-master panel decision 2026-05-17 (Cagan / Poppendieck / Cutler) the
work in this repo is tracked across **two** Jira projects, split by buyer
profile:

| Project | Key | Board | Scope |
|---|---|---|---|
| **CJI Pulse** | PULSE | Scrum | Engine work — schemas, adapters, scoring, lineage, synthesis interface, FrictionBench, question classes. The platform offering — what engine licensees (Tableau / Looker / internal dashboard buyers) consume. |
| **Holter** | HOL | Kanban | Build / UI / interface / product-experience work — UI framework, three-altitude design, sleek visual identity, deployment + CI/CD, hosted ops, partner trial flows, billing, customer-facing docs. The product offering — what full-product customers experience. |

**Scope split rule of thumb:**
- Engine API stability / schema evolution / scoring algorithms / anything an engine-licensee buyer cares about → **PULSE**
- UI / design / deployment / hosted ops / partner onboarding / anything a full-product customer experiences → **HOL**

Both projects contribute commits to **this repo**. The split is at the
work-tracking level, not the codebase level.

### URLs

- PULSE: `cjipro.atlassian.net/jira/software/projects/PULSE`
- HOL:   `cjipro.atlassian.net/jira/software/projects/HOL/boards/134`

### Numbering

- **PULSE-1..91** (current high water): includes the v1 design spine
  (PULSE-87 schema / PULSE-88 FrictionBench / PULSE-89 lineage+synthesis) and
  the build infra that brought Holter into existence (PULSE-90 scaffolding /
  PULSE-91 migration). PULSE-92 = next engine ticket.
- **HOL-1** = UI framework decision panel (foundational). HOL-2 = next UI/build ticket.

## Locked decisions

### HOL-1 — Identity + surface architecture (LOCKED 2026-05-17)

**Identity statement (load-bearing):**

> Pulse is an evidentiary investigation engine for regulated decisions — it
> converts customer-experience signals into decision packs whose every claim
> carries declared confidence, fairness attestation, and a verifiable lineage,
> and renders those packs across whatever altitude or surface the moment requires.

**Holter = the bundle**, no separate brand surface. Engine-only buyers get
PULSE; full-product buyers get Holter (which wraps Pulse with five UI surfaces).

**4-voice panel** (Cassie Kozyrkov / Avinash Kaushik / Jonathan Cherki / Ali Ghodsi)
ran on the corrected frame after Hussain's reframe: "we are an intelligence
company, we do decision packs, although our saying is decisions-not-dashboards
we will have craving from stakeholders to see charts / KPIs." Pip-freeze from
bank env validated framework candidates as env-present.

**Five surfaces (one Python stack family, all from APPROVED_LIBRARIES.md):**

| # | Surface | Stack | Audience | Ticket |
|---|---|---|---|---|
| 1 | Pulse Home | Streamlit | All roles, entry feed | HOL-4 |
| 2 | Investigation Workspace | Panel + HoloViz | Investigation consumer; three-altitude single surface | HOL-3 |
| 3 | Pulse Monitor | Panel + Bokeh | Day-to-day analysts; chart-compressed Journey rendering | HOL-7 (gated) |
| 4 | MLOps Console | Streamlit + FastAPI | ML eng + MRM; drift, fairness, lineage, synthesis governance | HOL-6 |
| 5 | Pulse Platform API | FastAPI + Pydantic | Other tools (Tableau, Databricks Apps, bank portals) | HOL-5 |

**Dashboard-tension resolution:** *rendering is the variable; investigation
is the invariant.* Surface 3 is not a fourth altitude or a separate product —
it is the Journey altitude rendered chart-first instead of narrative-first,
with lineage hash + confidence band + Designed Ceiling on every chart.

**Build order:** HOL-3 (Workspace) → HOL-4 (Home) → HOL-5 (API) → HOL-6 (MLOps) → HOL-7 (Monitor). HOL-8 (pyproject 3.11 tightening) runs in parallel.

**Hard launch gate on HOL-7:** decision-packs registry must have ≥40 templates covering FrictionBench 12-cell × multiple signatures. **12 cells now deep** (3 showcase + 9 fan-out done 2026-05-17/18); 13 packs total including the `journey_friction` test fixture. ~27 more cohort/remediation variant packs to clear the 40-floor. Calendar dates do not unlock this; registry depth does.

**Full plan + verification + risks:** `C:\Users\hussa\.claude\plans\adaptive-mapping-popcorn.md`

### Canvas-as-discipline + Value/Risk computed slots (LOCKED 2026-05-18)

Holter understands the Barclays Data Product Canvas (Decision Intelligence Demand & Delivery Playbook, p.51) but communicates in briefing form, not canvas form. **Canvas = skeleton (governance contract). Briefing = body (voice).**

Canvas slots split into three classes:
- **Declared** (author writes, validator checks): Problem · Hypothesis · Data · Actions · Actors · KPIs · Risks
- **Computed** (engine derives at runtime, reproducible per methodology version): **Value · Performance/Impact · Solution**
- **Attached** (organizational fact, lives outside pack): Budget · Owner

**Value & Risk are computed**, not declared. Each gets a methodology peer of `pulse/frictionbench/`:
- `pulse/value/` — Value tier from friction severity × population × frequency × cohort vulnerability × counterfactual baseline
- `pulse/risk/` — Risk tier from friction signature + regulatory taxonomy match + bank-policy thresholds + Chronicle precedent matches

**Value × Risk 2×2 → CLARK-style Action tier:** `ACUTE / REGULATORY-FLAG / COMMERCIAL-OPPORTUNITY / WATCH / NOMINAL`. Load-bearing cell is `REGULATORY-FLAG` (high risk, low value — "not just a value question").

### MIL briefing as canonical Workspace aesthetic (LOCKED 2026-05-18)

The Workspace surface (HOL-3) uses the MIL Sonar V4 briefing template, **not** the editorial / news-portal aesthetic. HOL-1's news-portal lock still applies to **Pulse Home** (HOL-4 — broad-audience entry feed) — surface-by-surface aesthetic from now on.

| Surface | Aesthetic | Audience |
|---|---|---|
| Pulse Home (HOL-4) | News portal | All roles, entry feed |
| Investigation Workspace (HOL-3) | MIL briefing | Investigation pros |
| MLOps Console (HOL-6) | MIL briefing | ML eng + MRM |
| Pulse Monitor (HOL-7) | TBD | Day-to-day analysts |
| Pulse Platform API (HOL-5) | n/a (programmatic) | Other tools |

**Where to find the briefing:**
- Renderer: `holter/preview/render_mil_briefing.py` (static HTML generator)
- Output: `dist/preview/index.html` (gitignored)
- Served at: **http://localhost:8502/** via `holter/preview/serve_briefing.py`
- Start: `py holter/preview/serve_briefing.py`

`holter/preview/templates_preview.py` (Bloomberg-terminal Streamlit) is **deprecated** — file in repo as design-iteration reference, not served on any port.

### HOL-3 Workspace template — locked box discipline + responsive clamp (SHIPPED 2026-05-18 → 19)

`holter/preview/render_holter.py` ports the :8502 MIL briefing into the Workspace surface (HOL-3) using a uniform 4-layer box contract — the same engine data (`discover_packs()` + PULSE-106 placement scenario) rendered through one disciplined box grid.

**Box discipline (universal, every box):**
- Layers: header 48px / headline 96px / body `1fr` / footer 48px
- Width: fluid 100% inside a responsive 3-col grid (2-col ≤1100px, 1-col ≤700px)
- Height: `clamp(520px, 78vh, 731px)` — body absorbs variance; chrome stays fixed
- Verified across 600 / 750 / 900 / 1080px viewport heights — ceiling caps at 731, floor holds at 520

**Where to find it:**
- Renderer: `holter/preview/render_holter.py`
- Output: `dist/preview/holter/index.html` (gitignored)
- Served at: **http://localhost:8504/** via `holter/preview/serve_holter.py`
- Start: `py holter/preview/serve_holter.py`

**Initial port commit:** `581c203` — 1842 LOC, both files added.

### Ticket spine — Value + Risk + Diagnosis methodology architecture (SHIPPED 2026-05-18)

Full v2 design spine shipped end-to-end in one day. Filed dependency-ordered (no phases), built and closed in the order the graph allowed.

| Key | Title | Status | Commit |
|---|---|---|---|
| [PULSE-102](https://cjipro.atlassian.net/browse/PULSE-102) | bank_policy.yaml config contract | ✅ Done | `20b3aec` |
| [PULSE-100](https://cjipro.atlassian.net/browse/PULSE-100) | Chronicle precedent library v0 (10 entries, curator-pending) | ✅ Done | `9cdf7a2` |
| [PULSE-99](https://cjipro.atlassian.net/browse/PULSE-99) | Risk methodology v0 + regulatory_taxonomy.yaml | ✅ Done | `6ef8fa5` |
| [PULSE-101](https://cjipro.atlassian.net/browse/PULSE-101) | Value methodology v0 | ✅ Done | `2eaa7d1` |
| [PULSE-103](https://cjipro.atlassian.net/browse/PULSE-103) | hypothesis.yaml canvas-completeness validator | ✅ Done | `b255b24` |
| [PULSE-105](https://cjipro.atlassian.net/browse/PULSE-105) | Diagnosis methodology v0 (Support-vs-Journey, runs BEFORE Risk/Value) | ✅ Done | `ba101cf` |
| [PULSE-104](https://cjipro.atlassian.net/browse/PULSE-104) | 12-pack backfill — product-meaningful canvas slots | ✅ Done | `6b37f7b` |
| [PULSE-106](https://cjipro.atlassian.net/browse/PULSE-106) | Agentic AI placement worked example (Diagnosis → Risk → Value → Action tier) | ✅ Done | `834d577` |
| [HOL-11](https://cjipro.atlassian.net/browse/HOL-11) | Briefing surface — placement matrix view | ✅ Done | `5145af1` |
| [HOL-9](https://cjipro.atlassian.net/browse/HOL-9) | Briefing surface — per-pack Value/Risk/Action badges + V3 scoring panels + Chronicle as matcher | ✅ Done | `1421be2` |
| [HOL-10](https://cjipro.atlassian.net/browse/HOL-10) | Top nav functional wire-up | 🟡 Phases 1+2 done; 3-6 pending | — |

**Project-split rule (formalised 2026-05-18):**
- Logical framework / methodology / engine → **PULSE**
- Design / UI / surface / experience → **HOL**

**Decision flow (engine spine, in order):**
```
Diagnosis (PULSE-105) → is this an AI-deployable problem?
       ↓
Risk    (PULSE-99)    → how exposed if we deploy / don't?
       ↓
Value   (PULSE-101)   → how big is the prize if we deploy correctly?
       ↓
CLARK-style Action tier → ACUTE / REGULATORY-FLAG / COMMERCIAL-OPPORTUNITY / WATCH / NOMINAL / NEEDS_MORE_DATA
```

Diagnosis can OVERRIDE the 2x2: `JOURNEY_PROBLEM` → "fix the journey" verb regardless of Action tier; `INCONCLUSIVE` → `NEEDS_MORE_DATA` regardless of how appealing the cell looks. See `pulse/diagnosis/DIAGNOSIS_DESIGN.md`.

**Curator-pending state on Chronicle:** all 10 seed CHR-friction entries ship `verification_status: pending_human_review`. Matcher fails closed. Risk methodology's `chronicle_precedent_match` adjustment cannot fire until a UK-banking-enforcement curator flips entries to `verified`. The briefing surface renders this transparently — never silent. See `pulse/risk/chronicle/SCHEMA.md` § Two-stage trust model.

**HOL-10 still in-progress:** phases 1 (filters) + 2 (search) shipped 2026-05-18 morning. Phases 3 (notifications/canvas-guide/settings), 4 (V3-layer filter recompute), 5 (multi-select), 6 (Date — blocked on PULSE-93) pending.

### Worked-example demo

`py -m pulse.scenarios.agentic_ai_placement.run` prints the placement matrix end-to-end. Briefing surface at `http://localhost:8502/` (start with `py holter/preview/serve_briefing.py`) renders the same matrix as a V3 panel plus per-pack badges + scoring panels + Chronicle as matcher.

### Session logs

- [`docs/sessions/2026-05-17.md`](docs/sessions/2026-05-17.md) — standup + pulse/ migration + HOL-1 closure
- [`docs/sessions/2026-05-18.md`](docs/sessions/2026-05-18.md) — 9-pack fan-out + briefing/canvas previews + Value/Risk architecture + 8 tickets filed + HOL-10 phases 1+2 + 8502 reroute + **evening: full v2 spine shipped (10 tickets PULSE-99/100/101/102/103/104/105/106 + HOL-9/HOL-11)**

## v1 design spine (already shipped, lives in while-sleeping pending migration)

| Ticket | Artefact |
|---|---|
| PULSE-87 | Canonical engine schema (`pulse/schema/`) + TAQ/real_bank adapter contracts |
| PULSE-88 | FrictionBench v0.1 public benchmark (`pulse/frictionbench/`) |
| PULSE-89 | Lineage chain + synthesis interface + decision-pack metadata + audit query spec |

All three commits live on `cjipro/mil_streamlit` `main` (GitHub + GitLab dual-push).
163 tests across `pulse/tests/` passing.

## Environment

- Windows machine — always use `py` not `python`
- Git Bash for git commands
- Claude Code for development
- Local path: `C:\Users\hussa\holter`
- `.env` lives in `C:\Users\hussa\while-sleeping\.env` (relative `../while-sleeping/.env`)

## Build posture

**De-paused 2026-05-17.** Build work resumed after Compliance situation
resolved (Amos 1-2-1 2026-05-11 landed cleanly; no escalation). See
`feedback_no_expand_during_compliance_situation.md` in while-sleeping memory
for full context.

The Amos interaction-pattern caution remains a watchword: anchor substantive
work in writing same day; silence is not absolution.

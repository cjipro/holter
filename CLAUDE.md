# CLAUDE.md — Holter

This file provides guidance to Claude Code when working in this repository.

## ⚠️ Load-bearing framing — read first (corrected 2026-05-19 EOD)

**Pulse IS a commercial-value engine. Consumer Duty is the moat. Governance is the audit trail.** That ordering is load-bearing. When describing Pulse to anyone — CEO, prospect, regulator, engineer, internal teammate — **always lead with commercial value.** Never lead with governance/compliance/MRM. Full rule in memory: [[commercial-value-first]] and [[dont-lead-with-governance]].

**The one-line statement (when asked "what is Pulse?"):**
> Pulse finds where customer-experience friction is costing the bank money — and continuously evidences that fixing it improves outcomes for the customer, not just the P&L.

**Failure mode to avoid:** the codebase has lots of governance machinery (lineage, attestation, MRM panes). The machinery is correctly built — but it's plumbing for the commercial play, not the play itself. Surfaces should answer the CCO/COO question ("where should we invest in journey changes?") first, the CRO question ("is this defensible?") second.

**Load-bearing action-tier cells:**
- `COMMERCIAL-OPPORTUNITY` — high value, low risk → product team owns this, ship it. *This is where the money is.*
- `REGULATORY-FLAG` — low value, high risk → compliance owns this.
- `ACUTE` — high value, high risk → C-suite escalation.

A surface that does not prominently surface `COMMERCIAL-OPPORTUNITY` is failing the framing.

## 🎯 Commercial-value audit (RUN 2026-05-19, verdict + remediation arc filed)

**Audit verdict (against the "does the interface answer the commercial value question" lens):**

| Surface | Verdict | Root cause |
|---|---|---|
| HOL-4 Home | **STRUCTURAL FAIL** | `_TIER_RANK` (render_home.py:72-79) puts `COMMERCIAL-OPPORTUNITY` at rank 2 behind `ACUTE`=0 and `REGULATORY-FLAG`=1. Hero is explicitly "highest-severity flagged signal" (line 533/761). All cards visible to CCO are ACUTE; no £ sizing, no affected-population, no Commercial-Opportunity queue. |
| HOL-3 Workspace | **PARTIAL FAIL** | Box 1 demotes Value tier to footer chip strip; ACTION line is governance-procedural. Box 2 tests detection, not commercial lift. Box 3 KPIs are operational (detected sessions, affected count) not commercial (£/conversion). |
| HOL-6 MLOps | **MINOR FAIL (half-finished bridge)** | Correctly framed as the gate, but the decision frame's 3-button cluster carries zero commercial signal-back — MRM reviewer can't see what business is held/unblocked by their decision. |
| Engine | **SHARED ROOT CAUSE** | `ValueScore` (pulse/value/score.py:33-50) returns categorical tier badge only — no £/month lift, no conversion delta, no CI. UI can't render sized commercial signal because engine doesn't surface it. |

**Remediation arc filed 2026-05-19 (4 tickets, see [[next-session-commercial-audit]] for audit detail):**

| Ticket | Project | Scope | Blocked-by |
|---|---|---|---|
| [HOL-55](https://cjipro.atlassian.net/browse/HOL-55) | HOL | Home dual-queue feed (Compliance + Commercial Opportunities) + commercial sizing strip on cards | PULSE-107 (partial — UI can ship without sizing) |
| [HOL-56](https://cjipro.atlassian.net/browse/HOL-56) | HOL | Workspace Box 1 promote Value to headline + Box 3 swap to commercial KPI + commercial verb on ACTION | PULSE-107 (partial — verb + headline can ship without sizing) |
| [HOL-57](https://cjipro.atlassian.net/browse/HOL-57) | HOL | MLOps Unblocks: affordance + commercial sign-off acknowledgement on APPROVE FOR PROD 14D | PULSE-107 |
| [PULSE-107](https://cjipro.atlassian.net/browse/PULSE-107) | PULSE | Extend ValueScore with `estimated_monthly_lift_gbp` + `conversion_rate_delta` + bootstrap CI + ARPU/journey block in `bank_policy.yaml` | — (engine work, no blocker) |

Audit screenshots: `dist/audit/hol4-home-*.png`, `dist/audit/hol3-workspace-*.png`, `dist/audit/hol6-mlops-*.png`.

## 🎯 Next session entry point (set 2026-05-22)

**FIRST ACTION every session: read the WHOLE memory** — not just `MEMORY.md`'s index, but enough of the linked entries to reconstruct full context before acting. Hussain's standing instruction (2026-05-21). Especially re-read [[commercial-value-first]] + [[dont-lead-with-governance]] + [[pulse-multisignal-identity]] + [[no-pound-pandora]] before any user-facing framing.

**Working mode now = cross-repo collaborative ([[cross-repo-collaboration]]).** Remove the silos between `holter`/Pulse · `while-sleeping`/MIL · `taq-app` · Hodos. Plan and design across all four concerns, not one repo at a time. **Keep the safety/contract boundaries** that are about governance not silos: real-bank PII never enters any OSS repo; `taq`/`real_bank` naming discipline; shared `.env` via `../while-sleeping/.env`; the TAQ↔Pulse crossing contracts.

**Where the build is:** the remediation arc (PULSE-107 + HOL-55/56/57) SHIPPED, then the £-as-primary framing was corrected to friction-volume ([[no-pound-pandora]]). The 10-firm game-changer panel ran ([[pulse-gamechanger-verdict]]) → conditional YES, keystone = detection runtime. **PULSE-126 detection runtime v0.1 is now BUILT + FrictionBench-validated** (`pulse/detection/`, macro 0.985, 0 FPs, cell-10 PASS, pushed). What's still open: the **synthetic→real transfer gap (PULSE-124) is unmeasured** — the real headline metric. Pre-analysis foundations PULSE-121..125 + HOL-62 gate the real-data run.

**SHIPPED since (2026-05-21/22):** the final design-lock pass (HOL-63 multi-signal strip + HOL-64 nav fix) AND the **production front-end** (HOL-65..69 + PULSE-127) — Streamlit + FastAPI + DuckDB, locked surfaces with live data + interactivity — all merged to `main` (`docs/front-end.md`, 495 tests). HOL + PULSE boards reconciled: shipped tickets closed; PULSE-84 closure audit run.

**🎯 NEXT FOCUS (set 2026-05-22): DATA PIPELINES + MARTS** (MA_D → MA_S sessionisation → marts). **Cross-repo home-split** (load-bearing, full detail in [[data-pipeline-marts-plan]]): Pulse-engine pipeline + marts build in **holter/`pulse/` on DuckDB** (PULSE-110 / 113–117 / 39 + the rolling-28d baseline; PySpark rejected); **while-sleeping** owns the legacy data infra (`mil/` MA_S/mart code, data dictionary, contracts) + MIL/Sonar + Hodos seed + `.env`; **real-bank ingestion** stays on the work machine. Guardrail: don't rebuild engine-pipeline pieces in while-sleeping (PULSE-91 consolidated the engine here). **Both a holter session and a while-sleeping session are in play** — read the WHOLE memory of whichever at session start.

**Defer:** HOL-49..54 residual backlog, HOL-7 (gated on registry ≥40 packs), HOL-47/48 (engine-blocked). Remaining PULSE-126 build items (rolling-28d baseline service, cohort split, bootstrap-CI calibration) are backlog. Any panel re-scoring of HOL-3/4/6 is premature.

## 🔒 Final design-lock pass — Holter surfaces LOCKED (2026-05-21)

Hussain directed a final design-lock visit: review all three live HTML surfaces **through the Chrome DevTools MCP** and confirm alignment with the *corrected* Pulse framing (the corrections that landed AFTER the 05-19 locks — [[no-pound-pandora]], [[commercial-value-first]], [[pulse-multisignal-identity]], [[friction-identification-is-core]]). Verdict + outcome:

**Already aligned (the post-05-19 corrections are visible + correct):** friction-volume primary with £ scaffolded behind it (`RECOVERABLE ~397/wk`); the dual Compliance/Commercial queue on Home; commercial-back on the MLOps governance decision (`~2,618 sessions/wk held`, no £ in the approval trail); cohort-disaggregated fairness.

**One material misalignment found + fixed this session:** multi-signal identity was not expressed — every finding read single-signal (app behavioural). Fixed by **HOL-63** — a `signal_provenance()` strip (`_shared.py`, single source of truth) on the Home heroes + Workspace verdict: `● BEHAVIOUR ● DEMOGRAPHICS` fused (teal), `○ VULNERABILITY ○ VOICE ○ CALLS` pending (dashed), each pending token naming its gating ticket on hover (VULNERABILITY→PULSE-122, VOICE/CALLS→PULSE-121). Honest provenance, never fabricated.

**Plus one bug fix:** **HOL-64** — MLOps top-nav stacked vertically (used `.home-topnav`, undefined in `_shared.CSS`); switched to `.holter-topnav`. Nav now consistent across all three surfaces.

**Lock state after this pass:** HOL-3 Workspace · HOL-4 Home · HOL-6 MLOps are **DESIGN-LOCKED** (HOL-6 promoted from LOCK-ELIGIBLE — the Opus-panel "one more iteration" ask is engine-contract CI work, HOL-48, not design). 485 tests pass. Surfaces re-verified live via MCP on :8504/:8505/:8506. HOL-7 Monitor stays gated (registry ≥40 packs); HOL-5 API shipped (no UI).

**Residual backlog (NOT lock-blockers):** extend the signal strip to feed cards + MLOps decision frame; per-finding provenance once the engine returns it; strict no-pound-pandora £-to-hover demotion. Do not re-open these surfaces for re-scoring without (a) ≥1 residual shipped OR (b) real-analyst study findings.

## 🏗️ Production front-end — BUILT on the work stack (2026-05-21)

After the lock, Hussain directed building the surfaces on the **proven work-machine stack — Streamlit + FastAPI + DuckDB** (not the static-HTML scaffold, which is now the design spec). Full runbook + architecture: [`docs/front-end.md`](docs/front-end.md). Pattern: **locked design injected via `components.html` (iframe → pixel-parity); interactivity + live data via Streamlit-native controls querying PULSE-127.**

Pipeline (all built + tested, **495 tests pass**, verified live via MCP on :8510): detection runtime (PULSE-126) → **DuckDB friction marts (PULSE-127, `pulse/serving/`)** → FastAPI `/friction/*` (HOL-5) → **Streamlit app (`holter/app/main.py`)**.

| Ticket | Shipped |
|---|---|
| HOL-65 | Streamlit shell + routing; locked surfaces verbatim |
| PULSE-127 | DuckDB read layer (per-session friction marts) |
| HOL-66 | Home — live friction volume (`live · PULSE-127`); verdict engine-of-record |
| HOL-67 | Workspace — journey selector drives VERDICT+EVIDENCE; RUN ANALYSIS → live metrics |
| HOL-68 | MLOps — model + pack decision actions → in-session event log; live "business held" metric |
| HOL-69 | serve/deploy runbook (`docs/front-end.md`); static `serve_*.py` relabelled design-spec |

All on branch `hol65-streamlit-foundation` (stacked on `hol63-64-design-lock`; merge that PR first). Run: `py -m streamlit run holter/app/main.py`. **Backlog:** cohort cut into cards; per-surface iframe heights; full-size mart rebuild. The static `:8504/05/06` previews remain for design iteration.

## Project Identity

- **Codename:** Holter (after Norman Holter, inventor of the wearable continuous ECG monitor, 1949)
- **Public product:** CJI Pulse — almost-real-time decision intelligence (one of four CJI products: Sonar / Reckoner / **Pulse** / Lever)
- **Importable Python package:** `pulse` — engine identity preserved; never `holter` in code
- **License:** Apache-2.0
- **Status:** scaffolded 2026-05-17 under PULSE-90; engine code (`pulse/`) **migrated into this repo** under PULSE-91 — `pulse/` (schema, adapters, frictionbench, lineage, synthesis, value, risk, diagnosis, decision_packs, detection) lives and is tested here (485 tests)

## Sister concerns

This repo lives alongside two others in the cjipro org. Each is a separate
git repo with its own dependency tree; they share `.env`, the Atlassian site,
and the GitHub org.

**Working mode (set 2026-05-21): silos removed — plan and design across all
concerns together.** Treat `holter`/Pulse, `while-sleeping`/MIL, `taq-app`,
and Hodos as one CJI surface at the *planning/design* level; the next few
sessions are explicitly cross-repo collaborative. This does NOT relax the
safety/contract boundaries below (those are about governance, not silos):
separate git history stands, real-bank PII never crosses, naming discipline
holds, and code crosses only via documented contracts — no shared imports.
See [[cross-repo-collaboration]].

| Repo | Path | Role |
|---|---|---|
| `cjipro/mil_streamlit` (`while-sleeping`) | `C:\Users\hussa\while-sleeping` | MIL sovereign engine + Sonar publisher + Hodos seed. Original home of pulse/ (now migrated into this repo under PULSE-91). |
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
- **Data layer: DuckDB + PyArrow over Parquet, not Spark.** PySpark 2.4 is
  incompatible with the Python 3.11 lock, so the data-serving engine is
  in-process DuckDB with PyArrow zero-copy interchange into FastAPI. Must
  scale to 2.4B–5B rows; the encoding/cache strategy (dictionary-encode
  low-cardinality string columns, pushdown, DuckDB resource caps) is tracked
  in [PULSE-110](https://cjipro.atlassian.net/browse/PULSE-110). Full rationale:
  [`docs/data-layer-architecture.md`](docs/data-layer-architecture.md).
- **Hodos relationship:** Holter is one application repo. The general engine
  extraction target is Hodos (deferred per architecture panel 2026-04-30 PM).
  Patterns proven in Holter that generalise become candidates for the Hodos
  seed when extraction begins. See [`docs/hodos-foundations.md`](docs/hodos-foundations.md)
  for the living inventory of foundations (proven primitives, candidates,
  domain-specific items, open boundary questions). Updated after each new
  surface design-locks. Do not extract today — per 2026-05-19 Hodos-panel
  verdict, build HOL-6 first; the panel reconvenes after the 3rd surface
  ships (DHH "3+ surfaces" rule).
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

- **PULSE-1..106** (current high water as of 2026-05-19): v1 design spine
  (PULSE-87 schema / PULSE-88 FrictionBench / PULSE-89 lineage+synthesis),
  build infra that brought Holter into existence (PULSE-90 scaffolding /
  PULSE-91 migration), and the v2 spine shipped 2026-05-18
  (PULSE-99..106: Risk methodology, Chronicle, Value methodology, bank_policy
  contract, hypothesis validator, 12-pack backfill, Diagnosis methodology,
  Agentic AI placement worked example); PULSE-107 filed 2026-05-19 post-audit
  (extend ValueScore with `estimated_monthly_lift_gbp` + bootstrap CI +
  `arpu_per_journey` block in `bank_policy.yaml` — blocks HOL-55/56/57).
  Then 2026-05-20/21: PULSE-108..118 (telephony linkage + data-layer panel
  set), PULSE-119/120 (decision-impact tracking methodology + trackable-record
  schema), PULSE-121..125 (the 6-firm-panel pre-analysis foundations:
  joins/vulnerability/recalibration/transfer-gap/Chronicle-curator), and
  **PULSE-126 = the detection runtime keystone — BUILT + FrictionBench-validated
  v0.1 2026-05-21** (`pulse/detection/`, macro 0.985, 0 FPs, cell-10 PASS).
  **PULSE-127 = DuckDB friction read layer — BUILT 2026-05-21** (`pulse/serving/`,
  per-session marts → DuckDB read functions; feeds the FastAPI Platform API →
  Streamlit front-end). **PULSE-128 = next engine ticket** (current high water PULSE-127).
- **HOL-1..69** (current high water as of 2026-05-21). Recent activity:
  HOL-12..17 shipped (HOL-3 Workspace design-panel arc, design-locked
  2026-05-19); HOL-18..23 filed as Workspace residual backlog; HOL-4,
  HOL-24..30 shipped (HOL-4 Pulse Home design-panel arc, design-locked
  2026-05-19); HOL-31..33 filed as Home residual backlog; HOL-34..38 filed
  as PR-panel structural backlog; HOL-5 Platform API shipped (`5a5c638`);
  HOL-35 `_shared.py` extraction shipped (Cannon condition met); HOL-39..46
  shipped (HOL-6 MLOps Console R1→R2→R3 panel arc, lock-eligible at
  composite 7.61 with 5 LOCK / 4 one-more across 9 voices); HOL-47..48
  filed as R3 residual backlog (durable challenge artifact · bootstrap CI
  on headline stats); HOL-49..54 PR-panel "file-it" batch all SHIPPED
  same-day (Beck tests · Metz pane-renderer extraction · Hickey eventLog
  schema + body-scope · van Rossum CSS extract · Hettinger type discipline);
  HOL-55..57 filed as commercial-value-audit remediation arc (Home dual-queue
  · Workspace headline Value · MLOps Unblocks affordance — blocked by
  PULSE-107) and SHIPPED, then friction-volume-reworked per [[no-pound-pandora]].
  Then 2026-05-20/21: HOL-58/59 (PR-panel refactor backlog: lift-strip extract
  · Protocol typing), HOL-60 (retroactive friction-volume surface rework),
  HOL-61 (Workspace EVIDENCE impact overlay — blocked by PULSE-119/120 +
  detector), HOL-62 (pre-analysis foundation 4/6: define decision-owner).
  Then 2026-05-21 final design-lock pass: HOL-63 (multi-signal provenance
  strip on Home heroes + Workspace verdict — SHIPPED), HOL-64 (MLOps top-nav
  stacking fix — SHIPPED). Then 2026-05-21 **production front-end build**
  (Streamlit + FastAPI + DuckDB, `holter/app/`): HOL-65 (Streamlit foundation),
  HOL-66 (Home live volume), HOL-67 (Workspace interactivity), HOL-68 (MLOps
  decision actions), HOL-69 (serve/deploy runbook + scaffold relabel) — all
  SHIPPED on branch `hol65-streamlit-foundation` (see `docs/front-end.md`).
  **HOL-70 = next UI/build ticket** (current high water HOL-69).

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

| # | Surface | Stack | Audience | Ticket | State |
|---|---|---|---|---|---|
| 1 | Pulse Home | static HTML (specced Streamlit; built HTML for fast iteration) | All roles, entry feed | HOL-4 | **✅ DESIGN-LOCKED 2026-05-19** (composite 8.20, live :8505) |
| 2 | Investigation Workspace | static HTML (specced Panel+HoloViz; built HTML) | Investigation consumer; three-altitude single surface | HOL-3 | **✅ DESIGN-LOCKED 2026-05-19** (composite 7.40, live :8504) |
| 3 | Pulse Monitor | Panel + Bokeh | Day-to-day analysts; chart-compressed Journey rendering | HOL-7 | 🔒 Gated on registry ≥40 packs (currently 13) |
| 4 | MLOps Console | static HTML (specced Streamlit+FastAPI; built HTML for parity with HOL-3/4) | ML eng + MRM; drift, fairness, lineage, synthesis governance | HOL-6 | **✅ LOCK-ELIGIBLE 2026-05-19** (composite 7.61 — R1 5.67 → R2 6.32 → R3 7.61; 5 LOCK / 4 one-more across 9 voices; Haiku panel unanimous LOCK; live :8506) |
| 5 | Pulse Platform API | FastAPI + Pydantic | Other tools (Tableau, Databricks Apps, bank portals) | HOL-5 | ✅ **SHIPPED** (309 LOC at `5a5c638`; programmatic, no UI) |

**Dashboard-tension resolution:** *rendering is the variable; investigation
is the invariant.* Surface 3 is not a fourth altitude or a separate product —
it is the Journey altitude rendered chart-first instead of narrative-first,
with lineage hash + confidence band + Designed Ceiling on every chart.

**Build order:** ~~HOL-3 (Workspace)~~ ✅ → ~~HOL-4 (Home)~~ ✅ → ~~HOL-5 (API)~~ ✅ → ~~HOL-35 `_shared.py`~~ ✅ → ~~HOL-6 (MLOps)~~ ✅ → **HOL-7 (Monitor)** ← next (gated on registry ≥40 packs). HOL-8 (pyproject 3.11 tightening) runs in parallel.

**Pre-condition for HOL-6 (met 2026-05-19):** [HOL-35](https://cjipro.atlassian.net/browse/HOL-35) `_shared.py` extraction shipped — Cannon's PR-panel ruling met. All 3 renderers (`render_holter`, `render_home`, `render_mlops`) now import primitives from `_shared.py` only; no cross-renderer imports.

**Hard launch gate on HOL-7:** decision-packs registry must have ≥40 templates covering FrictionBench 12-cell × multiple signatures. **12 cells now deep** (3 showcase + 9 fan-out done 2026-05-17/18); 13 packs total including the `journey_friction` test fixture. ~27 more cohort/remediation variant packs to clear the 40-floor. Calendar dates do not unlock this; registry depth does.

**Full plan + verification + risks:** `C:\Users\hussa\.claude\plans\adaptive-mapping-popcorn.md`

### Canvas-as-discipline + Value/Risk computed slots (LOCKED 2026-05-18)

Holter understands the real_bank Data Product Canvas (Decision Intelligence Demand & Delivery Playbook, p.51) but communicates in briefing form, not canvas form. **Canvas = skeleton (governance contract). Briefing = body (voice).**

Canvas slots split into three classes:
- **Declared** (author writes, validator checks): Problem · Hypothesis · Data · Actions · Actors · KPIs · Risks
- **Computed** (engine derives at runtime, reproducible per methodology version): **Value · Performance/Impact · Solution**
- **Attached** (organizational fact, lives outside pack): Budget · Owner

**Value & Risk are computed**, not declared. Each gets a methodology peer of `pulse/frictionbench/`:
- `pulse/value/` — Value tier from friction severity × population × frequency × cohort vulnerability × counterfactual baseline
- `pulse/risk/` — Risk tier from friction signature + regulatory taxonomy match + bank-policy thresholds + Chronicle precedent matches

**Value × Risk 2×2 → CLARK-style Action tier:** `ACUTE / REGULATORY-FLAG / COMMERCIAL-OPPORTUNITY / WATCH / NOMINAL`. Load-bearing cell is `REGULATORY-FLAG` (high risk, low value — "not just a value question").

### Process artifacts — review discipline established 2026-05-19

Three reusable patterns established during the HOL-3 + HOL-4 design-lock arc. **Apply on every subsequent surface and every significant push.**

#### Design-panel review (3×3×3 voice methodology)

Run for any new surface or any major surface revision. Three model classes (Opus + Sonnet + Haiku) × three named expert voices per panel (Data Product + Decision Intelligence + UX) = **9 voices per round**. Rounds repeat until diminishing returns (R2→R3 delta < +0.3 mean OR at least one panel says "lock and ship"). Different roster per surface — credibility comes from voice diversity across milestones.

See [[panel-review-process]] memory for the methodology and [[holter-scorecard]] for the 5-dimension weighted score framework that consumes panel output. HOL-3 hit 7.40 composite / 7.89 panel mean in 3 rounds; HOL-4 hit **8.20 / 8.28** in 3 rounds (unanimous lock — first across both arcs). Rosters used so far:

| Surface | Opus | Sonnet | Haiku |
|---|---|---|---|
| HOL-3 | DJ Patil · Cassie Kozyrkov · Jakob Nielsen | Hilary Mason · Lorien Pratt · Edward Tufte | Eric Colson · Annie Duke · Stephen Few |
| HOL-4 | Vicki Boykis · Philip Tetlock · Steve Krug | Wes McKinney · Nate Silver · Khoi Vinh | Andrew Ng · Gary Klein · Erik Spiekermann |

#### PR-panel review (pre-push code-review gate)

Run before any push of ≥10 commits to private remote. Same 3×3 structure but with code-review voices instead of design voices. See [[pr-panel-process]] memory. Caught a pre-existing real-bank name leak on 2026-05-19 that would have hand-carried unchanged to the work environment.

Roster used so far: Linus Torvalds · Rich Hickey · Brian Kernighan (Opus) · Guido van Rossum · Raymond Hettinger · Brett Cannon (Sonnet) · Kent Beck · Martin Fowler · Sandi Metz (Haiku).

#### Fix-first discipline

When PR-panel says FIX FIRST: address truly bug-class items immediately (correctness, leaks, hygiene); file structural items as backlog tickets that explicitly cite the dissenting voice. Hickey's R2 rule: "file it or it dies." HOL-34..38 are the canonical examples — 5 structural refactors filed with named-voice attribution so the debt is tracked, not forgotten.

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

### HOL-3 Workspace surface — DESIGN-LOCKED 2026-05-19

The Workspace (`holter/preview/render_holter.py`, served at `:8504`) is the deep-build surface — it's now design-locked after a 3-round multi-model panel review process. Further iteration belongs in *content* (engine returns richer verdict objects), not *layout*.

**Box discipline (universal, every box):**
- Layers: header 48px / headline 96px / body `1fr` / footer 48px
- Width: fluid 100% inside a responsive 3-col grid (2-col ≤1100px, 1-col ≤700px)
- Height: `clamp(520px, 78vh, 731px)` — body absorbs variance; chrome stays fixed
- `.holter-box` overflow: visible (so tooltips escape); each layer clips its own content via overflow: hidden on `.box-header` / `.box-headline` / `.box-footer`
- Verified across 600 / 750 / 900 / 1080px viewport heights

**Investigation triad (topbar, locked):**
- **Box 1 VERDICT** — selection-driven; header carries Key Area (e.g., `CUSTOMER EXPERIENCE`); headline shows CLARK tier badge + breadcrumb; body is `body_action_primary` (ACTION dominant) + supporting Diagnosis/Value/Risk chip strip + Kozyrkov-separated DECISION QUALITY strip + "What this means" synthesis line
- **Box 2 HYPOTHESIS** — interactive test bench; headline dropdown (per-pack) + `RUN ANALYSIS` button; body shows H1 + OUTCOME/SESSIONS/METHOD tiles + "What this means" synthesis + cohort + evidence
- **Box 3 EVIDENCE** — taste of data; headline `headline_stat_card` (today's KPI + delta vs 7d + trajectory); body sparkline with Designed Ceiling reference line + single primary supporting KPI + `<details>` "DETAIL ▾" progressive disclosure + "What this tells us" synthesis

**Universal hover-glossary:** `STATUS_GLOSSARY` (scoped by dimension: action/diagnosis/value/risk/severity) wraps every tier token via `tooltip_token()`. Persistent fallback: top-nav `Aa` icon opens a native `<details>` panel listing every entry grouped by dimension. No JS required.

**Where to find it:**
- Renderer: `holter/preview/render_holter.py`
- Output: `dist/preview/holter/index.html` (gitignored)
- Served at: **http://localhost:8504/** via `holter/preview/serve_holter.py`
- Start: `py holter/preview/serve_holter.py`

#### Panel review process (lock justification)

Three panels × three model classes (Opus / Sonnet / Haiku) × three named experts per panel (Data Product / Decision Intelligence / UX) = **9 voices**. Three rounds across 2026-05-19. Each round generated a "what's left" list which then drove the next round's tickets.

| Round | Opus mean | Sonnet mean | Haiku mean | All-9 mean |
|---|---|---|---|---|
| R1 (baseline) | 6.5 | 6.7 | 7.0 | 6.72 |
| R2 (after HOL-12/13/14) | 8.0 | 8.0 | 6.83 | 7.55 |
| R3 (after HOL-15/16/17) | 8.33 | 8.33 | 7.00 | 7.89 |

Net uplift R1 → R3: **+1.17**. Opus + Sonnet converged at 8.33; Haiku held lower because its lens is regulated-product governance, which is a feature dimension not a layout one. Diminishing returns hit at R3.

**Holter scorecard (5 weighted dimensions, regulated-banking weights):**

| # | Dimension | Score | Weight | Weighted |
|---|---|---|---|---|
| 1 | Verifiable transparency | 7.5 | 30% | 2.25 |
| 2 | Cognitive load management | 8.0 | 15% | 1.20 |
| 3 | Decision-action coupling | 6.5 | 25% | 1.625 |
| 4 | Fairness + bias surfacing | 8.5 | 15% | 1.275 |
| 5 | Regulator survival (Section 166) | 7.0 | 15% | 1.05 |
| | **Composite** | **7.40** | | |

#### Ticket spine — panel-review remediation (SHIPPED 2026-05-19)

| Key | Round | Voice that flagged it | Commit |
|---|---|---|---|
| [HOL-12](https://cjipro.atlassian.net/browse/HOL-12) | R1→R2 | Mason/Tufte/Patil/Few/Colson (5 of 9) — "What this means" synthesis lines | `6721529` |
| [HOL-13](https://cjipro.atlassian.net/browse/HOL-13) | R1→R2 | Patil/Kozyrkov/Pratt (3 of 9) — Box 1 ACTION primary hierarchy | `624cc0f` |
| [HOL-14](https://cjipro.atlassian.net/browse/HOL-14) | R1→R2 | Nielsen/Duke/Mason (3 of 9) — hover-glossary on every tier token | `197225e` |
| [HOL-15](https://cjipro.atlassian.net/browse/HOL-15) | R2→R3 | Few — Box 3 single-KPI + progressive disclosure | `2360423` |
| [HOL-16](https://cjipro.atlassian.net/browse/HOL-16) | R2→R3 | Nielsen — tooltip overflow fix + persistent glossary in top nav | `0ad263f` |
| [HOL-17](https://cjipro.atlassian.net/browse/HOL-17) | R2→R3 | Tufte — Designed Ceiling reference line on sparkline | `076ca21` |
| [HOL-3 port](https://cjipro.atlassian.net/browse/HOL-3) | (foundation) | initial Workspace port from :8502 | `581c203` |

#### Residual backlog (filed 2026-05-19 — NOT lock-blockers)

Six tickets capture the panel-flagged items that did NOT ship before lock. Treated as backlog because they're either feature work (Duke, Kozyrkov), engine-contract work (Patil, Colson), or low-impact cosmetic (Mason, Pratt). The Workspace surface is design-locked despite these being open:

| Key | Voice | Dimension | Lock-blocker? |
|---|---|---|---|
| [HOL-18](https://cjipro.atlassian.net/browse/HOL-18) | Patil | Decision-action coupling | No — engine-contract work (action verb taxonomy) |
| [HOL-19](https://cjipro.atlassian.net/browse/HOL-19) | Kozyrkov | Verifiable transparency | No — feature (confidence interrogability) |
| [HOL-20](https://cjipro.atlassian.net/browse/HOL-20) | Mason | Cognitive load | No — cosmetic (synthesis typography) |
| [HOL-21](https://cjipro.atlassian.net/browse/HOL-21) | Pratt | Decision-action coupling | No — visual enhancement (override connector) |
| [HOL-22](https://cjipro.atlassian.net/browse/HOL-22) | Colson | Decision-action coupling | No — engine-contract work (consequence sentence) |
| [HOL-23](https://cjipro.atlassian.net/browse/HOL-23) | Duke | Regulator survival (Section 166) | **Conditional** — required for Section 166 readiness, not for lock |

#### Missing validation layer

Voice panels test design coherence. They do **not** test whether an investigator in a hurry at 4:45pm on a Friday will actually act on the verdict. Next validation layer = **task-completion study with real analysts**: "Here's a verdict. What do you do next? Show me." Measure time-to-action and action-correctness. Track as a future research arc, not as design iteration.

**Do not re-open the Workspace surface for panel re-scoring without (a) shipping ≥3 of the residual tickets, OR (b) a real-analyst study with new findings.** Synthetic expert voices have hit their ceiling on this surface.

### HOL-4 Pulse Home — DESIGN-LOCKED 2026-05-19

The first-of-five surface (`holter/preview/render_home.py`, served at `:8505`) — "first-30-seconds" entry feed for all roles. Built same-day as HOL-3 lock; locked after 2 rounds of panel review + polish-pass. Per HOL-1 lock: news-portal aesthetic, distinct from Workspace box discipline.

**Layout (locked):**
- Sticky top nav (shared identity strip with Workspace — CJI PULSE logo + utility cluster + `Aa` glossary panel)
- Mono-uppercase nameplate masthead (demoted from serif per Spiekermann — HOL-26)
- **Hero card**: full-width, tier-railed, serif headline (single serif lead per Economist principle), signature-led summary, confidence chip + velocity tag + delta strip, INVESTIGATE → with provenance tooltip
- **FLAGGED SIGNALS grid**: 3 cards selected for journey + signature-class diversity (`select_flagged_grid()` runs 3 passes — signature cap + journey breadth + fallback). Each card carries confidence + velocity + tier-change (dedup'd if duplicate) + click preview
- **AWAITING REVIEW**: dashed-rail "held" state with `HELD · awaiting sign-off` tag — semantic break from live FLAGGED cards (HOL-28)
- **MLOPS ALERTS**: solid-rail live alerts, distinct visual weight from held

**HOL-4 spec negative scope respected (verification = absence):**
- NO KPI tiles · NO trend charts · NO sidebar / navigation menu · NO personalisation

**Departure from HOL-4 spec (Streamlit):** built as static HTML + render + serve pattern matching `serve_holter.py`. Rationale: rapid screenshot iteration proven on HOL-3 (see [[panel-review-process]]). If pure-Streamlit production shipping wanted later, that's a separate ticket — the design language and data flow port cleanly.

**Universal pattern reused from Workspace:** `STATUS_GLOSSARY` + `tooltip_token()` + `Aa` panel imported directly from `render_holter.py` — single source of truth.

#### Panel review process (lock justification)

Three panels × three model classes × three named experts per panel = **9 fresh voices** (no overlap with HOL-3 voices per the [[panel-review-process]] memory). Two rounds + a polish-pass. Hit lock at R2 + polish.

| Round | Opus mean | Sonnet mean | Haiku mean | All-9 mean |
|---|---|---|---|---|
| R1 (baseline) | 6.0 | 7.17 | 6.0 | 6.39 |
| R2 (after HOL-24/25/26) | **8.33** | **8.33** | 7.17 | **7.94** |
| R3 (after polish-pass HOL-27/28/29/30) | **8.67** | **8.67** | **7.5** | **8.28** |

Net uplift R1 → R3: **+1.89** — larger than HOL-3's R1→R3 (+1.17). HOL-3 reached 7.89 final after 3 rounds; HOL-4 reached **8.28** after 3 rounds. The R1 critiques converted to ticket work unusually cleanly because the surface had fewer load-bearing dimensions to balance.

**Notable voice records on HOL-4:**
- Tetlock R1 → R2: 5 → 8 (+3) — largest single-voice uplift in any round across all panels HOL-3+HOL-4 combined
- Boykis R1 → R3: 6 → 9 (+3) — largest total trajectory across all 18 voice-panel-rounds
- Krug R2 + R3: 9/10 held — first 9 from any voice in any panel
- **R3: three voices at 9/10 simultaneously** (Boykis, Vinh, Krug) — first time
- **R3: UNANIMOUS "LOCK" verdict** across all 3 panels — first time across both HOL-3 and HOL-4 panel arcs (HOL-3 R3 had Haiku saying "don't lock yet")

#### Holter scorecard (5 weighted dimensions, regulated-banking weights)

Same framework as HOL-3 (see [[holter-scorecard]]). HOL-4 R3 scorecard (post-R3 panel validation, 2026-05-19):

| # | Dimension | Score | Weight | Weighted |
|---|---|---|---|---|
| 1 | Verifiable transparency | 8.5 | 30% | 2.55 |
| 2 | Cognitive load management | 9.0 | 15% | 1.35 |
| 3 | Decision-action coupling | 8.5 | 25% | 2.125 |
| 4 | Fairness + bias surfacing | 7.5 | 15% | 1.125 |
| 5 | Regulator survival (Section 166) | 7.0 | 15% | 1.05 |
| | **Composite** | **8.20** | | |

Composite +0.80 above HOL-3 (7.40) and +0.35 above the pre-R3 estimate (7.85). Driven by: stronger transparency (confidence chip + velocity tag + provenance-tooltip), stronger decision-action coupling (CTA verb differentiation + click preview + held-state semantics), and lifted cognitive load (Krug 9/10 + Vinh 9/10 + Boykis 9/10 — three voices at ceiling). Regulator survival flat — same gap as HOL-3 (decision-date / override-with-reason — engine schema work tracked under [[HOL-33]]).

#### Ticket spine — HOL-4 build + remediation (SHIPPED 2026-05-19)

| Key | Round | Voice / Job | Commit |
|---|---|---|---|
| [HOL-4](https://cjipro.atlassian.net/browse/HOL-4) | v0 | Initial port (hero + flagged feed + stub awaiting + stub MLOps) | `7938577` |
| [HOL-25](https://cjipro.atlassian.net/browse/HOL-25) | R1→R2 | Boykis/Vinh/Krug/Ng/Klein — de-template (dedupe grid, varied summaries, kill slug breadcrumb) | `6e75752` |
| [HOL-24](https://cjipro.atlassian.net/browse/HOL-24) | R1→R2 | Tetlock/Klein/Silver/McKinney/Vinh — per-card delta layer (confidence + time-since + tier-change + preview) | `69287ea` |
| [HOL-26](https://cjipro.atlassian.net/browse/HOL-26) | R1→R2 | Spiekermann/Vinh — typography pass (single serif lead, contrast lift) | `c828dee` |
| [HOL-29](https://cjipro.atlassian.net/browse/HOL-29) | R2→polish | Boykis — signature-class diversity in FLAGGED grid | `a19d863` |
| [HOL-30](https://cjipro.atlassian.net/browse/HOL-30) | R2→polish | Silver — suppress duplicate tier-change chips across row | `4bc88ab` |
| [HOL-28](https://cjipro.atlassian.net/browse/HOL-28) | R2→polish | Vinh — AWAITING REVIEW pending-state visual wash | `3ac56d2` |
| [HOL-27](https://cjipro.atlassian.net/browse/HOL-27) | R2→polish | Klein — categorical velocity tag (JUST HOT / STEADY / COOLING / PLATEAU) | `cfd3b6a` |

#### Residual backlog (NOT lock-blockers — filed post-R3)

| Key | Voice | Item | Type |
|---|---|---|---|
| [HOL-31](https://cjipro.atlassian.net/browse/HOL-31) | McKinney | Text-floor for sub-finding count + metadata-strip responsive sizing | Polish (Home a11y) |
| [HOL-32](https://cjipro.atlassian.net/browse/HOL-32) | Ng | Preserve card-identity Home → Workspace handoff (`?pack=` param) | Cross-surface routing |
| [HOL-33](https://cjipro.atlassian.net/browse/HOL-33) | Tetlock | Render confidence band + weekly base rate (blocked on PULSE schema work) | UI-blocked-on-engine |
| (deferred) | — | Real-analyst task-completion study | Validation arc, not design |

#### Missing validation layer

Same caveat as HOL-3: voice panels test design coherence, not real-user task completion. The 9-voice × 3-round arc has hit its ceiling on this surface. Re-opening for panel re-scoring without (a) ≥2 of the residual tickets shipped OR (b) real-analyst study findings is not earning more signal.

**Lock is unanimous** — Opus, Sonnet, AND Haiku all explicitly verdicted "LOCK" at R3. First unanimous lock across both HOL-3 and HOL-4 panel arcs.

### HOL-6 MLOps Console — LOCK-ELIGIBLE 2026-05-19

The 4th surface in the design-panel arc (`holter/preview/render_mlops.py`, served at `:8506`) — MRM (Model Risk Management) reviewer console for drift / fairness / lineage / synthesis governance. Built same-day as HOL-3 + HOL-4 lock; lock-eligible after 3 rounds of panel review + 8 build tickets. MIL briefing aesthetic per HOL-1's surface-by-surface aesthetic rule. Built static-HTML pattern same as HOL-3/4 (departure from the ticket's specced Streamlit+FastAPI — rationale: cross-surface design parity + same-day iteration).

**4 panes (locked):**
- **DRIFT MONITORS** — Worst-cell delta KPI + cohort-disaggregated sparklines per cell, window scrubber [7d][14d][30d], severity-gradient narrative
- **FAIRNESS RE-CHECK** — Worst equalised-odds primary KPI (HOL-46) + per-metric below-floor counts + cohort narrative
- **LINEAGE VERIFIER** — Chain health stat + per-cell hash-link with click-to-expand 5-deep ancestry (sha → pipeline → dataset → date per hop) + chain-status severity
- **SYNTHESIS GOVERNANCE** — Per-pack attestation table with sortable columns + Attest/Challenge/Defer inline actions on PENDING rows + session-log strip

**Universal patterns shipped in HOL-6 R2 build (HOL-39..46):**
- **Drill-through coupling** (HOL-39) — clicking any `cell N` link highlights every matching row across all 4 panes
- **Severity-gradient narrative** (HOL-40) — each pane ends with NOMINAL/WATCH/ESCALATE/ACUTE-colored block; ACUTE non-suppressible
- **In-session event log** (HOL-42 + HOL-44) — `window.holterEventLog` shared between cell-scope (Attest/Challenge/Defer) and model-scope (Approve/Committee/Retrain) decisions
- **Window scrubber + multi-pre-rendered SVG variants** (HOL-43) — `body[data-window]` flips which SVG variant is visible per row
- **Lineage hash click-to-expand** (HOL-43) — `.hash-link` toggles `.hash-chain` block underneath the row
- **Top-of-page decision frame** (HOL-44) — trigger sentence + 3-button decision cluster + session badge; replaces bare masthead
- **Pane-scoped severity filter + sortable SYNTHESIS table** (HOL-45) — `data-severity` per row + filter strip per pane; `th.sortable` with asc/desc indicators
- **THRESHOLD_RULES dict + threshold tooltips** (HOL-45) — plain-language rule string for every severity badge + status + metric; surfaced as native `title` on `.threshold-token`
- **Primary-KPI-with-secondary-annotation** (HOL-46) — replaces 3-chip equal-weight strip with `headline_stat_card` + demoted PASS/FAIL counts as meta

**Where to find it:**
- Renderer: `holter/preview/render_mlops.py`
- Output: `dist/preview/mlops/index.html` (gitignored)
- Served at: **http://localhost:8506/** via `holter/preview/serve_mlops.py`
- Start: `py holter/preview/serve_mlops.py`

#### Panel review process (lock justification)

Three panels × three model classes × three named experts per panel = **9 fresh voices** (no overlap with HOL-3 or HOL-4 voices per [[panel-review-process]]). Three rounds across 2026-05-19. Largest single-round uplift on any HOL surface to date (+1.29 R2→R3).

Roster:
| Surface | Opus | Sonnet | Haiku |
|---|---|---|---|
| HOL-6 | Cathy O'Neil · Douglas Hubbard · Bret Victor | Andrew Banin · Linda Rock · Aza Raskin | Cyrus Burt · Gerd Gigerenzer · Indi Young |

| Round | Opus mean | Sonnet mean | Haiku mean | All-9 mean |
|---|---|---|---|---|
| R1 (v0 baseline) | 5.67 | 5.67 | 5.67 | **5.67** |
| R2 (after HOL-39/40/41) | 6.50 | 5.95 | 6.52 | **6.32** |
| R3 (after HOL-42/43/44/45/46) | **7.57** | **7.29** | **7.97** | **7.61** |

Net uplift R1 → R3: **+1.94** (HOL-3 was +1.17, HOL-4 was +1.89). **Above HOL-3's lock threshold (7.40); below HOL-4 (8.20).**

**R3 verdict tally:**
- **LOCK** (5 voices): Rock (Sonnet, with caveat), Raskin (Sonnet), Burt (Haiku), Gigerenzer (Haiku, 8.40 — highest single voice across all 3 surfaces), Young (Haiku)
- **One-more-iteration** (4 voices): Banin (Sonnet), O'Neil (Opus), Hubbard (Opus, HOL-CI ask), Victor (Opus)

Per the panel-review-process rule ("rounds repeat until ≥1 panel says lock"), HOL-6 is lock-eligible (Haiku panel unanimous LOCK). Sonnet panel 2/3 LOCK with hard-gate (HOL-42 attest/challenge/defer) cleared. Opus panel unanimous one-more-iteration but their ask (HOL-48 confidence intervals) is engine-contract work, not design-language work.

#### Holter scorecard (5 weighted dimensions, R3 cross-panel)

Same framework as HOL-3 + HOL-4 (see [[holter-scorecard]]). Computed from the 9-voice R3 weighted means:

| Dimension | R3 score | Weight | Weighted |
|---|---|---|---|
| Verifiable transparency | 7.7 | 30% | 2.31 |
| Cognitive load | 7.2 | 15% | 1.08 |
| Decision-action coupling | 7.5 | 25% | 1.875 |
| Fairness surfacing | 7.4 | 15% | 1.11 |
| Regulator survival | 7.3 | 15% | 1.095 |
| **Composite** | | | **7.47** |

Composite 7.47 (vs HOL-3 7.40, HOL-4 8.20). Decision-action coupling 7.5 — closed Rock's R2 4/10 critique via HOL-42 attest/challenge/defer + HOL-44 model-scope decision frame.

#### Ticket spine — HOL-6 build + 3-round arc (SHIPPED 2026-05-19)

| Key | Round | Voice / Job | Commit |
|---|---|---|---|
| [HOL-6](https://cjipro.atlassian.net/browse/HOL-6) | v0 | Initial 4-pane render | `d477a47` |
| [HOL-41](https://cjipro.atlassian.net/browse/HOL-41) | R1→R2 | Cohort sparklines | (commit before HOL-39) |
| [HOL-40](https://cjipro.atlassian.net/browse/HOL-40) | R1→R2 | Severity-gradient narrative | (commit before HOL-39) |
| [HOL-39](https://cjipro.atlassian.net/browse/HOL-39) | R1→R2 | Victor — cell-id drill-through across panes | `6178a39` |
| [HOL-42](https://cjipro.atlassian.net/browse/HOL-42) | R2→R3 | Rock (hard-gate) — Attest/Challenge/Defer on PENDING rows | `abfb66a` |
| [HOL-43](https://cjipro.atlassian.net/browse/HOL-43) | R2→R3 | Victor/Hubbard/Banin/O'Neil — interrogable sparkline + lineage chain + scrubber | `e21ccb7` |
| [HOL-44](https://cjipro.atlassian.net/browse/HOL-44) | R2→R3 | Young — top-of-page decision frame | `750b496` |
| [HOL-45](https://cjipro.atlassian.net/browse/HOL-45) | R2→R3 | Burt/Gigerenzer — filter + sort + threshold tooltips | `7d6f929` |
| [HOL-46](https://cjipro.atlassian.net/browse/HOL-46) | R2→R3 | Raskin (R1+R2 carryover) — fairness primary KPI | `8e7eb40` |

#### Residual backlog (filed 2026-05-19 — NOT lock-blockers)

| Key | Voice | Item | Type |
|---|---|---|---|
| [HOL-47](https://cjipro.atlassian.net/browse/HOL-47) | Banin + Rock | Durable challenge artifact (lineage-attached, not in-session only) | Engine-contract (PRA-defensibility) |
| [HOL-48](https://cjipro.atlassian.net/browse/HOL-48) | Hubbard + O'Neil + Victor | Bootstrap confidence intervals on every headline stat | Engine-contract (CI from existing bootstrap) |

#### Missing validation layer

Same caveat as HOL-3 + HOL-4: voice panels test design coherence, not real-user task completion. The 9-voice × 3-round arc has hit its ceiling on this surface. Re-opening for panel re-scoring without (a) HOL-47 or HOL-48 shipped OR (b) real-analyst MRM-reviewer study findings is not earning more signal.

**Lock is lock-eligible (not unanimous like HOL-4)** — Haiku panel unanimous LOCK; Sonnet panel 2/3 LOCK; Opus panel unanimous one-more-iteration but their ask is engine-contract work tracked under HOL-48. Per panel-review-process rule, HOL-6 is lock-eligible at composite 7.61.

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
- [`docs/sessions/2026-05-19.md`](docs/sessions/2026-05-19.md) — HOL-3 design-lock (composite 7.40, panel mean 7.89) + HOL-4 design-lock (composite 8.20, panel mean 8.28, unanimous) + virtual PR-panel pre-push gate (3-panel × 3-voice code review with Torvalds/Hickey/Kernighan · van Rossum/Hettinger/Cannon · Beck/Fowler/Metz) + Barclays scrub (closed pre-existing OSS naming-discipline leak from commit `cb188a9`) + **pushed 35 commits to `cjipro/holter` main at `8f8704f`**. 16 tickets shipped, 14 filed as backlog, 27 distinct expert voices used.

## v1 design spine (shipped, now migrated into this repo under PULSE-91)

| Ticket | Artefact |
|---|---|
| PULSE-87 | Canonical engine schema (`pulse/schema/`) + TAQ/real_bank adapter contracts |
| PULSE-88 | FrictionBench v0.1 public benchmark (`pulse/frictionbench/`) |
| PULSE-89 | Lineage chain + synthesis interface + decision-pack metadata + audit query spec |

These originally landed on `cjipro/mil_streamlit` `main` (GitHub + GitLab dual-push),
then migrated here under PULSE-91. `pulse/` now lives + is tested in this repo
(485 tests across `pulse/tests/` passing as of 2026-05-21).

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

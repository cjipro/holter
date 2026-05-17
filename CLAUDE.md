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

**Hard launch gate on HOL-7:** decision-packs registry must have ≥40 templates covering FrictionBench 12-cell × multiple signatures. Currently 1 (`pulse/decision_packs/example_pack/`). Calendar dates do not unlock this; registry depth does.

**Full plan + verification + risks:** `C:\Users\hussa\.claude\plans\adaptive-mapping-popcorn.md`

### Session log

Latest session: [`docs/sessions/2026-05-17.md`](docs/sessions/2026-05-17.md) — full record of this repo's standup, pulse/ migration, and (now) HOL-1 closure.

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

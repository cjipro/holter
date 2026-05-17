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

## Open decisions (read this first on next-session start)

### HOL-1 — UI framework decision (DEFERRED, pending pip library audit)

Panel ran 2026-05-17 (Harris / Gross / Rauch / Wathan), recommended
SvelteKit. **Decision deferred** after Hussain reframe:

> Sonar sits outside the bank → tech stack doesn't matter for fit.
> Holter sits **inside** the bank → tech stack alignment matters.
> Aesthetic = media news portal, not dashboard.
> Initial preference: Python 3.11 + Streamlit.

Pip library audit required before lock. Hussain will share `pip freeze`
from target bank environment at session start.

**Next-session re-evaluation pool** (revise candidates against reframe):

| Stack | Bank-stack alignment | News-portal fit | Solo-maintenance | Already in MIL/Sonar? |
|---|---|---|---|---|
| Streamlit | High (data-team familiar) | Low (dashboard-shaped) | Light | Yes (`app/cji_app.py` + MIL pages) |
| Jinja2 + FastAPI + Tailwind | High (standard Python web) | High (Sonar V4 proves it) | Light | Partial (Jinja2 in Sonar V4 publish chain; FastAPI not yet) |
| FastAPI + HTMX + Tailwind | Medium (HTMX less known) | High | Lightest | No (HTMX not used) |
| SvelteKit / Next.js | Low (JS toolchain) | Medium (achievable) | Heavy | No |

Likely answer: Streamlit for internal dev surfaces (analyst playgrounds) +
Jinja2/FastAPI + Tailwind for customer-facing reading surface. Two surfaces,
two stacks, both Python, both already in MIL stack.

**HOL-1 status:** To Do. **Owner:** Hussain (next-session input) + Claude (panel re-run).

### Session log

Latest session: [`docs/sessions/2026-05-17.md`](docs/sessions/2026-05-17.md) — full record of this repo's standup, pulse/ migration, and HOL-1 deferral.

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

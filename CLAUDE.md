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
- **Hodos relationship:** Holter is one application repo. The general engine
  extraction target is Hodos (deferred per architecture panel 2026-04-30 PM).
  Patterns proven in Holter that generalise become candidates for the Hodos
  seed when extraction begins.
- **No phases, no timelines.** Work moves ticket-to-ticket on dependency-readiness
  (see `feedback_no_phases_jira_tickets.md` memory in while-sleeping).
- **No ship without ticket.** Every change in this repo requires a Jira ticket
  in PULSE first (see `feedback_no_ship_without_ticket.md` memory).

## Jira

- **Project:** PULSE (`cjipro.atlassian.net/jira/software/projects/PULSE`)
- **Board:** Scrum
- **Numbering:** PULSE-1+ (PULSE-87/88/89 are v1 design spine; PULSE-90 is this scaffolding)

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

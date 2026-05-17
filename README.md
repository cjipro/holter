# Holter

Codename for the engine build of **CJI Pulse** — almost-real-time decision
intelligence for customer-journey friction.

Named after [Norman Holter](https://en.wikipedia.org/wiki/Norman_Holter)
(1914–1983), who invented the wearable continuous ECG monitor in 1949. The
Holter monitor catches arrhythmias by recording during normal daily activity
rather than in a clinic snapshot. This codename does the analogous thing for
customer journeys: continuous detection of friction signatures in the wild,
rather than after-the-fact in a usability study.

## Status

**Scaffolding only at this stage** (PULSE-90, 2026-05-17). The engine code
currently lives in [`cjipro/mil_streamlit`](https://github.com/cjipro/mil_streamlit)
at `pulse/` and will migrate to this repo in a follow-up ticket.

## Tree (planned)

```
holter/
├── pulse/              # engine (migrates from while-sleeping)
│   ├── schema/         # canonical event schema + validator
│   ├── adapters/       # TAQ + real_bank source adapters
│   ├── contracts/      # per-source field mappings
│   ├── lineage/        # hash-chained audit log
│   ├── synthesis/      # SynthesisProvider interface (deterministic in v1)
│   ├── decision_packs/ # pack metadata schema + validator
│   ├── convergence/    # fairness method registry
│   ├── audit/          # audit query interface spec
│   ├── frictionbench/  # FrictionBench v0.1 public benchmark spec
│   └── tests/          # 163 tests, all passing
├── interface/          # UI layer (TBD)
└── docs/               # design docs + governance
```

## v1 design spine (shipped 2026-05-17)

| Ticket | Title |
|---|---|
| [PULSE-87](https://cjipro.atlassian.net/browse/PULSE-87) | Canonical engine schema + TAQ/real_bank adapter contracts |
| [PULSE-88](https://cjipro.atlassian.net/browse/PULSE-88) | FrictionBench v0.1 — public benchmark for journey-friction detection |
| [PULSE-89](https://cjipro.atlassian.net/browse/PULSE-89) | Lineage chain + synthesis interface + decision-pack metadata + audit query spec |
| [PULSE-90](https://cjipro.atlassian.net/browse/PULSE-90) | Codename Holter + repo scaffolding (this commit) |

## Architectural commitments

- **Non-LLM runtime.** Pulse v1 is classical ML + statistics + Jinja2
  templates. Zero LLM inference in the runtime path. AI is dev-time only.
- **Lineage at the perimeter.** Every output Pulse produces is re-derivable
  from inputs the audit bundle names. Hash-chained log, MIL-65 pattern.
- **Multi-path convergence + fairness methods** required for high-stakes
  investigations (regulatory escalation, vulnerability disparity claims).
- **Naming discipline.** `taq` (synthetic) + `real_bank` (production) only.
  Never the real bank's name in any travelling artefact.

## Why "Holter" not "Pulse"

"Pulse" is the public product brand and one of four CJI products. This
codename names the engineering artefact — the repo, the local dev dir, the
ops conversation. The Python package stays `pulse` so the engine identity
survives any future repo moves. The pattern mirrors **Hodos** (engineering
codename for the general open-source engine extraction target).

Naming decision documented in PULSE-90; panel-decided 2026-05-17.

## License

Apache-2.0. See `LICENSE`.

## Sister concerns

- [`cjipro/mil_streamlit`](https://github.com/cjipro/mil_streamlit) — MIL
  sovereign engine + Sonar publisher; currently hosts the `pulse/` tree
  pending migration here.
- `cjipro/taq-app` (private) — closed synthetic banking environment that
  emits the TAQ telemetry Pulse consumes.

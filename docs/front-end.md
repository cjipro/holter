# Holter front-end — run & deploy (HOL-69)

The production front-end runs on the proven work-machine stack: **Streamlit +
FastAPI + DuckDB** (see [[work-machine-stack]]). This doc is the runbook +
the map of what's production vs design-spec.

## Architecture (HOL-65 decision)

```
detection runtime (PULSE-126)
        │  synthetic taq corpus, in-process
        ▼
DuckDB friction marts (PULSE-127)        pulse/serving/marts.py  → dist/marts/*.parquet
        │  read functions                pulse/serving/read.py
        ▼
FastAPI Platform API (HOL-5)             holter/api/app.py  →  /friction/summary | /by-journey | /by-cohort
        │
        ▼
Streamlit app (HOL-65/66/67/68)          holter/app/main.py
   • locked surfaces injected via components.html (iframe → CSS isolation,
     pixel-parity — NOT rebuilt in native widgets)
   • interactivity + live data via Streamlit-native controls outside the iframe
```

**Why this split:** native Streamlit widgets can't reproduce the bespoke locked
layouts (box discipline / news-portal), so the locked HTML/CSS from
`holter/preview/` is injected verbatim via `components.html`. Interactivity
(filters, RUN ANALYSIS, decision actions) therefore lives in Streamlit controls
*outside* the iframe, which re-query PULSE-127 and re-render.

## Run it (local, taq synthetic)

```bash
# Front-end (Streamlit) — the primary entry point
py -m streamlit run holter/app/main.py            # default :8501, or --server.port 8510

# Platform API (FastAPI) — optional, for programmatic / external consumers
py -m uvicorn holter.api.app:app --reload --port 8000
```

The Streamlit app reads live friction data directly via `pulse.serving.read`
(it lazily materialises `dist/marts/session_friction.parquet` on first run from
the detection runtime). The FastAPI layer exposes the same data over HTTP for
other tools (Tableau / Databricks Apps / bank portals).

Rebuild the mart at full size: `py -m pulse.serving.marts`.

## Work machine (real_bank)

Same code; the boundary holds — **work-machine code/data never enters this
repo.** On the work machine the marts are built from `real_bank` telemetry via
the crossing contract; only the read API + the taq path live here. Naming
discipline (`taq` / `real_bank` only) is unchanged.

## Production vs design-spec

| Path | Role |
|---|---|
| `holter/app/main.py` | **Production front-end** (Streamlit). The served surface. |
| `holter/preview/_shared.py` + `render_home/holter/mlops.py` | **Design spec + shared block library.** Their `render_page()` HTML is what the Streamlit app injects. Also still runnable as static previews for fast design iteration. |
| `holter/preview/serve_home.py` / `serve_holter.py` / `serve_mlops.py` | **Design-iteration scaffold** (static `http.server` on :8504/05/06). Superseded as the *delivery* path by the Streamlit app; kept for screenshot-driven design work. |

## Surfaces in the Streamlit app

| Surface | Ticket | Live behaviour |
|---|---|---|
| Pulse Home | HOL-66 | Cards show live friction volume (`live · PULSE-127`); verdict engine-of-record |
| Investigation Workspace | HOL-67 | Journey selector drives VERDICT + EVIDENCE; RUN ANALYSIS → live friction metrics |
| MLOps Console | HOL-68 | Model + pack decision actions → in-session event log; live "business held" metric |

## Backlog

- Surface the live **cohort** cut (`/friction/by-cohort`) into the cards (endpoint built, not yet rendered).
- Tune iframe heights per surface; consider hiding the iframe's static (non-functional) buttons now that Streamlit drives the real actions.
- `"/wk"` framing on the synthetic batch corpus becomes a true rate on real_bank time-windowed data.

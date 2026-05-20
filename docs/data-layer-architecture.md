# Data-layer architecture

**Purpose:** record the data-layer engine choice for Pulse — what serves session
data to the surfaces, why it was chosen, and the scale it must reach. This is
design rationale, not an implementation log.

**Boundary:** real-bank telemetry is processed on a separate work machine; this
repo never sees production PII. The figures here are capacity targets and an
architecture decision, not bank data.

---

## The three-layer shape

```
Local storage — Hive-partitioned Parquet
        │
        ▼
1. Data & exploit layer    — DuckDB (in-process, strict resource caps)
        │                     direct-from-Parquet streaming, session aggregates
        ▼  PyArrow tables (zero-copy)
2. Service & interface layer — FastAPI (Pulse Platform API / HOL-5)
        │                     runs ValueScore / scoring; caches hot tables
        ▼  Arrow IPC / thin JSON
3. Product altitude layer   — surfaces (Home / Workspace / MLOps)
                              viewport-limited presentation
```

Layer 1 + 2 are the data-layer concern of this document. Layer 3 rendering is
covered by the surface tickets (HOL-3/4/6).

## The decision: DuckDB + PyArrow, not Spark

The data-serving engine is **DuckDB**, with **PyArrow** as the zero-copy table
interchange into the FastAPI layer.

**Why not PySpark** — the original plan was to cache tables in FastAPI via
PySpark. **PySpark 2.4 is incompatible with Python 3.11** (the bank-locked
version): 2.4 tops out at Python 3.7, and Python 3.11 support did not arrive
until Spark 3.4. The Python-3.11 lock (see `APPROVED_LIBRARIES.md`) ruled out
the Spark path. **This was a compatibility decision, not a scale decision** —
DuckDB was chosen deliberately under the version lock.

**Why DuckDB fits** — in-process (no JVM, no cluster), reads Parquet/Arrow
natively, and handles single-node analytics over billions of rows comfortably.
`pyarrow==18.1.0` is on the approved list; `duckdb` is confirmed available in
the bank env (pin provisional in `APPROVED_LIBRARIES.md` pending exact version).

## Scale target

| | Rows | Columns |
|---|---|---|
| Design floor | **2.4B** | 30+ |
| Design goal | **5B** | 30+ |

Several columns carry long strings — session page names and operation codes —
repeated across the row set. The product bar is a **lightning-fast experience**
at this scale, which makes the cache memory footprint and query latency the
binding constraints.

## Performance + footprint strategy → PULSE-110

Tracked in [PULSE-110](https://cjipro.atlassian.net/browse/PULSE-110). The core
levers:

- **Dictionary-encode the low-cardinality string columns** — page names,
  operation codes, journey/screen/signature ids are a finite set of distinct
  values repeated across billions of rows. Storing each distinct value once +
  integer references (rather than the full string per row) is the dominant
  memory saving and speeds filters (DuckDB operates on dictionary-encoded
  vectors natively; PyArrow exposes `dictionary_encode()`).
- **Pushdown** — projection (load only needed columns) + predicate / partition
  pruning (Hive partitions) so no query scans the full row set.
- **DuckDB resource caps** — memory limit + spill-to-disk so the engine
  degrades gracefully rather than OOMs.
- **Parquet tuning** — zstd compression, row-group sizing.
- **Benchmark ladder** — establish baseline + target for memory + p95 latency
  across the scale ladder; define the "lightning-fast" bar quantitatively.

## Constraints

- Python 3.11; DuckDB + PyArrow only (no Spark). Single-node.
- Every dependency on `APPROVED_LIBRARIES.md` (mirrored in `while-sleeping`).
- Engine logic stays in `pulse/`; the data layer serves it. The surfaces
  consume via the Platform API (HOL-5), never reaching into the data layer
  directly.

## Sequencing note

This is **data-layer foundation**, distinct from the deferred commercial
projection layer (calls/£/conversion sizing). Pulse's fundamental objective is
to identify friction; the projections that monetise identified friction come
later. But the identification core itself queries this data at scale — so the
data layer being fast at 2.4B–5B rows is foundational, not premature.

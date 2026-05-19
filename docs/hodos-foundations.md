# Hodos foundations inventory

**Purpose:** living catalogue of which primitives, patterns, and process artifacts in Holter could anchor a Hodos seed when extraction eventually begins.

**Not the purpose:** an extraction plan. Per CLAUDE.md architectural lock, Hodos extraction is deferred per architecture panel 2026-04-30 PM. This doc tells you what's *available* if/when that conversation reopens — it does not advocate for extracting now.

**Refresh discipline:** update this doc after each new surface ships (HOL-6, HOL-5, HOL-7, or any subsequent). Each surface either *promotes* a candidate to proven (because the same shape recurred) or *invalidates* an assumption (because the surface needed something different). When 3 surfaces have inhabited a primitive without forking, it becomes a Hodos seed entry. Until then it's a candidate.

---

## Status as of 2026-05-19

| | |
|---|---|
| Surfaces design-locked | **2 of 5** — HOL-3 Workspace (composite 7.40) · HOL-4 Pulse Home (composite 8.20) |
| Surfaces remaining | HOL-6 MLOps Console (next) · HOL-5 Platform API · HOL-7 Pulse Monitor (gated) |
| Pattern travel | Pulse Home reuses Workspace helpers via direct module import → **one hop proven** |
| Process artifacts in use | Design-panel review · PR-panel review · 5-dimension scorecard · fix-first discipline |
| Cross-panel verdict on Hodos extraction (2026-05-19) | 1 READY-with-conditions · 6 NEEDS WORK · 2 BAD CANDIDATE — consensus: **not yet, but primitives are real** |

---

## ✅ Proven primitives — extraction-safe

These primitives have either travelled across surfaces (HOL-3 → HOL-4) or are framework-shaped enough that all 9 Hodos-panel voices independently named them as candidates. Lift these into a Hodos seed without speculation.

### 1. The 4-layer box discipline

- Contract: `header 48px / headline 96px / body 1fr / footer 48px` with `clamp(520px, 78vh, 731px)` height
- Files: `holter/preview/render_holter.py` (CSS lines ~473-545) — used in HOL-3 + HOL-4 with identical contract
- **Why it's a foundation:** Pulse Home adopted it unchanged. Survived 3 design-panel rounds × 2 surfaces × 18 voices. The body layer absorbs variance via `grid-template-rows: 48px 96px 1fr 48px` while the chrome stays fixed.
- **Domain-neutral:** the layer contract makes no friction/decision-intelligence claims.

### 2. `render_box()` + `body_*` component family

- Functions: `render_box(header, accent_color, headline, body, footer)` plus body composables:
  - `body_action_primary(label, text, color)` — dominant tier-railed block
  - `body_action_line(text, color)` — secondary callout
  - `body_kpi_tiles([(value, label, sub, color), ...])` — 3-col grid
  - `body_chip_strip([(label, count, color), ...])` — small chip row
  - `body_bars([(label, pct, value, color), ...])` — horizontal bars
  - `body_lines([(text, color), ...])` — text rows
  - `body_disclosure(summary, content)` — native `<details>` progressive disclosure
  - `body_quality_strip(items, label)` — dashed-separated metadata row
  - `body_primary_kpi(value, label, sub, color)` — single highlighted KPI
- File: `holter/preview/render_holter.py` lines ~712-880
- **Why it's a foundation:** textbook single-responsibility helpers. Each takes simple data (tuples of strings + colors), returns HTML strings, composes cleanly. No engine knowledge in any of them.
- **Caveat:** signatures are positional and inflexible — Katz flagged this. Lift the SHAPE but expect to add an `attrs` dict during the actual Hodos extraction.

### 3. `STATUS_GLOSSARY` + `tooltip_token()` — bounded vocabulary registry

- Pattern: dict keyed by `(dimension, token) → definition` with a `tooltip_token(dim, token) → HTML span` wrapper
- File: `holter/preview/render_holter.py` lines ~194-249
- **Why it's a foundation:** dimension-scoping is the load-bearing insight. The same literal token (`NOMINAL`, `WATCH`, `COMMERCIAL-OPPORTUNITY`) means different things in Action vs Value vs Risk dimensions — the dimension scope makes the registry future-safe.
- **Generalizes as:** any domain that ships categorical tier vocabulary (severity grading, risk scoring, status enums) gets the pattern for free.

### 4. Headline shape vocabulary

- Three patterns earned through use across surfaces:
  - `headline_tier_badge(tier, color, context)` — verdict displays
  - `headline_stat_card(label, value, delta, traj, ...)` — KPI displays
  - `headline_chip_strip([(value, label, color), ...])` — multi-value summaries
- File: `holter/preview/render_holter.py` lines ~748-820
- **Why it's a foundation:** different box purposes need different headline shapes — this catalogue proved out across 12+ box renderers. Hodos surfaces will need the same triad.

### 5. CSS design-token system

- All colours, fonts, spacing, borders defined as CSS custom properties in `:root` (`--bg`, `--card`, `--blue`, `--red`, `--mono`, `--sans`, etc.)
- Files: both `render_holter.py` and `render_home.py` declare the same token set
- **Why it's a foundation:** theme replacement is one CSS-variable swap; no hex values scattered in templates.
- **Caveat:** the variables are currently duplicated across the two renderers. Future `_shared.py` extraction ([HOL-35](https://cjipro.atlassian.net/browse/HOL-35)) should consolidate.

### 6. Static-emit + 54-LOC dev-server pattern

- Pattern: `render_*.py` produces a static HTML file under `dist/preview/<surface>/index.html`; `serve_*.py` is a tiny `http.server` wrapper that re-renders on startup and serves the static file
- Files: `serve_holter.py` + `serve_home.py` (both 54 lines, copy-pasted apart from the renderer import + port)
- **Why it's a foundation:** Hohpe called this "option-preserving" — the rendered HTML deploys anywhere (CDN, S3, file://, intranet share, hand-carried zip). No runtime engine dependency at the destination.
- **Generalises as:** the same pattern works for any renderer that takes data and emits HTML.

### 7. Hover-tooltip pattern (`[data-tooltip]` + CSS-only)

- Pattern: HTML element carries `data-tooltip="explanation"` attribute; CSS `[data-tooltip]:hover::after` renders the tooltip with no JavaScript
- Files: CSS at `render_holter.py` lines ~709-728; usage via `tooltip_token()`
- **Why it's a foundation:** zero-JS, keyboard-friendly via focus styling extension, escape-aware (`html.escape(quote=True)` applied at boundaries per the PR-panel hardening pass)
- **Generalises as:** any glossary, definition, provenance display.

### 8. Sparkline SVG helper

- Function: `sparkline_svg(values, color, reference_value=None)` — inline SVG, optional dashed reference line, no chart library
- File: `render_holter.py` lines ~880-925
- **Why it's a foundation:** Tufte-grade minimal data-ink; the reference-line parameter is the load-bearing extension (HOL-17 — Designed Ceiling).
- **Generalises as:** any small time-series visualisation across any domain.

---

## ⚠️ Candidate primitives — too fresh, need more data points

These are pattern-shaped but have one consumer or fewer than one full surface of use. **Do not lift into Hodos yet** — they need HOL-6 (and probably HOL-5/7) to either confirm or invalidate.

| Candidate | Where | Status | Promotion condition |
|---|---|---|---|
| Delta meta strip (confidence + time-since + tier-change + preview) | `render_home.py` `card_delta()` + `render_delta_strip()` | HOL-4 only | HOL-6 cards adopt the same shape unchanged |
| Held-vs-live card state | `render_home.py` `is_pending=True` + CSS `.feed-card.is-pending` | One stub card in HOL-4 | HOL-6 has a held-state card that uses the same treatment |
| Velocity tag (JUST HOT / STEADY / COOLING / PLATEAU) | `render_home.py` `_classify_velocity()` + `render_velocity_tag()` | HOL-4 cards only | HOL-6/7 cards need the same tempo signal |
| Decision Quality strip (Kozyrkov separation) | `render_holter.py` `body_quality_strip()` | HOL-3 Box 1 only | HOL-6 MLOps Console needs a decision-quality concept |
| Confidence chip (HIGH/MEDIUM/LOW with score) | `render_home.py` `render_confidence_chip()` | HOL-4 only | HOL-6/7 surfaces both display confidence in the same form |
| "What this means" synthesis line | `body_lines` callsites in HOL-3 + HOL-4 box bodies | 2 surfaces use it | One more surface confirms it's a discipline, not a coincidence |
| Cross-surface routing (`?pack=` handoff) | NOT YET BUILT — [HOL-32](https://cjipro.atlassian.net/browse/HOL-32) | Backlog | The cross-surface contract is implemented |
| Persistent glossary affordance (`<details>` in top nav) | `render_holter.py` + cross-imported into `render_home.py` | 2 surfaces share it via import | `_shared.py` extraction ([HOL-35](https://cjipro.atlassian.net/browse/HOL-35)) → both surfaces import from neutral source |

---

## 🚫 Domain-specific — stays in Holter, do not extract

These are Pulse/banking/friction-detection specific. Lifting them into Hodos would force every adopting domain to overload their meaning.

| Item | Why it stays |
|---|---|
| `discover_packs()` + `get_pack_cell()` | Reads `pulse/decision_packs/*.yaml` — Pulse-specific layout |
| `_build_pack_cell_index()` engine bridge | Imports `pulse.scenarios.agentic_ai_placement` directly |
| `_DIAG_PREFIX` (SUPPORT_PROBLEM / JOURNEY_PROBLEM / BOTH / INCONCLUSIVE) | Friction-attribution methodology vocabulary |
| `_CARD_SUMMARY_TEMPLATES` | Friction-signature × diagnosis templates ([HOL-38](https://cjipro.atlassian.net/browse/HOL-38) will lift this to a contract YAML but the content stays Pulse-side) |
| CLARK Action tiers (ACUTE / REGULATORY-FLAG / COMMERCIAL-OPPORTUNITY / WATCH / NOMINAL / NEEDS_MORE_DATA) | Decision-intelligence methodology, not domain-neutral |
| `signature_id`, `journey_id`, `screen_id` fields | FrictionBench domain vocabulary |
| "Designed ceiling" sparkline reference line concept | Domain-neutral mechanism, but the *meaning* is Pulse-specific (engine confidence) — lift the mechanism, leave the semantics |
| Pulse-specific stub data (`_STUB_AWAITING_REVIEW`, `_STUB_MLOPS_ALERTS`) | Placeholder for engine output — will become Pulse-side fixtures |

---

## ❓ Open boundary questions — must resolve BEFORE extraction

Per the 2026-05-19 Hodos panel, these are the design judgments that need to be made when extraction begins. They are NOT pre-extraction work today — they require data points from HOL-6 onwards to know what shape they should take. File only when the shape becomes obvious.

| Question | Voice that raised it | What HOL-6+ needs to reveal |
|---|---|---|
| Typed `Verdict` envelope (JSON Schema vs Python class) | Hohpe, Martin | What fields actually travel between engine and any UI consumer |
| Protocol port for engine dependency inversion | Martin | Whether MLOps consumes a different engine call vs the placement scenario |
| `render_box()` API flexibility (`attrs` dict, optional layers, data-* threading) | Katz, Wickham | What flexibility HOL-6 surfaces actually need that current contract can't provide |
| Domain-neutral token registry separation | Evans | Whether HOL-6 introduces new tier vocabulary that collides with current `STATUS_GLOSSARY` keys |
| Engine bridge as adapter vs direct import | Martin, Cannon | Whether MLOps Console can share the same `_build_pack_cell_index()` or needs a different bridge |

---

## 🧪 Reusable process artifacts (not code — methodology)

These are arguably the *highest-leverage* foundations because they're already documented in memory and survive any code refactor.

| Artifact | Location | Status |
|---|---|---|
| **Design-panel review process** (3 models × 3 named experts × N rounds = 9-voice methodology) | Memory: [[panel-review-process]] | Validated on HOL-3 (3 rounds) + HOL-4 (3 rounds + polish). **27 distinct voices used so far.** Reusable on any future surface. |
| **PR-panel review process** (pre-push code-review gate, same 3×3 with code-review voices) | Memory: [[pr-panel-process]] | Validated on the 34-commit push 2026-05-19. Caught a pre-existing real-bank name leak that would have hand-carried. |
| **5-dimension Holter scorecard** (verifiable transparency 30% · cognitive load 15% · decision-action coupling 25% · fairness surfacing 15% · regulator survival 15%) | Memory: [[holter-scorecard]] | Composite scores: HOL-3 7.40, HOL-4 8.20. Reusable on any regulated-banking surface. |
| **Hodos extraction-readiness panel** (this doc's origin — 3 panels × 3 software-engineering voices) | This session 2026-05-19 | One round so far. Reusable when extraction reopens post-HOL-6. |
| **Fix-first discipline** (PR-panel says FIX FIRST → bug-class items ship immediately; structural items file as backlog tickets explicitly citing the dissenting voice) | Pattern documented in [[pr-panel-process]] | Validated 2026-05-19. Hickey's rule: "file it or it dies." |

**These methodologies generalise to ANY decision-intelligence product Hodos eventually hosts.** They don't depend on Pulse, friction, or banking.

---

## Extraction posture (recommended)

Per the 2026-05-19 Hodos panel and DHH's "3+ surfaces" rule:

1. **Do not extract today.** Holter at 2/5 surfaces hasn't proven the pattern enough.
2. **Build HOL-6 next** (the explicit MLOps Console). After HOL-6 ships and design-locks, **refresh this document**:
   - Promote candidates that recurred (HOL-6 used the same delta strip / velocity tag / etc.)
   - Demote/remove candidates that HOL-6 didn't need
   - Note new candidates HOL-6 invented
3. **Build HOL-5 (API) or HOL-7 (Monitor) third** depending on which one is unblocked. Same refresh.
4. **After 3rd surface design-locks**, the panel re-convenes with real data: "you now have 3 surfaces — has the pattern crystallised?" If yes, start the actual Hodos extraction conversation with this document as the starting kit.

Until then: **this document IS the answer to "are the foundations available?"** — yes, in the sections above, with the honesty about which are proven vs candidate vs domain-specific.

---

## Refresh log

| Date | Trigger | Changes |
|---|---|---|
| 2026-05-19 | Initial draft after Hodos panel R1 (Evans/Hohpe/Martin · Yegge/DHH/Spolsky · Wickham/Hintjens/Katz) | First inventory of 8 proven primitives + 8 candidates + open boundary questions |

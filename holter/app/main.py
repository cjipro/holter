"""Holter production front-end — Streamlit shell (HOL-65 foundation).

Runs the design-locked surfaces (HOL-3 Workspace / HOL-4 Home / HOL-6 MLOps)
on the production stack. Per the HOL-65 architecture decision, the bespoke
locked layouts are preserved by injecting their rendered HTML/CSS through
``streamlit.components.v1.html`` — a sandboxed iframe, so the surface's own
CSS is isolated from Streamlit's and the locked design renders verbatim
(pixel-parity by construction). Native-widget rebuilds would not reproduce
the box discipline / news-portal layouts.

Scope of THIS file (foundation):
  - Streamlit app shell + sidebar surface routing.
  - Reuse the ``render_page()`` HTML from ``holter/preview/`` (the shared
    block library), driven by the engine's existing taq data path.

NOT yet here (incremental, tracked):
  - Live data via the FastAPI Platform API + DuckDB read layer (PULSE-127).
  - Per-surface interactivity — filters / RUN ANALYSIS / decision actions
    (HOL-66 / HOL-67 / HOL-68).

Run:
    py -m streamlit run holter/app/main.py
    # or pick a port:  py -m streamlit run holter/app/main.py --server.port 8510
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from holter.preview import render_holter, render_home, render_mlops  # noqa: E402

# Surface registry: label -> (render_page callable, iframe height px).
# Heights are generous so the (variable-height) surfaces fit; the iframe
# scrolls if a surface overflows. Tuned per surface in HOL-66/67/68.
_SURFACES: dict[str, tuple] = {
    "Pulse Home": (render_home.render_page, 2400),
    "Investigation Workspace": (render_holter.render_page, 1500),
    "MLOps Console": (render_mlops.render_page, 2600),
}

st.set_page_config(
    page_title="CJI Pulse — Holter",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def _surface_html(name: str) -> str:
    """Render a surface's locked HTML once per (name, code) — Streamlit
    re-runs the script on every interaction, so cache the heavy render."""
    render_page, _ = _SURFACES[name]
    return render_page()


def main() -> None:
    st.sidebar.markdown("## CJI&nbsp;PULSE")
    st.sidebar.caption("Holter front-end · HOL-65 foundation")
    choice = st.sidebar.radio(
        "Surface", list(_SURFACES), label_visibility="collapsed"
    )
    st.sidebar.divider()
    st.sidebar.caption(
        "Locked design rendered via `components.html`. Live data + "
        "interactivity land in HOL-66/67/68."
    )

    _, height = _SURFACES[choice]
    components.html(_surface_html(choice), height=height, scrolling=True)


main()

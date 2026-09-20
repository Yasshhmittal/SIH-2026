"""
app.py — NEBULA Streamlit UI entry point.

Three-column layout (from plan §7, 165–210 minutes):
  INPUT FILES | AGENT TIMELINE | EVIDENCE

Below the columns, a full-width results area surfaces the router decision,
grounded analysis + citations, validation, and the downloadable DOCX.

Phase 9 hardening baked in:
  - Startup Ollama/model preflight (fail fast, clear message)
  - Results persisted in st.session_state (downloads/interactions never wipe them)
  - run_agent wrapped in try/except with a clean user-facing error
  - One-click sample documents for a deterministic demo
  - Graceful empty-evidence / insufficient-evidence states
Everything runs locally — no cloud AI, no network egress.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import streamlit as st

from core.health import check_ollama

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NEBULA · Local AI Workbench",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
body { background-color: #0d0f14; color: #e0e6f0; }
.stApp { background-color: #0d0f14; }
.block-container { padding-top: 1.5rem; }

/* Header banner */
.nebula-header {
    background: linear-gradient(135deg, #1a1f2e 0%, #12192b 100%);
    border: 1px solid #2a3550;
    border-radius: 10px;
    padding: 1rem 2rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 1.5rem;
}
.nebula-title { font-size: 2rem; font-weight: 800; color: #4fc3f7; letter-spacing: 3px; }
.nebula-sub { font-size: 0.85rem; color: #78909c; margin-top: 0.2rem; }
.status-pill {
    background: #1b3a2a; color: #4caf50; border: 1px solid #4caf50;
    border-radius: 20px; padding: 0.2rem 0.8rem; font-size: 0.75rem; font-weight: 700;
}
.status-pill-bad {
    background: #3e1f1f; color: #ef5350; border: 1px solid #ef5350;
    border-radius: 20px; padding: 0.2rem 0.8rem; font-size: 0.75rem; font-weight: 700;
}

/* Panel titles */
.panel-title {
    font-size: 0.7rem; font-weight: 700; letter-spacing: 2px;
    color: #546e7a; text-transform: uppercase; margin-bottom: 0.8rem;
}

/* Timeline events */
.event-ok   { color: #4caf50; font-size: 0.85rem; margin: 0.15rem 0; font-family: monospace; }
.event-warn { color: #ffa726; font-size: 0.85rem; margin: 0.15rem 0; font-family: monospace; }
.event-err  { color: #ef5350; font-size: 0.85rem; margin: 0.15rem 0; font-family: monospace; }
.event-info { color: #90caf9; font-size: 0.85rem; margin: 0.15rem 0; font-family: monospace; }

/* Evidence card */
.evidence-card {
    background: #0f1e33; border: 1px solid #1e3a5f; border-radius: 6px;
    padding: 0.6rem 0.8rem; margin-bottom: 0.6rem;
}
.evidence-score { color: #4fc3f7; font-size: 0.75rem; font-weight: 700; }
.evidence-text  { color: #b0bec5; font-size: 0.8rem; margin-top: 0.3rem; }

/* Router decision chips */
.router-row { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.5rem; }
.router-chip {
    background: #12233b; border: 1px solid #29527d; border-radius: 6px;
    padding: 0.35rem 0.7rem; font-size: 0.78rem; color: #cfd8e3;
}
.router-chip b { color: #4fc3f7; }
.router-chip-off { opacity: 0.5; }

/* Grounded-claim cards */
.claim {
    border-radius: 6px; padding: 0.55rem 0.8rem; margin-bottom: 0.5rem;
    font-size: 0.85rem; border-left: 4px solid #555;
}
.claim-supported { background: #10261a; border-left-color: #4caf50; }
.claim-inference { background: #26220f; border-left-color: #ffa726; }
.claim-uncertain { background: #2a1520; border-left-color: #ab47bc; }
.claim-label { font-size: 0.68rem; font-weight: 800; letter-spacing: 1px; text-transform: uppercase; }
.label-supported { color: #66bb6a; }
.label-inference { color: #ffb74d; }
.label-uncertain { color: #ce93d8; }
.claim-text { color: #e0e6f0; margin: 0.25rem 0; }
.citation {
    color: #90caf9; font-size: 0.74rem; margin-top: 0.2rem;
    padding-left: 0.6rem; border-left: 2px solid #29527d;
}
.citation-evidence { color: #78909c; font-style: italic; }

/* Human review warning */
.human-review {
    background: #3e1f1f; border: 2px solid #c62828;
    border-radius: 8px; padding: 0.8rem 1.2rem;
    color: #ef9a9a; font-weight: 700; font-size: 1rem;
    text-align: center; margin-top: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ───────────────────────────────────────────────────────────
if "result" not in st.session_state:
    st.session_state.result = None        # last AgentState
if "events" not in st.session_state:
    st.session_state.events = []           # timeline strings
if "run_error" not in st.session_state:
    st.session_state.run_error = None      # unexpected crash message
if "sample_loaded" not in st.session_state:
    st.session_state.sample_loaded = False
if "preflight" not in st.session_state:
    st.session_state.preflight = check_ollama()

SAMPLE_INSPECTION = Path("data/inspection/inspection_report.pdf")
SAMPLE_SOP = Path("data/knowledge/SOP_MAINT_017.pdf")


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="nebula-header">
  <div>
    <div class="nebula-title">🛡️ NEBULA</div>
    <div class="nebula-sub">PRAHARÍ · Sovereign On-Premise Agentic AI Workbench</div>
  </div>
  <div style="margin-left:auto;">
    <span class="status-pill">● OFFLINE / LOCAL · NO CLOUD AI</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Preflight banner ──────────────────────────────────────────────────────────
pf = st.session_state.preflight
pf_cols = st.columns([6, 1])
with pf_cols[0]:
    if pf.ready:
        st.success(f"✅ Local runtime ready — Ollama up, models present: {', '.join(pf.models_present)}. {pf.message}")
    elif pf.ollama_up:
        st.warning(f"⚠️ {pf.message}")
    else:
        st.error(f"⛔ {pf.message}")
with pf_cols[1]:
    if st.button("↻ Re-check", use_container_width=True):
        st.session_state.preflight = check_ollama()
        st.rerun()

# ── Three-column layout ───────────────────────────────────────────────────────
col_input, col_timeline, col_evidence = st.columns([1, 1.4, 1.2], gap="medium")

# ──────────────────────────────────────────────────────────────────────────────
# LEFT COLUMN — INPUT FILES
# ──────────────────────────────────────────────────────────────────────────────
with col_input:
    st.markdown('<div class="panel-title">📁 INPUT FILES</div>', unsafe_allow_html=True)

    inspection_file = st.file_uploader(
        "Inspection Report (PDF)",
        type=["pdf"],
        key="inspection_upload",
        help="Upload the confidential inspection report PDF.",
    )

    sop_file = st.file_uploader(
        "SOP / Knowledge Base (PDF)",
        type=["pdf"],
        key="sop_upload",
        help="Upload the SOP or maintenance manual for retrieval.",
    )

    if st.button("📎 Load sample demo documents", use_container_width=True):
        try:
            if not (SAMPLE_INSPECTION.exists() and SAMPLE_SOP.exists()):
                from scripts.test_pipeline import create_test_pdfs
                create_test_pdfs()
            st.session_state.sample_loaded = True
            st.rerun()
        except Exception as exc:
            st.error(f"Could not prepare sample documents: {exc}")

    # Resolve which documents will actually be used (uploads take precedence).
    use_sample = st.session_state.sample_loaded and SAMPLE_INSPECTION.exists() and SAMPLE_SOP.exists()
    has_docs = (inspection_file is not None and sop_file is not None) or use_sample

    if inspection_file is None and sop_file is None and use_sample:
        st.caption(f"Using sample: {SAMPLE_INSPECTION.name} + {SAMPLE_SOP.name}")

    task_input = st.text_area(
        "Task description",
        value=(
            "Analyze this inspection report against the maintenance SOP. "
            "Identify supported findings, cite the evidence, state uncertainty, "
            "and prepare a human-reviewable draft approval note."
        ),
        height=110,
        key="task_input",
    )

    run_btn = st.button(
        "▶  Run Agent",
        type="primary",
        use_container_width=True,
        disabled=(not pf.ready or not has_docs),
    )

    if not pf.ready:
        st.caption("Agent disabled until the local runtime is ready (see banner above).")
    elif not has_docs:
        st.caption("Upload both PDFs, or load the sample documents, to enable the agent.")


# ── Timeline rendering helper ─────────────────────────────────────────────────
def _timeline_html(events: list[str]) -> str:
    html_lines = []
    for e in events:
        if "✅" in e:
            cls = "event-ok"
        elif "❌" in e:
            cls = "event-err"
        elif "⚠️" in e:
            cls = "event-warn"
        else:
            cls = "event-info"
        html_lines.append(f'<div class="{cls}">{e}</div>')
    return "".join(html_lines) or '<div class="event-info">Agent has not run yet.</div>'


with col_timeline:
    st.markdown('<div class="panel-title">⚙️  AGENT TIMELINE</div>', unsafe_allow_html=True)
    timeline_placeholder = st.empty()
    timeline_placeholder.markdown(_timeline_html(st.session_state.events), unsafe_allow_html=True)

with col_evidence:
    st.markdown('<div class="panel-title">📋 RETRIEVED SOP EVIDENCE</div>', unsafe_allow_html=True)
    evidence_placeholder = st.empty()


# ──────────────────────────────────────────────────────────────────────────────
# RUN AGENT
# ──────────────────────────────────────────────────────────────────────────────
if run_btn:
    from core.agent import run_agent

    cleanup_paths: list[str] = []
    try:
        # Resolve input paths: uploaded files → temp; else sample documents.
        if inspection_file is not None and sop_file is not None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix="inspection_") as f:
                f.write(inspection_file.read())
                inspection_path = f.name
                cleanup_paths.append(inspection_path)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix="sop_") as f:
                f.write(sop_file.read())
                sop_path = f.name
                cleanup_paths.append(sop_path)
        else:
            inspection_path = str(SAMPLE_INSPECTION)
            sop_path = str(SAMPLE_SOP)

        # Live timeline updates during the (blocking) run.
        st.session_state.events = []

        def on_progress(msg: str) -> None:
            st.session_state.events.append(msg)
            timeline_placeholder.markdown(
                _timeline_html(st.session_state.events), unsafe_allow_html=True
            )

        with st.spinner("Agent running — sequential local models (one at a time)…"):
            state = run_agent(
                task=task_input,
                inspection_path=inspection_path,
                sop_path=sop_path,
                progress_callback=on_progress,
            )

        st.session_state.result = state
        st.session_state.run_error = None

    except Exception as exc:
        # Unexpected failure outside the agent's own per-step guards.
        st.session_state.result = None
        st.session_state.run_error = str(exc)
    finally:
        for p in cleanup_paths:
            try:
                os.unlink(p)
            except Exception:
                pass


# ──────────────────────────────────────────────────────────────────────────────
# RENDER RESULTS (always, from session_state — survives reruns / downloads)
# ──────────────────────────────────────────────────────────────────────────────
state = st.session_state.result

# Right column — retrieved SOP evidence
with col_evidence:
    if state and state.retrieved:
        cards = []
        for rc in state.retrieved:
            snippet = rc.chunk.text[:250].replace("\n", " ")
            cards.append(
                f'<div class="evidence-card">'
                f'<div class="evidence-score">'
                f'{rc.chunk.document} · Page {rc.chunk.page} · score {rc.score:.3f}'
                f'</div>'
                f'<div class="evidence-text">{snippet}…</div>'
                f'</div>'
            )
        evidence_placeholder.markdown("".join(cards), unsafe_allow_html=True)
    else:
        evidence_placeholder.caption("Retrieved SOP chunks will appear here after a run.")


def _render_claim(claim, kind: str) -> str:
    """Render one grounded claim with its citations as HTML."""
    label_txt = {"supported": "Supported fact", "inference": "Inference", "uncertain": "Uncertainty"}[kind]
    parts = [
        f'<div class="claim claim-{kind}">',
        f'<span class="claim-label label-{kind}">{label_txt}</span>',
        f'<div class="claim-text">{claim.claim}</div>',
    ]
    for src in claim.sources:
        ev = (src.evidence[:180] + "…") if src.evidence and len(src.evidence) > 180 else (src.evidence or "")
        parts.append(
            f'<div class="citation">↳ {src.document} · Page {src.page}'
            + (f'<br><span class="citation-evidence">“{ev}”</span>' if ev else "")
            + "</div>"
        )
    parts.append("</div>")
    return "".join(parts)


# ── Unexpected crash ──────────────────────────────────────────────────────────
if st.session_state.run_error:
    st.divider()
    st.error(f"⛔ The agent stopped unexpectedly: {st.session_state.run_error}")
    st.caption("Check that Ollama is running and the models are pulled, then try again.")

# ── Full-width results area ───────────────────────────────────────────────────
if state:
    st.divider()

    # Pipeline halted early (bad file, empty retrieval, model error, …)
    if state.error:
        st.error(f"⛔ Pipeline stopped: {state.error}")

    # Router decision
    if state.router_plan:
        st.markdown('<div class="panel-title">🧭 Router Decision (deterministic — not an LLM)</div>', unsafe_allow_html=True)
        p = state.router_plan
        di = state.doc_info or {}
        vision_cls = "" if p.get("use_vision") else "router-chip-off"
        st.markdown(
            '<div class="router-row">'
            f'<div class="router-chip">Task class: <b>{di.get("task_class", "—")}</b></div>'
            f'<div class="router-chip">Pages: <b>{di.get("page_count", "—")}</b></div>'
            f'<div class="router-chip">Reasoning: <b>{p.get("reasoning_model")}</b></div>'
            f'<div class="router-chip">Embeddings: <b>{p.get("embedding_model")}</b></div>'
            f'<div class="router-chip">OCR: <b>{p.get("ocr_engine")}</b> ({"on" if p.get("use_ocr") else "off"})</div>'
            f'<div class="router-chip {vision_cls}">Vision: <b>Qwen2.5-VL-7B</b> ({"on" if p.get("use_vision") else "skipped"})</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    # Grounded analysis + citations
    r = state.reasoning
    if r:
        st.markdown('<div class="panel-title">🧠 Grounded Analysis & Citations</div>', unsafe_allow_html=True)
        ga, gb = st.columns([1.4, 1])
        with ga:
            if r.supported_findings:
                st.markdown("**Supported findings**")
                st.markdown("".join(_render_claim(c, "supported") for c in r.supported_findings), unsafe_allow_html=True)
            if r.inferences:
                st.markdown("**Inferences**")
                st.markdown("".join(_render_claim(c, "inference") for c in r.inferences), unsafe_allow_html=True)
            if r.uncertainties:
                st.markdown("**Uncertainties / missing information**")
                st.markdown("".join(_render_claim(c, "uncertain") for c in r.uncertainties), unsafe_allow_html=True)
            if not (r.supported_findings or r.inferences or r.uncertainties):
                st.info("The model returned no structured claims. See the DOCX raw output for review.")
        with gb:
            st.markdown("**Recommended action**")
            st.info(r.recommended_action or "Cannot determine from the provided evidence.")

    # Validation
    if state.validation:
        v = state.validation
        st.markdown('<div class="panel-title">✔️ Validation</div>', unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("Grounding", "PASSED ✓" if v.passed else "FAILED ✗")
        m2.metric("Unsupported claims", v.unsupported_count)
        m3.metric("Invalid citations", len(v.invalid_citations))
        if not v.passed:
            st.error(f"Grounding failed: {v.failure_reason}")
        if v.warnings:
            with st.expander(f"Validator warnings ({len(v.warnings)})"):
                for w in v.warnings:
                    st.markdown(f"- {w}")

    # Documents processed (OCR status + confidence)
    if state.pages:
        with st.expander(f"📄 Documents processed — {len(state.pages)} page(s), OCR status & confidence"):
            for pg in state.pages:
                conf = f" · OCR confidence {pg.ocr_confidence:.2f}" if pg.ocr_confidence is not None else ""
                st.markdown(f"**{pg.document} · Page {pg.page}** — `{pg.source_type}`{conf}")
                st.caption((pg.text[:300] + "…") if len(pg.text) > 300 else (pg.text or "(no text extracted)"))
                for vo in pg.visual_observations:
                    st.markdown(f"&nbsp;&nbsp;👁 *[{vo.confidence}]* {vo.text}", unsafe_allow_html=True)

    # Deliverable
    st.markdown('<div class="panel-title">📝 Deliverable</div>', unsafe_allow_html=True)
    if state.docx_path and Path(state.docx_path).exists():
        with open(state.docx_path, "rb") as f:
            st.download_button(
                label="⬇  Download Approval Note (.docx)",
                data=f.read(),
                file_name=Path(state.docx_path).name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
    elif state.validation and not state.validation.passed:
        st.warning(
            "No approval note was generated — the evidence was insufficient to ground the findings. "
            "This is the intended safe behaviour: NEBULA refuses rather than fabricating an approval."
        )

    # Always show the human-review disclaimer after a run
    st.markdown(
        '<div class="human-review">⚠ AI-DRAFTED — HUMAN REVIEW REQUIRED</div>',
        unsafe_allow_html=True,
    )

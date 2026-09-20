git add .gitignore
git commit -m "Remove virtual environment from repository"# NEBULA Prototype — Build Status

| Phase | Description | Status |
|---|---|---|
| **Phase 0** | Environment setup & smoke tests (Ollama, Qwen, BGE, OCR) | ✅ **COMPLETE** |
| **Phase 1** | Document Loader, PaddleOCR, and Page-Aware Chunking | ✅ **COMPLETE** |
| **Phase 2** | BGE-M3 local SOP indexing and cosine retrieval | ✅ **COMPLETE** |
| **Phase 3** | Deterministic Router & Pipeline Agent | ✅ **COMPLETE** |
| **Phase 4** | Qwen2.5-VL-7B integration (visual processing) | ✅ **COMPLETE** |
| **Phase 5** | Qwen2.5-7B grounded reasoning & schema extraction | ✅ **COMPLETE** |
| **Phase 6** | Validation Engine (hallucination checks & citations) | ✅ **COMPLETE** |
| **Phase 7** | DOCX Artifact Generation | ✅ **COMPLETE** |
| **Phase 8** | Streamlit UI | ✅ **COMPLETE** |
| **Phase 9** | Demo Hardening | ✅ **COMPLETE** |

---

## Technical Notes

*   **Inference Engine:** Switched from direct `transformers` to `Ollama` (`Q4_K_M` GGUF) due to Apple M4 16GB RAM limit and tight disk space (27GB free).
*   **Sequential Loading:** Enforced explicit `keep_alive=0` in Ollama wrappers (`qwen_text.py`, `qwen_vl.py`, `bge.py`) so models are instantly evicted from VRAM after their phase finishes. This prevents macOS OOM kills.
*   **Validation Fix:** Mechanism 4 in the validator was updated to allow citations to both the SOP chunks AND the original observed inspection report pages.
*   **Integration Test:** `scripts/test_pipeline.py` created synthetic industrial PDFs and verified the entire pipeline end-to-end. All 8 stages passed in ~37 seconds.

## Phase 8 — Streamlit UI (`app.py`)

*   **Three-column workbench:** INPUT FILES · AGENT TIMELINE · RETRIEVED SOP EVIDENCE, with a full-width results area below.
*   **Full pipeline made visible:** document upload (or one-click sample docs), task prompt, live agent timeline, the deterministic **router decision** (task class, page count, selected reasoning/embedding/OCR models, vision on/off), retrieved SOP chunks with similarity scores, grounded findings/inferences/uncertainties each with **source citations**, validation metrics, per-page OCR status + confidence, and the downloadable approval-note DOCX.
*   **Offline proof:** persistent "OFFLINE / LOCAL · NO CLOUD AI" pill.

## Phase 9 — Demo Hardening

*   **Startup preflight (`core/health.py`):** probes Ollama + the three required models with a short timeout; the UI shows a clear banner and disables **Run Agent** until the local runtime is ready (with the exact `ollama pull` command if a model is missing).
*   **Screen-wipe bug fixed:** results are persisted in `st.session_state` and re-rendered on every rerun, so clicking Download (or any widget) no longer blanks the page.
*   **Graceful failures:** `run_agent` is wrapped in try/except for a clean user-facing message; every pipeline abort sets `AgentState.error` and is surfaced; insufficient-evidence retrieval shows the intended "refuses rather than fabricating" message instead of a DOCX.
*   **Configurable timeouts:** all Ollama calls bounded by env-configurable timeouts (`OLLAMA_*_TIMEOUT`) so a hung server fails cleanly instead of freezing the demo. `keep_alive=0` eviction preserved.
*   **Deterministic demo flow:** "Load sample demo documents" regenerates the synthetic pump-inspection + SOP PDFs if missing.
*   **Verification:** headless boot + `scripts/ui_e2e_test.py` drive the real UI flow (load sample → run → render) via Streamlit `AppTest`; end-to-end run passes with grounding validated and a DOCX produced.

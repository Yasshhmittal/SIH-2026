# NEBULA / PRAHARÍ — Sovereign On-Premise Agentic AI Workbench
## 2–4 Hour Prototype

> **Prototype status.** This is a working vertical slice / proof-of-concept of the NEBULA strategy.
> It demonstrates local execution, agentic flow, OCR, vision, semantic retrieval, grounded reasoning,
> and DOCX generation — without any cloud AI dependency.

---

## Hard model constraints (prototype)

| Role | Model |
|---|---|
| Reasoning / drafting | Qwen2.5-7B-Instruct |
| Visual understanding | Qwen2.5-VL-7B-Instruct |
| Embeddings / retrieval | BGE-M3 |
| OCR | PaddleOCR |

No other LLMs, VLMs, cloud APIs, or external services.

---

## Prerequisites

- Apple M4 MacBook Air · 16 GB unified memory
- macOS 26.x (Sequoia / Tahoe)
- Python 3.11 (Homebrew recommended for ML compatibility)
- ~15 GB free disk space (models)

## Setup

```bash
# 1. Clone / enter project
cd nebula-prototype

# 2. Create virtual environment (Python 3.11)
/opt/homebrew/bin/python3.11 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. (Optional) Copy env file — defaults are already baked into the code;
#    only needed if you want to override model tags/timeouts via your shell.
cp .env.example .env

# 5. Pre-index the SOP knowledge base (optional — the app also builds the
#    index on demand, and the "Load sample" button generates demo PDFs)
python scripts/preindex.py

# 6. Launch UI
streamlit run app.py
```

## Demo workflow

1. Confirm the green **preflight banner** ("Local runtime ready") — the agent stays disabled until Ollama + the three models are detected.
2. Upload `inspection_report.pdf` + `SOP_MAINT_017.pdf`, **or** click **📎 Load sample demo documents** for a deterministic one-click demo.
3. Enter (or keep) the task description.
4. Click **▶ Run Agent**.
5. Watch the live **agent timeline**: Classify → OCR → Vision → Retrieve → Reason → Validate → DOCX.
6. Review the results area: **router decision**, retrieved SOP evidence, grounded findings/inferences/uncertainties **with citations**, **validation** metrics, and per-page OCR status.
7. Download the approval-note DOCX. (If evidence is insufficient, the agent refuses and explains — no DOCX is fabricated.)

## Offline / sovereignty test

```bash
# Turn off Wi-Fi, then:
streamlit run app.py
# Full workflow completes locally with no cloud dependency.
```

## Project structure

```
nebula-prototype/
├── app.py                  Streamlit UI entry point
├── requirements.txt
├── .env.example
│
├── core/
│   ├── agent.py            Bounded task workflow controller
│   ├── router.py           Deterministic component selector
│   ├── validator.py        Grounding / citation validator
│   ├── health.py           Startup Ollama/model preflight check
│   └── schemas.py          Dataclass result definitions
│
├── models/
│   ├── qwen_text.py        Qwen2.5-7B wrapper
│   ├── qwen_vl.py          Qwen2.5-VL-7B wrapper
│   └── bge.py              BGE-M3 wrapper
│
├── document/
│   ├── loader.py           PDF / text extraction (PyMuPDF)
│   ├── ocr.py              PaddleOCR wrapper
│   └── chunker.py          Evidence chunk creation
│
├── rag/
│   ├── index.py            Offline embedding cache builder
│   └── retrieve.py         Cosine top-k retrieval
│
├── artifacts/
│   └── docx.py             Approval-note DOCX generator
│
├── scripts/
│   ├── smoke_test.py       Phase-0 component checks
│   ├── preindex.py         Pre-build SOP embedding cache
│   ├── test_pipeline.py    Synthetic-PDF end-to-end backend test
│   └── ui_e2e_test.py      Streamlit AppTest UI end-to-end test
│
├── data/
│   ├── inspection/         Upload inspection reports here
│   └── knowledge/          SOP documents for RAG
│
├── cache/                  BGE-M3 embeddings (.npy) + chunks (.json)
├── logs/                   Event log (events.jsonl)
└── output/                 Generated DOCX files
```

## Limitations (prototype)

- Single-user, sequential model execution
- In-memory NumPy retrieval (not Qdrant)
- No RBAC, no audit chain, no formal network isolation
- Visual step is best-effort (Qwen2.5-VL is the slowest component)

> **AI-DRAFTED — HUMAN REVIEW REQUIRED**
> Production deployment requires formal network/security hardening.

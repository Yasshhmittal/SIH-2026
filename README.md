# PRAHARI — sovereign on-premise agentic AI workbench

**SIH 2026 · Problem SIH26117 · Mangalore Refinery & Petrochemicals Ltd · Team The Nebula**

AI comes to your data — not the other way around.

An air-gapped agentic workbench for confidential industrial knowledge work: plans
multi-step tasks, routes each step to the right local open-weight model, calls
local tools, grounds every claim in the organisation's own SOPs, runs code in a
network-isolated sandbox, and returns real files — Word, Excel, PowerPoint —
without a single byte leaving the premises.

Full design record: [`context.md`](context.md)

---

## Status

| Plane | State |
|---|---|
| Model router + residency manager | **Working** — deterministic scoring, real swap measurement, live decision tables |
| Agent loop (classify → plan → execute) | **Working** — schema-constrained decoding, bounded repair, recipes |
| Deterministic calculation engine | **Working** — sympy + pint, units, full step list |
| DOCX deliverable renderer | **Working** — real .docx from a typed spec |
| Filesystem tools (jailed) | **Working** |
| Knowledge plane (OCR, Qdrant, citations) | **Stubbed** — fixed seed corpus, P3 |
| Sandbox code execution | **Stubbed** — P4 |
| Security proof (egress guard, monitor, audit chain) | **Not built** — P6 |
| Frontend | Prototype — Vite + React, streaming timeline wired |

---

## Quick start

Requires Python 3.11+, Ollama running locally, and the models pulled.

```bash
# 1. models (about 8 GB total, one time)
ollama pull qwen2.5:3b-instruct
ollama pull qwen2.5-coder:1.5b
ollama pull bge-m3
ollama pull moondream

# 2. dependencies
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt    # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # Linux/macOS

# 3. run the backend
PYTHONPATH=backend .venv/Scripts/python -m uvicorn prahari.main:app \
    --host 127.0.0.1 --port 8077

# 4. run the flagship task from the console
PYTHONPATH=backend .venv/Scripts/python scripts/run_task.py
```

Then open <http://127.0.0.1:8077/docs> for the API, or the frontend:

```bash
cd frontend && npm install && npm run dev
```

---

## Try these

```bash
# flagship: scanned inspection report -> cited approval note
python scripts/run_task.py

# ask a question grounded in the SOPs
python scripts/run_task.py "What is the minimum retirement thickness for 8 inch sour service piping?"

# any prompt you like
python scripts/run_task.py "Summarise the last inspection report"
```

---

## How it works

```
RECEIVE → CLASSIFY → PLAN ─┬─► SELECT → EXECUTE → OBSERVE → CRITIC ─┐
                           │                                        │
                           └────────── REPLAN (≤2) ◄────────────────┘
                                              │ pass
                              SYNTHESIZE → DELIVER → AWAIT_HUMAN
```

**The LLM fills in parameters and judges outcomes. Code owns the control flow.**
That single decision is what makes a 3B model reliable enough for a refinery:

- Every LLM output is **schema-constrained** — Ollama takes a JSON Schema as a
  decoding constraint, so a malformed plan is unrepresentable rather than caught.
- Plans are a **typed DAG**, validated against the tool registry *before* execution.
- Known task archetypes use **recipes** — the plan skeleton is code, and the model
  only classifies. This took the flagship task from 60s to 3.5s.
- A **critic** checks postconditions; failure triggers a bounded repair.

### Routing is per *step*, not per task

So a single run visibly moves between models. The router scores every candidate:

```
hard gates:  modality ⊇ task.modalities  AND  roles ∋ task.role     else reject
score     =  w_q·quality + w_ctx·fits_context + w_lat/est_latency
             − w_swap·swap_cost(m)     ← 0 if already in VRAM
             − w_vram·vram_pressure(m)
```

Real output from this machine — same request, different residency, different pick:

```
empty budget       →  qwen2.5-coder:1.5b   (the 7B would take 83% of a 6 GB budget)
7B already loaded  →  qwen2.5-coder:7b     (already resident, pays no swap penalty)
```

### Numbers are never computed by the model

`calc.evaluate` uses sympy with units from pint, and returns the ordered step
list. In a refinery a hallucinated decimal place is a safety incident, so the
LLM decides *what* to compute and the engine decides *what the answer is*.

### Adding a model is one registry entry

`config/models.yaml`, then `ollama pull`, then `POST /api/models/reload`. No code
change — that is the problem statement's "addable without redesigning the system".

---

## Layout

```
backend/prahari/
  api/         FastAPI routes + SSE event stream
  agent/       loop, schemas, hints, extract, recipes
  router/      registry, scorer, residency manager
  llm/         Ollama client
  tools/       base (registry + policy), calc, files, deliverables, stubs
config/        models.yaml, profiles.yaml
frontend/      Vite + React console
scripts/       run_task.py (console client), checks
```

---

## Testing

```bash
PYTHONPATH=backend .venv/Scripts/python -m pytest backend/tests -q
PYTHONPATH=backend .venv/Scripts/python scripts/check_pipeline.py
```

`tests/test_extract.py` pins the value-attribution logic, which once swapped two
thickness readings and produced a confidently wrong corrosion rate. A wrong
number that looks right is the worst failure this system can produce.

---

## Security posture

No network tool and no shell tool exist in the registry — by construction, not by
policy. `fs.read`/`fs.write` are jailed to the run workspace. Even a fully
compromised agent has no route out. The egress guard, live network monitor,
canary and hash-chained audit log land in phase P6.

**Explicitly not claimed:** protection from screen photography, a malicious admin
with physical access, or a user copying a generated file to removable media.

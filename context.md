# PRAHARI — Project Context

> **Purpose of this file.** A complete record of the design conversation for PRAHARI:
> the problem, every question asked and answered, the decisions taken, the reasoning
> behind them, and the architecture we agreed on. Written so that a teammate — or a
> future session — can pick up the project cold and be fully oriented.
>
> **Status at time of writing:** design agreed in conversation; spec not yet written;
> no code written yet. Awaiting "go" to start P0.
>
> **Date:** 11 September 2026
> **Team:** The Nebula · SIH 2026 · Problem Statement **SIH26117**
> **Organisation:** Mangalore Refinery & Petrochemicals Ltd (MRPL)
> **Theme:** Smart Automation · **Category:** Software

---

## 1. The Problem Statement (verbatim — this is the contract)

**Title:** Sovereign On-Premise Agentic AI Workbench using Open-Weight Multimodal LLMs
for Confidential Industrial Work

### Background

> Refineries, PSUs, defence-linked manufacturing units and government offices generate
> a lot of routine but sensitive knowledge work. Approval notes, board presentations,
> engineering calculations, code for internal tools, review of scanned drawings and
> inspection reports. None of this can go through cloud AI assistants like Claude or
> Codex because the underlying data is confidential: Piping & Instrument Diagrams,
> financials, vendor negotiations, unreleased designs, internal correspondence,
> confidential business strategies etc. Company policy keeps this data on premises, so
> people either do the work manually resulting in productivity gain [sic — loss], or
> they quietly paste confidential material into public tools anyway. Open weight large
> reasoning models have reached a point where a genuinely useful assistant built on
> them is realistic. But nothing deployable exists today that industrial users can
> actually work with the way they use Claude or Codex.

### Description

> The idea is a self-hosted, air gapped AI workbench running entirely on the
> organization's own GPU server. Nothing leaves the premises. The backend should not be
> locked to one model. It needs to support multiple open weight models at once and
> automatically pick the right one for a given task based on what that task needs, a
> coding request handled differently from a document summary request. New open weight
> models should be addable later without redesigning the system, since this space is
> moving fast.
>
> The assistant also needs to actually act like an agent. Plan out multi step work, call
> local tools such as file read and write, code execution in a sandbox, spreadsheet
> work, internal document search, and iterate on a task instead of answering once and
> stopping. It needs to handle more than text too: scanned PDFs, handwritten notes,
> engineering drawings, photographs, read through on device OCR and vision models.
> Output should be real deliverables, approval notes, PPT/Word/Excel files, working
> code, calculations with steps shown, not just chat replies. And it needs to ground
> itself in the organization's own manuals, SOPs and past correspondence through a local
> knowledge base connector, again with nothing going external.

### Expected Solution — the grading rubric

> A working local deployment, demonstrable on a single workstation or server with a mid
> range GPU (use a smaller open weight model if 120B class hardware isn't available at
> the venue), that shows model auto selection across at least two different task types.
> An agentic task carried through end to end, for example reading a scanned inspection
> report, pulling out key findings and drafting an approval note as a Word file. A
> coding task run and verified in a sandbox. A multimodal task involving image or
> scanned document understanding. The system should also show, through logs or a visible
> network monitor, that no external calls are made at any point. That's the actual proof
> of the sovereign claim, not just a statement of it.

### Requirements extracted from the PS

**Functional**
1. Self-hosted, air-gapped, runs on the org's own GPU server; nothing leaves the premises
2. Multiple open-weight models supported at once; automatic selection per task type
3. New models addable later **without redesigning the system**
4. Agentic: plans multi-step work, calls local tools, **iterates instead of stopping**
5. Local tools required: file read/write, sandboxed code execution, spreadsheet work,
   internal document search
6. Multimodal on-device: scanned PDFs, handwritten notes, engineering drawings, photographs
7. Real deliverables: approval notes, PPT/Word/Excel, working code, **calculations with
   steps shown** — not chat replies
8. Grounded in the org's manuals, SOPs and **past correspondence** via a **local knowledge
   base connector**

**Demonstrables (6)**
1. Working local deployment on a single workstation, mid-range GPU (smaller model permitted)
2. Model auto-selection across ≥2 task types
3. An agentic task end-to-end (e.g. scanned inspection report → findings → Word approval note)
4. A coding task run and verified in a sandbox
5. A multimodal task (image / scanned document understanding)
6. **Proof** via logs or a visible network monitor that no external calls are made

**Product bar (stated explicitly in the Background)**
- Must be usable "the way they use Claude or Codex" — threaded, conversational,
  file-producing, iterative. Not a research demo, not a one-shot form.

---

## 2. Two readings of the PS that changed the design

These were not obvious on first pass and both materially shaped the architecture.

### 2.1 The real pain is shadow AI, not missing productivity

The Background says people *"quietly paste confidential material into public tools anyway."*

That is a live data-exfiltration channel, not a productivity gap. So PRAHARI's job is
partly a **shadow-AI countermeasure**. This sets a harsh bar: if the local tool is
clunky, people route around it and the leakage continues. **A mediocre sovereign tool is
worse than useless, because it provides false assurance.**

### 2.2 The PS names its own UX benchmark

*"nothing deployable exists today that industrial users can actually work with the way
they use Claude or Codex."*

This forced a correction to an earlier sketch that was too much "batch pipeline console."
The product must be a **workbench with a conversation**: threads, attachments, visible
work, and **revisable artifacts** ("make paragraph 3 formal and add a cost table" → v2 of
the same Word file). The PS also states iteration outright: *"iterate on a task instead
of answering once and stopping."* That means two kinds of iteration:
- **Intra-run:** critic fails a postcondition → replan
- **Inter-turn:** user pushes back → agent revises the existing artifact

---

## 3. Prior artifact: the submitted PPT (reference only, not binding)

File: `PRAHARI_SIH26117_FINAL.pptx` (7 slides). The user was explicit, twice:

> "there is no pressure to stick with the ppt you can take different route if you think
> there is some problem with the ppt path but it should high end"
>
> "not the ppt one, the ppt i provided you is for refrence it can be change depending on
> how we are making"

**What the deck committed to:** Next.js console · FastAPI control plane · Ollama hot-swap
with Qwen2.5-7B / Coder-7B / VL-7B / bge-m3 · PaddleOCR+Tesseract · Qdrant hybrid ·
Docker `net=none` sandbox · hash-chained audit · live network monitor · SQLite ·
deterministic router · 8-step agent loop (≤12 steps, ≤2 replans) · 36-hour build plan ·
3 MVP demos (report→note, coding self-fix, sovereignty proof).

**Name:** PRAHARI (Hindi: sentinel / guardian).
**Tagline:** "AI comes to your data — not the other way around." *(Kept — it is exactly
the right framing; see §7.1.)*

---

## 4. Discovery — every question asked and answered

The brainstorming skill was invoked and the task classified as **architectural** (new
project, multiple subsystems, no existing code to read). The user asked to be asked how
many questions I wanted; they chose **full depth (8 questions)**.

### Meta-question — how many questions?
**Answer:** "All 8 — full depth."

### Q1 — Hardware
**Answer:**
- This development laptop (Windows 11): **no NVIDIA GPU**
- Target/demo laptop: **RTX 3050, 6 GB VRAM** — design for this
- Possible later: Ubuntu box with **RTX 5060 Ti, 16 GB** — *explicitly "don't consider it
  right now"*

### Q2 — Runway
**Answer:** *"i have to show tomorrow till 4pm in the evening i want show a working
prototype then i can make it more desgined but keep in mind from this time ownward i have
32 hours i will give each hour for this work."*

→ **32 hours, deadline tomorrow 16:00.** Working prototype required by then; polish
continues after. At this point the remaining 6 questions were compressed into one batch
to save the user's clock, with two assumptions stated and accepted: synthetic corpus
generated by me, and yes — build it, not just plan it.

### Q3 — Team
**Answer:** **2–3 people.**

### Q4 — Environment already installed on this laptop
**Answer: all four.** Docker Desktop + WSL2 working · Ollama installed · Python 3.11/3.12
· Node.js 18+.
→ **No setup tax.** This is a significant time saving and removed the biggest sprint risk.

### Q5 — Fidelity to the PPT
**Answer:** free rein, but "it should high end." The PS is the contract.

### Q6 — Which demo must not fail
**Answer:** the user declined to rank, said not to over-constrain by time, and re-pasted
the full PS to emphasise: **build to the PS's Expected Solution list, all of it.**

### Follow-up conceptual questions from the user
- *"how will the ai agent work for different companies… are we going to train it on what
  the company is using?"* → answered in §7.2 (**no training; org packs**)
- *"how are we keeping their data confidential and also providing them an ai agent?"* →
  answered in §7.1 (**move the model, not the data**)
- *"is it like — company buys a licence, installs locally, puts data in a folder, asks
  questions?"* → **Yes**, with four corrections; see §7.3

---

## 5. Hard constraints (the box we are building inside)

| Constraint | Value | Consequence |
|---|---|---|
| Demo GPU | RTX 3050, **6 GB** (~5.2 GB usable) | 3B models only; exactly **one** generative model resident at a time; hot-swap is mandatory, not optional |
| Dev machine | Windows 11, **no NVIDIA GPU** | Plumbing developed against CPU inference with 1.5B models; GPU work verified on the 3050 box |
| Time | **32 hours**, deadline tomorrow 16:00 | Phase gates + a pre-agreed cut list |
| Team | 2–3 people | Three tracks: backend spine / corpus+frontend / sandbox+security+rehearsal |
| Environment | Docker+WSL2, Ollama, Python 3.11+, Node 18+ **all present** | Zero setup phase |
| Licence posture | Air-gapped target | **No online licence activation possible** — see §7.3 |

### VRAM budget on the 3050 (the decisive calculation)

```
Total VRAM                         6.0 GB
− Windows desktop compositor      ~0.8 GB
= Usable                          ~5.2 GB

Generative models (one at a time):
  qwen2.5:3b-instruct-q4_K_M       2.4 GB   text / reasoning / writing
  qwen2.5-coder:3b                 2.4 GB   code
  qwen2.5vl:3b                     3.4 GB   vision / scans / drawings

Embeddings: bge-m3 → RUN ON CPU (frees ~1.2 GB)
```

**Decision: embeddings run on CPU.** Ingest is offline/batched, and a query embedding is
one short string — CPU latency is acceptable. This reserves the entire GPU for exactly one
generative model, which makes the swap logic clean and predictable.

---

## 6. Decisions taken, with reasoning

### D1 — LLM fills parameters and judges outcomes; **code owns the control flow**
*The single most important decision in the system.*

A 3B model given free-form "think and pick a tool" will hallucinate tool names, emit
broken JSON, and loop forever. So:
- Every LLM output is **schema-constrained** (Ollama structured-output mode takes a JSON
  Schema and forces conformance) — the planner *cannot* emit an invalid plan
- Plans are a **typed DAG**: `{tool, args, why, postconditions}`, validated against the
  tool registry **before** any execution
- Known archetypes ship a **plan skeleton** ("recipe") the planner starts from and may
  modify, add to, or reorder
- A **Critic** checks postconditions against the real observation; failure → bounded replan

**Why this is also the *right* answer for the domain, not just a workaround:** an
unbounded free-form agent is *worse* for a refinery. Constrained means auditable, bounded,
and incapable of rogue actions. Reliability here is a feature, not a compromise.

### D2 — Route per **step**, not per task
The router runs at every step of the plan. A single flagship run therefore visibly uses
VL → text → Coder. This satisfies PS demonstrable #2 ("auto-selection across ≥2 task
types") *inside one demo* rather than requiring two separate ones.

### D3 — Never fine-tune. Knowledge lives outside the model
Five reasons, the last decisive:
1. **No data** — fine-tuning needs thousands of labelled examples; MRPL has SOPs, not a training set
2. **No GPU** — 6 GB; fine-tuning even a 3B is GPU-days
3. **SOPs change** — you cannot retrain on every clause amendment
4. **Fine-tuned facts cannot be cited** — a refinery needs *"t_min = 6.4 mm, SOP-INS-07
   §4.2, p.12"* with an openable pointer. Weights have no page numbers
5. **The PS forbids it** — *"New open weight models should be addable later without
   redesigning the system."* Fine-tuning **couples** knowledge to weights, so every new
   model means redoing all training. Knowledge must be **decoupled** from the model

### D4 — Deterministic calculation engine, never LLM arithmetic
`calc.evaluate` uses **sympy + pint**. In a refinery an LLM doing arithmetic freehand is a
safety liability. It returns value, unit, **and the ordered step list** — so *"calculations
with steps shown"* (PS requirement) is a data structure, not narration.

### D5 — Confidence-routed OCR cascade, not flat OCR
```
born-digital PDF  → PyMuPDF: exact text + bbox          (no OCR at all)
scanned page      → render 300 dpi → Tesseract + per-word confidence
                        └─ low conf OR drawing OR handwriting
                             └─ escalate to Qwen2.5-VL ("transcribe, preserve tables")
```
Better than the deck's flat "PaddleOCR + Tesseract", *and* it sidesteps PaddlePaddle,
whose Windows install can consume hours. The cascade **is** the multimodal requirement:
handwritten notes and engineering drawings land in tier 3 by design.

### D6 — Keep bounding boxes through the whole pipeline
Chunks carry `{doc_id, page, bbox, section}`. Clicking a citation **highlights the exact
region on the scanned page**. Disproportionately high credibility per hour of work.

### D7 — Mechanical citation verification
Model receives chunks as `[C1]…[C7]` and must cite. Then, **in code**:
1. every `[Cn]` must exist
2. numbers and entities in the sentence must actually appear in chunk *n*
3. any sentence containing a number but no citation is **flagged**

Flagged claims render with a warning chip and are **excluded from the final DOCX** unless
a human approves. Grounding you can check, not grounding you hope for.

### D8 — Plan-aware model prefetch
Because we hold the whole plan DAG upfront, we know step 5 needs Coder while step 3 is
doing CPU-bound OCR — so the load starts early and the swap is hidden. Most agents cannot
do this because they do not have the plan.

### D9 — Ollama native on Windows; Docker only for Qdrant and the sandbox
Avoids WSL2 GPU-passthrough pain entirely. Ollama uses CUDA natively on Windows.

### D10 — `org_id` scoping from hour one
Cheap now (~90 min), nearly impossible to retrofit at hour 25. Enables the multi-company
demo (§9, Demo E) and is the foundation of the whole business model.

### D11 — No dedicated reranker
Costs VRAM we do not have. Qdrant's native RRF fusion is sufficient. Optional LLM rerank
of top-12 only when the text model happens to already be loaded (free).

### D12 — No network tool, no shell tool, ever
See §7.1. This is what makes the confidentiality claim structural rather than aspirational.

---

## 7. The three conceptual explanations given to the user

These were the user's own questions and the answers are core to the pitch.

### 7.1 How confidentiality works — "move the model, not the data"

The asymmetry that makes it possible:

| | Model weights | Their data |
|---|---|---|
| Size | ~8 GB, fixed | Terabytes, growing |
| Confidential? | **No** — Apache-2.0, public | **Yes** — P&IDs, financials, vendor terms |
| Moves how often? | **Once, ever** | Continuously, forever |

Cloud AI moves the **private, dynamic** thing to a stranger's computer thousands of times
a day. We move the **public, static** thing onto their box **once**, and their data never
travels at all.

> **Confidentiality is not a feature we bolted on. It is a consequence of the fact that
> the data never moves.** There is no transmission to secure, no retention policy to
> trust, no jurisdiction to worry about, no deletion promise to believe.

**Six defence layers, by threat:**

1. **Network exfiltration** — no cloud SDKs or API keys in the codebase at all (a judge
   can `grep` live and see nothing); in-process socket guard raising on any non-loopback
   connect; offline pins (`HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE`, `OLLAMA_HOST=127.0.0.1`,
   Next telemetry off); host firewall outbound DENY; live monitor + canary; air-gap capable
2. **Exfiltration via the agent's own tools** — *the layer most people miss.* There is
   **no network tool** in the registry (no `http.get`, no `email.send`, no webhook) and
   **no shell tool ever** (a shell is a universal exfiltration primitive). Filesystem is
   jailed to `./data/orgs/<org>/workspace`. Sandbox has `--network none`.
   → **Even a fully compromised agent has no route out.** Architecture, not vigilance.
3. **Prompt injection from their own documents** — retrieved/OCR'd text is framed as
   untrusted data, never instructions; tool calls accepted only from the planner channel,
   schema-validated; and because of layer 2, a *successful* injection still cannot
   exfiltrate. Blast radius capped at "produces a wrong document", which human review catches
4. **Data at rest** — one directory `./data/orgs/<org_id>/`; full-disk encryption as
   deployment guidance; Qdrant and SQLite bound to `127.0.0.1`; org isolation via separate
   collections + `org_id` on every query.
   **Noted explicitly: embeddings are not encryption.** Vectors can be partially inverted,
   so the vector DB is classified as confidential as the source documents
5. **Insider activity** — hash-chained audit log `hash(n) = sha256(payload(n) ‖ hash(n−1))`,
   tamper-evident, exportable for the CISO; mandatory human approval on every deliverable
   so accountability stays with a named person; RBAC + SSO in V1
6. **Supply chain** — open weights with published checksums; **SHA-256 of every model file
   displayed at boot**; models pulled once on a staging machine then carried in; deps
   pinned and hash-locked; Docker images built locally from a pinned base

**Explicitly NOT claimed** (stating limits is what makes the rest credible): screen
photography; a malicious admin with physical access; a user copying a DOCX to USB (that is
existing DLP's job); the model being wrong — hence deterministic calculations, verified
citations, and the human approval gate.

**Why it is still a good assistant.** The only thing given up is **raw model size** — and
the PS explicitly permits that. Everything else gets *better* locally:

| | Cloud AI | PRAHARI |
|---|---|---|
| Knows their business | Only what someone dared paste in | Indexes their **entire** 40-year document estate |
| Can touch real systems | No | Reads their shares, writes their workspace, runs their calcs |
| Latency | Round trip abroad | Local |
| Marginal cost | Per token, forever | ₹0 |
| Raw horsepower | **Higher** ✔ | Lower |

> **A 3B model reading the actual SOP beats a 400B model guessing at it.** Most of this
> work is *look up the right clause, apply the right formula, fill the right template,
> cite the source* — a retrieval-and-tools problem, not a model-size problem.

### 7.2 How it works for different companies — "one engine, many org packs"

**We never train a model per company. Not once, not for anybody.**

> **The model brings the skill. Their folder brings the facts.**
> We ship the skill. They own the facts. The two never mix, and the facts never leave the building.

**Analogy:** Microsoft does not build a different Excel for each company. They ship one
Excel; every company installs the same one and opens *their own* spreadsheets in it. Excel
was never "trained" on your company.

**Four layers of company-specificity:**

| Layer | Mechanism | Cost to onboard a company |
|---|---|---|
| 1 · Their documents | Indexed locally; the model **reads** them at answer time (RAG) | Minutes — point a connector at their share |
| 2 · Their formats | Letterhead, clause numbering, sign-off blocks, XLSX/PPTX templates | Hours — drop in a template file |
| 3 · Their language & math | Glossary of abbreviations; calculation standards as named formulas | Hours — edit two YAML files |
| 4 · Fine-tuning (LoRA) | *Optional, V2+.* Only ever for **house tone/style**, never facts | GPU-days |

Layers 1–3 are ~99% of it and require zero training.

**A company, in our system, is one folder:**

```
orgs/
├── mrpl/
│   ├── profile.yaml          # name, metric units, fiscal year, approval hierarchy
│   ├── connectors.yaml       # \\fileserver\Engineering\SOPs, \\...\Inspection
│   ├── glossary.yaml         # CDU, VDU, HGU, MOC, WO, T&I → their meanings
│   ├── standards/
│   │   └── calc_library.yaml # corrosion rate per API 570; their t_min rules
│   ├── templates/
│   │   ├── approval_note.docx
│   │   ├── inspection_sheet.xlsx
│   │   └── board_deck.pptx
│   ├── recipes/
│   │   └── inspection_report_to_note.yaml
│   ├── policy.yaml           # allowed tools, approver roles, retention
│   └── kb/                   # built index (Qdrant collection + SQLite rows)
└── defence_unit_a/           # different company, SAME engine, no retraining
```

**A concrete trace — why no training is needed.**
Engineer asks: *"Is the measured thickness at Elbow E-14 acceptable?"*

```
1  Embed the question with bge-m3                  → local, on CPU
2  Hybrid search MRPL's collection                 → SOP-INS-07 §4.2, page 12:
       "minimum retirement thickness for 8in CS piping in sour service shall be 6.4 mm"
3  That text is injected into the prompt as        → [C3]
4  Model composes: "Measured 5.9 mm is below the 6.4 mm retirement threshold [C3];
       recommend derate or replacement."
5  Verifier checks "6.4" really appears in C3      → ✓ PASS
6  Citation chip [C3] → click → highlights that exact box on page 12
```

**The model never knew 6.4 mm.** It read it one second ago from MRPL's own file. If MRPL
amends the clause to 6.0 mm tomorrow, the answer changes tomorrow — nobody retrains anything.

**Training vs. what we do:**

| | Training (the common misconception) | What we actually do |
|---|---|---|
| Mechanism | Model **memorises** documents into its weights | Model **reads** relevant pages when asked |
| Cost | GPU-weeks, per company | Milliseconds, per question |
| When an SOP is revised | Model is now **wrong**; retrain | **Already current** |
| Can cite a page? | **No** — a blurry memory | **Yes** — click to see the highlighted box |
| Swap in a better model | Redo all training | Change one config line |

### 7.3 The commercial shape — the user's mental model, confirmed

The user proposed: *"we make one AI agent, a PSU buys a licence, installs it on their own
system, puts their data in a folder, and asks questions — same for other companies."*

**Confirmed correct**, with four corrections:

1. **"They will download it"** → an air-gapped PSU *cannot download*. It arrives on
   physical media or their internal repo. This is a **selling point** — it is exactly how
   defence and PSU sites are willing to accept software
2. **"Data in a specific folder"** → two modes. A watched folder (simple, good for demo),
   **or** — what real deployments want — point it at their **existing shares**, read-only.
   Nobody wants to copy 40 years of documents into a magic folder; that is itself a storage
   and security problem
3. **"Ask any question"** → *undersells it badly.* The PS says *"not just chat replies."*
   It **produces the work**: Word approval notes, Excel with live formulas, PowerPoint
   board decks, sandbox-tested code, calculations with every step shown — and then revises
   them on request. The difference between a search box and a colleague
4. **The licence** → models are free (Apache-2.0). What is licensed is **our engine**:
   routing, agent loop, tool gateway, grounded citations, sandbox, audit chain, sovereignty
   controls, deployment kit.
   > *"Why pay when Ollama is free?"* — Ollama runs a model. We run a **business process**.
   > Ollama is one component inside our system.

   **Critical consequence:** an air-gapped product **cannot have online licence
   activation** — a licence server phoning home would destroy the entire sovereignty claim.
   So: a **signed offline licence file**, node-locked to a machine fingerprint, verified
   locally with a public key. Never a call home. Each installation is its own island; we
   never see a single customer document, not even in principle.

**Deployment lifecycle:**
- *What we ship:* one installer / USB — engine, open-weight models, Qdrant + sandbox image,
  empty `orgs/` with a blank template pack
- *Day 1 install (~2 h, their IT):* copy to GPU server → run installer → **no internet at
  any point** → open browser on the plant LAN
- *Day 1 point at data (~1 h + unattended indexing):* edit `connectors.yaml`, click Index
- *Day 2 tailor (~half a day with one of their engineers):* letterhead template, glossary,
  calculation standards
- *Every day after:* no internet, no per-token bill, nothing leaves the building
- *Six months later:* new model ships → one registry line + drop in the file. No
  re-indexing, no retraining — the knowledge base is untouched because knowledge was never
  in the model

---

## 8. The architecture

### 8.1 System shape

```
┌─ ON-PREMISE TRUST BOUNDARY ─────────────────────────────────┐
│                                                              │
│  UI        Next.js: threads · attachments · live timeline    │
│            · router table · sources+bbox · security · artifacts│
│                              ↕ SSE                           │
│  CONTROL   FastAPI: classify → route → plan → execute        │
│            → observe → critic → replan? → artifact           │
│                                                              │
│  ROUTER    registry(YAML) · scorer · VRAM mgr · swap ctl     │
│  KNOWLEDGE connector · ingest · OCR cascade · Qdrant hybrid   │
│            · citations + verifier                            │
│  TOOLS     deny-by-default registry, JSON-Schema'd args      │
│  SANDBOX   Docker --network none, caps dropped, 20 s cap     │
│                                                              │
│  SECURITY  in-process egress guard · live net monitor        │
│            · hash-chained audit · SQLite                     │
└──────────────────────────╳───────────────────────────────────┘
                      NO PATH OUT
```

### 8.2 Agent protocol

```
RECEIVE → GROUND → CLASSIFY → PLAN ─┬─► SELECT → EXECUTE → OBSERVE → CRITIC ─┐
                                    │                                         │
                                    └──────────── REPLAN (≤2) ◄───────────────┘
                                                     │ pass
                                     SYNTHESIZE → DELIVER → AWAIT_HUMAN
                                                              │
                                              "revise it" ────┘ (new run → artifact v2)
```

| State | What it does |
|---|---|
| RECEIVE | User turn + attachments + thread context + referenced artifacts |
| GROUND | Quick retrieval so the planner references real documents |
| CLASSIFY | Intent + required capabilities + modalities → typed `TaskSpec` |
| PLAN | Schema-constrained DAG, seeded by recipe if an archetype matches |
| SELECT | Router picks a model **per step** |
| EXECUTE | Tool gateway with policy check |
| OBSERVE | Typed observation |
| CRITIC | Postcondition check; may trigger REPLAN |
| SYNTHESIZE | Compose final answer + artifacts |
| DELIVER | Artifacts written with citations attached |
| AWAIT_HUMAN | Approve / request changes → new run that edits the artifact |

**Budgets:** ≤14 steps, ≤2 replans, ≤3 sandbox retries, wall-clock cap, token cap. On
exhaustion: stop and return partial results — never an infinite loop.

### 8.3 Model router

Registry entry — adding a model is one entry plus `ollama pull`, zero code:

```yaml
- id: qwen2.5-coder:3b
  roles: [code]
  modalities: [text]
  vram_mb: 2400
  ctx: 32768
  quality: 0.60          # capability prior
  speed_tok_s: null      # measured at first use, not guessed
```

Scoring — deterministic and explainable:

```
hard gates:  modality ⊇ task.modalities  AND  roles ∋ task.role     else reject
score     =  w_q·quality + w_ctx·fits_context + w_lat/est_latency
             − w_swap·swap_cost(m)     ← 0 if already in VRAM
             − w_vram·vram_pressure(m)
```

The `swap_cost` term **is** the resource-awareness: when quality is close it keeps the
resident model. The router emits a **decision record** — the full score table, every
candidate, why each loser lost — rendered in the UI. *That table is the evidence for PS
demonstrable #2.*

**Models (6 GB profile):**

| Role | Model | VRAM |
|---|---|---|
| text / reasoning / writing | `qwen2.5:3b-instruct-q4_K_M` | 2.4 GB |
| code | `qwen2.5-coder:3b` | 2.4 GB |
| vision / scans / drawings | `qwen2.5vl:3b` | 3.4 GB |
| embeddings | `bge-m3` | **CPU** |

Dev-machine (no GPU) plumbing pair: `qwen2.5:1.5b`, `qwen2.5-coder:1.5b`.

### 8.4 Knowledge plane

**Connector, not uploader.** `FolderConnector(path, globs, watch)` points at a share,
hashes, detects changes, re-indexes incrementally. Handles PDF · DOCX · XLSX · PPTX ·
images · TXT · **EML/MSG** (that is "past correspondence"). Pluggable so SharePoint-on-prem
drops in later.

**Ingestion:**
```
file → type detect
  ├ born-digital PDF → PyMuPDF: text + blocks + bbox per page
  ├ scanned PDF/image → render 300 dpi → Tesseract (+per-word confidence)
  │     └─ low conf / drawing / handwriting → escalate to Qwen2.5-VL
  ├ DOCX → python-docx paragraphs + tables
  ├ XLSX → openpyxl sheets → row text
  ├ PPTX → python-pptx
  └ EML/MSG → headers + body + attachments (recurse)
       ↓ layout-aware chunking (~600 tok, 80 overlap, never split a table row)
       ↓ metadata {doc_id, page, bbox, section, doc_type, date, connector, org_id}
       ↓ embed (bge-m3, CPU) + BM25 sparse
       ↓ Qdrant upsert (named vectors: dense + sparse)
```

**Retrieval:** Qdrant Query API with `prefetch` on both vectors + native `fusion: rrf`.

### 8.5 Tool catalogue

Every tool declares a JSON Schema for args and a capability set
(`fs.read:/data/inbox`, `exec:sandbox`). Policy gate before, audit record after.

| Group | Tools |
|---|---|
| Knowledge | `kb.search` · `kb.sources` · `doc.read` · `doc.regions` |
| Perception | `ocr.page` · `vision.ask` · `table.extract` |
| Compute | `calc.evaluate` · `sheet.read` · `code.run` |
| Files | `fs.read` · `fs.write` (jailed to `./data/orgs/<org>/workspace`) |
| Deliverables | `docx.render` · `docx.revise` · `xlsx.render` · `pptx.render` |
| Meta | `models.reload_registry` · `audit.verify` |

**Deliberately absent: any network tool, and any shell tool.**

### 8.6 Sandbox

```
docker run --rm --network none --read-only
  --cap-drop ALL --security-opt no-new-privileges
  --pids-limit 128 --memory 512m --cpus 1
  --user 65534:65534 -v <job>:/job:ro
  prahari-sandbox:py311  timeout 20 python /job/main.py
```

Self-correction: generate → run → parse traceback → patch → rerun, ≤3 attempts. One demo
has the generated code deliberately attempt a fetch — and fail. Egress proof from inside.

### 8.7 Data model (SQLite)

```
threads(id, org_id, title, created_at)
messages(id, thread_id, role, content, created_at)
runs(id, thread_id, message_id, status, budget_json, started, ended)
steps(id, run_id, idx, tool, args_json, model_id, status, observation_json, duration_ms, tokens)
router_decisions(id, step_id, chosen, candidates_json, weights_json)
artifacts(id, run_id, kind, path, version, parent_version, approved_by, approved_at)
documents(id, org_id, source_uri, sha256, pages, ingested_at, connector_id)
chunks(id, doc_id, page, bbox_json, text, section)        ← mirrored to Qdrant
audit(seq, ts, actor, event, payload_json, prev_hash, hash)
security_events(id, ts, kind, detail_json)
```

Artifacts are **versioned** — that is what makes "iterate on the deliverable" work.

### 8.8 Backend module layout

```
prahari/
  api/            FastAPI routes + SSE event stream
  agent/          loop, planner, critic, state
  router/         registry, scorer, vram manager, swap controller
  models/         ollama client, prompts, schema-constrained decode
  knowledge/      connectors, ingest, ocr cascade, chunker, qdrant store,
                  hybrid search, citation verifier
  tools/          registry, policy, one module per tool
  sandbox/        docker runner
  security/       egress guard, net monitor, audit chain, attestation
  deliverables/   docx / xlsx / pptx renderers
  store/          sqlite (threads, runs, steps, artifacts, audit)
  orgs/           profile loader, template resolver
```

### 8.9 Interface

```
┌ Threads ┬──────── Conversation ─────────┬──── Inspector ────┐
│ Inspec- │ 🧑 "Draft approval note per   │ [Sources]         │
│ tion    │     SOP" 📎 report.pdf        │  scan page w/     │
│ note    │                                │  bbox highlight   │
│         │ ✅ Plan · seeded from recipe   │                   │
│ P&ID Q  │ ✅ 1 OCR (VL) ......... 4.2s   │ [Models]          │
│         │ ✅ 2 Extract findings . 2.1s   │  VRAM ▓▓▓▓░ 3.4/5 │
│ Corro-  │ ✅ 3 SOP retrieve [C3] . 0.3s  │  loaded: VL-3B    │
│ sion    │ ✅ 4 calc 0.42 mm/yr .. 0.01s  │  swap log: 1.8s   │
│ script  │ ✅ 5 Critic: 3/3 pass          │                   │
│         │ 📄 approval_note.docx  v1      │ [Security]        │
│         │    [Preview][Download][Revise] │ EXTERNAL: 0 ✅    │
│         │                                │ [Test canary]     │
└─────────┴────────────────────────────────┴───────────────────┘
   top bar:  ● AIR-GAPPED · 0 EXTERNAL CONNECTIONS · audit ✓ 247
```

---

## 9. The demos

### Demo A — flagship: scanned inspection report → Word approval note

| # | Action | Model / tool |
|---|---|---|
| 1 | Classify → `document_to_deliverable`; plan seeded from recipe | text 3B, schema-forced |
| 2 | Router: input is a scan → text-only models **hard-gated out** → VL wins (table shown) | router |
| 3 | OCR cascade; the thickness table escalates to VL | Tesseract → VL |
| 4 | Extract typed findings `{location, t_nom, t_actual, t_min, years}` | VL → text |
| 5 | **Prefetch**: swap VL→text while retrieval runs on CPU | swap controller |
| 6 | Retrieve the SOP's retirement-thickness clause + page + bbox | Qdrant hybrid |
| 7 | **Deterministic** corrosion rate `(t_nom−t_actual)/yrs`, remaining life `(t_actual−t_min)/rate`, mm/yr | `calc.evaluate` |
| 8 | Critic: ≥1 finding? every claim cited? units consistent? | verifier |
| 9 | Render DOCX — findings, cited clause, calculation steps, recommendation | `docx.render` |
| 10 | Human clicks **Approve**; then *"add a cost table"* → **v2** | `docx.revise` |

Real API-510/570-shaped inspection math. Step 10 is the "iterate, don't stop" requirement,
made visible.

### Demo B — coding, verified in sandbox
*"Write and test a script that computes corrosion rate from this CSV."* → Coder model →
sandbox run → a test **fails** → reads the traceback, patches, reruns, **passes**. The
script also attempts one outbound fetch, which fails — proving `net=none` from the inside.

### Demo C — multimodal
P&ID question answered against a drawing region, plus a **handwritten** field note
transcribed. Both cited back to the highlighted image region.

### Demo D — extensibility, live
Append a YAML entry, hit reload, the new model appears in the router table **in front of
the judges**. "Addable without redesign," demonstrated rather than asserted.

### Demo E — multi-company (bonus, P6, never allowed to threaten the core)
Same box, same models, same question — flip org from **MRPL** to **Defence Unit A**. The
answer now cites a different standard and the Word file comes out on different letterhead.
Answers "does this only work for MRPL?" in 30 seconds.

### The sovereignty proof — 90 seconds on stage
1. `grep -r "openai\|anthropic\|api_key\|https://" src/` → **nothing**
2. Security panel: **EXTERNAL CONNECTIONS: 0**, from live `netstat`
3. Hit the canary → **BLOCKED**, logged as a security event
4. **Pull the cable.** Run Demo A end to end. Identical result
5. Open the audit log, verify the hash chain → **✓ 247 entries intact**
6. Show the model SHA-256s from the boot attestation panel

---

## 10. Requirements traceability

| PS requirement | Where it is satisfied |
|---|---|
| Working local deployment, mid-range GPU, smaller model OK | RTX 3050 6 GB, one command, Qwen2.5 3B trio |
| Model auto-selection across ≥2 task types | Per-step routing + visible score tables (Demos A & B) |
| Agentic task end-to-end | Demo A, all 10 steps, plus turn-2 revision |
| Coding task run and verified in a sandbox | Demo B, with self-correction |
| Multimodal task | Demo C + the OCR cascade inside Demo A |
| **Proof** of no external calls | Live monitor · canary BLOCKED · hash-chained audit · cable pull |
| Real deliverables (Word/Excel/PPT, code, calcs with steps) | DOCX/XLSX/PPTX renderers; `calc` returns step lists |
| Grounded in manuals / SOPs / correspondence | Folder connector incl. EML, hybrid RAG, verified citations |
| New models addable without redesign | Demo D, live |
| Tools: file r/w, sandbox exec, spreadsheet, doc search | §8.5 tool catalogue |
| Iterate instead of stopping | Critic→replan (intra-run) + artifact revision (inter-turn) |

---

## 11. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| `qwen2.5vl:3b` will not pull / run on the 3050 | **Highest — could force redesign** | **Verify first.** Fallbacks: `moondream` (1.8B), `llava:7b` |
| 3B plans poorly | High | Schema-forced output + recipe skeletons + repair loop (D1) |
| Swap latency feels slow | Medium | Plan-aware prefetch (D8); surface the swap in UI as the feature it is |
| OCR quality on real scans | Medium | Cascade (D5); we control the demo corpus |
| Docker Desktop flakiness on Windows | Medium | Pre-build sandbox image; health check at boot |
| Clock | High | Phase gates + pre-agreed cut list |

**Cut list, in order:** PPTX renderer → EML connector → LLM reranker → air-gapped USB
bundle → Demo E. Everything above those stays.

---

## 12. Build plan — 32 hours, 3 tracks

**Track 1** (user + Claude): backend spine — the critical path
**Track 2**: synthetic corpus, then frontend
**Track 3**: sandbox image, security proof, rehearsal

| Phase | Hrs | Gate — how we know it is done |
|---|---|---|
| **P0** Walking skeleton | 0–2 | Type a task → a fake 3-step plan streams into the real UI |
| **P1** Router + VRAM swap | 2–6 | Real score table, measured swap ms |
| **P2** Agent loop + 4 tools | 6–11 | A multi-step task emits a real DOCX |
| **P3** Knowledge plane | 11–17 | SOP answer with a clickable, highlighted citation |
| **P4** Sandbox + self-fix | 17–21 | Test fails → agent fixes → passes |
| **P5** Multimodal | 21–25 | Drawing Q&A with region highlight |
| **P6** Security + audit + polish (+ Demo E) | 25–29 | Canary BLOCKED, monitor live, chain verifies |
| **P7** Rehearsal + backup recording | 29–32 | Clean run with the cable out |

**Why P0 first:** a skeleton that streams a *fake* plan end-to-end by hour two kills the
integration risk that actually sinks sprints like this. Everything after P0 is filling in
real implementations behind interfaces that already work.

---

## 13. Stack

All local, all open-source.

| Layer | Choice |
|---|---|
| Model runtime | **Ollama, native on Windows** (not in Docker — dodges WSL2 GPU passthrough) |
| Models | Qwen2.5-3B-Instruct · Qwen2.5-Coder-3B · Qwen2.5-VL-3B · bge-m3 (CPU) |
| Backend | Python 3.11 + FastAPI + SSE |
| Vector DB | Qdrant (Docker), hybrid dense+sparse, native RRF |
| OCR | Tesseract → Qwen2.5-VL escalation (PaddleOCR optional, not required) |
| PDF | PyMuPDF (text, blocks, bbox, page raster) |
| Math | sympy + pint (deterministic, units-aware) |
| Deliverables | python-docx · openpyxl · python-pptx |
| Sandbox | Docker, `--network none`, caps dropped |
| Storage | SQLite |
| Frontend | Next.js + React + Tailwind |
| Deploy | Docker Compose (Qdrant + sandbox image) + a start script |

---

## 14. Departures from the submitted PPT

Permitted explicitly by the user; recorded so the difference is deliberate, not accidental.

| Change | Why |
|---|---|
| 3B Qwen trio, not 7B | 6 GB reality; PS explicitly permits smaller models |
| Embeddings on **CPU** | Frees ~1.2 GB so one full generative model fits |
| OCR **cascade** with VL escalation | Better quality routing; avoids PaddlePaddle's Windows install risk |
| Deterministic `calc` (sympy + pint) | LLM arithmetic is unacceptable in this domain |
| Schema-constrained decoding | Removes most 3B fragility |
| Plan-aware model prefetch | Hides swap latency; only possible because we hold the DAG |
| Citation **verifier** | Makes grounding mechanically checkable |
| In-process egress guard + canary | Proves the claim instead of asserting it |
| Ollama native on Windows | Dodges WSL2 GPU passthrough entirely |
| No dedicated reranker | Costs VRAM we do not have |
| Per-**step** routing (not per task) | Makes auto-selection visible inside one demo |
| `org_id` scoping + org packs | Enables multi-company story; cheap now, impossible later |
| Threaded conversational UI + artifact revision | The PS names Claude/Codex as the UX bar |

---

## 15. Open items / next actions

### Immediate — blocking
- [ ] **Verify `ollama pull qwen2.5vl:3b` works on the RTX 3050 laptop.** The only
      remaining item that could force a design change. Fallbacks: `moondream`, `llava:7b`
- [ ] Pull the other three models on the 3050 box (~8 GB total, longest lead time):
      `qwen2.5:3b-instruct-q4_K_M`, `qwen2.5-coder:3b`, `bge-m3`
- [ ] Pull the CPU plumbing pair on the dev laptop: `qwen2.5:1.5b`, `qwen2.5-coder:1.5b`

### Awaiting user decision
- [ ] **Approve this design** → then write the spec to
      `docs/superpowers/specs/2026-09-11-prahari-design.md` and start P0

### Deferred / not yet decided
- Whether Demo E (multi-company switch) survives the clock — planned for P6, first to be cut
- Whether the air-gapped USB bundle export is built during the sprint or described only
- HIGH profile tuning for the 16 GB 5060 Ti box — explicitly out of scope for now

---

## 16. Phrases worth keeping for the pitch

- *"AI comes to your data — not the other way around."* (from the deck; it is exactly right)
- *"The model brings the skill. Their folder brings the facts."*
- *"Confidentiality is not a feature we bolted on. It is a consequence of the fact that
  the data never moves."*
- *"Even a fully compromised agent has no route out."*
- *"A 3B model reading the actual SOP beats a 400B model guessing at it."*
- *"Ollama runs a model. We run a business process."*
- *"That's the actual proof of the sovereign claim, not just a statement of it."* (the PS's
  own words — quote them back)

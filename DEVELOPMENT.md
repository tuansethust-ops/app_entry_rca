# Development Guide: App Entry RCA

This document records the development process, architectural decisions, and integration notes for the `app_entry_rca` project to facilitate future enhancements.

## 1. Project Context & Evolution

The **App Entry RCA** project aims to perform deterministic, evidence-driven Android app-launch performance regression analysis (DUT vs REF).
The project evolved through several major phases:
1. **Prototype Phase (v1-v3):** Basic trace reading, python-embedded rules.
2. **Contract-Driven Phase (v4-v7):** Shifted to explicit skill routing, declarative `leaf_rules.yaml`, and semantic leaf IDs (e.g., `p3.bindapplication...`).
3. **Web UI & Batch Processing Phase:** Added an interactive FastAPI-based web dashboard to eliminate CLI friction and support concurrent folder-level batch analysis.

## 2. Core Architecture

The system operates as an orchestrator pipeline running multiple independent "skills".

```text
Trace Pair (DUT/REF) 
  -> trace-ingestion 
  -> launch-context 
  -> trace-validation 
  -> phase-localizer
  -> Capability Skills (CPU, IO, Memory, Render, etc.)
  -> leaf-evaluator 
  -> evidence-graph-ranking
  -> report-generator
```

### Key Components
- `app_entry_rca/core/`: Contains models, trace backend protocols, and the orchestrator logic.
- `app_entry_rca/workflow/`: Handles skill routing based on taxonomies.
- `taxonomy/`: YAML/JSON definitions for phases, leaves, and thresholds.
- `skills/`: Individual capability plugins (e.g., `memory-gc-analysis`).
- `web/`: FastAPI server, WebSocket emitter, and static frontend assets.

## 3. Web UI Implementation Details

The Web UI was built with a "Local-First" philosophy to handle massive `.perfetto` and `.log` traces without network upload bottlenecks.

### Backend (`web/`)
- **Framework:** `FastAPI` + `Uvicorn`.
- **API Endpoints:**
  - `GET /api/browse`: Navigates the server's local filesystem to select traces.
  - `POST /api/scan-folders`: Intelligently parses trace filenames (`<model>_<os>_<ram>_..._<app>.log`) to extract metadata and pair DUT/REF apps automatically.
  - `POST /api/batch`: Submits multiple paired traces into the async job manager.
  - `GET /ws/jobs/{id}`: WebSocket endpoint broadcasting real-time progress.
- **Event Emitter:** The core `orchestrator.py` was retrofitted to accept an `event_callback`. This callback sends `skill.started`, `skill.completed`, and `job.completed` events through an `asyncio.Queue` bridging the synchronous analysis threads with the asynchronous WebSocket server.

### Frontend (`web/static/` & `web/templates/`)
- **Tech Stack:** Vanilla HTML/CSS/JS (Zero external framework dependencies aside from Chart.js via CDN).
- **Design System:** Dark glassmorphism (`rgba(255,255,255,0.05)`, backdrop filters).
- **Modules:**
  - `app.js`: Core navigation, API communication, and Quick Scan logic.
  - `websocket.js`: Real-time log streaming and progress bar updates.
  - `report.js`: Renders the final `final_leaves.json`, Gantt charts, and evidence trees.
  - `charts.js`: Renders phase comparison and skill execution times using Chart.js.

## 4. Known Gotchas & Future Work

### Trace Backend Compatibility
The `TraceBackend` protocol dictates how skills fetch metrics. When adding new backends, ensure ALL protocol methods (e.g., `longest`, `sum_slice_ms`) are fully implemented to avoid runtime `AttributeError`s during skill execution.

### CPU Core Logic
In earlier versions, core analysis was hardcoded to big cores (e.g., `cpus=(6,7)`). This was fixed in `systrace.py` to dynamically evaluate all available CPUs. When writing new scheduler skills, always use dynamic CPU sets.

### Future Work Candidates
1. **O(n²) Bottlenecks:** Certain skills parsing massive nested slice arrays might still suffer from O(n²) time complexity. Optimizing the in-memory `Slice` filtering using interval trees could yield speedups.
2. **Memory Snapshot Parsing:** Fully implement the parser for `Start_LogFile`/`End_LogFile` markers if exact `MemTotal` or `MemFree` regressions need to be included in the P8 Cross-Cutting Evidence phase.
3. **Persisting Jobs Database:** Currently, the `JobManager` stores job states in memory (`dict`). For persistent history across server restarts, integrate a lightweight database (e.g., SQLite/TinyDB).

## 5. Development Workflow

**Run API Tests:**
```bash
python3 -m pytest tests/
```

**Run Web Server:**
```bash
python3 run_web.py
```

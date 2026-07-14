# Jarvis OS – Project Context

## 🧠 Project Status (as of 2026-07-13)

- **Location**: `/mnt/jarvis_home/jarvis-os` (on the 1TB D drive)
- **Docker**: Running with 3 services (postgres, tts, api). Docker root moved to `/mnt/jarvis_home/docker` – no more OS drive space issues.
- **API**: Stable – responds to `/health`, `/api/chat`, `/api/tts`, `/api/transcribe`, etc.
- **LLM**: Model loaded (`/app/models/dolphin-2_6-phi-2.Q4_K_M.gguf`). Sometimes fails to produce tool‑calls, but falls back to template response.
- **Web UI**: Fully functional at `http://localhost:8000` – voice, wake word, streaming, TTS.

---

## ✅ Completed Phases

### Phase 0 – Governance (Complete)
- Constitution, Development Constitution, Operational Policies, Execution Model, Core Abstractions defined.
- Architecture Review process established.

### Phase I – Architectural Consolidation (Complete)
- Goals, Tasks, Capabilities, Events, Memory as first‑class objects.
- Unified Capability Registry (with backward‑compatible `ToolRegistry` alias).
- DigitalTwin stores state snapshots in Memory.
- State machine introduced (ExecutionState, PlatformState).

### Phase II – Core Abstractions (Complete)
- Task ownership enforced (every Task belongs to a Goal).
- Planner introduced (`src/execution/planner.py`) – creates Tasks from Goals.
- ChiefOfStaff updated to enforce Goal ownership and use formal states.
- `priority` field removed from Task (moved to GoalBudget).
- All code aligned with the five core abstractions.

### Phase III – Execution Platform (Complete)
- Planner creates a structured plan (list of Tasks) for each Goal.
- ChiefOfStaff (Scheduler) dispatches Tasks to departments.
- Retry logic integrated (max retries, exponential backoff planned).
- Budget system is defined, but enforcement is still limited (will be expanded in later phases).
- Event vocabulary expanded (PlanCreated, TaskRejected, etc.).

---

## ✅ Working Features
- **`execute:` command** – runs any shell command through `system_control` (tested with `echo`, `git` push).
- **Web UI** – full voice, wake‑word (Porcupine/annyang), TTS, streaming, theme toggle.
- **Memory** – embeddings, semantic search, SQLite/Postgres, consolidation pipeline.
- **User management** – registration, login, API key authentication.
- **TTS proxy** – via Edge TTS container.
- **Transcription** – Whisper (tiny) for voice input.
- **Capability registry** – 15 capabilities registered (research, coding, system, weather, calendar, email, etc.).
- **DigitalTwin** – hardware, capabilities, environment stored as MemoryRecords.
- **Event Bus** – standard vocabulary, audit logging.

---

## 📁 Key Files (Current)
| File | Purpose |
|------|---------|
| `src/api.py` | FastAPI entry point, streaming, auth |
| `src/v2_main.py` | Engine initialisation, registries, departments |
| `src/executive/mind.py` | Goal creation, fast‑path, LLM ReAct, Planner integration |
| `src/execution/planner.py` | Creates Tasks from Goals |
| `src/executive/chief_of_staff.py` | Task scheduling, retries, state management |
| `src/core/tools.py` | Unified Capability Registry |
| `src/core/models.py` | Core data models (Goal, Task, Capability, Event, Memory) |
| `src/bridge/synapse.py` | Secure system command execution |
| `src/core/security.py` | Path/command validation, audit |
| `src/llm_engine.py` | Model loading, inference, simulation |
| `src/templates.py` | System prompt and formatting |
| `src/static/index.html` | Full web UI |
| `governance/core_abstractions.md` | Five core abstractions (Goal, Task, Capability, Event, Memory) |
| `CONSTITUTION.md`, `DEVELOPMENT_CONSTITUTION.md`, `EXECUTION_MODEL.md`, `OPERATIONAL_POLICIES.md`, `ARCHITECTURE.md` | Governance documents |

---

## ⚠️ Known Issues / Limitations
- **LLM tool‑call generation** – the `phi-2` model sometimes fails to output `<tool_call>` tags. The prompt has been improved, but this is a model limitation. Workaround: use `execute:` for system commands.
- **Multi‑step planning** – Planner currently creates only one Task per Goal. This will be enhanced in later phases.
- **`psycopg2` not installed** – falls back to SQLite. Works for now; we can install it later for PostgreSQL performance.
- **Budget enforcement** – defined but not yet fully implemented in the Scheduler. Will be expanded in Phase IV/V.

---

## 🧪 Test Commands
```bash
# Greeting
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: c44dcd566e20d12f361464fb83c3734e02c60dbfd8b4f75e9a98f24d63c24918" \
  -d '{"message": "Hello Jarvis"}'

# Research (uses Planner & LLM)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: c44dcd566e20d12f361464fb83c3734e02c60dbfd8b4f75e9a98f24d63c24918" \
  -d '{"message": "Research the future of AI"}'

# execute: system command
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: c44dcd566e20d12f361464fb83c3734e02c60dbfd8b4f75e9a98f24d63c24918" \
  -d '{"message": "execute: echo Hello from Jarvis"}'
cat > CONTEXT.md << 'EOF'
# Jarvis OS – Project Context (Updated 2026-07-14)

## 🧠 Current Status
- **Phases I‑IV complete**. Phase V (Knowledge Platform) is next.
- **API**: Stable, responds to `/api/chat`, `/health`, etc.
- **LLM**: Model loaded, fallback works.
- **Web UI**: Fully functional at `http://localhost:8000`.

## ✅ Completed Phases
- **Phase 0**: Governance (Constitution, Development Constitution, etc.)
- **Phase I**: Architectural Consolidation (Goals, Tasks, Capabilities, Events, Memory)
- **Phase II**: Core Abstractions (Planner, State Machine, Budgets)
- **Phase III**: Execution Platform (Scheduler, Retry Engine)
- **Phase IV**: Capability Platform (Contract, Context, Providers, Registry, Resolver, Execution, Confidence, Health)

## 🧩 Key Components (Current)
- **Executive Mind**: Creates Goals, manages fast‑path, LLM ReAct.
- **Planner**: Creates Tasks from Goals.
- **ChiefOfStaff**: Schedules Tasks to departments.
- **Capability Registry**: Stores manifests, implementations, health, confidence.
- **Capability Resolver**: Scores and selects the best capability.
- **Capability Execution**: Invokes capabilities with retries, timeouts.
- **Infrastructure Health**: Centralised health monitoring.

## 📁 New Directories
- `src/capabilities/` – Capability Platform (contract, context, manifest, registry, resolver, execution, providers, budgets, policies, events, sdk).
- `src/infrastructure/` – Health monitoring.

## 🚀 Next Phase
**Phase V: Knowledge Platform** – enhance memory consolidation, sleep learning, compression.

## 🧪 Test Commands
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: c44dcd566e20d12f361464fb83c3734e02c60dbfd8b4f75e9a98f24d63c24918" \
  -d '{"message": "Hello Jarvis"}'
# Jarvis OS – Project Context (2026-07-14)

## Project Status

- **Phase 0**: Governance (complete)
- **Phase I**: Architectural Consolidation (complete)
- **Phase II**: Core Abstractions (complete)
- **Phase III**: Execution Platform (complete)
- **Phase IV**: Capability Platform (complete)
- **Phase V**: Cognitive Platform (complete – architecture and integration done)

## Working Components

- API is stable and responds to `/api/chat` and `/health`.
- `execute:` commands work.
- **Goals, Tasks, Capabilities, Events, Memory** are fully implemented.
- **Planner** creates Tasks from Goals.
- **ChiefOfStaff** schedules Tasks.
- **Capability Registry** is unified.
- **Cognitive Workspace** tracks current Goal, Task, conversation, and capability results.
- **Experience Recording** stores user input and assistant responses.
- **Recall Engine** and **Cognitive Assistant** are wired in.
- **Sleep Scheduler** runs in the background.
- **Docker** root and containerd data are on the D drive.

## Upcoming Phase

**Phase VI: Executive Intelligence** – improve planning, reasoning, decision quality, and learning. This will build on the Cognitive Platform to make Jarvis smarter.

## Test Commands

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: c44dcd566e20d12f361464fb83c3734e02c60dbfd8b4f75e9a98f24d63c24918" \
  -d '{"message": "Hello Jarvis"}'

cat > CONTEXT.md << 'EOF'
# Jarvis OS – Project Context (2026-07-14)

## 🧠 Project Status
- **Phases 0–VI complete**. System is stable and fully integrated.
- **API**: Stable, responds to `/api/chat`, `/health`, etc.
- **LLM**: Model loaded, fallback works.
- **Web UI**: Fully functional at `http://localhost:8000`.

## ✅ Completed Phases
- **Phase 0**: Governance (Constitution, etc.)
- **Phase I**: Architectural Consolidation (Goals, Tasks, Capabilities, Events, Memory)
- **Phase II**: Core Abstractions (Planner, State Machine, Budgets)
- **Phase III**: Execution Platform (Scheduler, Retry Engine)
- **Phase IV**: Capability Platform (Contract, Context, Providers, Registry, Resolver, Execution, Confidence)
- **Phase V**: Cognitive Platform (Experience, Attention, Workspace, Reflection, Learning, Knowledge, Recall, Assistant, Sleep, Health)
- **Phase VI**: Executive Model (Intent, Goals, Strategy, Planning, Decision, Delegation, Review, Adaptation)

## 🧩 Key Components
- **ExecutiveMind**: Orchestrates Intent → Goals → Strategy → Planning → Decision → Delegation → Execution → Review → Adaptation.
- **CognitiveWorkspace**: Current "mind" of Jarvis (Goal, Task, Conversation, Memories, Capability Results).
- **CapabilityRegistry**: Stores manifests, implementations, health, confidence.
- **CapabilityResolver**: Scores and selects the best capability.
- **PlanningEngine**: Creates Tasks from Goals and Strategy.
- **DecisionEngine**: Commits to a course of action.
- **DelegationManager**: Directs work to Capability and Execution Platforms.
- **AdaptationEngine**: Changes direction when conditions change.
- **KnowledgeStore**: Stores Facts, Procedures, Preferences, Relationships, Skills, Projects, Decisions, Principles.
- **RecallEngine**: Active memory API – provides suggestions, warnings, reminders.
- **CognitiveAssistant**: Subconscious of Jarvis – constant monitoring.

## 🧪 Test Commands
```bash
# Greeting
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: c44dcd566e20d12f361464fb83c3734e02c60dbfd8b4f75e9a98f24d63c24918" \
  -d '{"message": "Hello Jarvis"}'

# Research (uses full pipeline)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: c44dcd566e20d12f361464fb83c3734e02c60dbfd8b4f75e9a98f24d63c24918" \
  -d '{"message": "Research the future of AI"}'

# execute: system command
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: c44dcd566e20d12f361464fb83c3734e02c60dbfd8b4f75e9a98f24d63c24918" \
  -d '{"message": "execute: echo Hello from Jarvis"}'

# Jarvis OS – Project Context (Updated 2026-07-14)

## 🧠 Current Status
- **Phases 0–VI Complete** – architecture and core systems are in place.
- **API**: Stable, responds to `/api/chat`, `/health`, etc.
- **LLM**: Model loaded from `/app/host_models/dolphin-2_6-phi-2.Q4_K_M.gguf`.
- **Web UI**: Fully functional at `http://localhost:8000`.
- **Research**: ✅ `research_specialist` executes Brave Search and returns results.
- **Execute**: ✅ `execute:` commands run via `system_control` and return output.
- **Fast‑path**: Greetings and simple queries are handled directly.

## ✅ Completed Phases
- **Phase 0**: Governance (Constitution, etc.)
- **Phase I**: Architectural Consolidation (Goals, Tasks, Capabilities, Events, Memory)
- **Phase II**: Core Abstractions (Planner, State Machine, Budgets)
- **Phase III**: Execution Platform (Scheduler, Retry Engine)
- **Phase IV**: Capability Platform (Contract, Context, Providers, Registry, Resolver, Execution, Confidence)
- **Phase V**: Cognitive Platform (Experience, Attention, Workspace, Reflection, Learning, Knowledge, Recall)
- **Phase VI**: Executive Model (Intent, Goals, Strategy, Planning, Decision, Delegation, Review, Adaptation)

## 🧩 Key Components
- **ExecutiveMind**: Orchestrates Intent → Goals → Strategy → Planning → Decision → Delegation → Execution → Review → Adaptation.
- **CognitiveWorkspace**: Current "mind" of Jarvis (Goal, Task, Conversation, Memories, Capability Results).
- **CapabilityRegistry**: Stores manifests, implementations, health, confidence.
- **CapabilityResolver**: Scores and selects the best capability.
- **PlanningEngine**: Creates Tasks from Goals and Strategy.
- **DecisionEngine**: Commits to a course of action.
- **DelegationManager**: Directs work to Capability and Execution Platforms.
- **AdaptationEngine**: Changes direction when conditions change.
- **KnowledgeStore**: Stores Facts, Procedures, Preferences, Relationships, Skills, Projects, Decisions, etc.
- **RecallEngine**: Active memory API – provides suggestions, warnings, reminders.
- **CognitiveAssistant**: Subconscious of Jarvis – constant monitoring.

## 🧪 Working Features
- **`research_specialist`** – uses Brave Search API (key must be in `.env` as `BRAVE_API_KEY`).
- **`execute:`** – runs system commands via `system_control` (safe, with security policies).
- **Web UI** – full voice, wake‑word, TTS, streaming, theme toggle.
- **Memory** – embeddings, semantic search, SQLite/Postgres, consolidation pipeline.
- **User management** – registration, login, API key authentication.
- **TTS proxy** – via Edge TTS container.
- **Transcription** – Whisper (tiny) for voice input.
- **Capability registry** – 15 capabilities registered (research, coding, system, weather, calendar, email, etc.).
- **DigitalTwin** – hardware, capabilities, environment stored as MemoryRecords.
- **Event Bus** – standard vocabulary, audit logging.

## 📁 Key Files (Current)
| File | Purpose |
|------|---------|
| `src/api.py` | FastAPI entry point, streaming, auth |
| `src/v2_main.py` | Engine initialisation, registries, departments |
| `src/executive/mind.py` | Goal creation, fast‑path, LLM ReAct, direct execution for research/execute |
| `src/executive/chief_of_staff.py` | Synchronous capability execution (inline, returns result) |
| `src/core/tools.py` | Unified Capability Registry |
| `src/core/models.py` | Core data models (Goal, Task, Capability, Event, Memory) |
| `src/bridge/synapse.py` | Secure system command execution |
| `src/core/security.py` | Path/command validation, audit |
| `src/llm_engine.py` | Model loading, inference |
| `src/templates.py` | System prompt and formatting |
| `src/static/index.html` | Full web UI |
| `governance/core_abstractions.md` | Five core abstractions (Goal, Task, Capability, Event, Memory) |
| `CONSTITUTION.md`, `DEVELOPMENT_CONSTITUTION.md`, `EXECUTION_MODEL.md`, `OPERATIONAL_POLICIES.md`, `ARCHITECTURE.md` | Governance documents |

## ⚠️ Known Issues / Limitations
- **Tool parameter mismatches** – some tools (e.g., `file_manager`, `todo`) receive unexpected parameters from the LLM, causing errors. These are non‑blocking and will be addressed in a future update.
- **Multi‑step planning** – Planner currently creates only one Task per Goal. Will be enhanced in later phases.
- **`psycopg2` not installed** – falls back to SQLite. Works for now; can install later for Postgres.
- **Budget enforcement** – defined but not fully implemented in the Scheduler. Will be expanded in future phases.

## 🚀 Next Phase
**Phase VII: Human Interaction Platform**
- Enhance voice, conversation, personality, UI, notifications, clarification, multi‑modal interaction, session continuity.
- Ensure the user always experiences a single intelligence.

## 🧪 Test Commands
```bash
# Greeting
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: c44dcd566e20d12f361464fb83c3734e02c60dbfd8b4f75e9a98f24d63c24918" \
  -d '{"message": "Hello Jarvis"}'

# Research
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: c44dcd566e20d12f361464fb83c3734e02c60dbfd8b4f75e9a98f24d63c24918" \
  -d '{"message": "Research the future of AI"}'

# Execute system command
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: c44dcd566e20d12f361464fb83c3734e02c60dbfd8b4f75e9a98f24d63c24918" \
  -d '{"message": "execute: echo Hello from Jarvis"}'

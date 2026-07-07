# Phoenix LLM (JARVIS Core)

The specialized, self-improving LLM engine for Phoenix OS (AIOS), designed to be the central cognitive layer for low-resource, AI-native hardware.

## 🧠 Cognitive Architecture

Phoenix LLM (JARVIS) uses a multi-agent orchestration model designed to balance high-level intelligence with the strict 1-2GB RAM constraints of Phoenix OS hardware.

### 1. Multi-Agent Swarm
- **Commander (Personality Layer)**: The primary interface. It handles general chat, maintains the JARVIS persona (calm, capable, professional), and orchestrates tasks by delegating to specialized agents or calling system functions.
- **Research Agent**: Specialized in multi-source information gathering. It integrates **real-time web search** (via DuckDuckGo) and cross-references results with local memory.
- **Coding Agent**: Specialized in code analysis, debugging, and review. It is pre-seeded with knowledge of the Phoenix OS (Rust/no_std) kernel architecture.

### 2. Dual-Tier Memory System
Memory is stored in a local SQLite database (`data/memory.db`) to ensure persistence and low memory overhead:
- **Episodic Memory**: A rolling history of specific interactions, including prompts, responses, and autonomous reflections.
- **Semantic Memory**: A permanent Knowledge Base of distilled facts, rules, and system principles.

## 📈 Self-Improvement Cycle

JARVIS is designed to get smarter with every use without the need for high-resource model retraining.

### Phase 1: Active Reflection
Immediately after an interaction, the **Reflection Module** analyzes the performance and extracts a "Lesson Learned." This lesson is stored in episodic memory and automatically injected into future prompts for immediate "behavioral" improvement.

### Phase 2: Sleep-Learning (Semantic Consolidation)
By selecting **Mode [4]**, the system enters "Sleep-Learning." It iterates through recent episodic reflections and uses the LLM to distill them into permanent, high-density factual statements in the **Semantic Knowledge Base**. This allows the model to "learn" new rules and facts permanently.

## 🔌 System Integration

### Synapse IPC Bridge
The engine includes a `SynapseBridge` that follows the Phoenix OS Synapse specification. It allows the LLM to send structured messages to the kernel (e.g., `SYSTEM_CALL` for stats, file listing, or power management).

### Knowledge Seeding
The `src/seed_knowledge.py` script allows JARVIS to ingest core system documentation directly from the Phoenix OS repository, ensuring it understands the operating system it is running on.

## 🚀 Setup & Usage

1. **Dependencies**: `pip install -r requirements.txt`
2. **Model**: Download a GGUF model (recommended: `phi-2.Q4_K_M.gguf`) into the `models/` directory.
3. **Seed Knowledge**: Run `export PYTHONPATH=$PYTHONPATH:. && python3 src/seed_knowledge.py` to ingest AIOS docs.
4. **Run**: `python3 src/main.py`

### CLI Modes:
- `[0] Commander`: Full JARVIS orchestration (Auto-delegation).
- `[1] Research`: Manual web research and info gathering.
- `[2] Coding`: Manual code analysis and review.
- `[3] Reflect`: Manually trigger reflection on the last interaction.
- `[4] Sleep-Learn`: Trigger semantic consolidation of all recent lessons.

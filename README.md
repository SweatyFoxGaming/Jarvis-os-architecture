# Phoenix LLM (JARVIS Core)

The specialized LLM engine for Phoenix OS (AIOS), focused on research, coding, and continuous self-improvement.

## Features

- **Lightweight**: Optimized for 1-2GB RAM hardware.
- **Self-Improving**: Uses Episodic Memory and a Reflection Loop to learn from every interaction.
- **Specialized**: Built-in agents for Research and Coding.
- **Standalone**: Can run as a companion service to Phoenix OS.
- **Sleep-Learning**: Autonomous fine-tuning pipeline to bake learned lessons into the model weights.

## Architecture

- `src/`: Core logic, memory management, and agents.
- `models/`: Storage for quantized model files (GGUF).
- `data/`: Local memory database and logs.

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Download a GGUF model into `models/`.
3. Run the CLI: `python src/main.py`

### Self-Improvement & Training

Phoenix LLM improves in two ways:
1. **Reflection (Active)**: After each interaction, JARVIS analyzes its performance and stores a "Lesson Learned" in its SQLite database. These lessons are injected into future prompts for immediate improvement.
2. **Sleep-Learning (Consolidation)**: By selecting Mode [4], JARVIS triggers "Semantic Consolidation." This process distills episodic experiences into core factual statements in the Semantic Knowledge Base, allowing for long-term growth and stable intelligence without the heavy resource cost of weight training.

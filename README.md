# Phoenix LLM (JARVIS Core)

The specialized LLM engine for Phoenix OS (AIOS), focused on research, coding, and continuous self-improvement.

## Features

- **Lightweight**: Optimized for 1-2GB RAM hardware.
- **Self-Improving**: Uses Episodic Memory and a Reflection Loop to learn from every interaction.
- **Specialized**: Built-in agents for Research and Coding.
- **Standalone**: Can run as a companion service to Phoenix OS.

## Architecture

- `src/`: Core logic, memory management, and agents.
- `models/`: Storage for quantized model files (GGUF).
- `data/`: Local memory database and logs.

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Download a GGUF model into `models/`.
3. Run the CLI: `python src/main.py`

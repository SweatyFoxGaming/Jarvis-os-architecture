import os
from src.memory import MemorySystem

def seed_knowledge(aios_path="aios_repo"):
    memory = MemorySystem()

    # Define core docs to seed
    docs = {
        "architecture": "SYSTEM_ARCHITECTURE_SPECIFICATION.md",
        "vision": "ULTIMATE_PHOENIX_VISION.md",
        "jarvis": "JARVIS_COGNITIVE_ARCHITECTURE.md",
        "ui": "AMBIENT_UI_SPECIFICATION.md"
    }

    print(f"--- Seeding Phoenix OS Knowledge from {aios_path} ---")

    for category, filename in docs.items():
        filepath = os.path.join(aios_path, "docs", filename)
        if os.path.exists(filepath):
            print(f"Reading {filename}...")
            with open(filepath, 'r') as f:
                content = f.read()
                # Store the whole doc as a major fact for now
                # In a more advanced version, we would chunk this.
                memory.add_fact("aios_doc", category, content)
                print(f"Seeded {category} knowledge.")
        else:
            print(f"Warning: {filename} not found.")

    # Seed core system principles
    memory.add_fact("aios_principle", "resource_limit", "Phoenix OS is designed for hardware with 1-2GB RAM.")
    memory.add_fact("aios_principle", "kernel_language", "The Phoenix OS kernel is written in Rust (no_std).")
    memory.add_fact("aios_principle", "ipc_system", "Synapse is the structured IPC system for Phoenix OS.")

    print("Knowledge seeding complete.")

if __name__ == "__main__":
    seed_knowledge()

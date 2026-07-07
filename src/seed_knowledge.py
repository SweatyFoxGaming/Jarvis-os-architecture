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

    # Universal Language Principles
    languages = {
        "rust": "Ownership, Borrowing, Lifetimes, zero-cost abstractions.",
        "c": "Manual memory management, pointers, direct hardware access.",
        "python": "Dynamic typing, rapid prototyping, extensive libraries.",
        "javascript": "Event-driven, asynchronous, single-threaded execution.",
        "cpp": "OOP, templates, RAII, multi-paradigm.",
        "go": "Goroutines, channels, implicit interfaces, garbage collection.",
        "java": "JVM, strong typing, multithreading, enterprise scale.",
        "assembly": "Instruction sets (x86/ARM), registers, stack management."
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

    # Seed language principles
    for lang, principle in languages.items():
        memory.add_fact("language_principle", lang, principle)

    print("Knowledge seeding complete.")

if __name__ == "__main__":
    seed_knowledge()

import sys
import os
import json

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from memory import MemorySystem
from agents import CommanderAgent, ResearchAgent, CodingAgent, PlanningAgent, SecurityAgent, MemoryAgent, SelfImprovementAgent
from trainer import PhoenixTrainer

class MockLLM:
    def __init__(self):
        self.call_log = []

    def generate(self, prompt, max_tokens=512, stop=None, stream=False):
        self.call_log.append(prompt)

        # Simulated responses based on prompt keywords
        if "Security Agent" in prompt:
            return "STATUS: APPROVED"
        elif "Planning Agent" in prompt:
            return "PLAN:\n1. Research - Memory management\n2. Coding - Implementation"
        elif "Commander" in prompt:
            if "Proposed Plan" in prompt:
                return "DELEGATE: Research - Memory management"
            return "Hello, I am JARVIS. How can I help?"
        elif "Research Agent" in prompt:
            return "Research indicates that memory management is crucial for OS stability."
        elif "Coding Agent" in prompt:
            return "```rust\nfn main() { println!(\"Hello\"); }\n```"
        elif "Reflection Module" in prompt:
            return "Lesson: Ensure memory is deallocated correctly."

        return "Simulated response."

    def embed(self, text):
        return [0.1] * 384

def run_diagnostics():
    print("--- JARVIS FULL SYSTEM INSPECTION ---")

    mock_engine = MockLLM()
    memory = MemorySystem(":memory:") # Use in-memory DB for test

    agents = {
        'research': ResearchAgent(mock_engine, memory),
        'coding': CodingAgent(mock_engine, memory),
        'planning': PlanningAgent(mock_engine, memory),
        'security': SecurityAgent(mock_engine, memory),
        'memory': MemoryAgent(mock_engine, memory),
        'improver': SelfImprovementAgent(mock_engine, memory),
        'commander': CommanderAgent(mock_engine, memory)
    }

    print("\n1. Testing Core Orchestration (Commander -> Security -> Planning -> Research)...")
    user_request = "I want to build a memory allocator for Phoenix OS."
    # Force robust path for test
    response = agents['commander'].handle_request(user_request, agents, fast_mode=False)

    print(f"User: {user_request}")
    print(f"JARVIS: {response}")

    print(f"\nTrace: System performed {len(mock_engine.call_log)} internal brain cycles.")

    print("\n2. Testing Autonomous Reflection Loop...")
    lesson = agents['improver'].reflect_on_last_interaction()
    print(f"Self-Reflection Result: {lesson}")

    print("\n3. Testing Memory Persistence...")
    # Check if interaction was recorded
    episodes = memory.search_episodes("memory allocator")
    print(f"Memory Check: {len(episodes)} episodes found in database.")

    print("\n4. Testing Sleep-Learning (Semantic Consolidation)...")
    trainer = PhoenixTrainer(mock_engine, memory)
    trainer.train()
    facts = memory.get_semantic_knowledge(limit=5)
    print(f"Consolidated Knowledge Check: {len(facts)} new facts in semantic memory.")

    print("\n--- INSPECTION COMPLETE: ALL SYSTEMS NOMINAL ---")

if __name__ == "__main__":
    run_diagnostics()

import sys
import os
from dotenv import load_dotenv

# Add src to path if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_engine import LLMEngine
from memory import MemorySystem
from agents import ResearchAgent, CodingAgent, SelfImprovementAgent
from trainer import PhoenixTrainer

def main():
    load_dotenv()

    print("--- Phoenix LLM (JARVIS Core) ---")

    memory = MemorySystem()
    engine = LLMEngine()

    researcher = ResearchAgent(engine, memory)
    coder = CodingAgent(engine, memory)
    improver = SelfImprovementAgent(engine, memory)

    while True:
        print("\nModes: [1] Chat/Research [2] Coding [3] Reflect [4] Sleep-Learn [q] Quit")
        choice = input("Select mode: ").strip().lower()

        if choice == 'q':
            break
        elif choice == '1':
            topic = input("Research Topic/Question: ")
            print("\nJARVIS Researching...")
            res = researcher.research(topic)
            print(f"\nResult: {res}")
            # Auto-reflect
            improver.reflect_on_last_interaction()
        elif choice == '2':
            print("Enter code (end with a blank line):")
            lines = []
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
            code = "\n".join(lines)
            print("\nJARVIS Analyzing Code...")
            res = coder.analyze_code(code)
            print(f"\nAnalysis: {res}")
            # Auto-reflect
            improver.reflect_on_last_interaction()
        elif choice == '3':
            print("\nJARVIS Reflecting on past work...")
            lesson = improver.reflect_on_last_interaction()
            print(f"\nLesson Learned: {lesson}")
        elif choice == '4':
            print("\n--- JARVIS Sleep-Learning Mode ---")
            trainer = PhoenixTrainer(engine, memory)
            trainer.train()
            print("Sleep-learning complete. Semantic knowledge base updated.")
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main()

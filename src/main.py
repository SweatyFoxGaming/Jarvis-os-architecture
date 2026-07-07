import sys
import os
from dotenv import load_dotenv

# Add src to path if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_engine import LLMEngine
from memory import MemorySystem
from agents import ResearchAgent, CodingAgent, SelfImprovementAgent, CommanderAgent, PlanningAgent, SecurityAgent, MemoryAgent
from trainer import PhoenixTrainer
from profiles import HardwareProfile
from gui import AmbientUI
from PyQt6.QtWidgets import QApplication

def main():
    load_dotenv()

    print("--- Phoenix LLM (JARVIS Core) ---")

    # Default to GUI if run without terminal (like .desktop file)
    is_terminal = sys.stdin.isatty()

    if not is_terminal:
        os.environ["HARDWARE_PROFILE"] = HardwareProfile.LOW
        memory = MemorySystem()
        engine = LLMEngine()

        agents = {
            'research': ResearchAgent(engine, memory),
            'coding': CodingAgent(engine, memory),
            'planning': PlanningAgent(engine, memory),
            'security': SecurityAgent(engine, memory),
            'memory': MemoryAgent(engine, memory),
            'improver': SelfImprovementAgent(engine, memory),
            'commander': CommanderAgent(engine, memory)
        }

        app = QApplication(sys.argv)
        window = AmbientUI(engine, memory, agents)
        window.show()
        sys.exit(app.exec())

    # Terminal Logic
    print("\nSelect Hardware Profile:")
    print("[1] Low-End (1-2GB RAM)")
    print("[2] Performance (4GB+ RAM)")
    p_choice = input("Choice: ").strip()
    os.environ["HARDWARE_PROFILE"] = HardwareProfile.PERFORMANCE if p_choice == '2' else HardwareProfile.LOW

    memory = MemorySystem()
    engine = LLMEngine()

    agents = {
        'research': ResearchAgent(engine, memory),
        'coding': CodingAgent(engine, memory),
        'planning': PlanningAgent(engine, memory),
        'security': SecurityAgent(engine, memory),
        'memory': MemoryAgent(engine, memory),
        'improver': SelfImprovementAgent(engine, memory),
        'commander': CommanderAgent(engine, memory)
    }

    print("\nSelect Interface:")
    print("[1] Desktop GUI (Ambient UI)")
    print("[2] Terminal CLI")
    i_choice = input("Choice: ").strip()

    if i_choice == '1':
        app = QApplication(sys.argv)
        window = AmbientUI(engine, memory, agents)
        window.show()
        sys.exit(app.exec())

    while True:
        print("\nModes: [0] Commander [1] Research [2] Coding [3] Reflect [4] Sleep-Learn [5] Learn-Lang [q] Quit")
        choice = input("Select mode: ").strip().lower()

        if choice == 'q':
            break
        elif choice == '0':
            user_input = input("Request: ")
            print("\nJARVIS Orchestrating...")
            res = agents['commander'].handle_request(user_input, agents)
            print(f"\nResponse: {res}")
            agents['improver'].reflect_on_last_interaction()
        elif choice == '1':
            topic = input("Research Topic/Question: ")
            print("\nJARVIS Researching...")
            res = agents['research'].research(topic)
            print(f"\nResult: {res}")
            # Auto-reflect
            agents['improver'].reflect_on_last_interaction()
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
            res = agents['coding'].analyze_code(code)
            print(f"\nAnalysis: {res}")
            # Auto-reflect
            agents['improver'].reflect_on_last_interaction()
        elif choice == '3':
            print("\nJARVIS Reflecting on past work...")
            lesson = agents['improver'].reflect_on_last_interaction()
            print(f"\nLesson Learned: {lesson}")
        elif choice == '4':
            print("\n--- JARVIS Sleep-Learning Mode ---")
            trainer = PhoenixTrainer(engine, memory)
            trainer.train()
            print("Sleep-learning complete. Semantic knowledge base updated.")
        elif choice == '5':
            lang = input("Which language/framework should JARVIS learn? ").strip()
            print(f"\nJARVIS Researching and learning {lang}...")
            # 1. Research the language
            knowledge = researcher.research(f"Core principles and best practices of {lang} programming language")
            # 2. Add to semantic memory
            embedding = engine.embed(knowledge)
            memory.add_fact("language_principle", lang, knowledge, embedding=embedding)
            print(f"\nJARVIS has integrated {lang} into its core knowledge base.")
        else:
            print("Invalid choice.")

if __name__ == "__main__":
    main()

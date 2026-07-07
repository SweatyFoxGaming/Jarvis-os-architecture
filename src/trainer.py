import os
import json

class PhoenixTrainer:
    def __init__(self, engine, memory):
        self.engine = engine
        self.memory = memory

    def train(self, data_path=None):
        """
        Implements 'Semantic Consolidation'.
        This process analyzes episodic memories and 'distills' them into
        compact Semantic Memory (Facts) that are permanently available.
        """
        print("--- Starting JARVIS Semantic Consolidation (Sleep-Learning) ---")

        # 1. Fetch episodes that haven't been consolidated
        cursor = self.memory.conn.cursor()
        cursor.execute("SELECT id, prompt, response, reflection FROM episodic_memory WHERE reflection IS NOT NULL AND consolidated = 0 LIMIT 10")
        rows = cursor.fetchall()

        if not rows:
            print("No new lessons to consolidate.")
            return

        for id, prompt, response, reflection in rows:
            print(f"Consolidating episode {id}...")

            consolidation_prompt = f"""
            System: You are the Knowledge Architect for Phoenix OS.
            Episode:
            User: {prompt}
            AI: {response}
            Reflection: {reflection}

            Task: Distill the above into a single, permanent factual statement or rule for the Semantic Knowledge Base.
            Format: Fact: [Statement]
            """

            fact = self.engine.generate(consolidation_prompt)
            if "Fact:" in fact:
                fact = fact.split("Fact:")[1].strip()

            # 2. Store as a permanent fact
            embedding = self.engine.embed(fact)
            self.memory.add_fact("consolidated_learning", f"episode_{id}", fact, embedding=embedding)

            # 3. Mark as consolidated
            cursor.execute("UPDATE episodic_memory SET consolidated = 1 WHERE id = ?", (id,))
            self.memory.conn.commit()

        print(f"Consolidated {len(rows)} episodes into permanent semantic knowledge.")

if __name__ == "__main__":
    print("Phoenix Trainer module loaded.")

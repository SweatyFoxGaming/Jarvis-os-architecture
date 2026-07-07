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

        # 4. Automated Memory Garbage Collection (Experience Summarization)
        print("--- Running Memory Garbage Collection ---")
        summary = self.memory.get_semantic_knowledge(limit=1) # Get some context

        # Trigger MemoryAgent logic through engine (simulated here for directness)
        cursor.execute("SELECT prompt, response FROM episodic_memory WHERE consolidated = 1 LIMIT 50")
        old_episodes = cursor.fetchall()

        if len(old_episodes) > 20:
            print(f"Summarizing {len(old_episodes)} old consolidated episodes...")

            summary_prompt = f"""
            System: You are the Memory Archiver for Phoenix OS.
            Episodes to archive: {old_episodes}

            Task: Distill these interactions into 5 core procedural skills or insights for the Semantic Skill Library.
            """
            archive_summary = self.engine.generate(summary_prompt)
            self.memory.add_fact("archived_experience", "historical_summary", archive_summary)
            print("Memory garbage collection complete.")

if __name__ == "__main__":
    print("Phoenix Trainer module loaded.")

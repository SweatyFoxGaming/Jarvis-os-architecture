from .memory import MemorySystem
from .llm_engine import LLMEngine

class BaseAgent:
    def __init__(self, engine: LLMEngine, memory: MemorySystem):
        self.engine = engine
        self.memory = memory

class ResearchAgent(BaseAgent):
    def research(self, topic):
        # 1. Retrieve existing knowledge and lessons
        existing = self.memory.search_episodes(topic)
        lessons = self.memory.get_recent_lessons(limit=5)
        knowledge = self.memory.get_semantic_knowledge(limit=10)

        context = "\n".join([f"Previous: {e[0]} -> {e[1]}" for e in existing])
        lessons_context = "\n".join([f"Lesson Learned: {l}" for l in lessons])
        knowledge_context = "\n".join([f"Fact: {k}" for k in knowledge])

        prompt = f"""
        System: You are the Research Agent for Phoenix OS.
        Core Knowledge Base:
        {knowledge_context}

        Context of previous research: {context}
        General lessons learned: {lessons_context}
        Topic: {topic}
        Task: Provide a detailed research report on the topic above. Be factual and concise.
        """
        response = self.engine.generate(prompt)
        self.memory.add_episode(f"Research: {topic}", response)
        return response

class CodingAgent(BaseAgent):
    def analyze_code(self, code_snippet, task="Review"):
        lessons = self.memory.get_recent_lessons(limit=5)
        knowledge = self.memory.get_semantic_knowledge(limit=10)

        context = "\n".join([f"Lesson Learned: {l}" for l in lessons])
        knowledge_context = "\n".join([f"Fact: {k}" for k in knowledge])

        prompt = f"""
        System: You are the Coding Agent for Phoenix OS.
        Core Knowledge Base:
        {knowledge_context}

        Lessons from experience: {context}
        Code:
        {code_snippet}

        Task: {task} this code. Suggest improvements if necessary, focusing on efficiency and readability.
        """
        response = self.engine.generate(prompt)
        self.memory.add_episode(f"Code Analysis ({task})", response)
        return response

class SelfImprovementAgent(BaseAgent):
    def reflect_on_last_interaction(self):
        # Get last episode
        cursor = self.memory.conn.cursor()
        cursor.execute("SELECT id, prompt, response FROM episodic_memory ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()

        if not row:
            return "No interactions to reflect on."

        id, prompt, response = row

        reflection_prompt = f"""
        System: You are the Reflection Module for Phoenix OS.
        Previous Interaction:
        Prompt: {prompt}
        Response: {response}

        Task: Critically analyze the response above. What could have been better? Provide a single "Lesson Learned" for the future.
        """
        lesson = self.engine.generate(reflection_prompt)

        cursor.execute("UPDATE episodic_memory SET reflection = ? WHERE id = ?", (lesson, id))
        self.memory.conn.commit()
        return lesson

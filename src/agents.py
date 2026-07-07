from .memory import MemorySystem
from .llm_engine import LLMEngine
from .synapse_bridge import SynapseBridge

class BaseAgent:
    def __init__(self, engine: LLMEngine, memory: MemorySystem):
        self.engine = engine
        self.memory = memory

from duckduckgo_search import DDGS

class ResearchAgent(BaseAgent):
    def _web_search(self, query):
        print(f"Searching web for: {query}...")
        try:
            with DDGS() as ddgs:
                results = [r for r in ddgs.text(query, max_results=3)]
                return "\n".join([f"{r['title']}: {r['body']}" for r in results])
        except Exception as e:
            return f"Web search failed: {e}"

    def research(self, topic):
        # 1. Retrieve existing knowledge and lessons
        web_data = self._web_search(topic)
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

        Real-time Web Search Results:
        {web_data}

        Context of previous research: {context}
        General lessons learned: {lessons_context}
        Topic: {topic}
        Task: Provide a detailed research report on the topic above. Be factual and concise. Incorporate web search results where relevant.
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

class CommanderAgent(BaseAgent):
    def __init__(self, engine, memory):
        super().__init__(engine, memory)
        self.bridge = SynapseBridge()

    def handle_request(self, user_input, agents):
        knowledge = self.memory.get_semantic_knowledge(limit=10)
        knowledge_context = "\n".join([f"Fact: {k}" for k in knowledge])

        prompt = f"""
        System: You are the Commander of Phoenix OS (JARVIS Personality Layer).
        You are professional, calm, and highly capable.
        Core Knowledge:
        {knowledge_context}

        User Request: {user_input}

        Task: Analyze the user request. Decide if you should:
        1. Handle it yourself (general chat).
        2. Delegate to an agent: "DELEGATE: [Agent Name] - [Instructions]"
        3. Execute a system command: "SYSTEM: [Command] - [Params]"

        System commands available: GET_STATS, LIST_FILES, REBOOT.
        """
        response = self.engine.generate(prompt)

        if "DELEGATE: Research" in response:
            topic = response.split("-")[1].strip()
            return agents['research'].research(topic)
        elif "DELEGATE: Coding" in response:
            snippet = response.split("-")[1].strip()
            return agents['coding'].analyze_code(snippet)
        elif "SYSTEM:" in response:
            cmd_part = response.split("SYSTEM:")[1].strip()
            cmd = cmd_part.split("-")[0].strip()
            params = cmd_part.split("-")[1].strip() if "-" in cmd_part else None
            return self.bridge.system_call(cmd, params)

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

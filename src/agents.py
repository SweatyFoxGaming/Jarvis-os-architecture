try:
    from .memory import MemorySystem
    from .llm_engine import LLMEngine
    from .synapse_bridge import SynapseBridge
except ImportError:
    from memory import MemorySystem
    from llm_engine import LLMEngine
    from synapse_bridge import SynapseBridge

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

    def research(self, topic, memory_agent=None):
        # 1. Use MemoryAgent for hierarchical context if available
        if memory_agent:
            context_block = memory_agent.retrieve_context(topic)
        else:
            existing = self.memory.search_episodes(topic)
            lessons = self.memory.get_recent_lessons(limit=5)
            knowledge = self.memory.get_semantic_knowledge(limit=10)
            context_block = f"Previous: {existing}\nLessons: {lessons}\nKnowledge: {knowledge}"

        # 2. Real-time web data
        web_data = self._web_search(topic)

        prompt = f"""
        System: You are the Research Agent for Phoenix OS.
        Contextual Background:
        {context_block}

        Real-time Web Search Results:
        {web_data}

        Topic: {topic}
        Task: Provide a detailed research report on the topic above. Be factual and concise.
        """
        response = self.engine.generate(prompt)
        self.memory.add_episode(f"Research: {topic}", response)
        return response

class CodingAgent(BaseAgent):
    def analyze_code(self, code_snippet, task="Review", memory_agent=None):
        if memory_agent:
            context_block = memory_agent.retrieve_context(code_snippet)
        else:
            lessons = self.memory.get_recent_lessons(limit=5)
            knowledge = self.memory.get_semantic_knowledge(limit=10)
            context_block = f"Lessons: {lessons}\nKnowledge: {knowledge}"

        prompt = f"""
        System: You are the Coding Agent for Phoenix OS.
        Contextual Background:
        {context_block}

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
        # 1. Security Audit
        audit = agents['security'].audit_request(user_input)
        if "STATUS: DENIED" in audit:
            return audit

        # 2. Planning (for complex requests)
        plan = agents['planning'].create_plan(user_input)
        print(f"\n[JARVIS Plan]:\n{plan}\n")

        # 3. Execution (Simulated multi-step for now)
        knowledge = self.memory.get_semantic_knowledge(limit=10)
        knowledge_context = "\n".join([f"Fact: {k}" for k in knowledge])

        prompt = f"""
        System: You are the Commander of Phoenix OS.
        Core Knowledge:
        {knowledge_context}

        User Request: {user_input}
        Proposed Plan: {plan}

        Task: Execute the plan. If delegation is needed, use DELEGATE: [Agent] or SYSTEM: [Command].
        """
        response = self.engine.generate(prompt)

        if "DELEGATE: Research" in response:
            parts = response.split("-")
            topic = parts[1].strip() if len(parts) > 1 else user_input
            return agents['research'].research(topic, memory_agent=agents['memory'])
        elif "DELEGATE: Coding" in response:
            parts = response.split("-")
            snippet = parts[1].strip() if len(parts) > 1 else user_input
            return agents['coding'].analyze_code(snippet, memory_agent=agents['memory'])
        elif "SYSTEM:" in response:
            cmd_part = response.split("SYSTEM:")[1].strip()
            cmd = cmd_part.split("-")[0].strip()
            params = cmd_part.split("-")[1].strip() if "-" in cmd_part else None
            return self.bridge.system_call(cmd, params)

        self.memory.add_episode(user_input, response)
        return response

class PlanningAgent(BaseAgent):
    def create_plan(self, user_request):
        prompt = f"""
        System: You are the Planning Agent for Phoenix OS.
        User Request: {user_request}

        Task: Break this request down into a structured, multi-step action plan.
        Each step should specify which agent (Research, Coding, System) is needed.

        Format:
        PLAN:
        1. [Agent] - [Task Description]
        2. [Agent] - [Task Description]
        ...
        """
        plan = self.engine.generate(prompt)
        return plan

class SecurityAgent(BaseAgent):
    def audit_request(self, request, context=""):
        prompt = f"""
        System: You are the Security Agent for Phoenix OS.
        You operate on a Capability-Based Security model.

        Request: {request}
        Context: {context}

        Task: Analyze the request for potential security risks, unauthorized access, or harmful commands.
        Respond with "STATUS: APPROVED" or "STATUS: DENIED - [Reason]".
        """
        audit = self.engine.generate(prompt)
        return audit

class MemoryAgent(BaseAgent):
    def retrieve_context(self, query):
        """
        Hierarchical retrieval:
        1. Recent episodic memory (last 5 interactions)
        2. Relevant semantic facts (keyword search)
        3. High-level distilled knowledge
        """
        recent = self.memory.search_episodes(query, limit=3)
        knowledge = self.memory.get_semantic_knowledge(limit=10)

        context = "--- Recent Interactions ---\n"
        context += "\n".join([f"Q: {r[0]}\nA: {r[1]}" for r in recent])
        context += "\n\n--- Core Knowledge ---\n"
        context += "\n".join([f"Fact: {k}" for k in knowledge])

        return context

    def summarize_experience(self):
        """
        Summarizes old memories to free up space/context while retaining key facts.
        """
        # Fetch 20 oldest unconsolidated episodes
        cursor = self.memory.conn.cursor()
        cursor.execute("SELECT prompt, response FROM episodic_memory WHERE consolidated = 0 LIMIT 20")
        rows = cursor.fetchall()

        if len(rows) < 10:
            return "Not enough experience to summarize yet."

        summary_prompt = f"""
        System: You are the Memory Agent for Phoenix OS.
        Experiences:
        {" ".join([f"({r[0]}, {r[1]})" for r in rows])}

        Task: Summarize these experiences into 3 core insights for the long-term semantic memory.
        """
        summary = self.engine.generate(summary_prompt)
        self.memory.add_fact("experience_summary", "auto_summary", summary)
        return summary

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

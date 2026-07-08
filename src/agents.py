try:
    from .memory import MemorySystem
    from .llm_engine import LLMEngine
    from .synapse_bridge import SynapseBridge
    from .profiles import HardwareProfile
except ImportError:
    from memory import MemorySystem
    from llm_engine import LLMEngine
    from synapse_bridge import SynapseBridge
    from profiles import HardwareProfile

class BaseAgent:
    def __init__(self, engine: LLMEngine, memory: MemorySystem):
        self.engine = engine
        self.memory = memory

import os
import requests

class ResearchAgent(BaseAgent):
    def _web_search(self, query):
        print(f"Searching Brave for: {query}...")
        api_key = os.getenv("BRAVE_API_KEY")
        if not api_key:
            return "Brave API key not found in .env"

        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key
        }
        params = {"q": query, "count": 3}

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            results = data.get("web", {}).get("results", [])
            return "\n".join([f"{r['title']}: {r['description']}" for r in results])
        except Exception as e:
            return f"Brave search failed: {e}"

    def research(self, topic, memory_agent=None, stream=False):
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
        System: You are the Research Agent for JARVIS.
        While your core identity is rooted in Phoenix OS, you are a general-purpose research specialist.

        Contextual Background:
        {context_block}

        Real-time Web Search Results:
        {web_data}

        Topic: {topic}
        Task: Provide a detailed research report on the topic above. Be factual and concise.
        """
        if stream:
            return self.engine.generate(prompt, stream=True)
        else:
            response = self.engine.generate(prompt)
            self.memory.add_episode(f"Research: {topic}", response)
            return response

class CodingAgent(BaseAgent):
    def analyze_code(self, code_snippet, task="Review", memory_agent=None, stream=False):
        if memory_agent:
            context_block = memory_agent.retrieve_context(code_snippet)
        else:
            lessons = self.memory.get_recent_lessons(limit=5)
            knowledge = self.memory.get_semantic_knowledge(limit=10)
            context_block = f"Lessons: {lessons}\nKnowledge: {knowledge}"

        # Pass 1: Generation/Initial Analysis
        prompt = f"""
        System: You are the Universal Multi-lingual Coding Specialist for JARVIS.

        Contextual Background:
        {context_block}

        Code:
        {code_snippet}

        Task: {task} this code. Provide idiomatic improvements, bug fixes, or architectural suggestions.
        """
        initial_response = self.engine.generate(prompt)

        # Pass 2: Proactive Self-Correction
        print("[CodingAgent] Performing proactive self-correction...")
        correction_prompt = f"""
        System: You are the Lead Code Reviewer for Phoenix OS.
        Initial Proposal:
        {initial_response}

        Task: Critically review your own proposal above.
        1. Are there any syntax errors?
        2. Is the memory management correct (especially for Rust/C)?
        3. Can it be more idiomatic?

        Provide the final, polished code and explanation.
        """
        if stream:
            return self.engine.generate(correction_prompt, stream=True)
        else:
            final_response = self.engine.generate(correction_prompt)
            self.memory.add_episode(f"Code Analysis ({task})", final_response)
            return final_response

class CommanderAgent(BaseAgent):
    def __init__(self, engine, memory):
        super().__init__(engine, memory)
        self.bridge = SynapseBridge()

    def _generate_tags(self, text):
        prompt = f"System: Generate 3 comma-separated keywords for the following: {text}"
        return self.engine.generate(prompt, max_tokens=20)

    def _generate_embedding(self, text):
        settings = HardwareProfile.get_settings()
        if settings.get("semantic_search"):
            return self.engine.embed(text)
        return None

    def _detect_unknown_language(self, text):
        # List of languages JARVIS "knows" (could be expanded by checking DB)
        known = ["rust", "python", "c", "cpp", "javascript", "go", "java", "assembly", "bash", "shell"]
        words = set(text.lower().replace("?", "").replace(".", "").replace(",", "").split())

        # Check if any known language is in the query - if so, we don't need to onboard
        if any(k in words for k in known):
            return None

        # Common tech keywords that suggest a new language request
        potential = ["zig", "mojo", "swift", "kotlin", "elixir", "haskell", "lua", "dart", "ruby", "clojure"]
        for p in potential:
            if p in words: return p
        return None

    def handle_request(self, user_input, agents, fast_mode=True, stream=False):
        # 0. Fast-exit for simple greetings to reduce latency
        greetings = ["hi", "hello", "hey", "jarvis"]
        if user_input.lower() in greetings:
            msg = "Hello. How can I assist you with Phoenix OS today?"
            if stream:
                def _gen():
                    for t in msg.split(): yield t + " "
                return _gen()
            return msg

        # 1. Autonomous Language Onboarding
        unknown = self._detect_unknown_language(user_input)
        if unknown:
            print(f"[JARVIS] New language detected: {unknown}. Autonomous onboarding triggered.")
            research_data = agents['research'].research(f"Core principles and best practices of {unknown} programming language")
            embedding = self.engine.embed(research_data)
            self.memory.add_fact("language_principle", unknown, research_data, embedding=embedding)

        # 1. Fast-Path: Combined Audit, Planning, and Decision
        if fast_mode:
            print("[JARVIS] Executing fast-path orchestration...")
            prompt = f"""
            System: You are the Commander (JARVIS Personality Layer).
            You are a highly capable AI assistant. While you are the 'brain' of Phoenix OS,
            you are fully capable of assisting with any general user request.
            Request: {user_input}

            Task:
            1. Audit: Is this safe?
            2. Plan: What are the steps?
            3. Decision: Should I handle it or delegate?

            Format:
            AUDIT: [APPROVED/DENIED]
            PLAN: [Steps]
            ACTION: [DELEGATE: Agent/SYSTEM: Cmd/CHAT: Msg]
            """
            fast_res = self.engine.generate(prompt)

            if "AUDIT: DENIED" in fast_res:
                return "Security Audit Denied."

            if "ACTION: DELEGATE" in fast_res or "ACTION: SYSTEM" in fast_res:
                # Extract action and continue execution
                response = fast_res.split("ACTION:")[1].strip()
            else:
                response = fast_res
        else:
            # Original robust multi-step path
            audit = agents['security'].audit_request(user_input)
            if "STATUS: DENIED" in audit:
                return audit
            plan = agents['planning'].create_plan(user_input)
            print(f"\n[JARVIS Plan]:\n{plan}\n")

            # 3. Execution (Simulated multi-step for now)
            self.memory.add_episode(user_input, "Multi-step plan initiated.")
            knowledge = self.memory.get_semantic_knowledge(limit=10)
            knowledge_context = "\n".join([f"Fact: {k}" for k in knowledge])

            prompt = f"""
            System: You are the Commander (JARVIS Personality Layer).
            You are a highly capable AI assistant. While you are the 'brain' of Phoenix OS,
            you are fully capable of assisting with any general user request.
            Core Knowledge:
            {knowledge_context}

            User Request: {user_input}
            Proposed Plan: {plan}

            Task: Execute the plan. If delegation is needed, use DELEGATE: [Agent] or SYSTEM: [Command].
            """
            response = self.engine.generate(prompt)

        if "DELEGATE: Research" in response or "Research" in response:
            parts = response.split("-")
            topic = parts[1].strip() if len(parts) > 1 else user_input
            return agents['research'].research(topic, memory_agent=agents['memory'], stream=stream)
        elif "DELEGATE: Coding" in response or "Coding" in response:
            parts = response.split("-")
            snippet = parts[1].strip() if len(parts) > 1 else user_input
            return agents['coding'].analyze_code(snippet, memory_agent=agents['memory'], stream=stream)
        elif "SYSTEM:" in response:
            cmd_part = response.split("SYSTEM:")[1].strip()
            cmd = cmd_part.split("-")[0].strip()
            params = cmd_part.split("-")[1].strip() if "-" in cmd_part else None
            return self.bridge.system_call(cmd, params)

        tags = self._generate_tags(user_input + " " + response)
        embedding = self._generate_embedding(user_input + " " + response)
        # Strip internal protocol markers if they leaked into chat
        markers = ["ACTION:", "CHAT:", "PLAN:", "AUDIT: APPROVED", "AUDIT:"]
        if isinstance(response, str):
            for m in markers:
                if m in response:
                    response = response.split(m)[-1].strip()

        # For streaming, we wrap the generator to record the full response at the end
        if stream and not isinstance(response, str):
            def _stream_recorder():
                full_text = ""
                for token in response:
                    full_text += token
                    yield token
                self.memory.add_episode(user_input, full_text)
            return _stream_recorder()

        if not stream:
            self.memory.add_episode(user_input, str(response))
        return response

class PlanningAgent(BaseAgent):
    def create_plan(self, user_request):
        prompt = f"""
        System: You are the Strategic Planning Agent for JARVIS.
        User Request: {user_request}

        Task: Break this request down into a structured, multi-step action plan.
        You can plan for any type of task (OS-related or general).
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
        2. Relevant semantic facts (keyword or vector search)
        3. High-level distilled knowledge
        """
        settings = HardwareProfile.get_settings()

        knowledge = self.memory.get_semantic_knowledge(limit=5) # Always get most recent facts

        if settings.get("semantic_search") and query:
            print("[Memory] Performing vector semantic search...")
            embedding = self.engine.embed(query)
            if embedding:
                semantic_knowledge = self.memory.semantic_search(embedding, limit=5)
                # Merge and deduplicate
                knowledge = list(set(knowledge + semantic_knowledge))

        recent = self.memory.search_episodes(query, limit=3)

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

    def compact_context(self, interactions):
        """
        Takes a list of interactions and compresses them into a single summary block
        to save tokens in the context window.
        """
        if not interactions:
            return ""

        compaction_prompt = f"""
        System: You are the Context Compactor for Phoenix OS.
        Interactions:
        {interactions}

        Task: Provide a 2-sentence summary of the conversation history above that preserves all key technical details.
        """
        return self.engine.generate(compaction_prompt)

class SelfImprovementAgent(BaseAgent):
    def optimize_system_prompts(self):
        """
        Meta-learning: Analyzes consolidated lessons and suggests
        improvements to the system's own prompts.
        """
        lessons = self.memory.get_recent_lessons(limit=10)
        if not lessons:
            return "No lessons to optimize from."

        optimization_prompt = f"""
        System: You are the Meta-Learning Optimizer for Phoenix OS.
        Recent Lessons:
        {lessons}

        Task: Based on these lessons, suggest one improvement to the Commander's system prompt to prevent future errors.
        """
        suggestion = self.engine.generate(optimization_prompt)
        self.memory.add_fact("meta_optimization", "prompt_suggestion", suggestion)
        return suggestion

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

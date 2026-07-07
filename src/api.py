import os
import sys
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import psutil

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm_engine import LLMEngine
from memory import MemorySystem
from agents import ResearchAgent, CodingAgent, SelfImprovementAgent, CommanderAgent, PlanningAgent, SecurityAgent, MemoryAgent
from profiles import HardwareProfile

app = FastAPI(title="JARVIS Cognitive API")

# Global instances (Lazy load or init on start)
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

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat(request: ChatRequest):
    response = agents['commander'].handle_request(request.message, agents)
    agents['improver'].reflect_on_last_interaction()
    return {"response": response}

@app.get("/api/status")
async def get_status():
    return {
        "cpu": psutil.cpu_percent(),
        "ram_available": psutil.virtual_memory().available // (1024*1024),
        "disk": psutil.disk_usage('/').percent,
        "os": "Ubuntu (Linux Host)",
        "memory_facts": len(memory.get_semantic_knowledge(limit=100))
    }

@app.post("/api/learn")
async def learn_lang(request: ChatRequest):
    knowledge = agents['research'].research(f"Core principles and best practices of {request.message} programming language")
    embedding = engine.embed(knowledge)
    memory.add_fact("language_principle", request.message, knowledge, embedding=embedding)
    return {"status": "success", "language": request.message}

# Serve static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

import os
import sys
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
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
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    # Determine if streaming is requested
    stream = agents['commander'].handle_request(request.message, agents, stream=True)

    async def event_generator():
        try:
            for token in stream:
                yield f"data: {token}\n\n"
            yield "data: [DONE]\n\n"
        finally:
            # Trigger reflection in the background after stream closes
            background_tasks.add_task(agents['improver'].reflect_on_last_interaction)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# OpenAI Compatibility Layer (with common aliases)
@app.get("/v1/models")
@app.get("/api/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "jarvis-cognitive-engine",
                "object": "model",
                "created": 1677610602,
                "owned_by": "phoenix-os"
            }
        ]
    }

@app.post("/v1/chat/completions")
@app.post("/api/v1/chat/completions")
async def chat_completions(request: Request):
    data = await request.json()
    messages = data.get("messages", [])
    user_msg = messages[-1]["content"] if messages else ""
    stream_requested = data.get("stream", False)

    if stream_requested:
        stream = agents['commander'].handle_request(user_msg, agents, stream=True)
        async def event_generator():
            import time
            import json
            for token in stream:
                chunk = {
                    "id": "chatcmpl-stream",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "jarvis-cognitive-engine",
                    "choices": [{"index": 0, "delta": {"content": token}, "finish_reason": None}]
                }
                yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"
            agents['improver'].reflect_on_last_interaction()
        return StreamingResponse(event_generator(), media_type="text/event-stream")

    response = agents['commander'].handle_request(user_msg, agents)
    agents['improver'].reflect_on_last_interaction()

    import time
    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "jarvis-cognitive-engine",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": response,
            },
            "finish_reason": "stop"
        }]
    }

@app.get("/props")
@app.get("/health")
async def props():
    return {"status": "up", "version": "1.5.0", "name": "JARVIS"}

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
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

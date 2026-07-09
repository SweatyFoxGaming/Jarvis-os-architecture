import os
import sys
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import anyio
import psutil
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.v2_main import CognitiveEngineV3

app = FastAPI(title="JARVIS Cognitive API V3")

# Allow browser cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instance
engine_v3 = CognitiveEngineV3()

class ChatRequest(BaseModel):
    message: str

@app.post("/api/chat")
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    async def event_generator():
        try:
            # In V3, we process request via Executive Mind and then dispatch
            def get_res():
                res = engine_v3.run(request.message)
                results = engine_v3.dispatch_tasks()

                final_output = f"[Executive Mind]: {res}\n\n"
                if results:
                    for task_id, output in results.items():
                        # Extract the main content from specialist output
                        content = output.get("report") or output.get("code") or str(output)
                        final_output += f"[Specialist]: {content}\n"
                return final_output

            result = await anyio.to_thread.run_sync(get_res)

            yield f"data: {result}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"
        finally:
            # V2 improvement logic
            pass

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

    response = engine_v3.run(user_msg)
    engine_v3.dispatch_tasks()

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
        "v2_active": True
    }

@app.post("/api/learn")
async def learn_lang(request: ChatRequest):
    response = engine_v3.run(f"Learn everything about {request.message}")
    engine_v3.dispatch_tasks()
    return {"status": "success", "language": request.message, "response": response}

# Serve static files
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

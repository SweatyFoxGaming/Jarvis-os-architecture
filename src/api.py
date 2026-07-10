"""
JARVIS Cognitive API V3 – FastAPI server with streaming chat,
OpenAI-compatible endpoints, system status, and static file serving.

Now with logging, secure config integration, error handling,
and graceful shutdown.
"""

import os
import sys
import logging
import time
import json
import traceback
from typing import Optional
from contextlib import asynccontextmanager

# ---------- PATH SETUP ----------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------- LOGGING ----------
logger = logging.getLogger(__name__)

# ---------- FASTAPI IMPORTS ----------
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import anyio
import psutil

# ---------- SECURE CONFIG ----------
try:
    from config.secure_config import AppConfig
    AppConfig.load()
    logger.info("[API] Secure configuration loaded.")
except Exception as e:
    logger.warning(f"[API] Secure config not available: {e}")

# ---------- ENGINE IMPORTS ----------
from src.v2_main import CognitiveEngineV3
from src.core.event_bus import EventBus
from src.core.digital_twin import DigitalTwin
from src.memory.tiered_memory import HierarchicalMemory
from src.core.security import SecurityModule

# ---------- GLOBALS ----------
_engine: Optional[CognitiveEngineV3] = None
_secure_memory = None


# ---------- LIFESPAN MANAGER ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown.
    Initializes the engine and cleans up on exit.
    """
    global _engine, _secure_memory

    # Startup
    logger.info("[API] Starting up...")

    try:
        # Build secure components
        try:
            from memory.secure_store import SecureMemoryStore
            _secure_memory = SecureMemoryStore(os.path.join(PROJECT_ROOT, "data", "memory.db"))
            logger.info("[API] SecureMemoryStore initialized.")
        except ImportError:
            logger.warning("[API] SecureMemoryStore not available.")
            _secure_memory = None

        # Create engine with secure components (if the engine accepts them)
        _engine = CognitiveEngineV3()
        if _secure_memory and hasattr(_engine, 'set_secure_memory'):
            _engine.set_secure_memory(_secure_memory)
            logger.info("[API] Secure memory attached to engine.")

        logger.info("[API] Cognitive Engine V3 initialized successfully.")
    except Exception as e:
        logger.error(f"[API] Failed to initialize engine: {e}", exc_info=True)
        # We'll still start, but endpoints will return errors.

    yield  # Server runs here

    # Shutdown
    logger.info("[API] Shutting down...")
    if _engine and hasattr(_engine, 'shutdown'):
        try:
            _engine.shutdown()
            logger.info("[API] Engine shut down.")
        except Exception as e:
            logger.warning(f"[API] Engine shutdown error: {e}")
    if _secure_memory and hasattr(_secure_memory, 'close'):
        try:
            _secure_memory.close()
            logger.info("[API] Secure memory closed.")
        except Exception as e:
            logger.warning(f"[API] Secure memory close error: {e}")


# ---------- APP CREATION ----------
app = FastAPI(
    title="JARVIS Cognitive API V3",
    version="1.5.0",
    description="Phoenix Intelligence Platform - Cognitive Engine API",
    lifespan=lifespan,
)

# ---------- CORS MIDDLEWARE ----------
# In production, restrict origins to specific domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- PYDANTIC MODELS ----------
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)


class ChatCompletionRequest(BaseModel):
    messages: list[dict] = Field(default_factory=list)
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 512
    stream: Optional[bool] = False


# ---------- ENDPOINTS ----------
@app.get("/health")
@app.get("/props")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "up",
        "version": "1.5.0",
        "name": "JARVIS",
        "engine_ready": _engine is not None,
    }


@app.get("/api/status")
async def get_status():
    """System status endpoint."""
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return {
            "cpu": cpu,
            "ram_available_mb": mem.available // (1024 * 1024),
            "ram_total_mb": mem.total // (1024 * 1024),
            "disk": disk.percent,
            "os": os.uname().sysname if hasattr(os, 'uname') else "Unknown",
            "engine_ready": _engine is not None,
        }
    except Exception as e:
        logger.error(f"[API] Status error: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@app.post("/api/chat")
async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
    """
    Streaming chat endpoint using Server‑Sent Events (SSE).
    Returns a stream of responses from the cognitive engine.
    """
    if _engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    async def event_generator():
        try:
            # Run the engine in a thread to avoid blocking the event loop
            def get_response():
                try:
                    res = _engine.run(request.message)
                    results = _engine.dispatch_tasks()
                    final_output = f"[Executive Mind]: {res}\n\n"
                    if results:
                        for task_id, output in results.items():
                            content = output.get("report") or output.get("code") or str(output)
                            final_output += f"[Specialist]: {content}\n"
                    return final_output
                except Exception as e:
                    logger.error(f"[API] Engine error in chat: {e}", exc_info=True)
                    return f"Error: {str(e)}"

            result = await anyio.to_thread.run_sync(get_response)
            yield f"data: {result}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"[API] Streaming error: {e}", exc_info=True)
            yield f"data: Error: {str(e)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # For nginx
        },
    )


# ---------- OPENAI COMPATIBILITY ENDPOINTS ----------
@app.get("/v1/models")
@app.get("/api/v1/models")
async def list_models():
    """List available models (OpenAI‑compatible)."""
    return {
        "object": "list",
        "data": [
            {
                "id": "jarvis-cognitive-engine",
                "object": "model",
                "created": 1677610602,
                "owned_by": "phoenix-os",
            }
        ],
    }


@app.post("/v1/chat/completions")
@app.post("/api/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI‑compatible chat completion endpoint (non‑streaming).
    """
    if _engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    try:
        # Extract last user message
        user_msg = ""
        for msg in reversed(request.messages):
            if msg.get("role") == "user":
                user_msg = msg.get("content", "")
                break
        if not user_msg:
            raise HTTPException(status_code=400, detail="No user message found")

        # Process through engine
        def process():
            try:
                response = _engine.run(user_msg)
                _engine.dispatch_tasks()
                return response
            except Exception as e:
                logger.error(f"[API] Engine error in completions: {e}", exc_info=True)
                raise

        response = await anyio.to_thread.run_sync(process)

        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "jarvis-cognitive-engine",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": response},
                    "finish_reason": "stop",
                }
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Chat completions error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/learn")
async def learn_lang(request: ChatRequest):
    """
    Endpoint for learning about a topic.
    """
    if _engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    try:
        prompt = f"Learn everything about {request.message}"
        response = _engine.run(prompt)
        _engine.dispatch_tasks()
        return {"status": "success", "language": request.message, "response": response}
    except Exception as e:
        logger.error(f"[API] Learn error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/shutdown")
async def shutdown():
    """
    Gracefully shut down the server (admin only – add auth in production).
    """
    logger.info("[API] Shutdown requested.")
    # Trigger lifespan shutdown by raising a signal or using a flag
    # For now, we'll just return and let the process exit.
    # In a real deployment, you'd need to send a signal to the process.
    return {"status": "shutdown initiated"}


# ---------- STATIC FILES ----------
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    logger.warning(f"[API] Static directory not found: {static_dir}")


# ---------- ERROR HANDLERS ----------
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all error handler to return JSON instead of HTML."""
    logger.error(f"[API] Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": str(exc)},
    )


# ---------- MAIN ENTRY ----------
if __name__ == "__main__":
    import uvicorn
    logger.info("[API] Starting server with uvicorn...")
    uvicorn.run(
        "src.api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Set True only for development
        workers=1,     # Increase for production
        log_level="info",
    )

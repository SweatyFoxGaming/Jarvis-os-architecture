"""
JARVIS Cognitive API V3 – Full API with user management.
"""

import os
import sys
import logging
import time
import json
import asyncio
from typing import Optional
from contextlib import asynccontextmanager
from collections import defaultdict

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from fastapi import FastAPI, Request, HTTPException, Depends, Security, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
import anyio
import psutil

from config.secure_config import AppConfig
AppConfig.load()

from src.v2_main import CognitiveEngineV3
from src.memory.knowledge_librarian import KnowledgeLibrarian
from src.core.user_manager import UserManager

# Globals
_engine = None
_secure_memory = None
_librarian = None
_user_manager = None
_consolidation_task = None

# API Key Auth
ADMIN_API_KEY = getattr(AppConfig, 'INTERNAL_API_KEY', None) or os.getenv("INTERNAL_API_KEY", "admin")
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

def validate_api_key(api_key: str = Security(api_key_header)) -> str:
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API Key")
    # Check if admin key
    if api_key == ADMIN_API_KEY:
        return "admin"  # Special user_id for admin
    # Check user via UserManager
    user = _user_manager.get_user_by_api_key(api_key) if _user_manager else None
    if user:
        return user["username"]
    raise HTTPException(status_code=403, detail="Invalid API Key")

# Rate limiting
RATE_LIMIT = 100
rate_limiter = defaultdict(lambda: {"count": 0, "reset": time.time() + 60})

def rate_limit(api_key: str):
    now = time.time()
    record = rate_limiter[api_key]
    if now > record["reset"]:
        record["count"] = 0
        record["reset"] = now + 60
    record["count"] += 1
    if record["count"] > RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

# Models
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)

class ChatCompletionRequest(BaseModel):
    messages: list[dict] = Field(default_factory=list)
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 512
    stream: Optional[bool] = False

# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _engine, _secure_memory, _librarian, _user_manager, _consolidation_task
    logger.info("[API] Starting up...")
    try:
        # Init secure memory
        from memory.secure_store import SecureMemoryStore
        _secure_memory = SecureMemoryStore(os.path.join(PROJECT_ROOT, "data", "memory.db"))
        logger.info("[API] SecureMemoryStore initialized.")

        # Init UserManager
        _user_manager = UserManager(db_path=os.path.join(PROJECT_ROOT, "data", "memory.db"), use_postgres=True)
        logger.info("[API] UserManager initialized.")

        # Init engine
        _engine = CognitiveEngineV3(secure_memory=_secure_memory, secure_runner=None)
        logger.info("[API] Engine created.")

        # Librarian
        memory = getattr(_engine, 'memory', None) or _engine.mind.memory
        _librarian = KnowledgeLibrarian(memory, secure_memory=_secure_memory, engine=_engine.engine)
        logger.info("[API] Librarian initialized.")

        # Start auto-consolidation
        async def auto_consolidate_loop():
            while True:
                await asyncio.sleep(1800)  # 30 min
                if _librarian:
                    try:
                        _librarian.consolidate_episodes()
                    except Exception as e:
                        logger.error(f"Auto-consolidation error: {e}")
        _consolidation_task = asyncio.create_task(auto_consolidate_loop())

        logger.info("[API] Startup complete.")
    except Exception as e:
        logger.error(f"Startup error: {e}", exc_info=True)

    yield

    # Shutdown
    logger.info("[API] Shutting down...")
    if _consolidation_task:
        _consolidation_task.cancel()
    if _engine:
        _engine.shutdown()
    if _secure_memory:
        _secure_memory.close()

# App
app = FastAPI(title="JARVIS API V3", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Public endpoints
@app.get("/health")
async def health_check():
    return {"status": "up", "version": "1.6.0", "engine_ready": _engine is not None}

# User endpoints (no auth required)
@app.post("/api/register")
async def register_user(data: UserRegister):
    if not _user_manager:
        raise HTTPException(503, "User manager not ready")
    api_key = _user_manager.create_user(data.username, data.password)
    if not api_key:
        raise HTTPException(400, "Username already exists or invalid")
    return {"username": data.username, "api_key": api_key}

@app.post("/api/login")
async def login_user(data: UserLogin):
    if not _user_manager:
        raise HTTPException(503, "User manager not ready")
    api_key = _user_manager.authenticate_user(data.username, data.password)
    if not api_key:
        raise HTTPException(401, "Invalid credentials")
    return {"username": data.username, "api_key": api_key}

# Protected endpoints (require valid API key)
@app.get("/api/status")
async def get_status(user_id: str = Depends(validate_api_key)):
    rate_limit(user_id)
    try:
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return {
            "cpu": cpu,
            "ram_available_mb": mem.available // (1024*1024),
            "disk": disk.percent,
            "engine_ready": _engine is not None,
            "user": user_id,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/chat")
async def chat(request: ChatRequest, user_id: str = Depends(validate_api_key)):
    rate_limit(user_id)
    if _engine is None:
        raise HTTPException(503, "Engine not initialized")
    async def event_generator():
        def get_response():
            try:
                res = _engine.run(request.message, user_id=user_id)
                if hasattr(_engine, 'dispatch_tasks'):
                    results = _engine.dispatch_tasks()
                else:
                    results = {}
                final_output = f"[Executive Mind]: {res}\n\n"
                if results:
                    for task_id, output in results.items():
                        content = output.get("report") or output.get("code") or str(output)
                        final_output += f"[Specialist]: {content}\n"
                return final_output
            except Exception as e:
                logger.error(f"Engine error: {e}", exc_info=True)
                return f"Error: {str(e)}"
        result = await anyio.to_thread.run_sync(get_response)
        yield f"data: {result}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Admin endpoints (use admin key, same as validate_api_key)
@app.get("/api/memory/pending")
async def get_pending_records(user_id: str = Depends(validate_api_key)):
    if _librarian is None:
        raise HTTPException(503, "Librarian not initialized")
    return _librarian.get_pending_records()

@app.post("/api/memory/verify/{record_uuid}")
async def verify_record(record_uuid: str, approve: bool = Query(...), user_id: str = Depends(validate_api_key)):
    if _librarian is None:
        raise HTTPException(503, "Librarian not initialized")
    success = _librarian.verify_record(record_uuid, approve)
    if not success:
        raise HTTPException(404, "Record not found")
    return {"status": "success"}

@app.post("/api/memory/verify_all")
async def verify_all_pending(approve: bool = Query(...), user_id: str = Depends(validate_api_key)):
    if _librarian is None:
        raise HTTPException(503, "Librarian not initialized")
    count = _librarian.verify_all_pending(approve)
    return {"processed": count}

@app.post("/api/admin/consolidate")
async def manual_consolidate(user_id: str = Depends(validate_api_key)):
    if _librarian is None:
        raise HTTPException(503, "Librarian not initialized")
    promoted = _librarian.consolidate_episodes()
    return {"promoted": promoted}

@app.get("/api/admin/consolidation/status")
async def consolidation_status(user_id: str = Depends(validate_api_key)):
    if _librarian is None:
        raise HTTPException(503, "Librarian not initialized")
    pending = _librarian.get_pending_records()
    return {
        "pending_records": len(pending),
        "enabled": True,
        "interval_minutes": 30,
    }

# Static files
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

# Error handler
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": str(exc)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=False, workers=1, log_level="info")

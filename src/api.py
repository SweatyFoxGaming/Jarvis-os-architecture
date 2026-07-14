"""
JARVIS Cognitive API V3 – Full API with user management, trace details,
public model list, governance, voice transcription (Whisper), TTS proxy,
auto-consolidation, and favicon.
"""

import os
import sys
import logging
import time
import json
import asyncio
import tempfile
from typing import Optional
from contextlib import asynccontextmanager
from collections import defaultdict

import anyio
import psutil
import httpx

from fastapi import FastAPI, Request, HTTPException, Depends, Security, Query, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

# Whisper for transcription
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from config.secure_config import AppConfig
AppConfig.load()

from src.v2_main import CognitiveEngineV3
from src.memory.knowledge_librarian import KnowledgeLibrarian
from src.core.user_manager import UserManager

# ---------- Globals ----------
_engine = None
_secure_memory = None
_librarian = None
_user_manager = None
_consolidation_task = None

# ---------- API Key Auth ----------
ADMIN_API_KEY = getattr(AppConfig, 'INTERNAL_API_KEY', None) or os.getenv("INTERNAL_API_KEY", "admin")
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

def validate_api_key(api_key: str = Security(api_key_header)) -> str:
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API Key")
    if api_key == ADMIN_API_KEY:
        return "admin"
    user = _user_manager.get_user_by_api_key(api_key) if _user_manager else None
    if user:
        return user["username"]
    raise HTTPException(status_code=403, detail="Invalid API Key")

# ---------- Rate Limiting ----------
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

# ---------- Pydantic Models ----------
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

# ---------- Whisper Model (lazy load) ----------
whisper_model = None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        if not WHISPER_AVAILABLE:
            raise RuntimeError("Whisper not installed")
        try:
            whisper_model = whisper.load_model("tiny")
            logger.info("[API] Whisper model loaded (tiny).")
        except Exception as e:
            logger.error(f"[API] Whisper load error: {e}")
            raise
    return whisper_model

# ---------- Lifespan ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _engine, _secure_memory, _librarian, _user_manager, _consolidation_task
    logger.info("[API] Starting up...")
    try:
        from memory.secure_store import SecureMemoryStore
        _secure_memory = SecureMemoryStore(os.path.join(PROJECT_ROOT, "data", "memory.db"))
        logger.info("[API] SecureMemoryStore initialized.")

        _user_manager = UserManager(db_path=os.path.join(PROJECT_ROOT, "data", "memory.db"), use_postgres=True)
        logger.info("[API] UserManager initialized.")

        _engine = CognitiveEngineV3(secure_memory=_secure_memory, secure_runner=None)
        logger.info("[API] Engine created.")

        memory = getattr(_engine, 'memory', None) or _engine.mind.memory
        _librarian = KnowledgeLibrarian(memory, secure_memory=_secure_memory, engine=_engine.engine)
        logger.info("[API] Librarian initialized.")

        # ---------- Auto‑consolidation loop ----------
        async def auto_consolidate_loop():
            logger.info("[API] Auto‑consolidation started. Will run every 30 minutes.")
            while True:
                await asyncio.sleep(1800)  # 30 minutes
                if _librarian:
                    try:
                        promoted = _librarian.consolidate_episodes()
                        if promoted > 0:
                            logger.info(f"[API] Auto‑consolidation promoted {promoted} records.")
                        else:
                            logger.debug("[API] Auto‑consolidation: no records promoted.")
                    except Exception as e:
                        logger.error(f"[API] Auto‑consolidation error: {e}", exc_info=True)
                else:
                    logger.warning("[API] Librarian not available for consolidation.")

        _consolidation_task = asyncio.create_task(auto_consolidate_loop())

        logger.info("[API] Startup complete.")
    except Exception as e:
        logger.error(f"Startup error: {e}", exc_info=True)

    yield

    logger.info("[API] Shutting down...")
    if _consolidation_task:
        _consolidation_task.cancel()
    if _engine:
        _engine.shutdown()
    if _secure_memory:
        _secure_memory.close()

# ---------- App ----------
app = FastAPI(title="JARVIS API V3", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ---------- Public Endpoints ----------
@app.get("/health")
@app.get("/props")
async def health_check():
    return {"status": "up", "version": "1.7.0", "engine_ready": _engine is not None}

@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)

@app.get("/v1/models")
@app.get("/api/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "jarvis-cognitive-engine", "object": "model", "created": 1677610602, "owned_by": "phoenix-os"}
        ],
    }

@app.get("/api/governance")
async def get_governance():
    from src.core.constitution import Constitution
    return {
        "name": "Jarvis Constitution",
        "version": Constitution.VERSION,
        "text": Constitution.get_full_text(),
    }

# ---------- User Endpoints ----------
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

# ---------- Protected Endpoints ----------
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

# ---------- CHAT ENDPOINT (UPDATED with robust error handling) ----------
@app.post("/api/chat")
async def chat(request: ChatRequest, user_id: str = Depends(validate_api_key)):
    rate_limit(user_id)
    if _engine is None:
        raise HTTPException(503, "Engine not initialized")

    # Detect if we should force agent mode (bypass fast path)
    msg = request.message.strip()
    force_agent = False
    if msg.startswith('!'):
        force_agent = True
        msg = msg[1:].strip()  # remove the prefix
    elif any(kw in msg.lower() for kw in ["push", "github", "commit", "deploy", "system_control", "execute"]):
        force_agent = True

    # Use the cleaned message if we stripped '!', else original
    final_message = msg if force_agent and request.message.startswith('!') else request.message

    async def event_generator():
        try:
            def get_response():
                try:
                    res, trace = _engine.run(final_message, user_id=user_id, force_agent=force_agent)
                    return res, trace
                except Exception as e:
                    logger.error(f"Engine error: {e}", exc_info=True)
                    return f"Error: {str(e)}", []

            result, trace = await anyio.to_thread.run_sync(get_response)
            logger.info(f"[API] Chat result: {result[:100] if result else 'empty'}...")
            if not result:
                result = "I'm sorry, I didn't get a response."

            # Always yield the result
            yield f"data: {result}\n\n"

            # Safely yield trace details if present
            if trace:
                for entry in trace:
                    try:
                        # Ensure the entry is JSON serializable
                        # Convert any non-serializable objects to strings
                        safe_entry = {}
                        for k, v in entry.items():
                            if isinstance(v, (dict, list, str, int, float, bool, type(None))):
                                safe_entry[k] = v
                            else:
                                safe_entry[k] = str(v)
                        yield f"data: detail: {json.dumps(safe_entry)}\n\n"
                    except Exception as e:
                        logger.warning(f"Failed to serialize trace entry: {e}")
                        # Skip this entry

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            # Try to send an error message
            try:
                yield f"data: Error: {str(e)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception:
                # If even that fails, just log and close
                logger.error("Failed to send error message in stream")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@app.post("/v1/chat/completions")
@app.post("/api/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, user_id: str = Depends(validate_api_key)):
    rate_limit(user_id)
    if _engine is None:
        raise HTTPException(503, "Engine not initialized")
    try:
        user_msg = ""
        for msg in reversed(request.messages):
            if msg.get("role") == "user":
                user_msg = msg.get("content", "")
                break
        if not user_msg:
            raise HTTPException(400, "No user message found")
        def process():
            response, trace = _engine.run(user_msg, user_id=user_id)
            if hasattr(_engine, 'dispatch_tasks'):
                _engine.dispatch_tasks()
            return response
        response = await anyio.to_thread.run_sync(process)
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "jarvis-cognitive-engine",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": response}, "finish_reason": "stop"}],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Completions error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/learn")
async def learn_lang(request: ChatRequest, user_id: str = Depends(validate_api_key)):
    rate_limit(user_id)
    if _engine is None:
        raise HTTPException(503, "Engine not initialized")
    try:
        prompt = f"Learn everything about {request.message}"
        response, trace = _engine.run(prompt, user_id=user_id)
        if hasattr(_engine, 'dispatch_tasks'):
            _engine.dispatch_tasks()
        return {"status": "success", "language": request.message, "response": response}
    except Exception as e:
        logger.error(f"Learn error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/shutdown")
async def shutdown(user_id: str = Depends(validate_api_key)):
    logger.info("Shutdown requested.")
    return {"status": "shutdown initiated"}

# ---------- Admin Endpoints ----------
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

# ---------- Voice Transcription ----------
@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...), user_id: str = Depends(validate_api_key)):
    rate_limit(user_id)
    if not WHISPER_AVAILABLE:
        raise HTTPException(503, "Whisper not installed")
    allowed_extensions = ('.webm', '.wav', '.mp3', '.m4a', '.flac', '.ogg')
    if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(400, "Unsupported audio format")
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    try:
        model = get_whisper_model()
        result = model.transcribe(tmp_path)
        text = result["text"].strip()
        os.unlink(tmp_path)
        return {"text": text}
    except Exception as e:
        os.unlink(tmp_path)
        logger.error(f"Transcription error: {e}", exc_info=True)
        raise HTTPException(500, f"Transcription error: {str(e)}")

# ---------- TTS Proxy ----------
@app.post("/api/tts")
async def text_to_speech(request: Request, user_id: str = Depends(validate_api_key)):
    rate_limit(user_id)
    try:
        data = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON body")

    tts_url = os.getenv("TTS_URL", "http://localhost:5051/v1/audio/speech")
    tts_api_key = os.getenv("TTS_API_KEY", "your_tts_key")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {tts_api_key}",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(tts_url, json=data, headers=headers)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)
            return Response(content=resp.content, media_type=resp.headers.get("content-type", "audio/mpeg"))
    except httpx.ConnectError:
        logger.error("TTS service connection error")
        raise HTTPException(503, "TTS service unavailable")
    except httpx.TimeoutException:
        logger.error("TTS service timeout")
        raise HTTPException(504, "TTS service timeout")
    except Exception as e:
        logger.error(f"TTS error: {e}", exc_info=True)
        raise HTTPException(500, f"TTS error: {str(e)}")

# ---------- Static Files ----------
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

# ---------- Error Handler ----------
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": str(exc)})

# ---------- Main Entry ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=False, workers=1, log_level="info")

"""
JARVIS Cognitive API V3 – Full API with user management, trace details,
public model list, governance, voice transcription (Whisper), TTS proxy,
auto-consolidation, favicon, and all platforms.
"""

import os
import sys
import logging
import time
import json
import asyncio
import tempfile
from typing import Optional, List
from contextlib import asynccontextmanager
from collections import defaultdict
from uuid import UUID

import anyio
import psutil
import httpx

from fastapi import FastAPI, Request, HTTPException, Depends, Security, Query, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from config.secure_config import AppConfig
AppConfig.load()

# ---- Force environment variables for email ----
os.environ.setdefault('EMAIL_USER', os.getenv('EMAIL_USER', ''))
os.environ.setdefault('EMAIL_PASSWORD', os.getenv('EMAIL_PASSWORD', ''))
os.environ.setdefault('EMAIL_HOST', os.getenv('EMAIL_HOST', 'smtp.gmail.com'))
os.environ.setdefault('EMAIL_PORT', os.getenv('EMAIL_PORT', '587'))
os.environ.setdefault('IMAP_HOST', os.getenv('IMAP_HOST', 'imap.gmail.com'))
os.environ.setdefault('IMAP_PORT', os.getenv('IMAP_PORT', '993'))

from src.v2_main import CognitiveEngineV3
from src.memory.knowledge_librarian import KnowledgeLibrarian
from src.core.user_manager import UserManager

# ---- Interaction Platform ----
from src.interaction import (
    InteractionManager,
    Interaction,
    InteractionSource,
    InteractionKind,
    SessionManager,
    PersonalityEngine,
    ConversationEngine,
    NotificationManager,
)
from src.interaction.models import Tone, NotificationType

# ---- Voice Engine ----
from src.voice import VoiceFactory

# ---- Ecosystem SDK & Validation ----
from src.ecosystem.sdk import PluginSDK
from src.ecosystem.validation import PluginValidator

# ---------- Globals ----------
_engine = None
_secure_memory = None
_librarian = None
_user_manager = None
_consolidation_task = None

# Interaction Platform globals
_interaction_manager = None
_notification_manager = None
_session_manager = None
_personality_engine = None
_conversation_engine = None

# Voice Engine globals
_stt_provider = None
_tts_provider = None

# ---------- API Key Auth ----------
ADMIN_API_KEY = getattr(AppConfig, 'INTERNAL_API_KEY', None) or os.getenv("INTERNAL_API_KEY", "admin")
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def validate_api_key(
    api_key: str = Security(api_key_header),
    api_key_query: str = Query(None, alias="api_key"),
) -> str:
    key = api_key or api_key_query
    if not key:
        raise HTTPException(status_code=401, detail="Missing API Key")
    if key == ADMIN_API_KEY:
        return "admin"
    user = _user_manager.get_user_by_api_key(key) if _user_manager else None
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

class MarkReadRequest(BaseModel):
    notification_id: str

# ---------- Lifespan ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _engine, _secure_memory, _librarian, _user_manager, _consolidation_task
    global _interaction_manager, _notification_manager, _session_manager, _personality_engine, _conversation_engine
    global _stt_provider, _tts_provider

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

        # ---- Interaction Platform ----
        _session_manager = SessionManager(secure_memory=_secure_memory)
        _personality_engine = PersonalityEngine()
        _notification_manager = NotificationManager(event_bus=_engine.event_bus)
        _conversation_engine = ConversationEngine(_session_manager, _personality_engine, _engine.mind)
        _interaction_manager = InteractionManager(_session_manager, _conversation_engine, _notification_manager)

        _engine.mind.set_session_manager(_session_manager)

        loaded = _session_manager.load_all_sessions()
        logger.info(f"[API] Loaded {loaded} sessions from KnowledgeStore.")

        logger.info("[API] Interaction Platform initialized.")

        # ---- Voice Engine ----
        _stt_provider = VoiceFactory.create_stt("whisper", model_name="tiny")
        _tts_provider = VoiceFactory.create_tts("edge_tts")
        logger.info("[API] Voice Engine initialized.")

        # ---------- Auto‑consolidation loop ----------
        async def auto_consolidate_loop():
            logger.info("[API] Auto‑consolidation started. Will run every 30 minutes.")
            while True:
                await asyncio.sleep(1800)
                if _librarian:
                    try:
                        promoted = _librarian.consolidate_episodes()
                        if promoted > 0:
                            logger.info(f"[API] Auto‑consolidation promoted {promoted} records.")
                    except Exception as e:
                        logger.error(f"[API] Auto‑consolidation error: {e}", exc_info=True)

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

# ---------- CHAT ENDPOINT ----------
@app.post("/api/chat")
async def chat(request: ChatRequest, user_id: str = Depends(validate_api_key)):
    rate_limit(user_id)
    if _interaction_manager is None:
        raise HTTPException(503, "Interaction Platform not initialized")

    msg = request.message.strip()
    force_agent = False
    if msg.startswith('!'):
        force_agent = True
        msg = msg[1:].strip()
    elif any(kw in msg.lower() for kw in ["push", "github", "commit", "deploy", "system_control", "execute"]):
        force_agent = True

    final_message = msg if force_agent and request.message.startswith('!') else request.message

    session_id = _session_manager.get_session_for_user(user_id)

    interaction = Interaction(
        session_id=session_id,
        source=InteractionSource.WEB,
        kind=InteractionKind.TEXT,
        content=final_message,
        metadata={
            "user_id": user_id,
            "force_agent": force_agent,
        },
    )

    result = _interaction_manager.handle(interaction)
    response_text = result.text or result.markdown or "No response."

    async def event_generator():
        yield f"data: {response_text}\n\n"
        if result.trace:
            for entry in result.trace:
                try:
                    safe_entry = {}
                    for k, v in entry.items():
                        if isinstance(v, (dict, list, str, int, float, bool, type(None))):
                            safe_entry[k] = v
                        else:
                            safe_entry[k] = str(v)
                    yield f"data: detail: {json.dumps(safe_entry)}\n\n"
                except Exception as e:
                    logger.warning(f"Failed to serialize trace entry: {e}")
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

# ---------- NOTIFICATION ENDPOINTS ----------
@app.get("/api/notifications/stream")
async def notifications_stream(user_id: str = Depends(validate_api_key)):
    if _interaction_manager is None:
        raise HTTPException(503, "Interaction Platform not initialized")

    session_id = _session_manager.get_session_for_user(user_id)
    queue = _interaction_manager.get_stream_queue(session_id)

    async def event_generator():
        try:
            yield f"event: connected\ndata: {json.dumps({'session_id': str(session_id), 'status': 'connected'})}\n\n"
            while True:
                try:
                    notification = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"event: notification\ndata: {json.dumps(notification.model_dump(mode='json'))}\n\n"
                except asyncio.TimeoutError:
                    yield f"event: ping\ndata: {json.dumps({'timestamp': time.time()})}\n\n"
        except asyncio.CancelledError:
            logger.info(f"[API] SSE client disconnected for session {session_id}")
        finally:
            _interaction_manager.remove_stream_queue(session_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )

@app.get("/api/notifications")
async def get_notifications(
    user_id: str = Depends(validate_api_key),
    limit: int = Query(50, ge=1, le=200),
    unread_only: bool = Query(False),
):
    if _interaction_manager is None:
        raise HTTPException(503, "Interaction Platform not initialized")
    session_id = _session_manager.get_session_for_user(user_id)
    notifications = _interaction_manager.get_notifications(session_id, unread_only=unread_only, limit=limit)
    return {
        "notifications": [n.model_dump(mode='json') for n in notifications],
        "count": len(notifications),
        "unread_count": len([n for n in notifications if not n.read]),
    }

@app.post("/api/notifications/mark_read")
async def mark_notification_read(
    request: MarkReadRequest,
    user_id: str = Depends(validate_api_key),
):
    if _interaction_manager is None:
        raise HTTPException(503, "Interaction Platform not initialized")
    try:
        notification_id = UUID(request.notification_id)
    except ValueError:
        raise HTTPException(400, "Invalid notification ID")
    success = _interaction_manager.mark_read(notification_id)
    if not success:
        raise HTTPException(404, "Notification not found")
    return {"status": "success"}

@app.post("/api/notifications/mark_all_read")
async def mark_all_notifications_read(user_id: str = Depends(validate_api_key)):
    if _interaction_manager is None:
        raise HTTPException(503, "Interaction Platform not initialized")
    session_id = _session_manager.get_session_for_user(user_id)
    count = _interaction_manager.mark_all_read(session_id)
    return {"status": "success", "marked_count": count}

# ---------- VOICE ENDPOINTS ----------
@app.post("/api/transcribe")
async def transcribe_audio(file: UploadFile = File(...), user_id: str = Depends(validate_api_key)):
    rate_limit(user_id)
    if _stt_provider is None:
        raise HTTPException(503, "STT provider not initialized")

    allowed = _stt_provider.get_supported_formats()
    if file.content_type not in allowed:
        raise HTTPException(400, f"Unsupported audio format. Supported: {', '.join(allowed)}")

    content = await file.read()
    try:
        text = _stt_provider.transcribe(content)
        return {"text": text}
    except Exception as e:
        logger.error(f"Transcription error: {e}", exc_info=True)
        raise HTTPException(500, f"Transcription error: {str(e)}")

@app.post("/api/tts")
async def text_to_speech(request: Request, user_id: str = Depends(validate_api_key)):
    rate_limit(user_id)
    if _tts_provider is None:
        raise HTTPException(503, "TTS provider not initialized")

    try:
        data = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON body")

    text = data.get("input") or data.get("text")
    if not text:
        raise HTTPException(400, "Missing 'text' or 'input' field")

    voice = data.get("voice")
    response_format = data.get("response_format", "mp3")
    speed = data.get("speed", 1.0)

    try:
        audio = _tts_provider.synthesize(text=text, voice=voice, response_format=response_format, speed=speed)
        return Response(content=audio, media_type=f"audio/{response_format}")
    except Exception as e:
        logger.error(f"TTS error: {e}", exc_info=True)
        raise HTTPException(500, f"TTS error: {str(e)}")

# ---------- EVOLUTION ENDPOINTS ----------

@app.post("/api/evolution/analyze/architecture")
async def evolution_analyze_architecture(user_id: str = Depends(validate_api_key)):
    """Run architecture analysis."""
    if not _engine or not hasattr(_engine, 'evolution'):
        raise HTTPException(503, "Evolution Platform not initialized")
    result = _engine.evolution.analyze_architecture()
    return result.model_dump(mode='json')

@app.post("/api/evolution/analyze/quality")
async def evolution_analyze_quality(user_id: str = Depends(validate_api_key)):
    """Run code quality analysis."""
    if not _engine or not hasattr(_engine, 'evolution'):
        raise HTTPException(503, "Evolution Platform not initialized")
    result = _engine.evolution.analyze_quality()
    return result.model_dump(mode='json')

@app.post("/api/evolution/analyze/performance")
async def evolution_analyze_performance(user_id: str = Depends(validate_api_key)):
    """Run performance analysis."""
    if not _engine or not hasattr(_engine, 'evolution'):
        raise HTTPException(503, "Evolution Platform not initialized")
    result = _engine.evolution.analyze_performance()
    return result.model_dump(mode='json')

@app.post("/api/evolution/analyze/security")
async def evolution_analyze_security(user_id: str = Depends(validate_api_key)):
    """Run security analysis."""
    if not _engine or not hasattr(_engine, 'evolution'):
        raise HTTPException(503, "Evolution Platform not initialized")
    result = _engine.evolution.analyze_security()
    return result.model_dump(mode='json')

@app.get("/api/evolution/recommendations")
async def evolution_get_recommendations(
    state: Optional[str] = Query(None),
    user_id: str = Depends(validate_api_key),
):
    """Get all recommendations, optionally filtered by state."""
    if not _engine or not hasattr(_engine, 'evolution'):
        raise HTTPException(503, "Evolution Platform not initialized")
    recs = _engine.evolution.get_recommendations(state)
    return {"recommendations": [r.model_dump(mode='json') for r in recs]}

@app.post("/api/evolution/recommendations/generate")
async def evolution_generate_recommendations(
    analysis_id: Optional[str] = Query(None),
    user_id: str = Depends(validate_api_key),
):
    """Generate recommendations from analysis results."""
    if not _engine or not hasattr(_engine, 'evolution'):
        raise HTTPException(503, "Evolution Platform not initialized")
    recs = _engine.evolution.generate_recommendations(analysis_id)
    return {"recommendations": [r.model_dump(mode='json') for r in recs]}

@app.post("/api/evolution/recommendations/{rec_id}/propose")
async def evolution_propose_recommendation(
    rec_id: str,
    user_id: str = Depends(validate_api_key),
):
    """Propose a recommendation for approval."""
    if not _engine or not hasattr(_engine, 'evolution'):
        raise HTTPException(503, "Evolution Platform not initialized")
    rec = _engine.evolution.propose(rec_id)
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    return rec.model_dump(mode='json')

@app.post("/api/evolution/recommendations/{rec_id}/approve")
async def evolution_approve_recommendation(
    rec_id: str,
    user_id: str = Depends(validate_api_key),
):
    """Approve a recommendation."""
    if not _engine or not hasattr(_engine, 'evolution'):
        raise HTTPException(503, "Evolution Platform not initialized")
    rec = _engine.evolution.approve(rec_id)
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    return rec.model_dump(mode='json')

@app.post("/api/evolution/recommendations/{rec_id}/reject")
async def evolution_reject_recommendation(
    rec_id: str,
    reason: Optional[str] = Query(None),
    user_id: str = Depends(validate_api_key),
):
    """Reject a recommendation."""
    if not _engine or not hasattr(_engine, 'evolution'):
        raise HTTPException(503, "Evolution Platform not initialized")
    rec = _engine.evolution.reject(rec_id, reason)
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    return rec.model_dump(mode='json')

@app.get("/api/evolution/analyses")
async def evolution_get_analyses(user_id: str = Depends(validate_api_key)):
    """Get all analyses."""
    if not _engine or not hasattr(_engine, 'evolution'):
        raise HTTPException(503, "Evolution Platform not initialized")
    analyses = _engine.evolution.get_analyses()
    return {"analyses": [a.model_dump(mode='json') for a in analyses]}

@app.get("/api/evolution/dependency-graph")
async def evolution_get_dependency_graph(user_id: str = Depends(validate_api_key)):
    """Get the latest dependency graph (JSON)."""
    if not _engine or not hasattr(_engine, 'evolution'):
        raise HTTPException(503, "Evolution Platform not initialized")
    graph = _engine.evolution.get_dependency_graph()
    if not graph:
        raise HTTPException(404, "No architecture analysis found; run analysis first.")
    return graph

@app.get("/api/evolution/dashboard")
async def evolution_dashboard(user_id: str = Depends(validate_api_key)):
    """Get the engineering health dashboard."""
    if not _engine or not hasattr(_engine, 'evolution'):
        raise HTTPException(503, "Evolution Platform not initialized")
    recs = _engine.evolution.get_recommendations()
    report = _engine.evolution.get_dashboard(recs)
    return report

@app.get("/api/evolution/trends")
async def evolution_trends(user_id: str = Depends(validate_api_key)):
    """Get trend report for all metrics."""
    if not _engine or not hasattr(_engine, 'evolution'):
        raise HTTPException(503, "Evolution Platform not initialized")
    return _engine.evolution.get_trend_report()

@app.get("/api/evolution/forecast")
async def evolution_forecast(
    horizon_days: int = Query(30, description="Forecast horizon in days"),
    user_id: str = Depends(validate_api_key),
):
    """Get forecast for key metrics."""
    if not _engine or not hasattr(_engine, 'evolution'):
        raise HTTPException(503, "Evolution Platform not initialized")
    return _engine.evolution.get_forecast(horizon_days)

@app.post("/api/evolution/recommendations/prioritize")
async def evolution_prioritize_recommendations(user_id: str = Depends(validate_api_key)):
    """Get recommendations sorted by priority."""
    if not _engine or not hasattr(_engine, 'evolution'):
        raise HTTPException(503, "Evolution Platform not initialized")
    recs = _engine.evolution.prioritize_recommendations()
    return {"recommendations": [r.model_dump(mode='json') for r in recs]}

@app.get("/api/evolution/goals")
async def evolution_get_goals(
    status: Optional[str] = Query(None, description="Filter by goal status"),
    user_id: str = Depends(validate_api_key),
):
    """Get engineering goals."""
    if not _engine or not hasattr(_engine, 'evolution'):
        raise HTTPException(503, "Evolution Platform not initialized")
    return {"goals": _engine.evolution.get_goals(status)}

@app.post("/api/evolution/goals")
async def evolution_create_goal(
    title: str = Query(...),
    description: str = Query(...),
    target_metric: str = Query(...),
    target_value: float = Query(...),
    user_id: str = Depends(validate_api_key),
):
    """Create a new engineering goal."""
    if not _engine or not hasattr(_engine, 'evolution'):
        raise HTTPException(503, "Evolution Platform not initialized")
    goal = _engine.evolution.create_goal(title, description, target_metric, target_value)
    return {"goal": goal}

@app.post("/api/evolution/goals/{goal_id}/progress")
async def evolution_update_goal_progress(
    goal_id: str,
    current_value: float = Query(...),
    user_id: str = Depends(validate_api_key),
):
    """Update the current progress of a goal."""
    if not _engine or not hasattr(_engine, 'evolution'):
        raise HTTPException(503, "Evolution Platform not initialized")
    result = _engine.evolution.update_goal_progress(goal_id, current_value)
    if not result:
        raise HTTPException(404, "Goal not found")
    return {"goal": result}

# ---------- ECOSYSTEM ENDPOINTS ----------

@app.get("/api/ecosystem/discover")
async def ecosystem_discover(user_id: str = Depends(validate_api_key)):
    """Discover new plugins."""
    if not _engine or not hasattr(_engine, 'ecosystem'):
        raise HTTPException(503, "Ecosystem Platform not initialized")
    discovered = _engine.ecosystem.discover()
    return {"discovered": [d.model_dump(mode='json') for d in discovered]}

@app.post("/api/ecosystem/install")
async def ecosystem_install(
    name: str = Query(...),
    version: str = Query("1.0.0"),
    description: str = Query(""),
    author: str = Query("Unknown"),
    user_id: str = Depends(validate_api_key),
):
    """Install a plugin."""
    if not _engine or not hasattr(_engine, 'ecosystem'):
        raise HTTPException(503, "Ecosystem Platform not initialized")
    manifest = _engine.ecosystem.install(name, version, description, author)
    return {"plugin": manifest.model_dump(mode='json')}

@app.post("/api/ecosystem/plugins/{plugin_id}/activate")
async def ecosystem_activate_plugin(
    plugin_id: str,
    user_id: str = Depends(validate_api_key),
):
    """Activate a plugin."""
    if not _engine or not hasattr(_engine, 'ecosystem'):
        raise HTTPException(503, "Ecosystem Platform not initialized")
    result = _engine.ecosystem.activate(plugin_id)
    if not result:
        raise HTTPException(400, "Plugin activation failed")
    return {"status": "activated"}

@app.post("/api/ecosystem/plugins/{plugin_id}/deactivate")
async def ecosystem_deactivate_plugin(
    plugin_id: str,
    user_id: str = Depends(validate_api_key),
):
    """Deactivate a plugin."""
    if not _engine or not hasattr(_engine, 'ecosystem'):
        raise HTTPException(503, "Ecosystem Platform not initialized")
    result = _engine.ecosystem.deactivate(plugin_id)
    if not result:
        raise HTTPException(400, "Plugin deactivation failed")
    return {"status": "deactivated"}

@app.delete("/api/ecosystem/plugins/{plugin_id}")
async def ecosystem_remove_plugin(
    plugin_id: str,
    user_id: str = Depends(validate_api_key),
):
    """Remove a plugin."""
    if not _engine or not hasattr(_engine, 'ecosystem'):
        raise HTTPException(503, "Ecosystem Platform not initialized")
    result = _engine.ecosystem.remove(plugin_id)
    if not result:
        raise HTTPException(404, "Plugin not found")
    return {"status": "removed"}

@app.get("/api/ecosystem/plugins")
async def ecosystem_list_plugins(
    state: Optional[str] = Query(None),
    user_id: str = Depends(validate_api_key),
):
    """List installed plugins."""
    if not _engine or not hasattr(_engine, 'ecosystem'):
        raise HTTPException(503, "Ecosystem Platform not initialized")
    plugins = _engine.ecosystem.list_plugins(state)
    return {"plugins": [p.model_dump(mode='json') for p in plugins]}

@app.get("/api/ecosystem/plugins/{plugin_id}/health")
async def ecosystem_plugin_health(
    plugin_id: str,
    user_id: str = Depends(validate_api_key),
):
    """Check plugin health."""
    if not _engine or not hasattr(_engine, 'ecosystem'):
        raise HTTPException(503, "Ecosystem Platform not initialized")
    health = _engine.ecosystem.health_check(plugin_id)
    return {"plugin_id": plugin_id, "health": health}

@app.get("/api/ecosystem/health")
async def ecosystem_health_all(user_id: str = Depends(validate_api_key)):
    """Health check for all active plugins."""
    if not _engine or not hasattr(_engine, 'ecosystem'):
        raise HTTPException(503, "Ecosystem Platform not initialized")
    results = _engine.ecosystem.health_check_all()
    return {"health": results}

@app.get("/api/ecosystem/marketplace/search")
async def ecosystem_marketplace_search(
    query: str = Query(""),
    user_id: str = Depends(validate_api_key),
):
    """Search the marketplace (stub)."""
    if not _engine or not hasattr(_engine, 'ecosystem'):
        raise HTTPException(503, "Ecosystem Platform not initialized")
    results = _engine.ecosystem.marketplace_search(query)
    return {"results": [r.model_dump(mode='json') for r in results]}

@app.post("/api/ecosystem/plugins/{plugin_id}/sandbox/test")
async def ecosystem_sandbox_test(
    plugin_id: str,
    permission: str = Query(..., description="Permission to test (filesystem, network, etc.)"),
    user_id: str = Depends(validate_api_key),
):
    """Test if a plugin has a specific permission."""
    if not _engine or not hasattr(_engine, 'ecosystem'):
        raise HTTPException(503, "Ecosystem Platform not initialized")
    sandbox = _engine.ecosystem.get_sandbox(plugin_id)
    if not sandbox:
        raise HTTPException(404, "Plugin not found or not active")
    try:
        # Convert permission string to enum
        perm = PluginPermission(permission)
        sandbox.require(perm)
        return {"has_permission": True, "permission": permission}
    except PermissionDenied:
        return {"has_permission": False, "permission": permission}
    except ValueError:
        raise HTTPException(400, f"Invalid permission: {permission}")

# ---------- SDK ENDPOINTS ----------

@app.post("/api/ecosystem/sdk/template")
async def ecosystem_create_template(
    name: str = Query(...),
    author: str = Query("Jarvis Developer"),
    version: str = Query("1.0.0"),
    description: str = Query(""),
    user_id: str = Depends(validate_api_key),
):
    """Create a new plugin template."""
    if not _engine or not hasattr(_engine, 'ecosystem'):
        raise HTTPException(503, "Ecosystem Platform not initialized")
    sdk = PluginSDK()
    success = sdk.create_template(name, author, version, description)
    if not success:
        raise HTTPException(400, "Plugin already exists or invalid name")
    return {"status": "created", "name": name}

@app.get("/api/ecosystem/sdk/validate")
async def ecosystem_validate_plugins(user_id: str = Depends(validate_api_key)):
    """Validate all plugins."""
    if not _engine or not hasattr(_engine, 'ecosystem'):
        raise HTTPException(503, "Ecosystem Platform not initialized")
    validator = PluginValidator()
    results = validator.validate_all()
    return {"results": results}

# ---------- MARKETPLACE ENDPOINTS ----------

@app.get("/api/ecosystem/marketplace/search")
async def ecosystem_marketplace_search(
    query: str = Query(""),
    user_id: str = Depends(validate_api_key),
):
    """Search the marketplace for plugins."""
    if not _engine or not hasattr(_engine, 'ecosystem'):
        raise HTTPException(503, "Ecosystem Platform not initialized")
    results = _engine.ecosystem.marketplace_search(query)
    return {"results": [r.model_dump(mode='json') for r in results]}

@app.post("/api/ecosystem/marketplace/install")
async def ecosystem_marketplace_install(
    plugin_id: str = Query(...),
    user_id: str = Depends(validate_api_key),
):
    """Install a plugin from the marketplace by ID."""
    if not _engine or not hasattr(_engine, 'ecosystem'):
        raise HTTPException(503, "Ecosystem Platform not initialized")
    success = _engine.ecosystem.marketplace_install(plugin_id)
    if not success:
        raise HTTPException(400, "Failed to install plugin from marketplace")
    return {"status": "installed", "plugin_id": plugin_id}

# ---------- Other Endpoints ----------
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

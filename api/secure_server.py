import os
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from starlette.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import your config (from File 1)
# Make sure config is loaded before running the server
from config.secure_config import AppConfig

# ---------- Load Config ----------
# This will raise a ValueError if keys are missing.
AppConfig.load()

# ---------- Pydantic Models ----------
class PromptRequest(BaseModel):
    prompt: str
    session_id: str | None = None

class PromptResponse(BaseModel):
    status: str
    result: str
    session_id: str | None = None

# ---------- FastAPI App Setup ----------
app = FastAPI(
    title="Phoenix Secure API",
    description="Secure JARVIS API with API-Key authentication",
    version="1.0.0"
)

# ---------- SECURE CORS ----------
# NEVER use allow_origins=["*"] in production. Specify exact domains.
ALLOWED_ORIGINS = [
    "http://localhost:3000",        # React dev
    "http://127.0.0.1:3000",
    "https://your-frontend.com",    # Replace with your actual domain
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Strict list
    allow_credentials=True,
    allow_methods=["POST", "GET"],  # Only allow what you need
    allow_headers=["X-API-Key", "Content-Type"],
)

# ---------- API Key Security ----------
API_KEY = AppConfig.OPENAI_API_KEY  # Or create a dedicated INTERNAL_API_KEY in .env
API_KEY_NAME = "X-API-Key"

# FastAPI's Security utility handles the header extraction
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

def validate_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Dependency injection for API Key validation.
    Raises HTTP 403 if invalid.
    """
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API Key. Please provide X-API-Key header."
        )
    return api_key


# ---------- Health Check (No auth required for basic health) ----------
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

# ---------- Secure Endpoint ----------
@app.post("/v1/execute", response_model=PromptResponse)
async def execute_prompt(
    request: PromptRequest,
    api_key: str = Depends(validate_api_key)  # THIS ENFORCES AUTH
):
    """
    Executes a prompt against the JARVIS engine.
    Requires X-API-Key header.
    """
    # Simulate processing (replace with your actual llm_engine.generate)
    import time
    time.sleep(1)
    
    # Mock response
    result_text = f"Processed: {request.prompt} (Session: {request.session_id})"
    
    return PromptResponse(
        status="success",
        result=result_text,
        session_id=request.session_id
    )


# ---------- Server Runner ----------
if __name__ == "__main__":
    print("[API] Starting Secure Server...")
    print(f"[API] Allowed Origins: {ALLOWED_ORIGINS}")
    print("[API] API Key Authentication ENABLED.")
    
    # CRITICAL FOR PRODUCTION:
    # - reload=False (prevents code leaks)
    # - workers=2 (or more for production)
    # - host=0.0.0.0 (exposes to network, use with firewall)
    uvicorn.run(
        "api.secure_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,      # NEVER True in production
        workers=2,
        log_level="warning"
    )

# Jarvis OS - Project Context

## Current State (2026-07-12)
- All Docker containers running (postgres, tts, api) and passing health checks.
- API is serving Swagger UI at /docs (browser needed).
- We discovered `/chat` endpoint exists but returns "Method Not Allowed" on POST.
- Need to identify correct HTTP method and payload structure.

## Next Action
- Fetch openapi.json to list all routes and their methods.
- Test likely candidates (GET /chat, POST /v1/chat, etc.).
- If still unresolved, review `src/api.py` for exact route definitions.

## Fast‑Path Bypass Added (2026-07-12)
- Added `force_agent` parameter to `ExecutiveMind.process_request` and `CognitiveEngineV3.run`.
- API now auto‑detects commands (keywords: push, github, commit, deploy, system_control, execute) and forces agent mode.
- Users can also prefix any message with `!` to skip the fast‑path entirely.
- To push code, use `!Use system_control to execute: cd /app && git add . && git commit -m "message" && git push origin main`

## Final Fix Applied (2026-07-12)
- Added `force_agent` parameter to bypass fast path.
- API auto‑detects commands containing `push`, `github`, `commit`, `deploy`, `system_control`, `execute` or starting with `!`.
- Jarvis now properly routes tool requests to LLM for execution.
- To push code, use: `!Use system_control to execute: cd /app && git add . && git commit -m "message" && git push origin main`

# Jarvis OS – Project Context (as of 2026-07-12)

## 🧱 Project Setup
- **Location**: `/home/ubuntu/jarvis-os` (moved from the deep nested `llm` folder).
- **Git repo**: `Jarvis-os-architecture` (remote origin set).
- **Docker Compose**: Three services (`postgres`, `tts`, `api`).
  - `api` image built from `Dockerfile` in root.
  - All code mounted via `- .:/app` – so `.git` is accessible inside the container.
  - Environment variables defined in `docker-compose.yml` and `.env`.

## ✅ Working Features
- API responds to `/health`, `/docs`, etc.
- **`execute:` command works** – runs any shell command through `system_control` (e.g., `git add . && git commit ...`).
- Security modules (`security.py`, `synapse.py`) allow chained shell commands (`&&`, `|`, etc.) with `shell=True`.
- `git` is installed in the container (Dockerfile includes `git`).
- The `system_control` handler in `v2_main.py` uses keyword arguments (`action=`, `command=`, etc.).
- `mind.py` has a **direct execution path** that bypasses the LLM for `execute:` and `system_control` – so these commands work even if the model fails.

## ⚠️ Current Known Issue
- **LLM model fails to download** – the default model `dolphin-2_6-phi-2.Q4_K_M.gguf` gives a 401 Unauthorized error from Hugging Face.
- **Impact**: The LLM-based conversation (`/api/chat` without `execute:`) falls back to a template response (no real AI).
- **Fix**: Either set a `HF_TOKEN` environment variable, or manually download a model to `/mnt/jarvis_home/models/` and update `MODEL_PATH` in `.env`.
- **Workaround**: Use `execute:` for all system tasks; the API still works for health checks, TTS, etc.

## 🧪 Test Command (always works)
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: c44dcd566e20d12f361464fb83c3734e02c60dbfd8b4f75e9a98f24d63c24918" \
  -d '{"message": "execute: cd /app && git add . && git commit -m \"final docker setup\" && git push origin main"}'

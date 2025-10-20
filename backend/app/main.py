import json
import logging
import os
from typing import Any, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
import socketio

from app.config import validate_settings, settings, setup_logging
from app.orchestrator.session_manager import SessionManager
from app.orchestrator.conversation import ConversationOrchestrator


fastapi_app = FastAPI(title="Horticulture Chatbot Backend", version="0.1.0")


def _allowed_origins_from_env() -> list[str]:
    """Compute allowed origins for CORS and Socket.IO.

    Defaults to local dev origins. Extends with values from `ALLOWED_ORIGINS`
    (comma-separated) or falls back to `NEXT_PUBLIC_BACKEND_URL` when set.
    Accepts bare hosts or full URLs; adds both http/https variants when possible.
    """
    base = [
        "http://localhost:3005",
        "http://localhost:3000",
        "http://127.0.0.1:3005",
        "http://127.0.0.1:3000",
    ]
    extra = os.getenv("ALLOWED_ORIGINS", "") or os.getenv("NEXT_PUBLIC_BACKEND_URL", "")
    tokens = [t.strip() for t in extra.split(",") if t.strip()]
    for t in tokens:
        if "://" in t:
            base.append(t)
            if t.startswith("http://"):
                base.append(t.replace("http://", "https://", 1))
            if t.startswith("https://"):
                base.append(t.replace("https://", "http://", 1))
        else:
            base.append(f"http://{t}")
            base.append(f"https://{t}")
    # de-duplicate, preserve order
    seen: set[str] = set()
    out: list[str] = []
    for o in base:
        if o not in seen:
            seen.add(o)
            out.append(o)
    return out


# CORS (frontend runs at host:3005 by compose ports)
_ALLOWED_ORIGINS = _allowed_origins_from_env()

fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Static files (serve generated images)
_HERE = os.path.dirname(__file__)
_STATIC_DIR = os.path.join(os.path.dirname(_HERE), "static")
if os.path.isdir(_STATIC_DIR):
    fastapi_app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


# Core singletons
sessions = SessionManager()
orchestrator = ConversationOrchestrator(sessions=sessions)


@fastapi_app.on_event("startup")
def _startup_validate_config():
    try:
        setup_logging()
        validate_settings(fail_on_missing_llm_key=True)
        logging.getLogger(__name__).info("Backend startup complete")
    except Exception as e:
        logging.getLogger(__name__).error("Startup validation failed: %s", e)
        raise


@fastapi_app.get("/health")
def health_check():
    return {"status": "ok"}


# ---------------- REST: Sessions ----------------
@fastapi_app.post("/api/sessions")
async def create_session() -> Dict[str, Any]:
    sid = await sessions.create_session()
    return {"session_id": sid}


@fastapi_app.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> Dict[str, Any]:
    data = await sessions.get_session(session_id)
    return data or {}


# ---------------- WebSocket fallback ----------------
@fastapi_app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        while True:
            text = await websocket.receive_text()
            reply = await orchestrator.process_message(session_id, text)
            await websocket.send_text(json.dumps(reply))
    except WebSocketDisconnect:
        return


# ---------------- Socket.IO setup ----------------
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=_ALLOWED_ORIGINS,
    ping_timeout=60,
    ping_interval=25,
)


@sio.event
async def connect(sid, environ, auth):  # type: ignore[no-redef]
    # Client may provide session_id later via messages
    logging.getLogger(__name__).info("Socket connected: %s", sid)


@sio.event
async def disconnect(sid):  # type: ignore[no-redef]
    logging.getLogger(__name__).info("Socket disconnected: %s", sid)


@sio.event
async def typing(sid, data):  # type: ignore[no-redef]
    # passthrough typing indicator for UX; not persisted
    await sio.emit("typing", data, to=sid)


@sio.event
async def message(sid, data):  # type: ignore[no-redef]
    try:
        session_id = (data or {}).get("sessionId") or (data or {}).get("session_id")
        text = (data or {}).get("text") or ""
        logging.getLogger(__name__).info("SIO message sid=%s session=%s text_len=%d", sid, session_id, len(text))
        if not session_id:
            # Auto-create if not provided
            session_id = await sessions.create_session()
            await sio.emit("session", {"sessionId": session_id}, to=sid)
        if not text:
            return
        await sio.emit("typing", {"isTyping": True}, to=sid)
        reply = await orchestrator.process_message(session_id, text)
        await sio.emit("response", {"sessionId": session_id, **reply}, to=sid)
    except Exception as e:
        logging.getLogger(__name__).exception("Socket message handler failed: %s", e)
        await sio.emit("app_error", {"message": str(e)}, to=sid)
    finally:
        await sio.emit("typing", {"isTyping": False}, to=sid)


# Wrap FastAPI app with Socket.IO ASGIApp at default path '/socket.io'
app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)

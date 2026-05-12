"""
GHOST Telegram Mini App backend.

Public app:
- /            Mini App shell
- /static/*    Frontend assets
- /health      Deployment health check

WebSockets:
- /ws/client   Telegram Mini App clients
- /ws/agent    Local Windows agent
"""

import asyncio
import hmac
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

try:
    from .models import AgentStatus, Prompt
    from .security import (
        agent_token,
        dev_session,
        env_bool,
        require_telegram_auth,
        validate_init_data,
    )
except ImportError:  # Allows `python main.py` from the backend folder.
    from models import AgentStatus, Prompt
    from security import (
        agent_token,
        dev_session,
        env_bool,
        require_telegram_auth,
        validate_init_data,
    )

try:
    from dotenv import load_dotenv

    ROOT = Path(__file__).resolve().parents[2]
    load_dotenv(ROOT / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except Exception:
    ROOT = Path(__file__).resolve().parents[2]


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("ghost.miniapp")

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
MAX_HISTORY = 200
MAX_TEXT_LENGTH = 12000


def _cors_origins() -> list[str]:
    raw = os.getenv("GHOST_CORS_ORIGINS", "").strip()
    if not raw:
        return ["*"]
    return [item.strip() for item in raw.split(",") if item.strip()]


app = FastAPI(title="GHOST Mini App", version="2.0.0", docs_url="/api/docs")

origins = _cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=origins != ["*"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@dataclass
class ClientConnection:
    ws: WebSocket
    session: object


class State:
    agent_ws: Optional[WebSocket] = None
    agent_last_seen: Optional[str] = None
    agent_info: dict = {}
    system_status: Optional[dict] = None
    clients: dict[str, ClientConnection] = {}
    pending: dict[str, asyncio.Future] = {}
    history: list[dict] = []


state = State()


@app.websocket("/ws/agent")
async def ws_agent(ws: WebSocket):
    if not _agent_authorized(ws):
        await ws.close(code=1008)
        return

    await ws.accept()
    state.agent_ws = ws
    state.agent_last_seen = _now()
    logger.info("Local agent connected")
    await _broadcast_agent_status(True)

    try:
        await ws.send_json({"type": "get_status"})
        while True:
            data = await ws.receive_json()
            state.agent_last_seen = _now()
            await _on_agent_msg(data)
    except (WebSocketDisconnect, Exception) as exc:
        logger.warning("Local agent disconnected: %s", exc)
        if state.agent_ws is ws:
            state.agent_ws = None
        await _broadcast_agent_status(False)


@app.websocket("/ws/client")
async def ws_client(ws: WebSocket):
    await ws.accept()
    session, error = _client_session(ws)
    if error:
        await ws.send_json({
            "type": "auth_error",
            "message": error,
            "auth_required": require_telegram_auth(),
        })
        await ws.close(code=1008)
        return

    cid = str(uuid.uuid4())
    state.clients[cid] = ClientConnection(ws=ws, session=session)
    logger.info("Client connected: %s (%s)", cid[:8], session.display_name)

    await ws.send_json({
        "type": "init",
        "agent_connected": state.agent_ws is not None,
        "agent_last_seen": state.agent_last_seen,
        "history": state.history[-50:],
        "session": session.as_dict(),
        "system": state.system_status,
        "auth_required": require_telegram_auth(),
    })

    try:
        while True:
            data = await ws.receive_json()
            await _on_client_msg(cid, data)
    except (WebSocketDisconnect, Exception):
        state.clients.pop(cid, None)
        logger.info("Client disconnected: %s", cid[:8])


async def _on_agent_msg(data: dict):
    msg_type = data.get("type")

    if msg_type == "agent_hello":
        state.agent_info = data.get("agent", {})
        await _broadcast_agent_status(True)
        return

    if msg_type == "status_snapshot":
        state.system_status = data.get("status") or {}
        await _broadcast({
            "type": "status_snapshot",
            "status": state.system_status,
        })
        return

    if msg_type == "screenshot":
        request_id = data.get("request_id")
        if request_id and request_id in state.pending:
            future = state.pending.pop(request_id)
            if not future.done():
                future.set_result(data)

        await _broadcast({
            "type": "screenshot",
            "prompt_id": data.get("prompt_id"),
            "kind": data.get("kind", "result"),
            "image_b64": data.get("image_b64", ""),
            "taken_at": data.get("taken_at", _now()),
        })
        return

    if msg_type == "prompt_sent":
        prompt_id = data.get("prompt_id")
        ok = bool(data.get("ok", True))
        result = "Prompt VS Code ga yuborildi." if ok else "Prompt yuborilmadi."
        await _patch_history(
            prompt_id,
            status="sent" if ok else "error",
            result=result,
            completed_at=_now(),
        )
        await _broadcast({
            "type": "prompt_sent",
            "prompt_id": prompt_id,
            "ok": ok,
        })
        return

    if msg_type == "command_result":
        command_id = data.get("command_id")
        ok = bool(data.get("ok", False))
        await _patch_history(
            command_id,
            status="done" if ok else "error",
            result=data.get("message") or ("Bajarildi." if ok else "Xato."),
            data=data.get("data") or {},
            completed_at=data.get("completed_at") or _now(),
        )
        return

    if msg_type == "pong":
        return

    logger.info("Unknown agent message: %s", msg_type)


async def _on_client_msg(cid: str, data: dict):
    msg_type = data.get("type")
    conn = state.clients.get(cid)
    if not conn:
        return

    if msg_type == "send_prompt":
        text = _clean_text(data.get("text", ""))
        if not text:
            return
        entry = _new_history_entry("claude", text, conn.session, action="claude.prompt")
        await _record_history(entry)

        if not await _send_agent({
            "type": "send_prompt",
            "prompt_id": entry["id"],
            "text": text,
        }):
            await _patch_history(
                entry["id"],
                status="error",
                result="Local agent ulanmagan. agent.py ni ishga tushiring.",
                completed_at=_now(),
            )
            await _send_to(cid, {
                "type": "error",
                "message": "Local agent ulanmagan. agent.py ni ishga tushiring.",
            })
        return

    if msg_type == "run_command":
        text = _clean_text(data.get("text", ""))
        action = _clean_text(data.get("action", ""), max_length=120)
        label = _clean_text(data.get("label", "")) or text or action
        if not label:
            return

        entry = _new_history_entry("command", label, conn.session, action=action or None)
        await _record_history(entry)

        if not await _send_agent({
            "type": "run_command",
            "command_id": entry["id"],
            "text": text,
            "action": action,
            "params": data.get("params") or {},
            "confirmed": bool(data.get("confirmed", False)),
        }):
            await _patch_history(
                entry["id"],
                status="error",
                result="Local agent ulanmagan. agent.py ni ishga tushiring.",
                completed_at=_now(),
            )
            await _send_to(cid, {
                "type": "error",
                "message": "Local agent ulanmagan. agent.py ni ishga tushiring.",
            })
        return

    if msg_type == "screenshot":
        prompt_id = data.get("prompt_id")
        kind = data.get("kind", "result")

        if not state.agent_ws:
            await _send_to(cid, {"type": "error", "message": "Agent ulanmagan."})
            return

        request_id = str(uuid.uuid4())
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        state.pending[request_id] = future

        await state.agent_ws.send_json({
            "type": "screenshot",
            "request_id": request_id,
            "prompt_id": prompt_id,
            "kind": kind,
        })

        try:
            await asyncio.wait_for(asyncio.shield(future), timeout=20.0)
        except asyncio.TimeoutError:
            state.pending.pop(request_id, None)
            await _send_to(cid, {
                "type": "error",
                "message": "Screenshot 20 soniyada kelmadi.",
            })
        return

    if msg_type == "get_status":
        if state.agent_ws:
            await state.agent_ws.send_json({"type": "get_status"})
        await _send_to(cid, {
            "type": "status_snapshot",
            "status": state.system_status,
        })
        return

    if msg_type == "clear_history":
        state.history.clear()
        await _broadcast({"type": "history_cleared"})
        return

    if msg_type == "ping":
        await _send_to(cid, {"type": "pong"})


@app.get("/api/status")
async def api_status():
    if not _rest_allowed():
        return JSONResponse({"error": "Telegram auth required"}, status_code=403)
    return AgentStatus(
        connected=state.agent_ws is not None,
        last_seen=state.agent_last_seen,
        clients=len(state.clients),
        system=state.system_status,
    )


@app.get("/api/history")
async def api_history():
    if not _rest_allowed():
        return JSONResponse({"error": "Telegram auth required"}, status_code=403)
    return {"history": state.history[-100:], "total": len(state.history)}


@app.delete("/api/history")
async def api_clear():
    if not _rest_allowed():
        return JSONResponse({"error": "Telegram auth required"}, status_code=403)
    state.history.clear()
    await _broadcast({"type": "history_cleared"})
    return {"ok": True}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "agent": state.agent_ws is not None,
        "clients": len(state.clients),
    }


if FRONTEND_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
@app.get("/{path:path}")
async def spa(path: str = ""):
    index = FRONTEND_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return JSONResponse({"status": "GHOST Mini App", "docs": "/api/docs"})


def _client_session(ws: WebSocket):
    init_data = ws.query_params.get("init_data", "")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    auth_required = require_telegram_auth()

    if init_data:
        max_age = int(os.getenv("GHOST_INITDATA_MAX_AGE", "86400"))
        session, error = validate_init_data(init_data, bot_token, max_age)
        return session, error

    if auth_required:
        return None, "Mini App Telegram ichida ochilishi kerak."

    return dev_session(), None


def _agent_authorized(ws: WebSocket) -> bool:
    required = agent_token()
    if not required:
        return True
    supplied = (
        ws.query_params.get("token")
        or ws.headers.get("x-ghost-agent-token")
        or ""
    )
    return hmac.compare_digest(required, supplied)


def _rest_allowed() -> bool:
    return env_bool("GHOST_PUBLIC_API", not require_telegram_auth())


def _new_history_entry(kind: str, text: str, session, action: Optional[str] = None) -> dict:
    return Prompt(
        kind=kind,
        text=text,
        action=action,
        user=session.as_dict(),
    ).model_dump()


async def _record_history(entry: dict):
    state.history.append(entry)
    if len(state.history) > MAX_HISTORY:
        state.history = state.history[-MAX_HISTORY:]
    await _broadcast({"type": "new_prompt", "prompt": entry})


async def _patch_history(entry_id: Optional[str], **patch):
    if not entry_id:
        return
    entry = _find_history(entry_id)
    if not entry:
        return
    entry.update(patch)
    await _broadcast({"type": "history_updated", "entry": entry})


def _find_history(entry_id: str) -> Optional[dict]:
    for entry in reversed(state.history):
        if entry.get("id") == entry_id:
            return entry
    return None


async def _send_agent(payload: dict) -> bool:
    if not state.agent_ws:
        return False
    try:
        await state.agent_ws.send_json(payload)
        return True
    except Exception as exc:
        logger.warning("Agent send failed: %s", exc)
        state.agent_ws = None
        await _broadcast_agent_status(False)
        return False


async def _broadcast_agent_status(connected: bool):
    await _broadcast({
        "type": "agent_status",
        "connected": connected,
        "last_seen": state.agent_last_seen,
        "agent": state.agent_info,
    })


async def _broadcast(data: dict):
    dead: list[str] = []
    for cid, conn in list(state.clients.items()):
        try:
            await conn.ws.send_json(data)
        except Exception:
            dead.append(cid)
    for cid in dead:
        state.clients.pop(cid, None)


async def _send_to(cid: str, data: dict):
    conn = state.clients.get(cid)
    if not conn:
        return
    try:
        await conn.ws.send_json(data)
    except Exception:
        state.clients.pop(cid, None)


def _clean_text(value: str, max_length: int = MAX_TEXT_LENGTH) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_length]


def _now() -> str:
    return datetime.now().isoformat()


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

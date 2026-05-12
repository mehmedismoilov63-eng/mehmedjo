"""
GHOST Claude Bridge — FastAPI Backend
- /ws/agent  : Local Agent ulanadi (WebSocket)
- /ws/client : Mini App ulanadi (WebSocket)
- /api/*     : REST endpoints
- /          : Mini App frontend (static)
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from models import AgentStatus, Prompt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("ghost.backend")

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="GHOST Claude Bridge", version="1.0.0", docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global state ──────────────────────────────────────────────────────────────

class State:
    agent_ws:        Optional[WebSocket]          = None
    agent_last_seen: Optional[str]                = None
    clients:         Dict[str, WebSocket]         = {}
    pending:         Dict[str, asyncio.Future]    = {}
    history:         list                         = []   # max 200

state = State()

# ── Agent WebSocket ───────────────────────────────────────────────────────────

@app.websocket("/ws/agent")
async def ws_agent(ws: WebSocket):
    await ws.accept()
    state.agent_ws       = ws
    state.agent_last_seen = _now()
    logger.info("Agent ulandi")
    await _broadcast({"type": "agent_status", "connected": True})

    try:
        while True:
            data = await ws.receive_json()
            state.agent_last_seen = _now()
            await _on_agent_msg(data)
    except (WebSocketDisconnect, Exception) as e:
        logger.warning(f"Agent uzildi: {e}")
        state.agent_ws = None
        await _broadcast({"type": "agent_status", "connected": False})


async def _on_agent_msg(data: dict):
    t = data.get("type")

    if t == "screenshot":
        rid = data.get("request_id")
        if rid and rid in state.pending:
            fut = state.pending.pop(rid)
            if not fut.done():
                fut.set_result(data)
        await _broadcast({
            "type":       "screenshot",
            "prompt_id":  data.get("prompt_id"),
            "kind":       data.get("kind"),
            "image_b64":  data.get("image_b64"),
            "taken_at":   data.get("taken_at", _now()),
        })

    elif t == "prompt_sent":
        await _broadcast({
            "type":      "prompt_sent",
            "prompt_id": data.get("prompt_id"),
            "ok":        data.get("ok", True),
        })

    elif t == "pong":
        pass   # last_seen already updated

# ── Client WebSocket ──────────────────────────────────────────────────────────

@app.websocket("/ws/client")
async def ws_client(ws: WebSocket):
    await ws.accept()
    cid = str(uuid.uuid4())
    state.clients[cid] = ws
    logger.info(f"Client ulandi: {cid[:8]}")

    await ws.send_json({
        "type":            "init",
        "agent_connected": state.agent_ws is not None,
        "history":         state.history[-50:],
    })

    try:
        while True:
            data = await ws.receive_json()
            await _on_client_msg(cid, data)
    except (WebSocketDisconnect, Exception):
        state.clients.pop(cid, None)
        logger.info(f"Client uzildi: {cid[:8]}")


async def _on_client_msg(cid: str, data: dict):
    t = data.get("type")

    if t == "send_prompt":
        text = (data.get("text") or "").strip()
        if not text:
            return
        prompt = Prompt(text=text)
        entry  = prompt.model_dump()

        # Tarixga qo'shish (max 200)
        state.history.append(entry)
        if len(state.history) > 200:
            state.history = state.history[-200:]

        await _broadcast({"type": "new_prompt", "prompt": entry})

        if state.agent_ws:
            await state.agent_ws.send_json({
                "type":      "send_prompt",
                "prompt_id": prompt.id,
                "text":      text,
            })
        else:
            await _send_to(cid, {
                "type":    "error",
                "message": "Local Agent ulanmagan. agent.py ni ishga tushiring.",
            })

    elif t == "screenshot":
        prompt_id = data.get("prompt_id")
        kind      = data.get("kind", "result")

        if not state.agent_ws:
            await _send_to(cid, {"type": "error", "message": "Agent ulanmagan."})
            return

        rid    = str(uuid.uuid4())
        loop   = asyncio.get_event_loop()
        future = loop.create_future()
        state.pending[rid] = future

        await state.agent_ws.send_json({
            "type":       "screenshot",
            "request_id": rid,
            "prompt_id":  prompt_id,
            "kind":       kind,
        })

        try:
            await asyncio.wait_for(asyncio.shield(future), timeout=20.0)
        except asyncio.TimeoutError:
            state.pending.pop(rid, None)
            await _send_to(cid, {
                "type":    "error",
                "message": "Screenshot 20s da kelmadi. Agent javob bermadi.",
            })

    elif t == "clear_history":
        state.history.clear()
        await _broadcast({"type": "history_cleared"})

    elif t == "ping":
        await _send_to(cid, {"type": "pong"})

# ── REST API ──────────────────────────────────────────────────────────────────

@app.get("/api/status")
async def api_status():
    return AgentStatus(
        connected=state.agent_ws is not None,
        last_seen=state.agent_last_seen,
        clients=len(state.clients),
    )

@app.get("/api/history")
async def api_history():
    return {"history": state.history[-100:], "total": len(state.history)}

@app.delete("/api/history")
async def api_clear():
    state.history.clear()
    await _broadcast({"type": "history_cleared"})
    return {"ok": True}

@app.get("/health")
async def health():
    return {"status": "ok", "agent": state.agent_ws is not None}

# ── Static (frontend) ─────────────────────────────────────────────────────────

_frontend = os.path.join(os.path.dirname(__file__), "..", "frontend")

if os.path.isdir(_frontend):
    app.mount("/static", StaticFiles(directory=_frontend), name="static")

@app.get("/")
@app.get("/{path:path}")
async def spa(path: str = ""):
    index = os.path.join(_frontend, "index.html")
    if os.path.isfile(index):
        return FileResponse(index)
    return JSONResponse({"status": "GHOST Claude Bridge", "docs": "/api/docs"})

# ── Helpers ───────────────────────────────────────────────────────────────────

async def _broadcast(data: dict):
    dead = []
    for cid, ws in list(state.clients.items()):
        try:
            await ws.send_json(data)
        except Exception:
            dead.append(cid)
    for cid in dead:
        state.clients.pop(cid, None)

async def _send_to(cid: str, data: dict):
    ws = state.clients.get(cid)
    if ws:
        try:
            await ws.send_json(data)
        except Exception:
            state.clients.pop(cid, None)

def _now() -> str:
    return datetime.now().isoformat()

# ── Entry ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

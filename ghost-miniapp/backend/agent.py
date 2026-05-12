"""
GHOST Local Agent
Sizning kompyuteringizda ishlaydi.
Backend (Railway/local) bilan WebSocket orqali gaplashadi.
VS Code ni boshqaradi va screenshot oladi.
"""

import asyncio
import base64
import json
import logging
import os
import sys
import tempfile
import time
from datetime import datetime

import websockets
from websockets.exceptions import ConnectionClosed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [AGENT] %(levelname)s %(message)s",
)
logger = logging.getLogger("ghost.agent")

BACKEND_WS     = os.getenv("GHOST_BACKEND_URL", "ws://localhost:8000/ws/agent")
RECONNECT_DELAY = 3

# ── VS Code ───────────────────────────────────────────────────────────────────

def _focus_vscode() -> bool:
    try:
        import pygetwindow as gw
        wins = gw.getWindowsWithTitle("Visual Studio Code") or gw.getWindowsWithTitle("Code")
        if not wins:
            return False
        w = wins[0]
        w.restore()
        w.activate()
        time.sleep(0.4)
        return True
    except Exception as e:
        logger.error(f"VS Code focus: {e}")
        return False


def send_prompt_to_vscode(text: str) -> bool:
    """Promptni VS Code Kiro/Claude chat ga yozib Enter bosadi"""
    try:
        import pyautogui
        import pyperclip

        if not _focus_vscode():
            logger.error("VS Code topilmadi")
            return False

        time.sleep(0.3)

        # Command palette → Focus Chat Input
        pyautogui.hotkey("ctrl", "shift", "p")
        time.sleep(0.5)
        pyperclip.copy("Focus Chat Input")
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.4)
        pyautogui.press("enter")
        time.sleep(0.5)

        # Inputni tozalab prompt yozish
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)
        pyautogui.press("delete")
        time.sleep(0.1)
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)
        pyautogui.press("enter")

        logger.info(f"Prompt yuborildi: '{text[:80]}'")
        return True

    except Exception as e:
        logger.error(f"send_prompt: {e}")
        return False


def take_screenshot() -> str:
    """VS Code oynasi yoki butun ekran screenshot → base64 PNG"""
    try:
        import pyautogui
        import pygetwindow as gw

        wins = gw.getWindowsWithTitle("Visual Studio Code") or gw.getWindowsWithTitle("Code")
        if wins:
            w = wins[0]
            w.restore()
            w.activate()
            time.sleep(0.3)
            region = (
                max(0, w.left),
                max(0, w.top),
                max(100, w.width),
                max(100, w.height),
            )
            img = pyautogui.screenshot(region=region)
        else:
            img = pyautogui.screenshot()

        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        img.save(path, optimize=True)

        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        os.unlink(path)
        return b64

    except Exception as e:
        logger.error(f"screenshot: {e}")
        return ""

# ── Message handler ───────────────────────────────────────────────────────────

async def handle(ws, data: dict):
    t = data.get("type")

    if t == "send_prompt":
        prompt_id = data.get("prompt_id")
        text      = data.get("text", "")
        loop      = asyncio.get_event_loop()
        ok        = await loop.run_in_executor(None, send_prompt_to_vscode, text)
        await ws.send(json.dumps({"type": "prompt_sent", "prompt_id": prompt_id, "ok": ok}))

    elif t == "screenshot":
        rid       = data.get("request_id")
        prompt_id = data.get("prompt_id")
        kind      = data.get("kind", "result")
        loop      = asyncio.get_event_loop()
        b64       = await loop.run_in_executor(None, take_screenshot)
        await ws.send(json.dumps({
            "type":       "screenshot",
            "request_id": rid,
            "prompt_id":  prompt_id,
            "kind":       kind,
            "image_b64":  b64,
            "taken_at":   datetime.now().isoformat(),
        }))
        logger.info(f"Screenshot yuborildi [{kind}]")

    elif t == "ping":
        await ws.send(json.dumps({"type": "pong"}))

# ── Main loop ─────────────────────────────────────────────────────────────────

async def run():
    while True:
        try:
            logger.info(f"Ulanilmoqda: {BACKEND_WS}")
            async with websockets.connect(
                BACKEND_WS,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5,
            ) as ws:
                logger.info("✅ Backend ga ulandi")
                async for raw in ws:
                    try:
                        await handle(ws, json.loads(raw))
                    except Exception as e:
                        logger.error(f"handle xato: {e}")

        except (ConnectionClosed, ConnectionRefusedError, OSError) as e:
            logger.warning(f"Uzildi ({e}). {RECONNECT_DELAY}s kutilmoqda...")
        except Exception as e:
            logger.error(f"Kutilmagan xato: {e}")

        await asyncio.sleep(RECONNECT_DELAY)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        BACKEND_WS = sys.argv[1]
    logger.info(f"GHOST Local Agent | Backend: {BACKEND_WS}")
    asyncio.run(run())

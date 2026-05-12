"""
GHOST Local Agent.

Runs on the Windows machine, connects to the Mini App backend over WebSocket,
executes approved local commands, drives VS Code chat, and returns screenshots.
"""

import asyncio
import base64
import json
import logging
import os
import platform
import socket
import subprocess
import sys
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import websockets
from websockets.exceptions import ConnectionClosed


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [GHOST AGENT] %(levelname)s %(message)s",
)
logger = logging.getLogger("ghost.agent")

RECONNECT_DELAY = int(os.getenv("GHOST_AGENT_RECONNECT_DELAY", "3"))
DANGEROUS_ACTIONS = {
    "system.lock",
    "system.sleep",
    "system.shutdown",
    "system.restart",
}


def _focus_vscode() -> bool:
    try:
        import pygetwindow as gw

        wins = (
            gw.getWindowsWithTitle("Visual Studio Code")
            or gw.getWindowsWithTitle("Code")
        )
        if not wins:
            return False
        window = wins[0]
        window.restore()
        window.activate()
        time.sleep(0.4)
        return True
    except Exception as exc:
        logger.error("VS Code focus failed: %s", exc)
        return False


def send_prompt_to_vscode(text: str) -> bool:
    try:
        import pyautogui
        import pyperclip

        if not _focus_vscode():
            _open_vscode()
            if not _focus_vscode():
                logger.error("VS Code window was not found")
                return False

        time.sleep(0.3)
        pyautogui.hotkey("ctrl", "shift", "p")
        time.sleep(0.5)
        pyperclip.copy("Focus Chat Input")
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.4)
        pyautogui.press("enter")
        time.sleep(0.5)

        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.1)
        pyautogui.press("delete")
        time.sleep(0.1)
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)
        pyautogui.press("enter")

        logger.info("Prompt sent to VS Code: %s", text[:80])
        return True
    except Exception as exc:
        logger.error("send_prompt failed: %s", exc)
        return False


def _open_vscode() -> bool:
    try:
        subprocess.Popen(
            ["code", str(PROJECT_ROOT)],
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(2)
        return True
    except Exception as exc:
        logger.error("VS Code open failed: %s", exc)
        return False


def take_screenshot(target: str = "vscode") -> str:
    try:
        import pyautogui
        import pygetwindow as gw

        img = None
        if target == "active":
            window = gw.getActiveWindow()
            if window:
                window.restore()
                window.activate()
                time.sleep(0.3)
                region = (
                    max(0, window.left),
                    max(0, window.top),
                    max(100, window.width),
                    max(100, window.height),
                )
                img = pyautogui.screenshot(region=region)

        if img is None and target == "vscode":
            wins = (
                gw.getWindowsWithTitle("Visual Studio Code")
                or gw.getWindowsWithTitle("Code")
            )
            if wins:
                window = wins[0]
                window.restore()
                window.activate()
                time.sleep(0.3)
                region = (
                    max(0, window.left),
                    max(0, window.top),
                    max(100, window.width),
                    max(100, window.height),
                )
                img = pyautogui.screenshot(region=region)

        if img is None:
            img = pyautogui.screenshot()

        buffer = BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        return base64.b64encode(buffer.getvalue()).decode("ascii")
    except Exception as exc:
        logger.error("screenshot failed: %s", exc)
        return ""


async def handle(ws, data: dict):
    msg_type = data.get("type")

    if msg_type == "send_prompt":
        prompt_id = data.get("prompt_id")
        text = data.get("text", "")
        loop = asyncio.get_event_loop()
        ok = await loop.run_in_executor(None, send_prompt_to_vscode, text)
        await ws.send(json.dumps({
            "type": "prompt_sent",
            "prompt_id": prompt_id,
            "ok": ok,
        }))
        return

    if msg_type == "run_command":
        command_id = data.get("command_id")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, execute_command, data)
        await ws.send(json.dumps({
            "type": "command_result",
            "command_id": command_id,
            **result,
        }))
        status = result.get("data", {}).get("status")
        if status:
            await ws.send(json.dumps({
                "type": "status_snapshot",
                "status": status,
            }))
        return

    if msg_type == "screenshot":
        request_id = data.get("request_id")
        prompt_id = data.get("prompt_id")
        kind = data.get("kind", "result")
        target = "screen" if kind == "screen" else "vscode"
        loop = asyncio.get_event_loop()
        image_b64 = await loop.run_in_executor(None, take_screenshot, target)
        await ws.send(json.dumps({
            "type": "screenshot",
            "request_id": request_id,
            "prompt_id": prompt_id,
            "kind": kind,
            "image_b64": image_b64,
            "taken_at": datetime.now().isoformat(),
        }))
        logger.info("Screenshot sent [%s]", kind)
        return

    if msg_type == "get_status":
        await ws.send(json.dumps({
            "type": "status_snapshot",
            "status": get_system_status(),
        }))
        return

    if msg_type == "ping":
        await ws.send(json.dumps({"type": "pong"}))


def execute_command(payload: dict) -> dict:
    text = (payload.get("text") or "").strip()
    action = (payload.get("action") or "").strip()
    params = payload.get("params") or {}
    confirmed = bool(payload.get("confirmed", False))

    if not action and text:
        intent = _parse_intent(text)
        if intent:
            action = intent.get("action", "")
            params = intent.get("parameters", {}) or {}
        else:
            action = _action_from_text(text)

    if not action:
        return _fail("Buyruq tushunilmadi.")

    if action in DANGEROUS_ACTIONS and not confirmed:
        return {
            "ok": False,
            "message": "Bu buyruq tasdiqlashni talab qiladi.",
            "data": {"needs_confirm": True, "action": action},
            "completed_at": datetime.now().isoformat(),
        }

    try:
        return execute_action(action, params, text)
    except Exception as exc:
        logger.exception("Command failed: %s", action)
        return _fail(f"Xatolik: {exc}")


def execute_action(action: str, params: dict[str, Any], raw_text: str = "") -> dict:
    if action in {"agent.status", "system.status"}:
        status = get_system_status()
        return _ok("Tizim holati yangilandi.", {"status": status})

    if action == "system.screenshot":
        image_b64 = take_screenshot("screen")
        return _ok("Skrinshot olindi.", {"image_b64": image_b64, "kind": "screen"})

    if action == "system.screenshot_window":
        image_b64 = take_screenshot("active")
        return _ok("Faol ish oynasi skrinshoti olindi.", {
            "image_b64": image_b64,
            "kind": "window",
        })

    if action == "system.volume_up":
        amount = int(params.get("amount", 10) or 10)
        return _volume_change(amount, "up")

    if action == "system.volume_down":
        amount = int(params.get("amount", 10) or 10)
        return _volume_change(amount, "down")

    if action == "system.volume_mute":
        return _volume_mute()

    if action == "system.volume_set":
        level = int(params.get("level", 50) or 50)
        return _volume_set(level)

    if action == "system.brightness_up":
        return _brightness_change(int(params.get("amount", 10) or 10), "up")

    if action == "system.brightness_down":
        return _brightness_change(int(params.get("amount", 10) or 10), "down")

    if action == "system.lock":
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=False)
        return _ok("Ekran qulflandi.")

    if action == "system.sleep":
        subprocess.run(
            ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
            check=False,
        )
        return _ok("Kompyuter uyqu rejimiga yuborildi.")

    if action == "system.shutdown":
        subprocess.run(["shutdown", "/s", "/t", "30"], check=False)
        return _ok("Kompyuter 30 soniyadan keyin o'chadi.")

    if action == "system.restart":
        subprocess.run(["shutdown", "/r", "/t", "30"], check=False)
        return _ok("Kompyuter 30 soniyadan keyin qayta yuklanadi.")

    if action == "system.cancel_shutdown":
        subprocess.run(["shutdown", "/a"], check=False)
        return _ok("Rejalashtirilgan o'chirish bekor qilindi.")

    if action == "system.time":
        return _ok(datetime.now().strftime("Hozir soat %H:%M."))

    if action == "system.date":
        return _ok(datetime.now().strftime("Bugungi sana: %Y-%m-%d."))

    if action == "system.battery":
        status = get_system_status()
        battery = status.get("battery")
        return _ok(f"Batareya: {battery if battery is not None else 'topilmadi'}.")

    if action == "system.info":
        status = get_system_status()
        return _ok(
            f"{status.get('hostname')} | CPU {status.get('cpu')}% | "
            f"RAM {status.get('ram')}%"
        )

    if action == "system.disk":
        return _ok(_disk_info())

    if action == "system.network":
        status = get_system_status()
        return _ok(f"IP: {status.get('ip', 'topilmadi')}")

    if action == "system.processes":
        return _ok(_top_processes())

    if action == "app.open":
        app_name = params.get("app_name") or _strip_command_words(raw_text)
        return _app_open(app_name)

    if action == "app.close":
        app_name = params.get("app_name") or _strip_command_words(raw_text)
        return _app_close(app_name)

    if action == "app.switch":
        app_name = params.get("app_name") or _strip_command_words(raw_text)
        return _app_switch(app_name)

    if action == "app.running_list":
        return _ok(_running_apps())

    if action == "browser.open_url":
        return _open_url(params.get("url") or raw_text)

    if action == "browser.search":
        query = params.get("query") or raw_text
        return _open_url("https://www.google.com/search?q=" + query)

    if action == "youtube.play":
        query = params.get("query") or raw_text
        return _open_url("https://www.youtube.com/results?search_query=" + query)

    if action in {
        "web.open_github",
        "web.open_gmail",
        "web.open_maps",
        "web.open_translate",
        "web.open_news",
    }:
        urls = {
            "web.open_github": "https://github.com",
            "web.open_gmail": "https://mail.google.com",
            "web.open_maps": "https://maps.google.com",
            "web.open_translate": "https://translate.google.com",
            "web.open_news": "https://news.google.com",
        }
        return _open_url(urls[action])

    if action == "media.play_pause":
        return _press("playpause", "Media play/pause bosildi.")
    if action == "media.next":
        return _press("nexttrack", "Keyingi trek.")
    if action == "media.prev":
        return _press("prevtrack", "Oldingi trek.")

    hotkeys = {
        "window.minimize": ("win", "down"),
        "window.maximize": ("win", "up"),
        "window.close": ("alt", "f4"),
        "window.switch": ("alt", "tab"),
        "window.desktop": ("win", "d"),
        "clipboard.copy": ("ctrl", "c"),
        "clipboard.paste": ("ctrl", "v"),
        "clipboard.select_all": ("ctrl", "a"),
        "keyboard.undo": ("ctrl", "z"),
        "keyboard.redo": ("ctrl", "y"),
        "keyboard.save": ("ctrl", "s"),
        "keyboard.new_tab": ("ctrl", "t"),
        "keyboard.close_tab": ("ctrl", "w"),
        "keyboard.refresh": ("f5",),
        "keyboard.fullscreen": ("f11",),
        "keyboard.enter": ("enter",),
        "keyboard.escape": ("escape",),
        "keyboard.delete": ("delete",),
    }
    if action in hotkeys:
        return _hotkey(*hotkeys[action])

    if action == "keyboard.type":
        return _type_text(params.get("text") or raw_text)

    if action == "clipboard.read":
        return _clipboard_read()

    if action == "system.clear_clipboard":
        return _clipboard_clear()

    return _fail("Bu buyruq mini app agentida hali yo'q.")


def get_system_status() -> dict[str, Any]:
    status: dict[str, Any] = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "time": datetime.now().isoformat(),
    }
    try:
        import psutil

        memory = psutil.virtual_memory()
        battery = psutil.sensors_battery()
        disk = psutil.disk_usage(Path.home().anchor or "/")
        status.update({
            "cpu": round(psutil.cpu_percent(interval=0.2), 1),
            "ram": round(memory.percent, 1),
            "battery": round(battery.percent, 1) if battery else None,
            "charging": bool(battery.power_plugged) if battery else None,
            "disk_free_gb": round(disk.free / (1024 ** 3), 1),
            "disk_total_gb": round(disk.total / (1024 ** 3), 1),
            "ip": _local_ip(),
        })
    except Exception as exc:
        status["error"] = str(exc)
    return status


def _parse_intent(text: str) -> dict | None:
    try:
        from config import Config
        from core.intent_parser import IntentParser

        parser = IntentParser(Config())
        return parser.parse(text)
    except Exception as exc:
        logger.debug("Intent parser unavailable: %s", exc)
        return None


def _action_from_text(text: str) -> str:
    normalized = text.strip().lower()
    aliases = {
        "status": "system.status",
        "holat": "system.status",
        "tizim": "system.status",
        "screenshot": "system.screenshot",
        "skrinshot": "system.screenshot",
        "lock": "system.lock",
        "qulfla": "system.lock",
        "mute": "system.volume_mute",
        "desktop": "window.desktop",
        "copy": "clipboard.copy",
        "paste": "clipboard.paste",
    }
    return aliases.get(normalized, "")


def _volume_change(amount: int, direction: str) -> dict:
    try:
        from modules.system.volume import VolumeController

        controller = VolumeController()
        ok = (
            controller.increase_volume(amount)
            if direction == "up"
            else controller.decrease_volume(amount)
        )
        if ok:
            current = round(controller.get_volume() * 100)
            return _ok(f"Ovoz {current}% bo'ldi.", {"volume": current})
    except Exception as exc:
        logger.debug("VolumeController fallback: %s", exc)

    key = "volumeup" if direction == "up" else "volumedown"
    presses = max(1, min(10, amount // 5 or 1))
    return _press(key, "Ovoz tugmasi bosildi.", presses=presses)


def _volume_mute() -> dict:
    try:
        from modules.system.volume import VolumeController

        controller = VolumeController()
        ok = controller.toggle_mute()
        if ok:
            return _ok("Mute holati almashtirildi.")
    except Exception as exc:
        logger.debug("Mute fallback: %s", exc)
    return _press("volumemute", "Mute tugmasi bosildi.")


def _volume_set(level: int) -> dict:
    level = max(0, min(100, level))
    try:
        from modules.system.volume import VolumeController

        controller = VolumeController()
        if controller.set_volume(level / 100):
            return _ok(f"Ovoz {level}% ga o'rnatildi.", {"volume": level})
    except Exception as exc:
        logger.debug("Set volume failed: %s", exc)
    return _fail("Ovozni aniq darajaga o'rnatib bo'lmadi.")


def _brightness_change(amount: int, direction: str) -> dict:
    try:
        import screen_brightness_control as sbc

        current = sbc.get_brightness(display=0)[0]
        value = current + amount if direction == "up" else current - amount
        value = max(0, min(100, value))
        sbc.set_brightness(value, display=0)
        return _ok(f"Yorqinlik {value}% bo'ldi.", {"brightness": value})
    except Exception as exc:
        logger.debug("Brightness failed: %s", exc)
        return _fail("Yorqinlikni o'zgartirib bo'lmadi.")


def _app_open(app_name: str) -> dict:
    app_name = (app_name or "").strip()
    if not app_name:
        return _fail("Qaysi ilova ochilishi kerak?")
    try:
        from config import Config
        from modules.system.applications import AppManager

        if AppManager(Config()).open_app(app_name):
            return _ok(f"{app_name} ochildi.")
    except Exception as exc:
        logger.debug("AppManager open fallback: %s", exc)
    try:
        subprocess.Popen(app_name, shell=True)
        return _ok(f"{app_name} ishga tushirildi.")
    except Exception:
        return _fail(f"{app_name} topilmadi.")


def _app_close(app_name: str) -> dict:
    app_name = (app_name or "").strip()
    if not app_name:
        return _fail("Qaysi ilova yopilishi kerak?")
    try:
        from config import Config
        from modules.system.applications import AppManager

        if AppManager(Config()).close_app(app_name):
            return _ok(f"{app_name} yopildi.")
    except Exception as exc:
        logger.debug("AppManager close fallback: %s", exc)
    subprocess.run(["taskkill", "/IM", app_name, "/F"], check=False)
    return _ok(f"{app_name} yopish buyrug'i yuborildi.")


def _app_switch(app_name: str) -> dict:
    app_name = (app_name or "").strip()
    if not app_name:
        return _fail("Qaysi oynaga o'tish kerak?")
    try:
        from config import Config
        from modules.system.applications import AppManager

        if AppManager(Config()).switch_to_app(app_name):
            return _ok(f"{app_name} oynasiga o'tildi.")
    except Exception as exc:
        logger.debug("App switch failed: %s", exc)
    return _fail(f"{app_name} oynasi topilmadi.")


def _running_apps() -> str:
    try:
        import psutil

        names = set()
        for proc in psutil.process_iter(["name"]):
            name = proc.info.get("name")
            if name and not name.lower().startswith("svchost"):
                names.add(name.replace(".exe", ""))
        top = sorted(names)[:12]
        return "Ochiq jarayonlar: " + ", ".join(top)
    except Exception:
        return "Ilovalar ro'yxatini olib bo'lmadi."


def _disk_info() -> str:
    try:
        import psutil

        parts = []
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                parts.append(
                    f"{partition.device}: "
                    f"{usage.free // (1024 ** 3)}GB bo'sh / "
                    f"{usage.total // (1024 ** 3)}GB"
                )
            except Exception:
                continue
        return " | ".join(parts) if parts else "Disk ma'lumoti topilmadi."
    except Exception:
        return "Disk ma'lumotini olib bo'lmadi."


def _top_processes() -> str:
    try:
        import psutil

        rows = []
        for proc in psutil.process_iter(["name", "cpu_percent"]):
            try:
                rows.append(proc.info)
            except Exception:
                continue
        top = sorted(rows, key=lambda item: item.get("cpu_percent") or 0, reverse=True)[:5]
        return " | ".join(f"{p['name']}: {p.get('cpu_percent', 0):.1f}%" for p in top)
    except Exception:
        return "Jarayonlar ma'lumotini olib bo'lmadi."


def _open_url(url: str) -> dict:
    import webbrowser
    from urllib.parse import quote_plus

    url = (url or "").strip()
    if not url:
        return _fail("URL yoki qidiruv matni kerak.")
    if " " in url and not url.startswith("http"):
        url = "https://www.google.com/search?q=" + quote_plus(url)
    elif not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return _ok(f"Ochildi: {url}", {"url": url})


def _hotkey(*keys: str) -> dict:
    try:
        import pyautogui

        if len(keys) == 1:
            pyautogui.press(keys[0])
        else:
            pyautogui.hotkey(*keys)
        return _ok("Tugma kombinatsiyasi bajarildi.", {"keys": keys})
    except Exception as exc:
        return _fail(f"Tugma bosilmadi: {exc}")


def _press(key: str, message: str, presses: int = 1) -> dict:
    try:
        import pyautogui

        pyautogui.press(key, presses=presses)
        return _ok(message, {"key": key, "presses": presses})
    except Exception as exc:
        return _fail(f"Tugma bosilmadi: {exc}")


def _type_text(text: str) -> dict:
    text = (text or "").strip()
    if not text:
        return _fail("Yoziladigan matn topilmadi.")
    try:
        import pyautogui
        import pyperclip

        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        return _ok("Matn joylashtirildi.")
    except Exception as exc:
        return _fail(f"Matn yozilmadi: {exc}")


def _clipboard_read() -> dict:
    try:
        import pyperclip

        text = pyperclip.paste()
        if not text:
            return _ok("Clipboard bo'sh.")
        preview = text if len(text) <= 800 else text[:800] + "..."
        return _ok(preview, {"clipboard": preview})
    except Exception as exc:
        return _fail(f"Clipboard o'qilmadi: {exc}")


def _clipboard_clear() -> dict:
    try:
        import pyperclip

        pyperclip.copy("")
        return _ok("Clipboard tozalandi.")
    except Exception as exc:
        return _fail(f"Clipboard tozalanmadi: {exc}")


def _strip_command_words(text: str) -> str:
    lowered = (text or "").lower()
    for word in [
        "open",
        "start",
        "close",
        "switch",
        "och",
        "ishga tushir",
        "yop",
        "almashtir",
        "ga o't",
        "ni",
    ]:
        lowered = lowered.replace(word, " ")
    return " ".join(lowered.split())


def _local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except Exception:
        return socket.gethostbyname(socket.gethostname())


def _ok(message: str, data: dict[str, Any] | None = None) -> dict:
    return {
        "ok": True,
        "message": message,
        "data": data or {},
        "completed_at": datetime.now().isoformat(),
    }


def _fail(message: str, data: dict[str, Any] | None = None) -> dict:
    return {
        "ok": False,
        "message": message,
        "data": data or {},
        "completed_at": datetime.now().isoformat(),
    }


def build_backend_ws_url() -> str:
    raw = os.getenv("GHOST_BACKEND_URL", "ws://localhost:8000/ws/agent").strip()
    parsed = urlparse(raw)
    scheme = parsed.scheme

    if scheme in {"http", "https"}:
        scheme = "wss" if scheme == "https" else "ws"
    elif scheme not in {"ws", "wss"}:
        raw = "ws://" + raw
        parsed = urlparse(raw)
        scheme = "ws"

    path = parsed.path.rstrip("/")
    if not path.endswith("/ws/agent"):
        path = (path + "/ws/agent") if path else "/ws/agent"

    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    token = os.getenv("GHOST_AGENT_TOKEN", "").strip()
    if token:
        query["token"] = token

    return urlunparse((
        scheme,
        parsed.netloc,
        path,
        "",
        urlencode(query),
        "",
    ))


def _redact_url(url: str) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if "token" in query:
        query["token"] = "***"
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        "",
        urlencode(query),
        "",
    ))


async def run():
    while True:
        backend_ws = build_backend_ws_url()
        try:
            logger.info("Connecting to %s", _redact_url(backend_ws))
            async with websockets.connect(
                backend_ws,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5,
                max_size=8 * 1024 * 1024,
            ) as ws:
                await ws.send(json.dumps({
                    "type": "agent_hello",
                    "agent": {
                        "hostname": socket.gethostname(),
                        "version": "2.0.0",
                        "platform": platform.platform(),
                    },
                }))
                await ws.send(json.dumps({
                    "type": "status_snapshot",
                    "status": get_system_status(),
                }))
                logger.info("Connected to backend")

                async for raw in ws:
                    try:
                        await handle(ws, json.loads(raw))
                    except Exception as exc:
                        logger.error("Message handling failed: %s", exc)

        except (ConnectionClosed, ConnectionRefusedError, OSError) as exc:
            logger.warning("Disconnected (%s). Retrying in %ss...", exc, RECONNECT_DELAY)
        except Exception as exc:
            logger.error("Unexpected error: %s", exc)

        await asyncio.sleep(RECONNECT_DELAY)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        os.environ["GHOST_BACKEND_URL"] = sys.argv[1]
    logger.info("GHOST Local Agent | Backend: %s", _redact_url(build_backend_ws_url()))
    asyncio.run(run())

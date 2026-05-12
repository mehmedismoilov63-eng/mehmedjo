"""
GHOST Advanced Features
Professional funksiyalar to'plami
"""

import os
import logging
import threading
import subprocess
import tempfile
import time
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
# 1. CLIPBOARD MANAGER - nusxalangan matnni o'qish
# ══════════════════════════════════════════════════════════════════

def read_clipboard() -> str:
    """Clipboard dagi matnni qaytaradi"""
    try:
        import pyperclip
        text = pyperclip.paste()
        if text and text.strip():
            # Uzun matnni qisqartirish
            if len(text) > 200:
                return f"Clipboard: {text[:200]}... ({len(text)} belgi)"
            return f"Clipboard: {text}"
        return "Clipboard bo'sh"
    except Exception as e:
        logger.error(f"Clipboard read error: {e}")
        return "Clipboard o'qib bo'lmadi"


def write_clipboard(text: str) -> str:
    """Matnni clipboard ga yozish"""
    try:
        import pyperclip
        pyperclip.copy(text)
        return f"Clipboard ga yozildi: {text[:50]}"
    except Exception as e:
        logger.error(f"Clipboard write error: {e}")
        return "Clipboard ga yozib bo'lmadi"


# ══════════════════════════════════════════════════════════════════
# 2. INTERNET TEZLIGI
# ══════════════════════════════════════════════════════════════════

def check_internet_speed() -> str:
    """Internet tezligini o'lchash (bir necha soniya ketadi)"""
    try:
        import speedtest
        st = speedtest.Speedtest(secure=True)
        st.get_best_server()

        download = st.download() / 1_000_000  # Mbps
        upload = st.upload() / 1_000_000      # Mbps
        ping = st.results.ping

        return (
            f"🌐 Internet tezligi:\n"
            f"⬇️ Yuklab olish: {download:.1f} Mbps\n"
            f"⬆️ Yuklash: {upload:.1f} Mbps\n"
            f"📡 Ping: {ping:.0f} ms"
        )
    except Exception as e:
        logger.error(f"Speed test error: {e}")
        return "Internet tezligini o'lchab bo'lmadi"


def check_internet_connection() -> str:
    """Internet ulanishini tekshirish"""
    try:
        import socket
        socket.setdefaulttimeout(3)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return "✅ Internet ulanishi mavjud"
    except Exception:
        return "❌ Internet ulanishi yo'q"


# ══════════════════════════════════════════════════════════════════
# 3. PAROL GENERATORI
# ══════════════════════════════════════════════════════════════════

def generate_password(length: int = 16, include_symbols: bool = True) -> str:
    """Kuchli parol generatsiya qilish"""
    try:
        import secrets
        import string

        chars = string.ascii_letters + string.digits
        if include_symbols:
            chars += "!@#$%^&*"

        password = ''.join(secrets.choice(chars) for _ in range(length))

        # Clipboard ga ham nusxalash
        try:
            import pyperclip
            pyperclip.copy(password)
            return f"🔐 Parol: {password}\n(Clipboard ga nusxalandi)"
        except Exception:
            return f"🔐 Parol: {password}"

    except Exception as e:
        logger.error(f"Password gen error: {e}")
        return "Parol generatsiya qilib bo'lmadi"


# ══════════════════════════════════════════════════════════════════
# 4. WINDOWS TOAST NOTIFICATION
# ══════════════════════════════════════════════════════════════════

def show_notification(title: str, message: str, duration: int = 5) -> str:
    """Windows toast notification ko'rsatish"""
    try:
        from winotify import Notification, audio

        toast = Notification(
            app_id="GHOST Assistant",
            title=title,
            msg=message,
            duration="short" if duration <= 5 else "long",
            icon=os.path.abspath("assets/ghost_icon.png") if os.path.exists("assets/ghost_icon.png") else ""
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()
        return f"Bildirishnoma yuborildi: {title}"
    except Exception as e:
        logger.error(f"Notification error: {e}")
        # Fallback - PowerShell orqali
        try:
            script = f'''
            Add-Type -AssemblyName System.Windows.Forms
            $notify = New-Object System.Windows.Forms.NotifyIcon
            $notify.Icon = [System.Drawing.SystemIcons]::Information
            $notify.Visible = $true
            $notify.ShowBalloonTip({duration * 1000}, "{title}", "{message}", [System.Windows.Forms.ToolTipIcon]::Info)
            '''
            subprocess.run(["powershell", "-Command", script], capture_output=True)
            return f"Bildirishnoma: {title}"
        except Exception:
            return "Bildirishnoma yuborib bo'lmadi"


# ══════════════════════════════════════════════════════════════════
# 5. DIKTOFON - ovozni faylga yozish
# ══════════════════════════════════════════════════════════════════

class VoiceRecorder:
    """Ovozni faylga yozish"""

    def __init__(self):
        self._recording = False
        self._thread = None
        self._frames = []
        self._filename = None

    def start(self, duration: int = 30) -> str:
        """Yozishni boshlash"""
        if self._recording:
            return "Allaqachon yozilmoqda"
        try:
            import pyaudio
            self._recording = True
            self._frames = []
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._filename = f"recordings/voice_{timestamp}.wav"
            os.makedirs("recordings", exist_ok=True)

            self._thread = threading.Thread(
                target=self._record, args=(duration,), daemon=True
            )
            self._thread.start()
            return f"🎙️ Yozish boshlandi ({duration} soniya)"
        except Exception as e:
            logger.error(f"Record start error: {e}")
            return "Yozishni boshlab bo'lmadi"

    def stop(self) -> str:
        """Yozishni to'xtatish"""
        if not self._recording:
            return "Yozish amalga oshmayapti"
        self._recording = False
        if self._thread:
            self._thread.join(timeout=2)
        return f"✅ Yozish to'xtatildi: {self._filename}"

    def _record(self, duration: int):
        try:
            import pyaudio, wave
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024
            )
            start = time.time()
            while self._recording and (time.time() - start) < duration:
                data = stream.read(1024, exception_on_overflow=False)
                self._frames.append(data)

            stream.stop_stream()
            stream.close()
            pa.terminate()

            # Faylga saqlash
            if self._frames and self._filename:
                with wave.open(self._filename, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    wf.writeframes(b''.join(self._frames))
        except Exception as e:
            logger.error(f"Record error: {e}")
        finally:
            self._recording = False


# ══════════════════════════════════════════════════════════════════
# 6. TEZKOR REJIMLAR (Macro)
# ══════════════════════════════════════════════════════════════════

def work_mode() -> str:
    """Ish rejimi: shovqinni o'chirish, brauzer ochish"""
    try:
        import pyautogui
        # Ovozni o'chirish
        pyautogui.press('volumemute')
        # Do Not Disturb (Windows Focus Assist)
        subprocess.Popen(
            'powershell -Command "Set-ItemProperty -Path HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings -Name NOC_GLOBAL_SETTING_ALLOW_TOASTS_ABOVE_LOCK -Value 0"',
            shell=True, capture_output=True
        )
        return "💼 Ish rejimi yoqildi: ovoz o'chirildi, bildirishnomalar bloklandi"
    except Exception as e:
        return f"Ish rejimini yoqib bo'lmadi: {e}"


def rest_mode() -> str:
    """Dam olish rejimi: yorqinlikni kamaytirish, musiqa"""
    try:
        import screen_brightness_control as sbc
        sbc.set_brightness(30)
        return "🌙 Dam olish rejimi: yorqinlik 30% ga tushirildi"
    except Exception as e:
        return "Dam olish rejimini yoqib bo'lmadi"


def presentation_mode() -> str:
    """Prezentatsiya rejimi: to'liq ekran, bildirishnomalar o'chiq"""
    try:
        import pyautogui
        pyautogui.hotkey('win', 'p')  # Proyektor rejimi
        time.sleep(0.5)
        return "📊 Prezentatsiya rejimi: ekran ulash menyusi ochildi"
    except Exception as e:
        return "Prezentatsiya rejimini yoqib bo'lmadi"


# ══════════════════════════════════════════════════════════════════
# 7. FAYL QIDIRISH
# ══════════════════════════════════════════════════════════════════

def search_files(query: str, search_dir: str = None) -> str:
    """Fayl qidirish"""
    try:
        if not query:
            return "Nima qidirish kerak?"

        search_path = search_dir or os.path.expanduser("~")
        found = []
        query_lower = query.lower()

        for root, dirs, files in os.walk(search_path):
            # Tizim papkalarini o'tkazib yuborish
            dirs[:] = [d for d in dirs if not d.startswith('.') and
                       d not in ('AppData', 'Windows', 'Program Files')]
            for f in files:
                if query_lower in f.lower():
                    found.append(os.path.join(root, f))
                    if len(found) >= 5:
                        break
            if len(found) >= 5:
                break

        if found:
            result = f"🔍 Topildi ({len(found)} ta):\n"
            result += "\n".join(f"• {f}" for f in found[:5])
            return result
        return f"'{query}' nomli fayl topilmadi"

    except Exception as e:
        logger.error(f"File search error: {e}")
        return "Fayl qidirib bo'lmadi"


def open_file(filepath: str) -> str:
    """Faylni ochish"""
    try:
        if os.path.exists(filepath):
            os.startfile(filepath)
            return f"Fayl ochildi: {os.path.basename(filepath)}"
        return f"Fayl topilmadi: {filepath}"
    except Exception as e:
        return f"Faylni ochib bo'lmadi: {e}"


# ══════════════════════════════════════════════════════════════════
# 8. TIZIM MONITORING (Telegram ga yuborish)
# ══════════════════════════════════════════════════════════════════

def get_full_system_report() -> str:
    """To'liq tizim hisoboti"""
    try:
        import psutil, socket

        # CPU
        cpu = psutil.cpu_percent(interval=1)
        cpu_freq = psutil.cpu_freq()
        cpu_count = psutil.cpu_count()

        # RAM
        ram = psutil.virtual_memory()

        # Disk
        disk_parts = []
        for p in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(p.mountpoint)
                disk_parts.append(
                    f"  {p.device}: {usage.free//1024**3}GB bo'sh / {usage.total//1024**3}GB"
                )
            except Exception:
                pass

        # Tarmoq
        net = psutil.net_io_counters()
        ip = socket.gethostbyname(socket.gethostname())

        # Batareya
        bat = psutil.sensors_battery()
        bat_str = f"{bat.percent:.0f}% ({'quvvat' if bat.power_plugged else 'batareya'})" if bat else "yo'q"

        # Uptime
        boot = psutil.boot_time()
        uptime = datetime.now() - datetime.fromtimestamp(boot)
        hours = int(uptime.total_seconds() // 3600)

        report = (
            f"💻 GHOST Tizim Hisoboti\n"
            f"🕐 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"⚡ CPU: {cpu:.0f}% ({cpu_count} yadro"
            + (f", {cpu_freq.current:.0f}MHz" if cpu_freq else "") + ")\n"
            f"🧠 RAM: {ram.used//1024**2}MB / {ram.total//1024**2}MB ({ram.percent:.0f}%)\n"
            f"💾 Disk:\n" + "\n".join(disk_parts) + "\n"
            f"🌐 IP: {ip}\n"
            f"📡 Tarmoq: ⬇️{net.bytes_recv//1024**2}MB ⬆️{net.bytes_sent//1024**2}MB\n"
            f"🔋 Batareya: {bat_str}\n"
            f"⏱️ Uptime: {hours} soat"
        )
        return report

    except Exception as e:
        logger.error(f"System report error: {e}")
        return "Tizim hisobotini olib bo'lmadi"


# ══════════════════════════════════════════════════════════════════
# 9. EKRAN YOZUVI (qisqa)
# ══════════════════════════════════════════════════════════════════

def start_screen_recording(duration: int = 30) -> str:
    """Ekranni yozish (ffmpeg kerak)"""
    try:
        # ffmpeg mavjudligini tekshirish
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, timeout=3
        )
        if result.returncode != 0:
            return "ffmpeg o'rnatilmagan. https://ffmpeg.org dan yuklab oling"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("recordings", exist_ok=True)
        output = f"recordings/screen_{timestamp}.mp4"

        cmd = [
            "ffmpeg", "-y",
            "-f", "gdigrab",
            "-framerate", "15",
            "-i", "desktop",
            "-t", str(duration),
            "-vcodec", "libx264",
            "-preset", "ultrafast",
            output
        ]

        threading.Thread(
            target=lambda: subprocess.run(cmd, capture_output=True),
            daemon=True
        ).start()

        return f"🎬 Ekran yozuvi boshlandi ({duration} soniya): {output}"

    except FileNotFoundError:
        return "ffmpeg topilmadi. https://ffmpeg.org dan yuklab oling"
    except Exception as e:
        logger.error(f"Screen record error: {e}")
        return "Ekran yozuvini boshlab bo'lmadi"


# ══════════════════════════════════════════════════════════════════
# 10. TEZKOR HISOB-KITOB
# ══════════════════════════════════════════════════════════════════

def smart_calculate(expression: str) -> str:
    """Aqlli hisoblash - foiz, valyuta, o'lchamlar"""
    try:
        import re

        # Foiz hisoblash: "300 ning 15 foizi"
        pct = re.search(r"(\d+(?:\.\d+)?)\s*(?:ning|из|от)?\s*(\d+(?:\.\d+)?)\s*(?:foiz|процент|%)", expression)
        if pct:
            base, percent = float(pct.group(1)), float(pct.group(2))
            result = base * percent / 100
            return f"{base} ning {percent}% = {result:.2f}"

        # Foiz qo'shish: "500 ga 20 foiz qo'sh"
        add_pct = re.search(r"(\d+(?:\.\d+)?)\s*(?:ga|к|плюс)\s*(\d+(?:\.\d+)?)\s*(?:foiz|%)", expression)
        if add_pct:
            base, percent = float(add_pct.group(1)), float(add_pct.group(2))
            result = base * (1 + percent / 100)
            return f"{base} + {percent}% = {result:.2f}"

        # Oddiy matematik
        safe = re.sub(r"[^\d\s\+\-\*\/\(\)\.\,]", "", expression.replace(",", "."))
        if safe.strip():
            result = eval(safe)
            if isinstance(result, float) and result == int(result):
                result = int(result)
            return f"= {result}"

        return "Ifodani tushunmadim"

    except Exception as e:
        return f"Hisoblashda xatolik: {e}"


# ══════════════════════════════════════════════════════════════════
# 11. LOCK OCHISH - PIN yoki parol bilan
# ══════════════════════════════════════════════════════════════════

def unlock_screen(pin: str = None) -> str:
    """
    Windows lock ekranini ochish.
    
    Usullar:
    1. PIN/parol bilan - pyautogui orqali avtomatik kiritish
    2. PINsiz - faqat ekranni uyg'otish
    """
    try:
        import pyautogui
        import time

        # Ekranni uyg'otish - sichqonchani qimirlatish
        pyautogui.moveRel(0, 1, duration=0.1)
        pyautogui.moveRel(0, -1, duration=0.1)
        time.sleep(0.3)

        # Enter bosish (lock ekranini ochish)
        pyautogui.press('enter')
        time.sleep(0.5)

        if pin:
            # PIN kiritish
            pyautogui.typewrite(str(pin), interval=0.05)
            time.sleep(0.2)
            pyautogui.press('enter')
            logger.info(f"Lock ekrani PIN bilan ochildi")
            return "🔓 Ekran PIN bilan ochildi"
        else:
            logger.info("Ekran uyg'otildi (PIN kiritilmadi)")
            return "🔓 Ekran uyg'otildi"

    except Exception as e:
        logger.error(f"Unlock error: {e}")
        return f"Ekranni ochib bo'lmadi: {e}"


def set_unlock_pin(pin: str) -> str:
    """
    GHOST uchun unlock PIN ni .env ga saqlash
    (Windows parolini o'zgartirmaydi - faqat GHOST uchun)
    """
    try:
        env_path = ".env"
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()

        if "GHOST_UNLOCK_PIN=" in content:
            import re
            content = re.sub(r"GHOST_UNLOCK_PIN=.*", f"GHOST_UNLOCK_PIN={pin}", content)
        else:
            content += f"\n# GHOST unlock PIN\nGHOST_UNLOCK_PIN={pin}\n"

        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"✅ Unlock PIN saqlandi"
    except Exception as e:
        return f"PIN saqlashda xatolik: {e}"


def get_unlock_pin() -> str:
    """Saqlangan unlock PIN ni olish"""
    return os.getenv("GHOST_UNLOCK_PIN", "")

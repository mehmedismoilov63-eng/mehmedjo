"""
Gemini AI Module - GHOST Assistant uchun AI miyasi
gemini-2.0-flash modeli - tez va bepul tier mavjud.
"""

import os
import json
import logging
from typing import Optional, Dict, Any

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    genai = None
    GEMINI_AVAILABLE = False

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sen GHOST - aqlli ovozli yordamchi.
Foydalanuvchi rus yoki o'zbek tilida gapiradi.
Qisqa, aniq javob ber (1-2 gap).

Agar tizim buyrug'i bo'lsa, FAQAT JSON qaytargin (boshqa matn yo'q):
{"action": "buyruq", "params": {...}, "response": "foydalanuvchiga javob"}

Mavjud buyruqlar:
- app.open / app.close  → params: {"app_name": "telegram|chrome|discord|..."}
- system.volume_up / system.volume_down → params: {"amount": 10}
- system.volume_mute
- system.screenshot
- system.brightness_up / system.brightness_down → params: {"amount": 10}
- system.shutdown / system.restart / system.sleep

Oddiy savol bo'lsa - faqat matn bilan javob ber.
Javob tilini foydalanuvchi tili bilan moslashtir."""


class GeminiAI:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        self.model = None
        self.chat = None
        self._model_name = ""

        if not GEMINI_AVAILABLE:
            logger.warning("google-generativeai o'rnatilmagan")
            return

        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            logger.warning("GEMINI_API_KEY .env faylida sozlanmagan")
            return

        try:
            genai.configure(api_key=self.api_key)

            # Model tanlash: limit tugasa keyingisiga o'tadi
            for model_name in [
                "gemini-1.5-flash-8b",   # eng ko'p limit: 15 req/min, 1500/day
                "gemini-1.5-flash",       # 15 req/min, 1500/day
                "gemini-2.0-flash",       # 15 req/min
            ]:
                try:
                    self.model = genai.GenerativeModel(
                        model_name=model_name,
                        system_instruction=SYSTEM_PROMPT,
                    )
                    self.chat = self.model.start_chat(history=[])
                    self._model_name = model_name
                    logger.info(f"Gemini AI tayyor: {model_name}")
                    break
                except Exception:
                    continue

        except Exception as e:
            logger.error(f"Gemini init xatosi: {e}")

    def is_available(self) -> bool:
        return self.model is not None

    def ask(self, user_text: str) -> Dict[str, Any]:
        if not self.is_available():
            return {"response": "AI ulangmagan. GEMINI_API_KEY ni .env ga qo'shing.", "action": None, "params": {}}
        try:
            resp = self.chat.send_message(user_text)
            content = resp.text.strip()
            logger.info(f"Gemini [{self._model_name}]: {content[:120]}")
            return self._parse(content)
        except Exception as e:
            err = str(e)
            logger.error(f"Gemini xatosi: {err}")
            if "API_KEY" in err or "401" in err or "403" in err:
                return {"response": "Gemini API key noto'g'ri.", "action": None, "params": {}}
            if "429" in err:
                # Limit - boshqa modelga o'tish
                return self._fallback_model(user_text)
            return {"response": "AI bilan bog'lanishda xatolik.", "action": None, "params": {}}

    def _fallback_model(self, user_text: str) -> Dict[str, Any]:
        """Limit tugaganda boshqa modelga o'tish"""
        fallbacks = ["gemini-1.5-flash-8b", "gemini-1.5-flash", "gemini-2.0-flash"]
        current = getattr(self, "_model_name", "")
        for name in fallbacks:
            if name == current:
                continue
            try:
                logger.info(f"Limit tugadi, {name} ga o'tilmoqda...")
                self.model = genai.GenerativeModel(
                    model_name=name,
                    system_instruction=SYSTEM_PROMPT,
                )
                self.chat = self.model.start_chat(history=[])
                self._model_name = name
                resp = self.chat.send_message(user_text)
                return self._parse(resp.text.strip())
            except Exception:
                continue
        return {"response": "Barcha Gemini modellari limitda. Biroz kuting.", "action": None, "params": {}}

    def _parse(self, content: str) -> Dict[str, Any]:
        try:
            s = content.find("{")
            e = content.rfind("}") + 1
            if s != -1 and e > s:
                data = json.loads(content[s:e])
                if "action" in data:
                    return {
                        "response": data.get("response", "Bajarildi"),
                        "action": data.get("action"),
                        "params": data.get("params", {})
                    }
        except (json.JSONDecodeError, ValueError):
            pass
        return {"response": content, "action": None, "params": {}}

    def clear_history(self):
        if self.model:
            self.chat = self.model.start_chat(history=[])

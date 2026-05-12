"""
Groq AI Module - GHOST Assistant uchun AI miyasi
llama-3.3-70b modeli ishlatiladi - tez va kuchli.

Qanday ishlaydi:
  1. Intent parser buyruqni tanisa → oddiy executor bajaradi (tez)
  2. Intent topilmasa → Groq ga yuboriladi (aqlli javob)
  3. Groq ham tizim buyruqlarini bajarishi mumkin (JSON orqali)
"""

import os
import json
import logging
from typing import Optional, Dict, Any

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    Groq = None
    GROQ_AVAILABLE = False

logger = logging.getLogger(__name__)

# Tizim prompti - GHOST ning shaxsiyati
SYSTEM_PROMPT = """Sen GHOST - aqlli ovozli yordamchi. 
Foydalanuvchi rus yoki o'zbek tilida gapiradi.
Qisqa, aniq va foydali javob ber (1-2 gap).

Agar foydalanuvchi tizim buyrug'i bersa, JSON formatida qaytargin:
{"action": "buyruq_nomi", "params": {...}, "response": "foydalanuvchiga javob"}

Mavjud buyruqlar:
- {"action": "app.open", "params": {"app_name": "telegram"}, "response": "Telegram ochilmoqda"}
- {"action": "app.close", "params": {"app_name": "chrome"}, "response": "Chrome yopilmoqda"}
- {"action": "system.volume_up", "params": {"amount": 10}, "response": "Ovoz oshirildi"}
- {"action": "system.volume_down", "params": {"amount": 10}, "response": "Ovoz kamaytirildi"}
- {"action": "system.volume_mute", "params": {}, "response": "Ovoz o'chirildi"}
- {"action": "system.screenshot", "params": {}, "response": "Skrinshot olindi"}
- {"action": "system.brightness_up", "params": {"amount": 10}, "response": "Yorqinlik oshirildi"}
- {"action": "system.brightness_down", "params": {"amount": 10}, "response": "Yorqinlik kamaytirildi"}
- {"action": "system.shutdown", "params": {}, "response": "Kompyuter o'chirilmoqda"}
- {"action": "system.restart", "params": {}, "response": "Qayta yuklanmoqda"}
- {"action": "system.sleep", "params": {}, "response": "Uyqu rejimi"}
- {"action": "weather.get", "params": {"location": "Toshkent"}, "response": "Ob-havo tekshirilmoqda"}

Agar oddiy savol bo'lsa (buyruq emas), faqat matn bilan javob ber.
Javob tilini foydalanuvchi tili bilan moslashtir (rus → rus, o'zbek → o'zbek).
"""


class GroqAI:
    """Groq AI bilan muloqot"""

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY", "")
        self.client: Optional[Groq] = None
        self.model = "llama-3.3-70b-versatile"
        self.conversation_history = []
        self.max_history = 6  # oxirgi 6 ta xabar

        if not GROQ_AVAILABLE:
            logger.warning("groq paketi o'rnatilmagan: pip install groq")
            return

        if not self.api_key or self.api_key == "your_groq_api_key_here":
            logger.warning("GROQ_API_KEY .env faylida sozlanmagan")
            return

        try:
            self.client = Groq(api_key=self.api_key)
            logger.info(f"Groq AI tayyor: {self.model}")
        except Exception as e:
            logger.error(f"Groq init xatosi: {e}")

    def is_available(self) -> bool:
        return self.client is not None

    def ask(self, user_text: str) -> Dict[str, Any]:
        """
        Groq ga savol yuborish.
        Qaytaradi: {
            "response": "foydalanuvchiga aytiladi",
            "action": "buyruq nomi yoki None",
            "params": {...}
        }
        """
        if not self.is_available():
            return {
                "response": "AI hozir mavjud emas. GROQ_API_KEY ni .env ga qo'shing.",
                "action": None,
                "params": {}
            }

        try:
            # Tarix qo'shish
            self.conversation_history.append({
                "role": "user",
                "content": user_text
            })

            # Oxirgi N ta xabarni yuborish
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            messages += self.conversation_history[-self.max_history:]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=300,
            )

            content = response.choices[0].message.content.strip()
            logger.info(f"Groq javob: {content[:100]}")

            # Tarixga qo'shish
            self.conversation_history.append({
                "role": "assistant",
                "content": content
            })

            # JSON buyruq borligini tekshirish
            result = self._parse_response(content)
            return result

        except Exception as e:
            err = str(e)
            logger.error(f"Groq xatosi: {err}")
            if "401" in err or "invalid_api_key" in err:
                return {"response": "Groq API key noto'g'ri. console.groq.com/keys dan yangi key oling.", "action": None, "params": {}}
            if "429" in err:
                return {"response": "Groq limit tugadi, biroz kuting.", "action": None, "params": {}}
            return {"response": "AI bilan bog'lanishda xatolik.", "action": None, "params": {}}

    def _parse_response(self, content: str) -> Dict[str, Any]:
        """Groq javobidan JSON buyruq yoki matn ajratib olish"""
        # JSON qidirish
        try:
            # { ... } ni topish
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                json_str = content[start:end]
                data = json.loads(json_str)
                if "action" in data:
                    return {
                        "response": data.get("response", "Bajarildi"),
                        "action": data.get("action"),
                        "params": data.get("params", {})
                    }
        except (json.JSONDecodeError, ValueError):
            pass

        # Oddiy matn javob
        return {
            "response": content,
            "action": None,
            "params": {}
        }

    def clear_history(self):
        """Suhbat tarixini tozalash"""
        self.conversation_history.clear()
        logger.info("Groq suhbat tarixi tozalandi")

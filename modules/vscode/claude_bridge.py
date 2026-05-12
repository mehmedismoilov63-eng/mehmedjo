"""
VS Code Claude Code ↔ Telegram Ko'prik

Oqim:
1. Prompt yuboriladi → VS Code ga yoziladi
2. Telegram da "📸 Natijani ko'rish" tugmasi chiqadi
3. Tugma bosilganda → darhol screenshot → Telegram ga yuboriladi
"""

import os
import time
import logging
import threading
import tempfile
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class ClaudeBridge:

    def __init__(self,
                 send_to_telegram: Callable[[str], None],
                 send_photo_to_telegram: Callable[[str, str], None] = None,
                 send_with_button: Callable[[str, str, str], None] = None):
        """
        send_to_telegram     - matn yuborish
        send_photo_to_telegram - rasm yuborish (path, caption)
        send_with_button     - tugmali xabar (text, button_text, callback_data)
        """
        self.send_to_telegram = send_to_telegram
        self.send_photo = send_photo_to_telegram
        self.send_with_button = send_with_button
        self._waiting = False

    def send_prompt(self, prompt: str) -> str:
        """Prompt yuborish va tugmali xabar ko'rsatish"""
        if self._waiting:
            return "⏳ Oldingi so'rov bajarilmoqda..."

        try:
            import pyautogui, pyperclip

            if not self._focus_vscode():
                return "❌ VS Code topilmadi"
            time.sleep(0.4)

            # Chat inputni ochish
            pyautogui.hotkey('ctrl', 'shift', 'p')
            time.sleep(0.5)
            pyperclip.copy("Focus Chat Input")
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.4)
            pyautogui.press('enter')
            time.sleep(0.4)

            # Inputni tozalab prompt yozish
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)
            pyautogui.press('delete')
            time.sleep(0.1)
            pyperclip.copy(prompt)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.3)

            self._waiting = True

            # Enter - yuborish
            pyautogui.press('enter')
            logger.info(f"Prompt yuborildi: '{prompt[:60]}'")

            # Tugmali xabar yuborish
            if self.send_with_button:
                self.send_with_button(
                    f"✅ *Prompt yuborildi:*\n`{prompt[:200]}`\n\n"
                    f"Claude javob bergandan keyin natijani ko'rish uchun tugmani bosing:",
                    "📸 Natijani ko'rish",
                    "get_screenshot"
                )
            else:
                self.send_to_telegram(
                    f"✅ Prompt yuborildi.\n/screenshot - natijani ko'rish"
                )

            self._waiting = False
            return ""  # tugmali xabar allaqachon yuborildi

        except Exception as e:
            self._waiting = False
            logger.error(f"send_prompt xato: {e}")
            return f"❌ Xatolik: {e}"

    def take_and_send_screenshot(self, caption: str = "🤖 Claude natija:"):
        """Darhol screenshot olib Telegram ga yuborish"""
        try:
            path = self._screenshot_vscode()
            if path and self.send_photo:
                self.send_photo(path, caption)
                logger.info("Screenshot yuborildi")
            else:
                self.send_to_telegram("❌ Screenshot olib bo'lmadi")
        except Exception as e:
            logger.error(f"Screenshot xato: {e}")
            self.send_to_telegram(f"❌ Screenshot xatosi: {e}")

    # ── Screenshot ──────────────────────────────────────────────────

    def _screenshot_vscode(self) -> Optional[str]:
        """VS Code oynasining screenshot ini olish"""
        try:
            import pyautogui
            import pygetwindow as gw

            # VS Code ni faollashtirish
            wins = (gw.getWindowsWithTitle("Visual Studio Code") or
                    gw.getWindowsWithTitle("Code"))
            if not wins:
                # Butun ekran screenshot
                img = pyautogui.screenshot()
            else:
                w = wins[0]
                w.restore()
                w.activate()
                time.sleep(0.3)
                left   = max(0, w.left)
                top    = max(0, w.top)
                width  = max(100, w.width)
                height = max(100, w.height)
                img = pyautogui.screenshot(region=(left, top, width, height))

            fd, path = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            img.save(path, optimize=True)
            return path

        except Exception as e:
            logger.error(f"Screenshot xato: {e}")
            return None

    # ── VS Code ─────────────────────────────────────────────────────

    def _focus_vscode(self) -> bool:
        try:
            import pygetwindow as gw
            wins = (gw.getWindowsWithTitle("Visual Studio Code") or
                    gw.getWindowsWithTitle("Code"))
            if wins:
                wins[0].restore()
                wins[0].activate()
                time.sleep(0.3)
                return True
            return False
        except Exception as e:
            logger.error(f"VS Code focus xato: {e}")
            return False

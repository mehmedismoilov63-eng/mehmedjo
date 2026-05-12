"""
GHOST Telegram Bot
Telegram orqali GHOST ga buyruq berish imkoniyati.

Ishlatish:
1. @BotFather dan bot yarating → token oling
2. .env ga TELEGRAM_BOT_TOKEN va TELEGRAM_OWNER_ID qo'shing
3. GHOST ishga tushganda bot avtomatik boshlanadi

Buyruqlar:
  /start   - botni ishga tushirish
  /help    - yordam
  /status  - GHOST holati
  Har qanday matn → GHOST bajaradi va javob qaytaradi
"""

import os
import logging
import threading
import asyncio
from typing import Optional, Callable

try:
    from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application, CommandHandler, MessageHandler,
        filters, ContextTypes, CallbackQueryHandler
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

logger = logging.getLogger(__name__)


class TelegramBotHandler:
    """GHOST uchun Telegram bot"""

    def __init__(self, command_callback: Callable[[str], str]):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.owner_id = os.getenv("TELEGRAM_OWNER_ID", "")
        self.command_callback = command_callback
        self.app: Optional[object] = None
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._bot: Optional[object] = None
        self.unlock_callback = None

        # Claude Bridge
        self._claude_bridge = None
        self._claude_mode = False

        if not TELEGRAM_AVAILABLE:
            logger.warning("python-telegram-bot o'rnatilmagan")
            return
        if not self.token or self.token == "your_telegram_bot_token_here":
            logger.warning("TELEGRAM_BOT_TOKEN .env da sozlanmagan")
            return

    def is_available(self) -> bool:
        return (TELEGRAM_AVAILABLE and
                bool(self.token) and
                self.token != "your_telegram_bot_token_here")

    def start(self):
        """Botni alohida threadda ishga tushirish"""
        if not self.is_available():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Telegram bot boshlandi")

    def stop(self):
        if self.app:
            try:
                asyncio.run_coroutine_threadsafe(
                    self.app.stop(), self._loop
                )
            except Exception:
                pass

    def send_message(self, text: str):
        """GHOST dan Telegram ga xabar yuborish (thread-safe)"""
        if not self.owner_id or not self._loop or not self._bot:
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self._bot.send_message(
                    chat_id=self.owner_id,
                    text=text,
                    parse_mode="Markdown"
                ),
                self._loop
            )
        except Exception as e:
            try:
                asyncio.run_coroutine_threadsafe(
                    self._bot.send_message(chat_id=self.owner_id, text=text),
                    self._loop
                )
            except Exception:
                logger.error(f"Telegram xabar yuborishda xato: {e}")

    def send_photo(self, photo_path: str, caption: str = ""):
        """Telegram ga rasm yuborish (thread-safe)"""
        if not self.owner_id or not self._loop or not self._bot:
            return
        try:
            async def _send():
                with open(photo_path, 'rb') as f:
                    await self._bot.send_photo(
                        chat_id=self.owner_id,
                        photo=f,
                        caption=caption,
                        parse_mode="Markdown"
                    )
                try:
                    import os
                    os.unlink(photo_path)
                except Exception:
                    pass

            asyncio.run_coroutine_threadsafe(_send(), self._loop)
        except Exception as e:
            logger.error(f"Telegram rasm yuborishda xato: {e}")

    def send_with_button(self, text: str, button_text: str, callback_data: str):
        """Inline tugmali xabar yuborish"""
        if not self.owner_id or not self._loop or not self._bot:
            return
        try:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(button_text, callback_data=callback_data)]
            ])

            async def _send():
                await self._bot.send_message(
                    chat_id=self.owner_id,
                    text=text,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )

            asyncio.run_coroutine_threadsafe(_send(), self._loop)
        except Exception as e:
            logger.error(f"Tugmali xabar yuborishda xato: {e}")

    # ── Internal ────────────────────────────────────────────────────

    def _run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._start_bot())

    async def _start_bot(self):
        self.app = Application.builder().token(self.token).build()
        self._bot = self.app.bot

        # Handlerlar
        self.app.add_handler(CommandHandler("start", self._cmd_start))
        self.app.add_handler(CommandHandler("help", self._cmd_help))
        self.app.add_handler(CommandHandler("status", self._cmd_status))
        self.app.add_handler(CommandHandler("unlock", self._cmd_unlock))
        self.app.add_handler(CommandHandler("claude", self._cmd_claude))
        self.app.add_handler(CommandHandler("claude_off", self._cmd_claude_off))
        self.app.add_handler(CommandHandler("copy", self._cmd_copy))
        # Inline tugmalar uchun
        self.app.add_handler(CallbackQueryHandler(self._on_callback))
        # Matn xabarlari
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message)
        )
        # Audio / ovozli xabarlar
        self.app.add_handler(
            MessageHandler(filters.VOICE | filters.AUDIO, self._on_voice)
        )

        logger.info("Telegram bot tayyor (matn + audio qabul qiladi)")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()

    def _is_owner(self, update: Update) -> bool:
        if not self.owner_id or self.owner_id == "your_telegram_id_here":
            return False  # Hali owner belgilanmagan - faqat /start orqali
        return str(update.effective_user.id) == str(self.owner_id)

    async def _cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        user_id = str(update.effective_user.id)
        user_name = update.effective_user.first_name or "Foydalanuvchi"

        # Agar owner ID sozlanmagan bo'lsa - birinchi yozgan odam owner bo'ladi
        if not self.owner_id or self.owner_id == "your_telegram_id_here":
            self.owner_id = user_id
            # .env faylga yozib qo'yamiz
            self._save_owner_id(user_id)
            logger.info(f"Yangi owner: {user_id} ({user_name})")
            await update.message.reply_text(
                f"👻 Salom {user_name}!\n"
                f"Siz GHOST ning egasi sifatida ro'yxatdan o'tdingiz.\n"
                f"Sizning ID: {user_id}\n\n"
                "Endi menga buyruq bering:\n"
                "• Открой телеграм\n"
                "• Громче / тише\n"
                "• Скриншот\n"
                "• Soat necha\n\n"
                "/help - barcha buyruqlar"
            )
            return

        if not self._is_owner(update):
            await update.message.reply_text("Ruxsat yo'q.")
            return

        await update.message.reply_text(
            f"👻 Salom {user_name}! GHOST tayyor.\n/help - buyruqlar"
        )

    def _save_owner_id(self, owner_id: str):
        """Owner ID ni .env ga yozish"""
        try:
            env_path = ".env"
            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()
            content = content.replace(
                "TELEGRAM_OWNER_ID=your_telegram_id_here",
                f"TELEGRAM_OWNER_ID={owner_id}"
            )
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Owner ID .env ga saqlandi: {owner_id}")
        except Exception as e:
            logger.error(f"Owner ID saqlashda xato: {e}")

    async def _cmd_help(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_owner(update):
            return
        await update.message.reply_text(
            "📋 GHOST buyruqlari:\n\n"
            "🔊 Ovoz: громче / тише / mute / громкость на 50\n"
            "💡 Yorqinlik: ярче / темнее\n"
            "📸 Skrinshot: скриншот / скриншот окна\n"
            "📸 Telegram: скриншот в телеграм\n"
            "🕐 Vaqt: soat necha / bugun\n"
            "🔋 Tizim: batareya / tizim / disk / сеть\n"
            "📊 Hisobot: полный отчёт\n"
            "📱 Ilovalar: открой [ilova] / закрой [ilova]\n"
            "🎵 Media: play / следующий / предыдущий\n"
            "🖥️ Oyna: свернуть / развернуть / рабочий стол\n"
            "⌨️ Klaviatura: сохрани / отмени / новая вкладка\n"
            "📁 Fayllar: загрузки / документы\n"
            "🔍 Fayl qidirish: найди файл [nom]\n"
            "⏰ Taymer: таймер 5 минут\n"
            "🌐 Internet: гугл [so'z] / youtube [qo'shiq]\n"
            "🌐 Tezlik: скорость интернета\n"
            "🌤️ Ob-havo: погода\n"
            "🔐 Parol: создай пароль\n"
            "📋 Clipboard: что скопировано\n"
            "🎙️ Diktofon: начни запись / останови запись\n"
            "🎬 Ekran yozuvi: запись экрана\n"
            "💼 Rejimlar: рабочий режим / ночной режим\n"
            "🔔 Bildirishnoma: покажи уведомление [matn]\n"
            "💻 Quvvat: выключи / перезагрузи / sleep / lock\n"
            "🔓 Unlock: /unlock [PIN] - ekranni lockdan ochish\n"
            "🎙️ Audio: ovozli xabar yuboring - GHOST bajaradi\n\n"
            "🤖 *Claude Code (VS Code):*\n"
            "/claude - Claude rejimini yoqish\n"
            "/claude [prompt] - bir martalik prompt\n"
            "/claude\\_off - rejimni o'chirish"
        )

    async def _cmd_status(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not self._is_owner(update):
            return
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.3)
            ram = psutil.virtual_memory()
            bat = psutil.sensors_battery()
            bat_text = f"{bat.percent:.0f}%" if bat else "yo'q"
            await update.message.reply_text(
                f"✅ GHOST ishlayapti\n\n"
                f"💻 CPU: {cpu:.0f}%\n"
                f"🧠 RAM: {ram.percent:.0f}%\n"
                f"🔋 Batareya: {bat_text}"
            )
        except Exception:
            await update.message.reply_text("✅ GHOST ishlayapti")

    async def _on_message(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Foydalanuvchi xabari kelganda"""
        if not self._is_owner(update):
            await update.message.reply_text("Ruxsat yo'q.")
            return

        text = update.message.text.strip()
        logger.info(f"Telegram buyruq: {text}")

        # ── Oddiy GHOST buyruqi ──
        await update.message.reply_text(f"⚙️ Bajarilmoqda: {text}")
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, self.command_callback, text
        )
        if response:
            await update.message.reply_text(f"✅ {response}")

    async def _on_voice(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Audio / ovozli xabar kelganda - STT bilan matnга aylantirib bajaradi"""
        if not self._is_owner(update):
            await update.message.reply_text("Ruxsat yo'q.")
            return

        await update.message.reply_text("🎙️ Audio qabul qilindi, tanilmoqda...")

        try:
            # Faylni yuklab olish
            if update.message.voice:
                file = await update.message.voice.get_file()
                ext = ".ogg"
            else:
                file = await update.message.audio.get_file()
                ext = ".mp3"

            import tempfile, os
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp_path = tmp.name

            await file.download_to_drive(tmp_path)

            # STT - faster-whisper bilan
            text = await asyncio.get_event_loop().run_in_executor(
                None, self._transcribe_audio, tmp_path
            )
            os.unlink(tmp_path)

            if not text:
                await update.message.reply_text("❌ Ovozni tanib bo'lmadi")
                return

            await update.message.reply_text(f"🗣️ Tanildi: *{text}*", parse_mode="Markdown")

            # Buyruqni bajarish
            response = await asyncio.get_event_loop().run_in_executor(
                None, self.command_callback, text
            )
            if response:
                await update.message.reply_text(f"✅ {response}")

        except Exception as e:
            logger.error(f"Voice message error: {e}")
            await update.message.reply_text(f"❌ Xatolik: {e}")

    def _transcribe_audio(self, audio_path: str) -> str:
        """Audio faylni matnга aylantirish"""
        try:
            import numpy as np

            # OGG → WAV konvertatsiya (pydub yoki ffmpeg)
            wav_path = audio_path.replace(".ogg", ".wav").replace(".mp3", ".wav")
            try:
                import subprocess
                subprocess.run(
                    ["ffmpeg", "-y", "-i", audio_path, "-ar", "16000",
                     "-ac", "1", "-f", "wav", wav_path],
                    capture_output=True, timeout=30
                )
                use_path = wav_path if os.path.exists(wav_path) else audio_path
            except Exception:
                use_path = audio_path

            # faster-whisper bilan tanish
            from faster_whisper import WhisperModel
            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(
                use_path, language="ru", beam_size=5,
                vad_filter=True
            )
            text = " ".join([s.text for s in segments]).strip()

            # Temp fayllarni tozalash
            import os
            for p in [wav_path]:
                if os.path.exists(p):
                    os.unlink(p)

            return text
        except Exception as e:
            logger.error(f"Transcribe error: {e}")
            return ""

    async def _cmd_unlock(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Noutbukni lockdan ochish - /unlock PIN"""
        if not self._is_owner(update):
            await update.message.reply_text("Ruxsat yo'q.")
            return

        args = ctx.args  # /unlock 1234
        pin = args[0] if args else None

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, self.unlock_callback, pin
        )
        await update.message.reply_text(result)

    # Bu callback assistant.py dan o'rnatiladi
    unlock_callback = None

    async def _cmd_claude(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """
        /claude — Claude Bridge ni ochish
        """
        if not self._is_owner(update):
            await update.message.reply_text("Ruxsat yo'q.")
            return

        miniapp_url = os.getenv("GHOST_MINIAPP_URL", "http://localhost:8000")
        is_https = miniapp_url.startswith("https://")

        if is_https:
            # HTTPS — Telegram Mini App tugmasi
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "🤖 Claude Bridge",
                    web_app={"url": miniapp_url}
                )
            ]])
            await update.message.reply_text(
                "👻 *Claude Bridge*\n\n"
                "• Prompt yozing → VS Code ga ketadi\n"
                "• 🔍 Tekshirish → prompt to'g'ri yozilganini ko'ring\n"
                "• ✅ Natija → Claude javobi tayyor bo'lganda ko'ring",
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
        else:
            # Local — brauzerda qo'lda ochish
            await update.message.reply_text(
                "👻 *Claude Bridge* ishga tushdi!\n\n"
                f"Brauzerda oching:\n`{miniapp_url}`\n\n"
                "• Prompt yozing → VS Code ga ketadi\n"
                "• 🔍 Tekshirish → prompt to'g'ri yozilganini ko'ring\n"
                "• ✅ Natija → Claude javobi tayyor bo'lganda ko'ring\n\n"
                "💡 Backend va Agent ishlab turganligini tekshiring",
                parse_mode="Markdown",
            )

    async def _cmd_claude_off(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Claude Code rejimini o'chirish (eski compat)"""
        if not self._is_owner(update):
            return
        await update.message.reply_text(
            "ℹ️ Claude Bridge endi Mini App orqali ishlaydi.\n"
            "/claude — Mini App ni ochish"
        )

    async def _cmd_copy(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """/copy - hozirgi clipboard matnini Telegram ga yuborish"""
        if not self._is_owner(update):
            return
        try:
            import pyperclip
            text = pyperclip.paste()
            if text and text.strip():
                preview = text[:4000]
                suffix = f"\n\n_...({len(text)} belgi)_" if len(text) > 4000 else ""
                await update.message.reply_text(
                    f"📋 *Clipboard:*\n\n`{preview}`{suffix}",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text("📋 Clipboard bo'sh")
        except Exception as e:
            await update.message.reply_text(f"❌ Clipboard o'qib bo'lmadi: {e}")

    async def _on_callback(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Inline tugma bosilganda"""
        query = update.callback_query
        await query.answer()

        if not self._is_owner(update):
            await query.edit_message_text("Ruxsat yo'q.")
            return

        data = query.data

        if data == "get_screenshot":
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text("📸 Screenshot olinmoqda...")

            loop = asyncio.get_event_loop()
            if self._claude_bridge:
                await loop.run_in_executor(
                    None,
                    self._claude_bridge.take_and_send_screenshot,
                    "🤖 Claude natija:"
                )
            else:
                await loop.run_in_executor(None, self._take_quick_screenshot)

    def _take_quick_screenshot(self):
        """Tez screenshot - bridge yo'q bo'lganda"""
        try:
            import pyautogui, tempfile, os
            img = pyautogui.screenshot()
            fd, path = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            img.save(path)
            self.send_photo(path, "📸 Screenshot")
        except Exception as e:
            self.send_message(f"❌ Screenshot xatosi: {e}")

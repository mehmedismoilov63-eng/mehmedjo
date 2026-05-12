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
    from telegram import (
        Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup,
        WebAppInfo, MenuButtonWebApp
    )
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
        self.miniapp_url = os.getenv("GHOST_MINIAPP_URL", "").strip()
        self.command_callback = command_callback
        self.app: Optional[object] = None
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._bot: Optional[object] = None
        self.unlock_callback = None

        # Claude Bridge
        self._claude_bridge = None
        self._claude_mode = False
        # Pending prompt (ruxsat kutilmoqda)
        self._pending_enhanced: str = ""
        self._pending_original: str = ""
        self._pending_update = None   # update object (reply uchun)

        # AI Voice Processor
        self._ai_processor = None   # lazy init (start() dan keyin)

        # Live stream
        self._live_task: Optional[asyncio.Task] = None
        self._live_interval = 3   # soniya

        # Screen stream (MJPEG)
        self._streamer = None

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
        """Inline tugmali xabar yuborish (screenshot + bekor qilish)"""
        if not self.owner_id or not self._loop or not self._bot:
            return
        try:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(button_text, callback_data=callback_data)],
                [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_prompt")],
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

    def _get_claude_bridge(self):
        """ClaudeBridge ni lazy init qilish"""
        if self._claude_bridge is None:
            from modules.vscode.claude_bridge import ClaudeBridge
            self._claude_bridge = ClaudeBridge(
                send_to_telegram=self.send_message,
                send_photo_to_telegram=self.send_photo,
                send_with_button=self.send_with_button,
            )
        return self._claude_bridge

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
        self.app.add_handler(CommandHandler("app", self._cmd_app))
        self.app.add_handler(CommandHandler("status", self._cmd_status))
        self.app.add_handler(CommandHandler("unlock", self._cmd_unlock))
        self.app.add_handler(CommandHandler("claude", self._cmd_claude))
        self.app.add_handler(CommandHandler("claude_off", self._cmd_claude_off))
        self.app.add_handler(CommandHandler("copy", self._cmd_copy))
        self.app.add_handler(CommandHandler("live", self._cmd_live))
        self.app.add_handler(CommandHandler("live_stop", self._cmd_live_stop))
        self.app.add_handler(CommandHandler("stream", self._cmd_stream))
        self.app.add_handler(CommandHandler("stream_stop", self._cmd_stream_stop))
        self.app.add_handler(CommandHandler("cancel", self._cmd_cancel))
        self.app.add_handler(CommandHandler("model", self._cmd_model))
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
        await self._setup_miniapp_menu()

        # AI processor — bot threadida ishga tushirish
        try:
            from modules.ai_voice_processor import AIVoiceProcessor
            self._ai_processor = AIVoiceProcessor(
                command_callback=self.command_callback,
                execute_intent_fn=getattr(self, "_execute_intent_fn", None),
            )
            if self._ai_processor.is_ai_available():
                logger.info("Telegram bot: AI processor tayyor ✅")
            else:
                logger.warning("Telegram bot: AI yo'q, intent parser ishlatiladi")
        except Exception as e:
            logger.error(f"AI processor init xato: {e}")

        await self.app.updater.start_polling(drop_pending_updates=True)
        await asyncio.Event().wait()

    def _is_owner(self, update: Update) -> bool:
        if not self.owner_id or self.owner_id == "your_telegram_id_here":
            return False
        user_id = str(update.effective_user.id)
        # Owner
        if user_id == str(self.owner_id):
            return True
        # Qo'shimcha ruxsat berilganlar
        allowed = os.getenv("TELEGRAM_ALLOWED_IDS", "")
        if allowed:
            allowed_list = [x.strip() for x in allowed.split(",") if x.strip()]
            if user_id in allowed_list:
                return True
        return False

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
                "/help - barcha buyruqlar\n"
                "/app - Telegram Mini App",
                reply_markup=self._miniapp_markup()
            )
            return

        if not self._is_owner(update):
            await update.message.reply_text("Ruxsat yo'q.")
            return

        await update.message.reply_text(
            f"👻 Salom {user_name}! GHOST tayyor.\n/help - buyruqlar"
        )

        if self._miniapp_markup():
            await update.message.reply_text(
                "GHOST Mini App",
                reply_markup=self._miniapp_markup()
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

    def _miniapp_markup(self):
        """Telegram Mini App ochish tugmasi"""
        if not self._miniapp_url_ready():
            return None
        return InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "GHOST Mini App",
                web_app=WebAppInfo(url=self.miniapp_url)
            )
        ]])

    def _miniapp_url_ready(self) -> bool:
        if not self.miniapp_url:
            return False
        if self.miniapp_url in {"http://localhost:8000", "https://your-app.railway.app"}:
            return False
        return self.miniapp_url.startswith("https://")

    async def _setup_miniapp_menu(self):
        """Bot menu tugmasiga Mini App ni ulash"""
        if not self._miniapp_url_ready():
            return
        try:
            await self._bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(
                    text="GHOST",
                    web_app=WebAppInfo(url=self.miniapp_url)
                )
            )
            logger.info("Telegram Mini App menu tugmasi sozlandi")
        except Exception as e:
            logger.warning(f"Mini App menu sozlashda xato: {e}")

    async def _cmd_app(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Telegram Mini App havolasini yuborish"""
        if not self._is_owner(update):
            await update.message.reply_text("Ruxsat yo'q.")
            return
        if not self.miniapp_url:
            await update.message.reply_text(
                "GHOST_MINIAPP_URL .env faylida sozlanmagan."
            )
            return
        if not self._miniapp_url_ready():
            await update.message.reply_text(
                "Mini App uchun HTTPS production URL kerak.\n"
                f"Hozirgi URL: {self.miniapp_url}"
            )
            return
        await update.message.reply_text(
            "GHOST Mini App",
            reply_markup=self._miniapp_markup()
        )

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
            "/claude\\_off - rejimni o'chirish\n"
            "/cancel - promptni bekor qilish (Esc)\n"
            "/model - model tanlash oynasini ochish\n"
            "/model [nom] - model qidirish\n\n"
            "🎥 *Live ekran:*\n"
            "/live - har 3s screenshot (live)\n"
            "/live 5 - har 5s screenshot\n"
            "/live\\_stop - to'xtatish\n\n"
            "📡 *Real-time stream:*\n"
            "/stream - brauzerda real vaqtda ekran\n"
            "/stream vscode - faqat VS Code oynasi\n"
            "/stream\\_stop - to'xtatish"
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
        """Foydalanuvchi matn xabari — AI orqali erkin nutqni tushunib bajaradi"""
        if not self._is_owner(update):
            await update.message.reply_text("Ruxsat yo'q.")
            return

        text = update.message.text.strip()
        logger.info(f"Telegram xabar: {text}")

        # ── Claude rejimi: har bir xabar to'g'ridan VS Code ga ──
        if self._claude_mode:
            self._claude_bridge = self._get_claude_bridge()
            await self._send_prompt_with_buttons(update, text)
            return

        # ── AI processor ──
        if self._ai_processor is None:
            from modules.ai_voice_processor import AIVoiceProcessor
            self._ai_processor = AIVoiceProcessor(self.command_callback)

        proc = self._ai_processor

        if proc.is_ai_available():
            # "Bajarilmoqda..." xabarini yuborib, keyin edit qilamiz
            status_msg = await update.message.reply_text("⚙️ Bajarilmoqda...")
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, proc.process_text, text, self._claude_bridge
            )
            # Status xabarni o'chirish
            try:
                await status_msg.delete()
            except Exception:
                pass
            await self._handle_ai_result(update, result, text)
        else:
            # AI yo'q — oddiy command_callback
            await update.message.reply_text(f"⚙️ Bajarilmoqda: {text}")
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, self.command_callback, text)
            if response:
                await update.message.reply_text(f"✅ {response}")

    async def _on_voice(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Audio / ovozli xabar — AI orqali erkin nutqni tushunib bajaradi"""
        if not self._is_owner(update):
            await update.message.reply_text("Ruxsat yo'q.")
            return

        # AI processor (bir marta yaratiladi)
        if self._ai_processor is None:
            from modules.ai_voice_processor import AIVoiceProcessor
            self._ai_processor = AIVoiceProcessor(self.command_callback)

        proc = self._ai_processor
        ai_badge = "🤖 AI" if proc.is_ai_available() else "⚙️"
        await update.message.reply_text(f"🎙️ Eshitilmoqda... {ai_badge}")

        try:
            import tempfile, os

            # Faylni yuklab olish
            if update.message.voice:
                file = await update.message.voice.get_file()
                ext = ".ogg"
            else:
                file = await update.message.audio.get_file()
                ext = ".mp3"

            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp_path = tmp.name
            await file.download_to_drive(tmp_path)

            # STT — Whisper
            loop = asyncio.get_event_loop()
            text = await loop.run_in_executor(None, proc.transcribe, tmp_path)
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

            if not text:
                await update.message.reply_text("❌ Ovozni tanib bo'lmadi. Qaytadan urinib ko'ring.")
                return

            await update.message.reply_text(
                f"🗣️ *Tanildi:* `{text}`",
                parse_mode="Markdown"
            )

            # Claude bridge (agar mavjud bo'lsa)
            bridge = self._claude_bridge

            # AI tahlil + bajarish
            result = await loop.run_in_executor(
                None, proc.process_text, text, bridge
            )

            await self._handle_ai_result(update, result, text)

        except Exception as e:
            logger.error(f"Voice message error: {e}", exc_info=True)
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
        """/claude — Claude rejimini yoqish yoki bir martalik prompt"""
        if not self._is_owner(update):
            await update.message.reply_text("Ruxsat yo'q.")
            return

        # Claude bridge yaratish
        self._claude_bridge = self._get_claude_bridge()

        args = ctx.args
        if args:
            # /claude bu kodni tuzat — bir martalik
            prompt = " ".join(args)
            await self._send_prompt_with_buttons(update, prompt)
        else:
            # /claude — rejimni yoqish
            self._claude_mode = True
            await update.message.reply_text(
                "🤖 *Claude rejimi yoqildi*\n\n"
                "Endi yozgan har bir xabaringiz VS Code ga yuboriladi.\n"
                "O'chirish: /claude\\_off",
                parse_mode="Markdown"
            )

    async def _handle_ai_result(self, update, result: dict, original_text: str):
        """AI natijasini Telegram ga yuborish (matn va audio uchun umumiy)"""
        reply     = result.get("reply", "")
        msg_type  = result.get("type", "chat")
        success   = result.get("success", True)
        screenshot_needed = result.get("screenshot_needed", False)

        # reply ichida raw JSON bo'lsa — tozalash
        if isinstance(reply, str) and reply.strip().startswith("{"):
            reply = "✅ Bajarildi"

        # ── Claude prompt → ruxsat so'rab yuborish ──
        if msg_type == "claude" and success and screenshot_needed:
            prompt = result.get("claude_prompt", original_text)
            self._claude_bridge = self._get_claude_bridge()
            await self._send_prompt_with_buttons(update, prompt)
            return

        # ── Claude bridge topilmadi ──
        if msg_type == "claude" and not success:
            await update.message.reply_text(
                "⏳ *VS Code ochilmoqda...*\n\nBiroz kuting, tayyor bo'lgach prompt yuboriladi.",
                parse_mode="Markdown"
            )
            return

        # ── Buyruq yoki chat javob ──
        if not reply:
            reply = "✅ Bajarildi" if msg_type == "command" else "❓ Javob yo'q"

        if msg_type == "command":
            icon = "✅" if success else "❌"
            await update.message.reply_text(f"{icon} {reply}")
        else:
            # Chat — markdown bilan, xato bo'lsa oddiy matn
            try:
                await update.message.reply_text(reply, parse_mode="Markdown")
            except Exception:
                await update.message.reply_text(reply)

    async def _send_prompt_with_buttons(self, update: Update, prompt: str,
                                         skip_confirm: bool = False):
        """
        Promptni AI bilan yaxshilab, foydalanuvchidan ruxsat so'rab, VS Code ga yuboradi.
        skip_confirm=True bo'lsa ruxsat so'ramasdan to'g'ridan yuboradi.
        """
        loop = asyncio.get_event_loop()

        # 1. Promptni AI bilan yaxshilash
        enhanced = await loop.run_in_executor(
            None, self._claude_bridge.enhance_prompt, prompt
        )

        # 2. Agar yaxshilangan prompt original dan farq qilsa — ruxsat so'rash
        if not skip_confirm and enhanced.strip() != prompt.strip():
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Ha, yubor",    callback_data="confirm_yes"),
                    InlineKeyboardButton("✏️ Originalini yubor", callback_data="confirm_orig"),
                ],
                [
                    InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_prompt"),
                ],
            ])
            # Pending sifatida saqlash
            self._pending_enhanced = enhanced
            self._pending_original = prompt
            await update.message.reply_text(
                f"🤖 *Prompt yaxshilandi. Yuborilsinmi?*\n\n"
                f"*Asl:* `{prompt[:200]}`\n\n"
                f"*Yaxshilangan:* `{enhanced[:300]}`",
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
            return

        # 3. Ruxsat kerak emas yoki bir xil — to'g'ridan yuborish
        await self._do_send_prompt(update, enhanced or prompt)

    async def _do_send_prompt(self, update_or_query, prompt: str):
        """Promptni VS Code ga yuborib natija tugmalarini ko'rsatish"""
        # update yoki query bo'lishi mumkin
        msg = getattr(update_or_query, "message", update_or_query)

        loop = asyncio.get_event_loop()
        ok = await loop.run_in_executor(
            None, self._claude_bridge.send_prompt_only, prompt
        )
        if not ok:
            await msg.reply_text(
                "❌ *VS Code ochilmadi*\n\n"
                "VS Code o'rnatilganligini tekshiring va qayta urinib ko'ring.",
                parse_mode="Markdown"
            )
            return

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔍 Tekshirish", callback_data="ss_check"),
                InlineKeyboardButton("✅ Natija",     callback_data="ss_result"),
            ],
            [
                InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_prompt"),
            ],
        ])
        preview = prompt[:300] + ("..." if len(prompt) > 300 else "")
        await msg.reply_text(
            f"⚡ *Prompt yuborildi*\n\n`{preview}`\n\n"
            f"_Natija tayyor bo'lgach tugmani bosing:_",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

    async def _cmd_claude_off(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """Claude rejimini o'chirish"""
        if not self._is_owner(update):
            return
        self._claude_mode = False
        await update.message.reply_text("✅ Claude rejimi o'chirildi. Oddiy buyruqlar ishlaydi.")

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

        # ── Prompt tasdiqlash ──
        if data == "confirm_yes":
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass
            prompt = self._pending_enhanced or self._pending_original
            self._pending_enhanced = ""
            self._pending_original = ""
            if prompt:
                await self._do_send_prompt(query, prompt)
            return

        if data == "confirm_orig":
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass
            prompt = self._pending_original
            self._pending_enhanced = ""
            self._pending_original = ""
            if prompt:
                await self._do_send_prompt(query, prompt)
            return

        # ── Screenshot tugmalari ──
        if data in ("ss_check", "ss_result", "get_screenshot"):
            caption = "🔍 Tekshirish natijasi" if data == "ss_check" else "✅ Yakuniy natija"
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass
            await query.message.reply_text("📸 Screenshot olinmoqda...")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, self._take_quick_screenshot, caption
            )

        # ── Bekor qilish ──
        elif data == "cancel_prompt":
            # Pending promptni ham tozalash
            self._pending_enhanced = ""
            self._pending_original = ""
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass

            loop = asyncio.get_event_loop()
            ok = await loop.run_in_executor(None, self._get_claude_bridge().cancel_prompt)
            if ok:
                await query.message.reply_text("⏹ *Prompt bekor qilindi*", parse_mode="Markdown")
            else:
                await query.message.reply_text("⏹ Bekor qilindi.")

    async def _cmd_cancel(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """/cancel — Claude promptini Escape bilan bekor qilish"""
        if not self._is_owner(update):
            return
        loop = asyncio.get_event_loop()
        ok = await loop.run_in_executor(None, self._get_claude_bridge().cancel_prompt)
        if ok:
            await update.message.reply_text("⏹ Prompt bekor qilindi (Escape bosildi)")
        else:
            await update.message.reply_text("❌ VS Code topilmadi")

    async def _cmd_model(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """/model [opus|sonnet|haiku] — Kiro modelini almashtirish"""
        if not self._is_owner(update):
            return

        bridge = self._get_claude_bridge()

        if not ctx.args:
            await update.message.reply_text(
                "🤖 *Model tanlang:*\n\n"
                "/model opus    — Claude Opus (eng kuchli)\n"
                "/model sonnet  — Claude Sonnet (tez + kuchli)\n"
                "/model haiku   — Claude Haiku (eng tez)",
                parse_mode="Markdown"
            )
            return

        model_name = ctx.args[0].lower()
        labels = {
            "opus":   "Claude Opus 🧠",
            "sonnet": "Claude Sonnet ⚡",
            "haiku":  "Claude Haiku 🚀",
        }

        if model_name not in labels:
            await update.message.reply_text(
                "❌ Noto'g'ri model.\n"
                "Variantlar: `opus`, `sonnet`, `haiku`",
                parse_mode="Markdown"
            )
            return

        loop = asyncio.get_event_loop()
        ok = await loop.run_in_executor(
            None, bridge.switch_model, model_name
        )

        if ok:
            await update.message.reply_text(
                f"✅ Model o'zgartirildi: *{labels[model_name]}*",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ VS Code topilmadi")

    async def _cmd_live(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """/live [interval] — VS Code ekranini video sifatida yuborish"""
        if not self._is_owner(update):
            return

        if self._live_task and not self._live_task.done():
            await update.message.reply_text("⚠️ Live allaqachon ishlayapti. To'xtatish: /live\\_stop")
            return

        # Har necha soniyada video (default 10s, min 5s, max 30s)
        duration = 10
        if ctx.args:
            try:
                duration = max(5, min(30, int(ctx.args[0])))
            except ValueError:
                pass
        self._live_interval = duration

        await update.message.reply_text(
            f"🎥 *Live video boshlandi*\n"
            f"Har {duration} soniyada video yuboriladi.\n"
            f"To'xtatish: /live\\_stop",
            parse_mode="Markdown"
        )

        self._live_task = asyncio.create_task(
            self._live_video_loop(int(update.effective_chat.id), duration)
        )

    async def _cmd_live_stop(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """/live_stop — Live streamni to'xtatish"""
        if not self._is_owner(update):
            return

        if self._live_task and not self._live_task.done():
            self._live_task.cancel()
            await update.message.reply_text("⏹ Live to'xtatildi.")
        else:
            await update.message.reply_text("ℹ️ Live ishlamayapti.")

    async def _cmd_stream(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """/stream [vscode] — Real-time MJPEG stream brauzerda"""
        if not self._is_owner(update):
            return

        if self._streamer and self._streamer.is_running:
            await update.message.reply_text(
                f"📡 Stream allaqachon ishlayapti:\n{self._streamer.public_url}\n\n"
                "To'xtatish: /stream\\_stop"
            )
            return

        await update.message.reply_text("⏳ Stream ishga tushirilmoqda...")

        from core.screen_stream import ScreenStreamer
        self._streamer = ScreenStreamer()

        # VS Code rejimi
        vscode_mode = ctx.args and ctx.args[0].lower() == "vscode"
        if vscode_mode:
            self._streamer.set_region_vscode()

        loop = asyncio.get_event_loop()
        url = await loop.run_in_executor(
            None,
            lambda: self._streamer.start(fps=10, quality=55, scale=0.65)
        )

        if url:
            mode_text = "VS Code oynasi" if vscode_mode else "Butun ekran"
            await update.message.reply_text(
                f"📡 *Live Stream tayyor!*\n\n"
                f"🔗 {url}\n\n"
                f"📺 Rejim: {mode_text}\n"
                f"Brauzerda oching — real vaqtda ko'rasiz.\n\n"
                f"To'xtatish: /stream\\_stop",
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
        else:
            await update.message.reply_text(
                "❌ Stream ishga tushmadi.\n\n"
                "Tekshiring:\n"
                "• `pip install flask opencv-python pyngrok`\n"
                "• ngrok token: `.env` ga `NGROK_AUTH_TOKEN=...` qo'shing\n"
                "  Token olish: https://dashboard.ngrok.com",
                parse_mode="Markdown"
            )

    async def _cmd_stream_stop(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        """/stream_stop — Streamni to'xtatish"""
        if not self._is_owner(update):
            return

        if self._streamer and self._streamer.is_running:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._streamer.stop)
            self._streamer = None
            await update.message.reply_text("⏹ Stream to'xtatildi.")
        else:
            await update.message.reply_text("ℹ️ Stream ishlamayapti.")
        """Har duration soniyada ekran videosini olib Telegram ga yuboradi"""
        loop = asyncio.get_event_loop()
        count = 0
        try:
            while True:
                count += 1
                await self._bot.send_message(
                    chat_id=chat_id,
                    text=f"🎥 Video #{count} yozilmoqda ({duration}s)..."
                )
                video_bytes = await loop.run_in_executor(
                    None, self._record_screen, duration
                )
                if video_bytes:
                    import io
                    await self._bot.send_video(
                        chat_id=chat_id,
                        video=io.BytesIO(video_bytes),
                        caption=f"🎥 Live #{count} · {duration}s",
                        supports_streaming=True,
                    )
                else:
                    await self._bot.send_message(
                        chat_id=chat_id, text="❌ Video olib bo'lmadi"
                    )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Live video loop xato: {e}")
            try:
                await self._bot.send_message(chat_id=chat_id, text=f"❌ Live xato: {e}")
            except Exception:
                pass

    def _record_screen(self, duration: int) -> bytes:
        """Ekranni duration soniya yozib MP4 qaytaradi"""
        try:
            import cv2
            import numpy as np
            import pyautogui
            import pygetwindow as gw
            import tempfile, os, time, io

            # VS Code oynasini aniqlash
            wins = gw.getWindowsWithTitle("Visual Studio Code") or gw.getWindowsWithTitle("Code")
            if wins:
                w = wins[0]
                w.restore()
                try:
                    w.activate()
                except Exception:
                    pass
                time.sleep(0.2)
                region = (max(0, w.left), max(0, w.top), max(100, w.width), max(100, w.height))
            else:
                import pyautogui as pag
                screen = pag.size()
                region = (0, 0, screen.width, screen.height)

            x, y, width, height = region
            # Juft bo'lishi kerak (codec talabi)
            width  = width  - (width  % 2)
            height = height - (height % 2)

            fd, tmp_path = tempfile.mkstemp(suffix=".mp4")
            os.close(fd)

            fps = 8
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(tmp_path, fourcc, fps, (width, height))

            start = time.time()
            while time.time() - start < duration:
                img = pyautogui.screenshot(region=(x, y, width, height))
                frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                # Resize — kichikroq fayl
                frame = cv2.resize(frame, (width // 2 * 2, height // 2 * 2))
                out.write(frame)
                time.sleep(1 / fps)

            out.release()

            with open(tmp_path, "rb") as f:
                data = f.read()
            os.unlink(tmp_path)
            return data

        except ImportError:
            logger.error("opencv-python o'rnatilmagan: pip install opencv-python")
            return b""
        except Exception as e:
            logger.error(f"_record_screen xato: {e}")
            return b""

    def _screenshot_b64(self) -> bytes:
        """VS Code yoki ekran screenshot → raw PNG bytes"""
        try:
            import pyautogui, pygetwindow as gw, io, time
            wins = gw.getWindowsWithTitle("Visual Studio Code") or gw.getWindowsWithTitle("Code")
            if wins:
                w = wins[0]
                w.restore()
                try:
                    w.activate()
                except Exception:
                    pass
                time.sleep(0.2)
                img = pyautogui.screenshot(region=(
                    max(0, w.left), max(0, w.top),
                    max(100, w.width), max(100, w.height)
                ))
            else:
                img = pyautogui.screenshot()

            # Sifatni kamaytirish — Telegram limit 10MB
            buf = io.BytesIO()
            img = img.resize((img.width // 2, img.height // 2))
            img.save(buf, format="JPEG", quality=60, optimize=True)
            return buf.getvalue()
        except Exception as e:
            logger.error(f"Screenshot b64 xato: {e}")
            return b""

    async def _send_photo_bytes(self, chat_id: int, data: bytes, caption: str = ""):
        """Bytes dan to'g'ridan-to'g'ri Telegram ga rasm yuborish"""
        try:
            import io
            await self._bot.send_photo(
                chat_id=chat_id,
                photo=io.BytesIO(data),
                caption=caption
            )
        except Exception as e:
            logger.error(f"send_photo_bytes xato: {e}")

    def _take_quick_screenshot(self, caption: str = "📸 Screenshot"):
        """VS Code screenshot olib Telegram ga yuborish"""
        try:
            import pyautogui, tempfile, os, time
            try:
                import pygetwindow as gw
                wins = gw.getWindowsWithTitle("Visual Studio Code") or gw.getWindowsWithTitle("Code")
                if wins:
                    w = wins[0]
                    try:
                        w.restore()
                        w.activate()
                        time.sleep(0.3)
                    except Exception:
                        pass   # activate xatosini e'tiborsiz qoldirish
                    region = (max(0,w.left), max(0,w.top), max(100,w.width), max(100,w.height))
                    img = pyautogui.screenshot(region=region)
                else:
                    img = pyautogui.screenshot()
            except Exception:
                img = pyautogui.screenshot()

            fd, path = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            img.save(path)
            self.send_photo(path, caption)
        except Exception as e:
            self.send_message(f"❌ Screenshot xatosi: {e}")

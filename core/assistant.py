"""
GHOST Assistant Core Module
Main assistant logic and coordination
"""

import threading
import time
import logging
import re
import urllib.parse
from PyQt6.QtCore import QObject, pyqtSignal
from typing import Optional, Dict, Any

from .wake_word_oww import WakeWordDetector
from .listener import VoiceListener
from .speaker import VoiceSpeaker
from .intent_parser import IntentParser
from .context_manager import ContextManager
from .voice_profiler import VoiceProfiler
from .telegram_bot import TelegramBotHandler
from config import Config

logger = logging.getLogger(__name__)

class GhostAssistant(QObject):
    """Main GHOST Assistant class"""
    
    # Signals
    wake_word_detected = pyqtSignal()
    response_ready = pyqtSignal(str)
    listening_started = pyqtSignal()
    listening_stopped = pyqtSignal()
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.is_running = False
        self.is_listening = False
        
        # Initialize components
        self.wake_word_detector = WakeWordDetector(config)
        self.voice_listener = VoiceListener(config)
        self.voice_speaker = VoiceSpeaker(config)
        self.intent_parser = IntentParser(config)
        self.context_manager = ContextManager()
        self.voice_profiler = VoiceProfiler(config)

        # Telegram bot - buyruqlarni qayta ishlash funksiyasini uzatamiz
        self.telegram_bot = TelegramBotHandler(
            command_callback=self._telegram_command
        )
        # Unlock callback ni o'rnatish
        self.telegram_bot.unlock_callback = self._unlock_from_telegram
        if self.telegram_bot.is_available():
            logger.info("Telegram bot ulandi")
        
        # Connect signals
        self.wake_word_detector.wake_word_detected.connect(self.on_wake_word_detected)
        self.voice_listener.speech_detected.connect(self.on_speech_detected)
        
        # Current user context
        self.current_user = None
        
    def start(self):
        """Start the assistant"""
        logger.info("Starting GHOST Assistant...")
        self.is_running = True
        # Telegram botni ishga tushirish
        if self.telegram_bot.is_available():
            self.telegram_bot.start()
        # Wake word detection
        self.wake_word_detector.start()
        self.assistant_loop()
        
    def stop(self):
        """Stop the assistant"""
        logger.info("Stopping GHOST Assistant...")
        self.is_running = False
        self.wake_word_detector.stop()
        self.voice_listener.stop()
        self.voice_speaker.stop()
        if self.telegram_bot.is_available():
            self.telegram_bot.stop()
        
    def assistant_loop(self):
        """Main assistant loop"""
        while self.is_running:
            try:
                time.sleep(0.1)  # Small delay to prevent CPU usage
            except Exception as e:
                logger.error(f"Error in assistant loop: {e}")
                
    def _telegram_command(self, text: str) -> str:
        """Telegram dan kelgan buyruqni bajarish va javob qaytarish"""
        try:
            intent = self.intent_parser.parse(text)
            if intent:
                response = self.execute_intent(intent)
                # Ovozda ham aytish (ixtiyoriy)
                self.voice_speaker.speak(response)
                return response
            return f"Tushunmadim: {text}"
        except Exception as e:
            logger.error(f"Telegram command error: {e}")
            return "Xatolik yuz berdi"

    def on_wake_word_detected(self):
        """Handle wake word detection"""
        if self.is_listening:
            return  # allaqachon eshitilmoqda
        logger.info("Wake word detected!")
        self.wake_word_detected.emit()
        self.response_ready.emit("🎤  Слушаю...")
        self.start_listening()
        self.play_wake_sound()
        
    def start_listening(self):
        """Start listening for user command"""
        if self.is_listening:
            return
            
        logger.info("Started listening for command...")
        self.is_listening = True
        self.listening_started.emit()
        
        # Start voice listener
        self.voice_listener.start_listening()
        
    def stop_listening(self):
        """Stop listening for user command"""
        if not self.is_listening:
            return
            
        logger.info("Stopped listening")
        self.is_listening = False
        self.listening_stopped.emit()
        
        # Stop voice listener
        self.voice_listener.stop_listening()
        
    def on_speech_detected(self, text: str, user_profile: Optional[Dict] = None):
        """Handle detected speech"""
        logger.info(f"Detected speech: {text}")
        
        # Stop listening
        self.stop_listening()
        
        # Update current user if voice profile detected
        if user_profile:
            self.current_user = user_profile
            logger.info(f"Detected user: {user_profile.get('name', 'Unknown')}")
        else:
            logger.info("Unknown user detected")
            
        # Process the command
        self.process_command(text)
        
    def process_command(self, command: str):
        """Process user command - intent parser orqali"""
        try:
            logger.info(f"Processing command: {command}")
            self.context_manager.add_command(command)
            self.response_ready.emit("⚙️  Выполняю...")

            intent = self.intent_parser.parse(command)
            if intent:
                response = self.execute_intent(intent)
                self.speak_response(response)
            else:
                self.speak_response(f"Не понял: \"{command}\"")

        except Exception as e:
            logger.error(f"Error processing command: {e}")
            self.speak_response("Произошла ошибка.")
            
    def execute_intent(self, intent: Dict[str, Any]) -> str:
        """Execute parsed intent"""
        action = intent.get('action')
        parameters = intent.get('parameters', {})
        
        logger.info(f"Executing intent: {action} with params: {parameters}")

        if action == 'system.volume_up':
            return self.execute_volume_change(parameters.get('amount', 10), 'up')
        elif action == 'system.volume_down':
            return self.execute_volume_change(parameters.get('amount', 10), 'down')
        elif action == 'system.volume_mute':
            return self.execute_volume_mute()
        elif action == 'system.volume_set':
            return self.execute_volume_set(parameters.get('level', 50))
        elif action == 'system.brightness_up':
            return self.execute_brightness_change(parameters.get('amount', 10), 'up')
        elif action == 'system.brightness_down':
            return self.execute_brightness_change(parameters.get('amount', 10), 'down')
        elif action == 'system.screenshot':
            return self.execute_screenshot()
        elif action == 'system.screenshot_window':
            return self.execute_screenshot_window()
        elif action == 'system.shutdown':
            return self.execute_shutdown()
        elif action == 'system.sleep':
            return self.execute_sleep()
        elif action == 'system.restart':
            return self.execute_restart()
        elif action == 'system.lock':
            return self.execute_lock()
        elif action == 'system.unlock':
            return self.execute_unlock(parameters.get('pin'))
        elif action == 'system.set_pin':
            return self.execute_set_unlock_pin(parameters.get('text', ''))
        elif action == 'system.cancel_shutdown':
            return self.execute_cancel_shutdown()
        elif action == 'system.time':
            return self.execute_time()
        elif action == 'system.date':
            return self.execute_date()
        elif action == 'system.battery':
            return self.execute_battery()
        elif action == 'system.info':
            return self.execute_system_info()
        elif action == 'system.disk':
            return self.execute_disk_info()
        elif action == 'system.network':
            return self.execute_network_info()
        elif action == 'system.processes':
            return self.execute_top_processes()
        elif action == 'app.open':
            return self.execute_app_open(parameters.get('app_name'))
        elif action == 'app.close':
            return self.execute_app_close(parameters.get('app_name'))
        elif action == 'app.switch':
            return self.execute_app_switch(parameters.get('app_name'))
        elif action == 'app.running_list':
            return self.execute_running_apps()
        elif action == 'media.play_pause':
            return self.execute_media_key('play_pause')
        elif action == 'media.next':
            return self.execute_media_key('next')
        elif action == 'media.prev':
            return self.execute_media_key('prev')
        elif action == 'window.minimize':
            return self.execute_window('minimize')
        elif action == 'window.maximize':
            return self.execute_window('maximize')
        elif action == 'window.close':
            return self.execute_window('close')
        elif action == 'window.switch':
            return self.execute_hotkey('alt', 'tab')
        elif action == 'window.desktop':
            return self.execute_hotkey('win', 'd')
        elif action == 'clipboard.copy':
            return self.execute_hotkey('ctrl', 'c')
        elif action == 'clipboard.paste':
            return self.execute_hotkey('ctrl', 'v')
        elif action == 'clipboard.select_all':
            return self.execute_hotkey('ctrl', 'a')
        elif action == 'keyboard.undo':
            return self.execute_hotkey('ctrl', 'z')
        elif action == 'keyboard.redo':
            return self.execute_hotkey('ctrl', 'y')
        elif action == 'keyboard.save':
            return self.execute_hotkey('ctrl', 's')
        elif action == 'keyboard.new_tab':
            return self.execute_hotkey('ctrl', 't')
        elif action == 'keyboard.close_tab':
            return self.execute_hotkey('ctrl', 'w')
        elif action == 'keyboard.refresh':
            return self.execute_hotkey('f5')
        elif action == 'keyboard.fullscreen':
            return self.execute_hotkey('f11')
        elif action == 'keyboard.zoom_in':
            return self.execute_hotkey('ctrl', '+')
        elif action == 'keyboard.zoom_out':
            return self.execute_hotkey('ctrl', '-')
        elif action == 'browser.search':
            return self.execute_browser_search(parameters.get('query', ''))
        elif action == 'browser.open_url':
            return self.execute_open_url(parameters.get('url', ''))
        elif action == 'youtube.play':
            return self.execute_youtube(parameters.get('query', ''))
        elif action == 'weather.get':
            return self.execute_weather_get(parameters.get('location'))
        elif action == 'calculator.calculate':
            return self.execute_calculate(parameters.get('expression'))
        elif action == 'translator.translate':
            return self.execute_translate(parameters.get('text'), parameters.get('target_lang'))
        elif action == 'files.open_downloads':
            return self.execute_open_folder('downloads')
        elif action == 'files.open_documents':
            return self.execute_open_folder('documents')
        elif action == 'files.open_desktop':
            return self.execute_open_folder('desktop')
        elif action == 'files.open_path':
            return self.execute_open_folder(parameters.get('path', ''))
        elif action == 'timer.set':
            return self.execute_timer(parameters.get('seconds', 60))
        elif action == 'reminder.set':
            return self.execute_reminder(parameters.get('text', ''))
        # ── Yangi buyruqlar ──
        elif action == 'mouse.scroll_up':
            return self.execute_mouse_scroll('up', parameters.get('amount', 3))
        elif action == 'mouse.scroll_down':
            return self.execute_mouse_scroll('down', parameters.get('amount', 3))
        elif action == 'mouse.click':
            return self.execute_mouse_click('left')
        elif action == 'mouse.double_click':
            return self.execute_mouse_click('double')
        elif action == 'mouse.right_click':
            return self.execute_mouse_click('right')
        elif action == 'mouse.center':
            return self.execute_mouse_center()
        elif action == 'keyboard.type':
            return self.execute_type_text(parameters.get('text', ''))
        elif action == 'keyboard.enter':
            return self.execute_hotkey('enter')
        elif action == 'keyboard.escape':
            return self.execute_hotkey('escape')
        elif action == 'keyboard.delete':
            return self.execute_hotkey('delete')
        elif action == 'keyboard.print_screen':
            return self.execute_hotkey('printscreen')
        elif action == 'system.empty_trash':
            return self.execute_empty_trash()
        elif action == 'system.kill_process':
            return self.execute_kill_process(parameters.get('text', ''))
        elif action == 'system.clear_clipboard':
            return self.execute_clear_clipboard()
        elif action == 'system.uptime':
            return self.execute_uptime()
        elif action == 'web.open_github':
            return self.execute_open_url('https://github.com')
        elif action == 'web.open_gmail':
            return self.execute_open_url('https://mail.google.com')
        elif action == 'web.open_maps':
            return self.execute_open_url('https://maps.google.com')
        elif action == 'web.open_translate':
            return self.execute_open_url('https://translate.google.com')
        elif action == 'web.open_news':
            return self.execute_open_url('https://news.google.com')
        elif action == 'telegram.send_screenshot':
            return self.execute_telegram_screenshot()
        elif action == 'telegram.send_sysinfo':
            return self.execute_telegram_sysinfo()
        elif action == 'voice.repeat':
            return self.execute_voice_repeat()
        elif action == 'voice.stop':
            self.voice_speaker.stop()
            return "To'xtatildi"
        # ── Advanced funksiyalar ──
        elif action == 'clipboard.read':
            return self.execute_clipboard_read()
        elif action == 'network.speed_test':
            return self.execute_speed_test()
        elif action == 'network.check':
            return self.execute_network_check()
        elif action == 'security.gen_password':
            return self.execute_gen_password(parameters.get('length', 16))
        elif action == 'system.notify':
            return self.execute_notify(parameters.get('text', 'GHOST'))
        elif action == 'recorder.start':
            return self.execute_recorder_start(parameters.get('seconds', 30))
        elif action == 'recorder.stop':
            return self.execute_recorder_stop()
        elif action == 'mode.work':
            return self.execute_mode('work')
        elif action == 'mode.rest':
            return self.execute_mode('rest')
        elif action == 'mode.presentation':
            return self.execute_mode('presentation')
        elif action == 'files.search':
            return self.execute_file_search(parameters.get('text', ''))
        elif action == 'system.full_report':
            return self.execute_full_report()
        elif action == 'screen.record':
            return self.execute_screen_record(parameters.get('seconds', 30))
        elif action == 'calculator.smart':
            return self.execute_smart_calc(parameters.get('text', ''))
        else:
            return "Bu buyruqni hali o'rganmaganman."
            
    def execute_volume_change(self, amount: int, direction: str) -> str:
        """Execute volume change command"""
        try:
            from modules.system.volume import VolumeController
            volume_controller = VolumeController()
            
            if direction == 'up':
                volume_controller.increase_volume(amount)
                return f"Громкость увеличена на {amount}%"
            else:
                volume_controller.decrease_volume(amount)
                return f"Громкость уменьшена на {amount}%"
                
        except Exception as e:
            logger.error(f"Error changing volume: {e}")
            return "Не удалось изменить громкость"
            
    def execute_volume_mute(self) -> str:
        """Execute volume mute command"""
        try:
            from modules.system.volume import VolumeController
            volume_controller = VolumeController()
            
            if volume_controller.toggle_mute():
                return "Звук выключен"
            else:
                return "Звук включён"
                
        except Exception as e:
            logger.error(f"Error toggling mute: {e}")
            return "Не удалось переключить звук"
            
    def execute_brightness_change(self, amount: int, direction: str) -> str:
        """Execute brightness change command"""
        try:
            from modules.system.brightness import BrightnessController
            brightness_controller = BrightnessController()
            
            if direction == 'up':
                brightness_controller.increase_brightness(amount)
                return f"Яркость увеличена на {amount}%"
            else:
                brightness_controller.decrease_brightness(amount)
                return f"Яркость уменьшена на {amount}%"
                
        except Exception as e:
            logger.error(f"Error changing brightness: {e}")
            return "Не удалось изменить яркость"
            
    def execute_screenshot(self) -> str:
        """Execute screenshot command"""
        try:
            from modules.system.screenshot import ScreenshotManager
            screenshot_manager = ScreenshotManager(self.config)
            
            filename = screenshot_manager.take_screenshot()
            return f"Скриншот сохранён: {filename}"
            
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return "Не удалось сделать скриншот"
            
    def execute_shutdown(self) -> str:
        """Execute shutdown command"""
        try:
            from modules.system.power import PowerManager
            power_manager = PowerManager(self.config)
            
            # Schedule shutdown with confirmation
            power_manager.schedule_shutdown(30)
            return "Компьютер выключится через 30 секунд."
            
        except Exception as e:
            logger.error(f"Error scheduling shutdown: {e}")
            return "Не удалось выключить компьютер"
            
    def execute_sleep(self) -> str:
        """Execute sleep command"""
        try:
            from modules.system.power import PowerManager
            power_manager = PowerManager(self.config)
            
            power_manager.sleep()
            return "Компьютер переходит в спящий режим"
            
        except Exception as e:
            logger.error(f"Error sleeping computer: {e}")
            return "Не удалось перевести в сон"
            
    def execute_restart(self) -> str:
        """Execute restart command"""
        try:
            from modules.system.power import PowerManager
            power_manager = PowerManager(self.config)
            
            power_manager.schedule_restart(30)
            return "Компьютер перезагрузится через 30 секунд."
            
        except Exception as e:
            logger.error(f"Error scheduling restart: {e}")
            return "Не удалось перезагрузить"
            
    def execute_app_open(self, app_name: str) -> str:
        """Execute app open command"""
        try:
            from modules.system.applications import AppManager
            app_manager = AppManager(self.config)
            
            if app_manager.open_app(app_name):
                return f"{app_name} открыт"
            else:
                return f"{app_name} topilmadi"
                
        except Exception as e:
            logger.error(f"Error opening app: {e}")
            return "Не удалось открыть приложение"
            
    def execute_app_close(self, app_name: str) -> str:
        """Execute app close command"""
        try:
            from modules.system.applications import AppManager
            app_manager = AppManager(self.config)
            
            if app_manager.close_app(app_name):
                return f"{app_name} закрыт"
            else:
                return f"{app_name} topilmadi"
                
        except Exception as e:
            logger.error(f"Error closing app: {e}")
            return "Не удалось закрыть приложение"
            
    def execute_translate(self, text: str, target_lang: str) -> str:
        """Execute translate command"""
        try:
            from modules.productivity.translator import TranslatorManager
            translator = TranslatorManager()
            
            result = translator.translate(text, target_lang)
            return result
            
        except Exception as e:
            logger.error(f"Error translating: {e}")
            return "Не удалось перевести"
            
    def execute_calculate(self, expression: str) -> str:
        """Execute calculate command"""
        try:
            from modules.productivity.calculator import Calculator
            calculator = Calculator()
            
            result = calculator.calculate(expression)
            return f"Результат: {result}"
            
        except Exception as e:
            logger.error(f"Error calculating: {e}")
            return "Не удалось вычислить"
            
    # ── Yangi handlerlar ────────────────────────────────────────────

    def execute_volume_set(self, level: int) -> str:
        try:
            from modules.system.volume import VolumeController
            vc = VolumeController()
            vc.set_volume(level / 100.0)
            return f"Ovoz {level}% ga o'rnatildi"
        except Exception as e:
            logger.error(f"Volume set error: {e}")
            return "Ovozni o'rnatib bo'lmadi"

    def execute_screenshot_window(self) -> str:
        try:
            from modules.system.screenshot import ScreenshotManager
            sm = ScreenshotManager(self.config)
            path = sm.take_active_window_screenshot()
            return f"Oyna skrinshoti saqlandi: {path}"
        except Exception as e:
            logger.error(f"Screenshot window error: {e}")
            return "Oyna skrinshoti olib bo'lmadi"

    def execute_lock(self) -> str:
        try:
            import subprocess
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
            return "🔒 Ekran qulflandi"
        except Exception as e:
            logger.error(f"Lock error: {e}")
            return "Qulflash amalga oshmadi"

    def execute_unlock(self, pin: str = None) -> str:
        """Ekranni lockdan ochish"""
        from modules.advanced.features import unlock_screen, get_unlock_pin
        # PIN berilmagan bo'lsa saqlanganni ishlatish
        if not pin:
            pin = get_unlock_pin()
        return unlock_screen(pin if pin else None)

    def execute_set_unlock_pin(self, pin: str) -> str:
        """Unlock PIN ni saqlash"""
        from modules.advanced.features import set_unlock_pin
        return set_unlock_pin(pin)

    def _unlock_from_telegram(self, pin: str = None) -> str:
        """Telegram /unlock buyrug'i"""
        from modules.advanced.features import unlock_screen, get_unlock_pin
        if not pin:
            pin = get_unlock_pin()
        result = unlock_screen(pin if pin else None)
        logger.info(f"Telegram unlock: {result}")
        return result

    def execute_cancel_shutdown(self) -> str:
        try:
            import subprocess
            subprocess.run(["shutdown", "/a"], check=True)
            return "O'chirish bekor qilindi"
        except Exception:
            return "Bekor qilish amalga oshmadi"

    def execute_disk_info(self) -> str:
        try:
            import psutil
            parts = psutil.disk_partitions()
            result = []
            for p in parts:
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    free_gb = usage.free // (1024**3)
                    total_gb = usage.total // (1024**3)
                    result.append(f"{p.device}: {free_gb}GB bo'sh / {total_gb}GB")
                except Exception:
                    pass
            return " | ".join(result) if result else "Disk ma'lumoti topilmadi"
        except Exception as e:
            return "Disk ma'lumotini olib bo'lmadi"

    def execute_network_info(self) -> str:
        try:
            import socket, psutil
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            stats = psutil.net_io_counters()
            sent_mb = stats.bytes_sent // (1024**2)
            recv_mb = stats.bytes_recv // (1024**2)
            return f"IP: {ip} | Yuborildi: {sent_mb}MB | Qabul: {recv_mb}MB"
        except Exception as e:
            return "Tarmoq ma'lumotini olib bo'lmadi"

    def execute_top_processes(self) -> str:
        try:
            import psutil
            procs = []
            for p in psutil.process_iter(['name', 'cpu_percent', 'memory_percent']):
                try:
                    procs.append(p.info)
                except Exception:
                    pass
            top = sorted(procs, key=lambda x: x.get('cpu_percent', 0), reverse=True)[:3]
            result = []
            for p in top:
                result.append(f"{p['name']}: CPU {p['cpu_percent']:.1f}%")
            return " | ".join(result) if result else "Jarayonlar topilmadi"
        except Exception as e:
            return "Jarayonlar ma'lumotini olib bo'lmadi"

    def execute_app_switch(self, app_name: str) -> str:
        try:
            from modules.system.applications import AppManager
            am = AppManager(self.config)
            if am.switch_to_app(app_name):
                return f"{app_name} ga o'tildi"
            return f"{app_name} topilmadi"
        except Exception as e:
            logger.error(f"App switch error: {e}")
            return "Ilovaga o'tib bo'lmadi"

    def execute_running_apps(self) -> str:
        try:
            import psutil
            names = set()
            for p in psutil.process_iter(['name']):
                try:
                    n = p.info['name']
                    if n and not n.endswith('svchost.exe') and len(n) > 3:
                        names.add(n.replace('.exe', ''))
                except Exception:
                    pass
            top = sorted(names)[:10]
            return "Ochiq: " + ", ".join(top)
        except Exception:
            return "Ilovalar ro'yxatini olib bo'lmadi"

    def execute_hotkey(self, *keys) -> str:
        try:
            import pyautogui
            if len(keys) == 1:
                pyautogui.press(keys[0])
            else:
                pyautogui.hotkey(*keys)
            labels = {
                ('ctrl', 'c'): "Nusxalandi",
                ('ctrl', 'v'): "Joylashtirildi",
                ('ctrl', 'a'): "Hammasi tanlandi",
                ('ctrl', 'z'): "Bekor qilindi",
                ('ctrl', 'y'): "Qaytarildi",
                ('ctrl', 's'): "Saqlandi",
                ('ctrl', 't'): "Yangi tab ochildi",
                ('ctrl', 'w'): "Tab yopildi",
                ('f5',):       "Yangilandi",
                ('f11',):      "To'liq ekran",
                ('ctrl', '+'): "Kattalashtirild",
                ('ctrl', '-'): "Kichraytirildi",
                ('alt', 'tab'): "Oynalar almashtirildi",
                ('win', 'd'):  "Ish stoli ko'rsatildi",
            }
            return labels.get(keys, "Bajarildi")
        except Exception as e:
            logger.error(f"Hotkey error: {e}")
            return "Tugma bosilmadi"

    def execute_open_folder(self, folder: str) -> str:
        try:
            import os, subprocess
            paths = {
                'downloads': os.path.join(os.path.expanduser("~"), "Downloads"),
                'documents': os.path.join(os.path.expanduser("~"), "Documents"),
                'desktop':   os.path.join(os.path.expanduser("~"), "Desktop"),
            }
            path = paths.get(folder, folder)
            if os.path.exists(path):
                subprocess.Popen(f'explorer "{path}"', shell=True)
                return f"Papka ochildi: {path}"
            return f"Papka topilmadi: {path}"
        except Exception as e:
            logger.error(f"Open folder error: {e}")
            return "Papkani ochib bo'lmadi"

    def execute_timer(self, seconds: int) -> str:
        def _timer_done():
            import time
            time.sleep(seconds)
            msg = f"⏰ Taymer tugadi! ({seconds} soniya)"
            self.speak_response(msg)
            if self.telegram_bot.is_available():
                self.telegram_bot.send_message(msg)

        import threading
        t = threading.Thread(target=_timer_done, daemon=True)
        t.start()
        mins = seconds // 60
        secs = seconds % 60
        if mins > 0:
            return f"Taymer {mins} daqiqa {secs} soniyaga o'rnatildi"
        return f"Taymer {secs} soniyaga o'rnatildi"

    def execute_reminder(self, text: str) -> str:
        if not text:
            return "Nima haqida eslatma?"
        # Oddiy eslatma - 1 daqiqadan keyin
        def _remind():
            import time
            time.sleep(60)
            msg = f"⏰ Eslatma: {text}"
            self.speak_response(msg)
            if self.telegram_bot.is_available():
                self.telegram_bot.send_message(msg)
        import threading
        threading.Thread(target=_remind, daemon=True).start()
        return f"Eslatma o'rnatildi: {text}"

    # ── Mouse ────────────────────────────────────────────

    def execute_mouse_scroll(self, direction: str, amount: int) -> str:
        try:
            import pyautogui
            clicks = amount if direction == 'up' else -amount
            pyautogui.scroll(clicks)
            return f"Scroll {'yuqoriga' if direction == 'up' else 'pastga'}"
        except Exception as e:
            logger.error(f"Scroll error: {e}")
            return "Scroll amalga oshmadi"

    def execute_mouse_click(self, click_type: str) -> str:
        try:
            import pyautogui
            if click_type == 'double':
                pyautogui.doubleClick()
                return "Ikki marta bosildi"
            elif click_type == 'right':
                pyautogui.rightClick()
                return "O'ng tugma bosildi"
            else:
                pyautogui.click()
                return "Bosildi"
        except Exception as e:
            logger.error(f"Click error: {e}")
            return "Bosib bo'lmadi"

    def execute_mouse_center(self) -> str:
        try:
            import pyautogui
            w, h = pyautogui.size()
            pyautogui.moveTo(w // 2, h // 2, duration=0.3)
            return "Sichqoncha markazga o'tdi"
        except Exception as e:
            return "Sichqonchani ko'chirib bo'lmadi"

    # ── Matn kiritish ────────────────────────────────────

    def execute_type_text(self, text: str) -> str:
        try:
            import pyautogui
            if not text:
                return "Nima yozishni ayting"
            pyautogui.typewrite(text, interval=0.05)
            return f"Yozildi: {text}"
        except Exception as e:
            logger.error(f"Type error: {e}")
            return "Yozib bo'lmadi"

    # ── Tizim tozalash ───────────────────────────────────

    def execute_empty_trash(self) -> str:
        try:
            import subprocess
            # Windows Recycle Bin tozalash
            subprocess.run([
                'powershell', '-Command',
                'Clear-RecycleBin -Force -ErrorAction SilentlyContinue'
            ], capture_output=True)
            return "Savatcha tozalandi"
        except Exception as e:
            logger.error(f"Empty trash error: {e}")
            return "Savatchani tozalab bo'lmadi"

    def execute_kill_process(self, process_name: str) -> str:
        try:
            import psutil
            if not process_name:
                return "Qaysi jarayonni o'chirish kerak?"
            killed = []
            for p in psutil.process_iter(['name', 'pid']):
                try:
                    if process_name.lower() in p.info['name'].lower():
                        p.kill()
                        killed.append(p.info['name'])
                except Exception:
                    pass
            if killed:
                return f"O'chirildi: {', '.join(killed)}"
            return f"'{process_name}' jarayoni topilmadi"
        except Exception as e:
            logger.error(f"Kill process error: {e}")
            return "Jarayonni o'chirib bo'lmadi"

    def execute_clear_clipboard(self) -> str:
        try:
            import subprocess
            subprocess.run([
                'powershell', '-Command',
                'Set-Clipboard -Value ""'
            ], capture_output=True)
            return "Clipboard tozalandi"
        except Exception as e:
            return "Clipboard tozalab bo'lmadi"

    def execute_uptime(self) -> str:
        try:
            import psutil, datetime
            boot = psutil.boot_time()
            uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(boot)
            hours = int(uptime.total_seconds() // 3600)
            minutes = int((uptime.total_seconds() % 3600) // 60)
            return f"Kompyuter {hours} soat {minutes} daqiqadan beri ishlayapti"
        except Exception:
            return "Uptime ma'lumotini olib bo'lmadi"

    # ── Telegram maxsus ──────────────────────────────────

    def execute_telegram_screenshot(self) -> str:
        try:
            from modules.system.screenshot import ScreenshotManager
            sm = ScreenshotManager(self.config)
            path = sm.take_screenshot()
            if path and self.telegram_bot.is_available():
                # Rasmni yuborish
                import asyncio
                async def _send():
                    await self.telegram_bot._bot.send_photo(
                        chat_id=self.telegram_bot.owner_id,
                        photo=open(path, 'rb'),
                        caption="📸 Skrinshot"
                    )
                asyncio.run_coroutine_threadsafe(
                    _send(), self.telegram_bot._loop
                )
                return "Skrinshot Telegramga yuborildi"
            return "Telegram ulanmagan"
        except Exception as e:
            logger.error(f"Telegram screenshot error: {e}")
            return "Skrinshot yuborib bo'lmadi"

    def execute_telegram_sysinfo(self) -> str:
        try:
            info = self.execute_system_info()
            battery = self.execute_battery()
            disk = self.execute_disk_info()
            msg = f"💻 Tizim:\n{info}\n🔋 {battery}\n💾 {disk}"
            if self.telegram_bot.is_available():
                self.telegram_bot.send_message(msg)
                return "Tizim ma'lumoti Telegramga yuborildi"
            return "Telegram ulanmagan"
        except Exception as e:
            return "Yuborib bo'lmadi"

    # ── Ovoz ────────────────────────────────────────────

    def execute_voice_repeat(self) -> str:
        last = self.context_manager.get_last_command()
        if last:
            cmd = last.get('command', '')
            self.voice_speaker.speak(cmd)
            return f"Takrorlandi: {cmd}"
        return "Takrorlanadigan narsa yo'q"

    # ── Advanced funksiyalar ─────────────────────────────

    def execute_clipboard_read(self) -> str:
        from modules.advanced.features import read_clipboard
        return read_clipboard()

    def execute_speed_test(self) -> str:
        """Internet tezligini o'lchash (background da)"""
        def _test():
            from modules.advanced.features import check_internet_speed
            result = check_internet_speed()
            self.speak_response(result)
            if self.telegram_bot.is_available():
                self.telegram_bot.send_message(result)
        import threading
        threading.Thread(target=_test, daemon=True).start()
        return "🌐 Internet tezligi o'lchanmoqda..."

    def execute_network_check(self) -> str:
        from modules.advanced.features import check_internet_connection
        return check_internet_connection()

    def execute_gen_password(self, length: int = 16) -> str:
        from modules.advanced.features import generate_password
        return generate_password(length)

    def execute_notify(self, text: str) -> str:
        from modules.advanced.features import show_notification
        return show_notification("GHOST Assistant", text or "Eslatma!")

    _recorder = None

    def execute_recorder_start(self, seconds: int = 30) -> str:
        from modules.advanced.features import VoiceRecorder
        if GhostAssistant._recorder is None:
            GhostAssistant._recorder = VoiceRecorder()
        return GhostAssistant._recorder.start(seconds)

    def execute_recorder_stop(self) -> str:
        if GhostAssistant._recorder:
            return GhostAssistant._recorder.stop()
        return "Yozish amalga oshmayapti"

    def execute_mode(self, mode: str) -> str:
        from modules.advanced.features import work_mode, rest_mode, presentation_mode
        if mode == 'work':
            return work_mode()
        elif mode == 'rest':
            return rest_mode()
        elif mode == 'presentation':
            return presentation_mode()
        return "Noma'lum rejim"

    def execute_file_search(self, query: str) -> str:
        from modules.advanced.features import search_files
        return search_files(query)

    def execute_full_report(self) -> str:
        from modules.advanced.features import get_full_system_report
        report = get_full_system_report()
        if self.telegram_bot.is_available():
            self.telegram_bot.send_message(report)
            return "📊 To'liq hisobot Telegramga yuborildi"
        return report

    def execute_screen_record(self, seconds: int = 30) -> str:
        from modules.advanced.features import start_screen_recording
        return start_screen_recording(seconds)

    def execute_smart_calc(self, expression: str) -> str:
        from modules.advanced.features import smart_calculate
        return smart_calculate(expression)

    def execute_time(self) -> str:
        from datetime import datetime
        now = datetime.now()
        return f"Сейчас {now.strftime('%H:%M')}"

    def execute_date(self) -> str:
        from datetime import datetime
        now = datetime.now()
        days = ["понедельник","вторник","среда","четверг","пятница","суббота","воскресенье"]
        months = ["yanvar","fevral","mart","aprel","may","iyun",
                  "iyul","avgust","sentabr","oktabr","noyabr","dekabr"]
        return f"Сегодня {now.strftime('%d.%m.%Y')}, {days[now.weekday()]}"

    def execute_battery(self) -> str:
        try:
            import psutil
            b = psutil.sensors_battery()
            if b:
                status = "от сети" if b.power_plugged else "от батареи"
                return f"Батарея: {b.percent:.0f}% ({status})"
            return "Данные о батарее не найдены"
        except Exception:
            return "Не удалось получить данные о батарее"

    def execute_system_info(self) -> str:
        try:
            import psutil, platform
            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory()
            return (f"Protsessor: {cpu:.0f}% | "
                    f"RAM: {ram.used//1024//1024} MB / {ram.total//1024//1024} MB")
        except Exception:
            return "Не удалось получить данные о системе"

    def execute_media_key(self, key: str) -> str:
        try:
            import pyautogui
            key_map = {
                "play_pause": "playpause",
                "next": "nexttrack",
                "prev": "prevtrack",
            }
            pyautogui.press(key_map.get(key, "playpause"))
            labels = {"play_pause": "Play/Pause", "next": "Следующий трек", "prev": "Предыдущий трек"}
            return labels.get(key, "Выполнено")
        except Exception as e:
            logger.error(f"Media key error: {e}")
            return "Не удалось нажать медиа-кнопку"

    def execute_window(self, action: str) -> str:
        try:
            import pyautogui
            if action == "minimize":
                pyautogui.hotkey("win", "down")
                return "Окно свёрнуто"
            elif action == "maximize":
                pyautogui.hotkey("win", "up")
                return "Окно развёрнуто"
            elif action == "close":
                pyautogui.hotkey("alt", "f4")
                return "Окно закрыто"
        except Exception as e:
            logger.error(f"Window action error: {e}")
            return "Не удалось управлять окном"

    def execute_browser_search(self, query: str) -> str:
        try:
            import webbrowser, urllib.parse
            if not query:
                return "Нима qidirishni ayting"
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            webbrowser.open(url)
            return f"Ищу: {query}"
        except Exception as e:
            logger.error(f"Browser search error: {e}")
            return "Не удалось выполнить поиск"

    def execute_open_url(self, url: str) -> str:
        try:
            import webbrowser
            if not url:
                return "Какой сайт открыть?"
            if not url.startswith("http"):
                url = "https://" + url
            webbrowser.open(url)
            return f"Открываю: {url}"
        except Exception as e:
            logger.error(f"Open URL error: {e}")
            return "Не удалось открыть сайт"

    def execute_youtube(self, query: str) -> str:
        try:
            import webbrowser
            if not query:
                webbrowser.open("https://youtube.com")
                return "YouTube ochildi"

            # YouTube search API (API key siz)
            video_url, title, duration = self._youtube_search(query)

            if video_url:
                webbrowser.open(video_url + "&autoplay=1")
                logger.info(f"YouTube play: {title}")
                return f"▶️ {title}" + (f" [{duration}]" if duration else "")

            # Fallback
            import urllib.parse
            webbrowser.open(
                f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
            )
            return f"YouTube da qidirilmoqda: {query}"

        except Exception as e:
            logger.error(f"YouTube error: {e}")
            return "YouTube ni ochib bo'lmadi"

    def _youtube_search(self, query: str):
        """YouTube dan birinchi video URL, nomi va davomiyligini qaytaradi"""
        try:
            import requests, urllib.parse, re, json

            # YouTube search sahifasini yuklaymiz
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
            }
            resp = requests.get(url, headers=headers, timeout=8)
            html = resp.text

            # ytInitialData dan video ma'lumotlarini ajratib olamiz
            match = re.search(r"var ytInitialData = ({.*?});</script>", html, re.DOTALL)
            if not match:
                return None, None, None

            data = json.loads(match.group(1))

            # Birinchi video topish
            contents = (
                data.get("contents", {})
                .get("twoColumnSearchResultsRenderer", {})
                .get("primaryContents", {})
                .get("sectionListRenderer", {})
                .get("contents", [])
            )

            for section in contents:
                items = (
                    section.get("itemSectionRenderer", {})
                    .get("contents", [])
                )
                for item in items:
                    video = item.get("videoRenderer", {})
                    if not video:
                        continue
                    video_id = video.get("videoId")
                    if not video_id:
                        continue

                    # Nom
                    title_runs = video.get("title", {}).get("runs", [])
                    title = title_runs[0].get("text", query) if title_runs else query

                    # Davomiylik
                    duration = (
                        video.get("lengthText", {}).get("simpleText", "")
                    )

                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    return video_url, title, duration

        except Exception as e:
            logger.warning(f"YouTube search parse error: {e}")

        return None, None, None

    def execute_weather_get(self, location: str = None) -> str:
        try:
            import requests
            city = location or "Tashkent"
            # wttr.in - bepul, ro'yxatdan o'tish shart emas
            url = f"https://wttr.in/{urllib.parse.quote(city)}?format=3&lang=ru"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                text = resp.text.strip()
                return f"Погода: {text}"
            return "Не удалось получить погоду"
        except Exception as e:
            logger.error(f"Weather error: {e}")
            return "Сервис погоды недоступен"

    def execute_calculate(self, expression: str) -> str:
        try:
            if not expression:
                return "Скажите выражение для вычисления"
            # Faqat raqam va matematik belgilar
            safe = re.sub(r"[^\d\s\+\-\*\/\(\)\.]", "", expression)
            result = eval(safe)
            return f"Результат: {result}"
        except Exception:
            return "Ошибка вычисления"

    def speak_response(self, response: str):
        logger.info(f"Speaking response: {response}")
        # GUI da javobni ko'rsatish
        self.response_ready.emit(response)
        # Ovozda aytish
        self.voice_speaker.speak(response)
        
    def play_wake_sound(self):
        """Play wake sound"""
        try:
            # Play a subtle wake sound
            self.voice_speaker.play_wake_sound()
        except Exception as e:
            logger.error(f"Error playing wake sound: {e}")

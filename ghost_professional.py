"""
GHOST Assistant - Professional Version
Complete voice assistant with GUI and wake word detection
"""

import os
import sys
import logging
import time
import threading
import queue
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from config import Config
from core.listener_simple import VoiceListener
from core.speaker_simple import VoiceSpeaker
from core.intent_parser import IntentParser
from core.context_manager import ContextManager
from core.wake_word_continuous import ContinuousWakeWordDetector
from gui.ghost_visual import GhostVisualManager

# Simple modules
from modules.system.volume import VolumeController
from modules.system.screenshot import ScreenshotManager
from modules.system.applications import AppManager

class ProfessionalGhostAssistant:
    """Professional GHOST Assistant with GUI and wake word detection"""
    
    def __init__(self):
        # Initialize logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/ghost.log'),
                logging.StreamHandler()
            ]
        )
        
        # Create logs directory
        os.makedirs('logs', exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Starting GHOST Assistant (Professional Version)")
        
        # Initialize config
        self.config = Config()
        
        # Initialize components
        self.initialize_components()
        
        # State
        self.is_running = False
        self.is_listening = False
        self.is_visible = False
        self.speaking_lock = threading.Lock()
        self.command_queue = queue.Queue()
        
        # Visual interface
        self.visual_manager = GhostVisualManager()
        
        # Wake word detection
        self.wake_detector = ContinuousWakeWordDetector(self.config)
        self.wake_detector.set_callback(self.on_wake_word_detected)
        
        # Timing
        self.last_command_time = 0
        self.command_cooldown = 2.0
        
    def initialize_components(self):
        """Initialize all components"""
        try:
            # Core components
            self.listener = VoiceListener(self.config)
            self.speaker = VoiceSpeaker(self.config)
            self.intent_parser = IntentParser(self.config)
            self.context_manager = ContextManager()
            
            # System modules
            self.volume_controller = VolumeController()
            self.screenshot_manager = ScreenshotManager(self.config)
            self.app_manager = AppManager(self.config)
            
            # Connect signals
            self.listener.set_callback(self.on_speech_detected)
            
            self.logger.info("Components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing components: {e}")
            
    def on_wake_word_detected(self, text):
        """Handle wake word detection"""
        current_time = time.time()
        if current_time - self.last_command_time < self.command_cooldown:
            return
            
        self.last_command_time = current_time
        
        self.logger.info(f"Wake word detected: {text}")
        
        # Show visual interface
        self.show_ghost()
        
        # Greet user
        self.speak_safe("Salom! Nima yordam bera olaman?")
        
        # Start listening for commands
        self.start_listening()
        
    def on_speech_detected(self, text, user_profile):
        """Handle speech detection"""
        with self.speaking_lock:
            self.logger.info(f"Speech detected: {text}")
            
            # Stop continuous listening
            self.wake_detector.stop()
            
            # Parse intent
            intent = self.intent_parser.parse(text)
            
            if intent:
                self.logger.info(f"Intent: {intent['intent']}")
                
                # Execute command
                response = self.execute_command(intent)
                
                # Add to context
                self.context_manager.add_command(text, intent)
                
                # Speak response
                if response:
                    self.speak_safe(response)
                    
                # Hide ghost after response
                threading.Timer(3.0, self.hide_ghost).start()
                
                # Restart wake word detection
                threading.Timer(5.0, self.restart_wake_detection).start()
                
            else:
                self.speak_safe("Tushunmadim, iltimos qayta ayting.")
                threading.Timer(3.0, self.hide_ghost).start()
                threading.Timer(5.0, self.restart_wake_detection).start()
                
    def execute_command(self, intent):
        """Execute command based on intent"""
        action = intent['intent']
        parameters = intent.get('parameters', {})
        
        try:
            # System commands
            if action == 'system.volume_up':
                amount = parameters.get('amount', 10)
                if self.volume_controller.increase_volume(amount):
                    return f"Ovoz {amount} ga oshirildi"
                else:
                    return "Ovozni oshirib bo'lmadi"
                    
            elif action == 'system.volume_down':
                amount = parameters.get('amount', 10)
                if self.volume_controller.decrease_volume(amount):
                    return f"Ovoz {amount} ga kamaytirildi"
                else:
                    return "Ovozni kamaytirib bo'lmadi"
                    
            elif action == 'system.volume_mute':
                if self.volume_controller.toggle_mute():
                    return "Ovoz o'chirildi"
                else:
                    return "Ovozni o'chirib bo'lmadi"
                    
            elif action == 'system.screenshot':
                screenshot_path = self.screenshot_manager.take_screenshot()
                if screenshot_path:
                    return f"Skrinshot olindi: {screenshot_path}"
                else:
                    return "Skrinshot olinmadi"
                    
            elif action.startswith('app.open'):
                app_name = parameters.get('app_name', '')
                if app_name:
                    if self.app_manager.open_app(app_name):
                        return f"{app_name} ochildi"
                    else:
                        return f"{app_name} ni ochib bo'lmadi"
                else:
                    return "Ilova nomini ayting"
                    
            elif action.startswith('app.close'):
                app_name = parameters.get('app_name', '')
                if app_name:
                    if self.app_manager.close_app(app_name):
                        return f"{app_name} yopildi"
                    else:
                        return f"{app_name} ni yopib bo'lmadi"
                else:
                    return "Ilova nomini ayting"
                    
            else:
                return f"Bajara olmaydigan buyruq: {action}"
                
        except Exception as e:
            self.logger.error(f"Error executing command {action}: {e}")
            return "Xatolik yuz berdi"
            
    def speak_safe(self, text):
        """Speak text safely with error handling"""
        try:
            # Fix TTS rate issue
            if hasattr(self.speaker, 'config'):
                self.speaker.config.tts.rate = 1.0  # Fixed rate
                
            self.speaker.speak(text)
                
        except Exception as e:
            self.logger.error(f"Error speaking: {e}")
            
    def show_ghost(self):
        """Show ghost visual"""
        if not self.is_visible:
            self.is_visible = True
            self.visual_manager.show_ghost()
            self.logger.info("Ghost visual shown")
            
    def hide_ghost(self):
        """Hide ghost visual"""
        if self.is_visible:
            self.is_visible = False
            self.visual_manager.hide_ghost()
            self.logger.info("Ghost visual hidden")
            
    def start_listening(self):
        """Start voice listening"""
        if not self.is_listening:
            self.is_listening = True
            self.logger.info("Voice listening started")
            
            # Start listening
            self.listener.start_listening()
            
    def stop_listening(self):
        """Stop voice listening"""
        if self.is_listening:
            self.is_listening = False
            self.listener.stop_listening()
            self.logger.info("Voice listening stopped")
            
    def restart_wake_detection(self):
        """Restart wake word detection"""
        if self.is_running and not self.wake_detector.is_listening:
            self.wake_detector.start()
            self.logger.info("Wake word detection restarted")
            
    def start(self):
        """Start assistant"""
        self.logger.info("Starting GHOST Assistant...")
        
        # Test microphone
        try:
            import speech_recognition as sr
            with sr.Microphone() as source:
                recognizer = sr.Recognizer()
                recognizer.adjust_for_ambient_noise(source, duration=1)
            print("✅ Mikrofon test muvaffaqiyatli")
        except Exception as e:
            print(f"❌ Mikrofon test xatosi: {e}")
            return False
            
        # Test TTS
        try:
            self.speak_safe("GHOST Assistant tayyor")
            print("✅ Ovozli test muvaffaqiyatli")
        except Exception as e:
            print(f"❌ Ovozli test xatosi: {e}")
            return False
            
        # Test visual interface
        if not self.visual_manager.init_visual():
            print("❌ Visual interface initialization failed")
            return False
            
        self.is_running = True
        
        print("👻 GHOST Assistant ishga tushdi!")
        print("=" * 60)
        print("📋 Buyruqlar:")
        print("   'ghost' - GHOST ni chaqirish")
        print("   'skrinshot' - Skrinshot olish")
        print("   'ovozni oshir' - Ovozni oshirish")
        print("   'ovozni kamaytir' - Ovozni kamaytirish")
        print("   'chrome och' - Chrome ni ochish")
        print("   'telegram och' - Telegram ni ochish")
        print("   'exit' - Chiqish")
        print("=" * 60)
        print()
        print("🎤 'ghost' deb ayting yoki 'gapirish' deb yozing")
        print("🔊 Javoblar ovozli eshitiladi")
        print("👻 GHOST ekranda paydo bo'ladi")
        print("⏹️ Chiqish uchun 'exit' deb yozing")
        print()
        
        # Start wake word detection
        self.wake_detector.start()
        
        # Start visual interface in separate thread
        visual_thread = threading.Thread(target=self.visual_manager.run, daemon=True)
        visual_thread.start()
        
        try:
            while self.is_running:
                command = input("🎤 Buyruq: ").strip().lower()
                
                if command == 'exit':
                    print("👋 GHOST Assistant to'xtatilmoqda...")
                    break
                elif command == 'gapirish':
                    self.start_listening()
                elif command == 'to\'xtat':
                    self.stop_listening()
                elif command == 'skrinshot':
                    path = self.screenshot_manager.take_screenshot()
                    print(f"📸 Skrinshot: {path}")
                elif command == 'ovozni oshir':
                    if self.volume_controller.increase_volume(10):
                        print("🔊 Ovoz oshirildi")
                    else:
                        print("❌ Ovozni oshirib bo'lmadi")
                elif command == 'ovozni kamaytir':
                    if self.volume_controller.decrease_volume(10):
                        print("🔉 Ovoz kamaytirildi")
                    else:
                        print("❌ Ovozni kamaytirib bo'lmadi")
                elif command == 'chrome och':
                    if self.app_manager.open_app('chrome'):
                        print("🌐 Chrome ochildi")
                    else:
                        print("❌ Chrome ni ochib bo'lmadi")
                elif command == 'telegram och':
                    if self.app_manager.open_app('telegram'):
                        print("📱 Telegram ochildi")
                    else:
                        print("❌ Telegram ni ochib bo'lmadi")
                else:
                    # Simulate speech detection
                    self.on_speech_detected(command, {})
                    
        except KeyboardInterrupt:
            print("\n👋 GHOST Assistant to'xtatildi")
            
        self.stop()
        return True
        
    def stop(self):
        """Stop assistant"""
        self.is_running = False
        self.stop_listening()
        self.wake_detector.stop()
        self.hide_ghost()
        
        self.logger.info("GHOST Assistant stopped")
        print("👋 GHOST Assistant to'liq to'xtatildi")

def main():
    """Main function"""
    try:
        # Initialize and start assistant
        assistant = ProfessionalGhostAssistant()
        assistant.start()
        
    except Exception as e:
        print(f"❌ Xatolik: {e}")
        logging.error(f"Main error: {e}")

if __name__ == "__main__":
    main()

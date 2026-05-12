"""
GHOST Assistant - Voice Only Version
Complete voice assistant without PicoVoice
"""

import os
import sys
import logging
import time
import threading
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from config import Config
from core.listener_simple import VoiceListener
from core.speaker_simple import VoiceSpeaker
from core.intent_parser import IntentParser
from core.context_manager import ContextManager

# Simple modules
from modules.system.volume import VolumeController
from modules.system.brightness import BrightnessController
from modules.system.power import PowerManager
from modules.system.screenshot import ScreenshotManager
from modules.system.applications import AppManager

class VoiceOnlyAssistant:
    """Complete voice assistant without wake word detection"""
    
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
        self.logger.info("Starting GHOST Assistant (Voice Only)")
        
        # Initialize config
        self.config = Config()
        
        # Initialize components
        self.initialize_components()
        
        # State
        self.is_running = False
        self.is_listening = False
        
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
            self.brightness_controller = BrightnessController()
            self.power_manager = PowerManager(self.config)
            self.screenshot_manager = ScreenshotManager(self.config)
            self.app_manager = AppManager(self.config)
            
            # Connect signals
            self.listener.set_callback(self.on_speech_detected)
            
            self.logger.info("Components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing components: {e}")
            
    def on_speech_detected(self, text, user_profile):
        """Handle speech detection"""
        self.logger.info(f"Speech detected: {text}")
        
        # Stop listening
        self.listener.stop_listening()
        self.is_listening = False
        
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
                self.speaker.speak(response)
        else:
            self.speaker.speak("Tushunmadim, iltimos qayta ayting.")
            
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
                    
            elif action == 'system.brightness_up':
                amount = parameters.get('amount', 10)
                if self.brightness_controller.increase_brightness(amount):
                    return f"Yorqinlik {amount} ga oshirildi"
                else:
                    return "Yorqinlikni oshirib bo'lmadi"
                    
            elif action == 'system.brightness_down':
                amount = parameters.get('amount', 10)
                if self.brightness_controller.decrease_brightness(amount):
                    return f"Yorqinlik {amount} ga kamaytirildi"
                else:
                    return "Yorqinlikni kamaytirib bo'lmadi"
                    
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
            
    def start_listening(self):
        """Start voice listening"""
        if not self.is_listening:
            self.is_listening = True
            self.speaker.play_wake_sound()
            self.listener.start_listening()
            print("🎤 Ovozli eshitish boshlandi...")
            
    def stop_listening(self):
        """Stop voice listening"""
        if self.is_listening:
            self.is_listening = False
            self.listener.stop_listening()
            print("🔇 Ovozli eshitish to'xtatildi")
            
    def start(self):
        """Start assistant"""
        self.logger.info("Starting GHOST Assistant...")
        
        # Test microphone
        try:
            import speech_recognition as sr
            with sr.Microphone() as source:
                self.recognizer = sr.Recognizer()
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("✅ Mikrofon test muvaffaqiyatli")
        except Exception as e:
            print(f"❌ Mikrofon test xatosi: {e}")
            return False
            
        # Test TTS
        try:
            self.speaker.speak("GHOST Assistant tayyor")
            print("✅ Ovozli test muvaffaqiyatli")
        except Exception as e:
            print(f"❌ Ovozli test xatosi: {e}")
            return False
            
        self.is_running = True
        
        print("👻 GHOST Assistant ishga tushdi!")
        print("=" * 60)
        print("📋 Buyruqlar:")
        print("   'gapirish' - Ovozli eshitishni boshlash")
        print("   'to'xtat' - Ovozli eshitishni to'xtatish")
        print("   'skrinshot' - Skrinshot olish")
        print("   'ovozni oshir' - Ovozni oshirish")
        print("   'ovozni kamaytir' - Ovozni kamaytirish")
        print("   'chrome och' - Chrome ni ochish")
        print("   'notepad och' - Notepad ni ochish")
        print("   'exit' - Chiqish")
        print("=" * 60)
        print()
        print("🎤 Ovozli buyruqlar uchun 'gapirish' deb yozing")
        print("🔊 Javoblar ovozli eshitiladi")
        print("⏹️ Chiqish uchun 'exit' deb yozing")
        print()
        
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
                elif command == 'notepad och':
                    if self.app_manager.open_app('notepad'):
                        print("📝 Notepad ochildi")
                    else:
                        print("❌ Notepad ni ochib bo'lmadi")
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
        
        self.logger.info("GHOST Assistant stopped")
        print("👋 GHOST Assistant to'liq to'xtatildi")

def main():
    """Main function"""
    try:
        # Initialize and start assistant
        assistant = VoiceOnlyAssistant()
        assistant.start()
        
    except Exception as e:
        print(f"❌ Xatolik: {e}")
        logging.error(f"Main error: {e}")

if __name__ == "__main__":
    main()

"""
Voice Test Without Wake Word
Direct voice recognition test
"""

import os
import sys
import logging
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from config import Config
from core.listener_simple import VoiceListener
from core.speaker_simple import VoiceSpeaker
from core.intent_parser import IntentParser

# Simple modules
from modules.system.volume import VolumeController
from modules.system.screenshot import ScreenshotManager

class VoiceOnlyTest:
    """Voice test without wake word detection"""
    
    def __init__(self):
        # Initialize logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize config
        self.config = Config()
        
        # Initialize components
        self.listener = VoiceListener(self.config)
        self.speaker = VoiceSpeaker(self.config)
        self.intent_parser = IntentParser(self.config)
        
        # System modules
        self.volume_controller = VolumeController()
        self.screenshot_manager = ScreenshotManager(self.config)
        
        # Set callback
        self.listener.set_callback(self.on_speech_detected)
        
    def on_speech_detected(self, text, user_profile):
        """Handle speech detection"""
        print(f"🎤 Siz aytdingiz: {text}")
        
        # Parse intent
        intent = self.intent_parser.parse(text)
        
        if intent:
            print(f"🎯 Buyruq: {intent['intent']}")
            
            # Execute command
            response = self.execute_command(intent)
            
            # Speak response
            if response:
                print(f"🔊 Javob: {response}")
                self.speaker.speak(response)
        else:
            print("❌ Buyruq tushunilmadi")
            
    def execute_command(self, intent):
        """Execute command based on intent"""
        action = intent['intent']
        parameters = intent.get('parameters', {})
        
        try:
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
                    
            elif action == 'system.screenshot':
                screenshot_path = self.screenshot_manager.take_screenshot()
                if screenshot_path:
                    return f"Skrinshot olindi: {screenshot_path}"
                else:
                    return "Skrinshot olinmadi"
                    
            else:
                return f"Test buyruq: {action}"
                
        except Exception as e:
            self.logger.error(f"Error executing command {action}: {e}")
            return "Xatolik yuz berdi"
            
    def run_test(self):
        """Run voice test"""
        print("🎤 GHOST Voice Test (Wake Wordsiz)")
        print("=" * 50)
        print("📋 Buyruqlar:")
        print("   'ovozni oshir' - Ovozni oshirish")
        print("   'ovozni kamaytir' - Ovozni kamaytirish")
        print("   'skrinshot ol' - Skrinshot olish")
        print("   'stop' - To'xtatish")
        print()
        print("🎤 Gapirish uchun ENTER tugmasini bosing...")
        print("🔊 Javob eshitiladi")
        print("⏹️ To'xtatish uchun Ctrl+C")
        print()
        
        # Start listening
        self.listener.start_listening()
        
        # Keep running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Test to'xtatildi")
            self.listener.stop_listening()

def main():
    """Main function"""
    try:
        test = VoiceOnlyTest()
        test.run_test()
        
    except Exception as e:
        print(f"❌ Xatolik: {e}")
        logging.error(f"Main error: {e}")

if __name__ == "__main__":
    main()

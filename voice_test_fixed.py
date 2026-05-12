"""
Fixed Voice Test
Simplified voice recognition test
"""

import os
import sys
import logging
import time
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from config import Config
from core.speaker_simple import VoiceSpeaker
from core.intent_parser import IntentParser

# Simple modules
from modules.system.volume import VolumeController
from modules.system.screenshot import ScreenshotManager

class VoiceTestFixed:
    """Fixed voice test"""
    
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
        self.speaker = VoiceSpeaker(self.config)
        self.intent_parser = IntentParser(self.config)
        
        # System modules
        self.volume_controller = VolumeController()
        self.screenshot_manager = ScreenshotManager(self.config)
        
    def test_voice_input(self):
        """Test voice input manually"""
        print("🎤 GHOST Voice Test")
        print("=" * 40)
        print("📋 Quyidagi buyruqlarni ayting:")
        print("   'ovozni oshir' - Ovozni oshirish")
        print("   'ovozni kamaytir' - Ovozni kamaytirish")
        print("   'skrinshot ol' - Skrinshot olish")
        print("   'stop' - To'xtatish")
        print()
        
        while True:
            try:
                # Get user input
                command = input("🎤 Gapiring: ").strip().lower()
                
                if command == 'stop':
                    print("👋 Test to'xtatildi")
                    break
                    
                # Parse intent
                intent = self.intent_parser.parse(command)
                
                if intent:
                    print(f"🎯 Buyruq aniqlandi: {intent['intent']}")
                    
                    # Execute command
                    response = self.execute_command(intent)
                    
                    # Speak response
                    if response:
                        print(f"🔊 Javob: {response}")
                        self.speaker.speak(response)
                else:
                    print("❌ Buyruq tushunilmadi")
                    
            except KeyboardInterrupt:
                print("\n👋 Test to'xtatildi")
                break
            except Exception as e:
                print(f"❌ Xatolik: {e}")
                
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
            
    def run(self):
        """Run the test"""
        print("👻 GHOST Assistant - Voice Test")
        print("🎤 Ovozli buyruqlar testi")
        print()
        
        # Test TTS
        print("🔊 TTS test...")
        self.speaker.speak("GHOST Assistant tayyor")
        
        # Start voice input test
        self.test_voice_input()

def main():
    """Main function"""
    try:
        test = VoiceTestFixed()
        test.run()
        
    except Exception as e:
        print(f"❌ Xatolik: {e}")
        logging.error(f"Main error: {e}")

if __name__ == "__main__":
    main()

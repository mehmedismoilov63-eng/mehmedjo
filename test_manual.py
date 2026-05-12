"""
Manual Test for GHOST Assistant
Test without wake word detection
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from config import Config
from core.listener_simple import VoiceListener
from core.speaker_simple import VoiceSpeaker
from core.intent_parser import IntentParser

# Simple modules
from modules.system.volume import VolumeController
from modules.system.brightness import BrightnessController
from modules.system.screenshot import ScreenshotManager
from modules.system.applications import AppManager

class ManualTest:
    """Manual test for GHOST functionality"""
    
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
        self.brightness_controller = BrightnessController()
        self.screenshot_manager = ScreenshotManager(self.config)
        self.app_manager = AppManager(self.config)
        
        # Set callback
        self.listener.set_callback(self.on_speech_detected)
        
        print("👻 GHOST Manual Test Mode")
        print("Commands:")
        print("  'test' - Test speech recognition")
        print("  'screenshot' - Take screenshot")
        print("  'volume up' - Increase volume")
        print("  'exit' - Exit")
        print()
        
    def on_speech_detected(self, text, user_profile):
        """Handle speech detection"""
        print(f"🎤 Detected: {text}")
        
        # Parse intent
        intent = self.intent_parser.parse(text)
        
        if intent:
            print(f"🎯 Intent: {intent['intent']}")
            
            # Execute command
            response = self.execute_command(intent)
            
            # Speak response
            if response:
                print(f"🔊 Response: {response}")
                self.speaker.speak(response)
        else:
            print("❌ No intent detected")
            
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
                    
            elif action == 'system.screenshot':
                screenshot_path = self.screenshot_manager.take_screenshot()
                if screenshot_path:
                    return f"Skrinshot olindi: {screenshot_path}"
                else:
                    return "Skrinshot olinmadi"
                    
            else:
                return f"Test command: {action}"
                
        except Exception as e:
            self.logger.error(f"Error executing command {action}: {e}")
            return "Xatolik yuz berdi"
            
    def run(self):
        """Run manual test"""
        while True:
            command = input("🎤 Say something (or type command): ").strip()
            
            if command.lower() == 'exit':
                print("👋 Exiting...")
                break
            elif command.lower() == 'test':
                print("🎤 Listening... Speak now!")
                self.listener.start_listening()
            elif command.lower() == 'screenshot':
                path = self.screenshot_manager.take_screenshot()
                print(f"📸 Screenshot: {path}")
            elif command.lower() == 'volume up':
                if self.volume_controller.increase_volume(10):
                    print("🔊 Volume increased")
                else:
                    print("❌ Failed to increase volume")
            else:
                # Simulate speech detection
                self.on_speech_detected(command, {})

if __name__ == "__main__":
    try:
        test = ManualTest()
        test.run()
    except Exception as e:
        print(f"❌ Error: {e}")

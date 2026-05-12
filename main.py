#!/usr/bin/env python3
"""
GHOST Windows Voice Assistant
Main Entry Point
Version: 1.0.0
"""

import sys
import os
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
import threading
import time

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.assistant import GhostAssistant
from gui.ghost_window import GhostWindow
from gui.tray_icon import TrayIcon
from gui.startup_prompt import StartupPrompt
from config import Config

# Configure logging
os.makedirs('logs', exist_ok=True)
_log_file = logging.FileHandler('logs/ghost.log', encoding='utf-8')
_log_console = logging.StreamHandler()
_log_fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
_log_file.setFormatter(_log_fmt)
_log_console.setFormatter(_log_fmt)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
# Eski handlerlarni olib tashlash
root_logger.handlers.clear()
root_logger.addHandler(_log_file)
root_logger.addHandler(_log_console)

logger = logging.getLogger(__name__)

class GhostApp:
    """Main application class for GHOST Assistant"""
    
    def __init__(self):
        self.config = Config()
        self.app = QApplication(sys.argv)
        self.assistant = None
        self.window = None
        self.tray_icon = None
        self.is_running = False
        
    def initialize(self):
        """Initialize all components"""
        try:
            logger.info("Initializing GHOST Assistant...")
            
            # Create directories
            os.makedirs('logs', exist_ok=True)
            os.makedirs('data/voice_profiles', exist_ok=True)
            
            # Initialize assistant
            self.assistant = GhostAssistant(self.config)
            
            # Initialize GUI
            self.window = GhostWindow(self.assistant)
            self.tray_icon = TrayIcon(self.assistant, self.window)
            
            # Connect signals
            self.assistant.wake_word_detected.connect(self.on_wake_word_detected)
            self.assistant.response_ready.connect(self.on_response_ready)
            
            self.is_running = True
            logger.info("GHOST Assistant initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize GHOST: {e}")
            return False
            
        return True
    
    def on_wake_word_detected(self):
        """Handle wake word detection"""
        logger.info("Wake word detected - showing assistant")
        self.window.show_assistant()
        
    def on_response_ready(self, response):
        """Handle assistant response"""
        self.window.display_response(response)
        
    def run(self):
        """Run the application"""
        if not self.initialize():
            return 1
            
        logger.info("Starting GHOST Assistant...")
        
        # Start assistant in background thread
        assistant_thread = threading.Thread(target=self.assistant.start, daemon=True)
        assistant_thread.start()
        
        # Show tray icon
        self.tray_icon.show()
        
        # Run Qt application
        return self.app.exec()
    
    def shutdown(self):
        """Shutdown the application"""
        logger.info("Shutting down GHOST Assistant...")
        self.is_running = False
        
        if self.assistant:
            self.assistant.stop()
            
        self.app.quit()

def main():
    """Main entry point"""
    # Startup prompt — foydalanuvchi ON ni bossa davom etadi
    if not StartupPrompt.ask():
        return 0

    app = GhostApp()
    
    try:
        return app.run()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        app.shutdown()
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        app.shutdown()
        return 1

if __name__ == "__main__":
    sys.exit(main())

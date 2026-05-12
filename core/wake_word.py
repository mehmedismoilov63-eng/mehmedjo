"""
Wake Word Detection Module
Uses pvporcupine for efficient wake word detection
"""

import threading
import struct
import logging
import time
from PyQt6.QtCore import QObject, pyqtSignal
from typing import Optional

try:
    import pvporcupine
except ImportError:
    pvporcupine = None
    logging.warning("pvporcupine not installed. Wake word detection will not work.")

import pyaudio

from config import Config

logger = logging.getLogger(__name__)

class WakeWordDetector(QObject):
    """Wake word detection using pvporcupine"""
    
    # Signals
    wake_word_detected = pyqtSignal()
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.is_running = False
        self.thread = None
        self.porcupine = None
        self.audio_stream = None
        self.pa = None
        
    def initialize(self):
        """Initialize wake word detector"""
        try:
            if pvporcupine is None:
                raise ImportError("pvporcupine not installed")
                
            if not self.config.wake_word.access_key:
                raise ValueError("PicoVoice access key not configured")
                
            # Initialize porcupine
            self.porcupine = pvporcupine.create(
                access_key=self.config.wake_word.access_key,
                keywords=[self.config.wake_word.keyword],
                sensitivities=[self.config.wake_word.sensitivity]
            )
            
            # Initialize PyAudio
            self.pa = pyaudio.PyAudio()
            
            # Create audio stream
            self.audio_stream = self.pa.open(
                rate=self.porcupine.sample_rate,
                channels=self.porcupine.channels,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.porcupine.frame_length
            )
            
            logger.info("Wake word detector initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize wake word detector: {e}")
            return False
            
    def start(self):
        """Start wake word detection"""
        if self.is_running:
            return
            
        if not self.initialize():
            logger.error("Cannot start wake word detection - initialization failed")
            return
            
        self.is_running = True
        self.thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.thread.start()
        
        logger.info("Wake word detection started")
        
    def stop(self):
        """Stop wake word detection"""
        if not self.is_running:
            return
            
        self.is_running = False
        
        if self.audio_stream:
            self.audio_stream.close()
            
        if self.porcupine:
            self.porcupine.delete()
            
        if self.pa:
            self.pa.terminate()
            
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
            
        logger.info("Wake word detection stopped")
        
    def _detection_loop(self):
        """Main detection loop"""
        logger.info("Wake word detection loop started")
        
        try:
            while self.is_running:
                # Read audio frame
                pcm = self.audio_stream.read(self.porcupine.frame_length, exception_on_overflow=False)
                
                # Convert to required format
                pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm)
                
                # Process frame
                result = self.porcupine.process(pcm)
                
                if result >= 0:
                    logger.info("Wake word detected!")
                    self.wake_word_detected.emit()
                    
                    # Small delay to prevent multiple detections
                    time.sleep(2.0)
                    
        except Exception as e:
            logger.error(f"Error in detection loop: {e}")
            
        logger.info("Wake word detection loop ended")
        
    def is_available(self) -> bool:
        """Check if wake word detection is available"""
        return pvporcupine is not None and self.config.wake_word.access_key is not None

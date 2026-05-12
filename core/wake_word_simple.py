"""
Wake Word Detection Module - Simple Version (without PyQt6)
Handles wake word detection using pvporcupine
"""

import logging
import threading
import time
import numpy as np
from typing import Callable, Optional

try:
    import pvporcupine
except ImportError:
    pvporcupine = None
    logging.warning("pvporcupine not installed. Wake word detection disabled.")

try:
    import pyaudio
except ImportError:
    pyaudio = None
    logging.warning("pyaudio not installed. Audio input disabled.")

from config import Config

logger = logging.getLogger(__name__)

class WakeWordDetector:
    """Wake word detector using pvporcupine"""
    
    def __init__(self, config: Config):
        self.config = config
        self.is_detecting = False
        self.thread = None
        self.audio_stream = None
        
        # Callback function
        self.wake_word_callback = None
        
        # Initialize porcupine
        self.porcupine = None
        self.initialize_porcupine()
        
        # Audio settings
        self.sample_rate = 16000
        self.frame_length = 512
        
    def initialize_porcupine(self):
        """Initialize pvporcupine"""
        try:
            if pvporcupine is None:
                logger.error("pvporcupine not available")
                return
                
            # Get access key from environment
            access_key = self.config.wake_word.access_key
            
            if not access_key:
                logger.warning("No PicoVoice access key found")
                return
                
            # Initialize porcupine
            self.porcupine = pvporcupine.create(
                access_key=access_key,
                keywords=[self.config.wake_word.keyword],
                sensitivities=[self.config.wake_word.sensitivity]
            )
            
            logger.info(f"Porcupine initialized with keyword: {self.config.wake_word.keyword}")
            
        except Exception as e:
            logger.error(f"Failed to initialize porcupine: {e}")
            
    def set_callback(self, callback: Callable):
        """Set callback function for wake word detection"""
        self.wake_word_callback = callback
        
    def connect(self, signal_name, callback):
        """Connect signal (for compatibility)"""
        if signal_name == 'wake_word_detected':
            self.set_callback(callback)
        
    def start(self):
        """Start wake word detection"""
        if self.is_detecting:
            return
            
        if not self.porcupine:
            logger.error("Porcupine not initialized")
            return False
            
        if pyaudio is None:
            logger.error("PyAudio not available")
            return False
            
        self.is_detecting = True
        self.thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.thread.start()
        
        logger.info("Wake word detection started")
        return True
        
    def stop(self):
        """Stop wake word detection"""
        if not self.is_detecting:
            return
            
        self.is_detecting = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
            
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
            
        logger.info("Wake word detection stopped")
        
    def _detection_loop(self):
        """Main detection loop"""
        logger.info("Wake word detection loop started")
        
        try:
            # Initialize audio stream
            pa = pyaudio.PyAudio()
            
            self.audio_stream = pa.open(
                rate=self.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.frame_length,
                input_device_index=self.config.audio.input_device
            )
            
            while self.is_detecting:
                # Read audio frame
                audio_frame = self.audio_stream.read(self.frame_length, exception_on_overflow=False)
                audio_frame = np.frombuffer(audio_frame, dtype=np.int16)
                
                # Process with porcupine
                if self.porcupine:
                    result = self.porcupine.process(audio_frame)
                    
                    if result >= 0:
                        logger.info(f"Wake word detected: {self.config.wake_word.keyword}")
                        
                        # Call callback if set
                        if self.wake_word_callback:
                            self.wake_word_callback()
                            
                        # Small delay to prevent multiple detections
                        time.sleep(2.0)
                        
        except Exception as e:
            logger.error(f"Error in detection loop: {e}")
        finally:
            if self.audio_stream:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
                pa.terminate()
                
            logger.info("Wake word detection loop ended")
            
    def is_available(self) -> bool:
        """Check if wake word detection is available"""
        return (self.porcupine is not None and 
                pyaudio is not None and
                self.config.wake_word.access_key is not None)
                
    def get_keyword_list(self) -> list:
        """Get list of available keywords"""
        if self.porcupine:
            return [self.config.wake_word.keyword]
        return []
        
    def test_microphone(self) -> bool:
        """Test microphone access"""
        try:
            if pyaudio is None:
                return False
                
            pa = pyaudio.PyAudio()
            
            # Try to open default input device
            stream = pa.open(
                rate=self.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.frame_length
            )
            
            # Read one frame
            frame = stream.read(self.frame_length)
            
            # Clean up
            stream.stop_stream()
            stream.close()
            pa.terminate()
            
            logger.info("Microphone test successful")
            return True
            
        except Exception as e:
            logger.error(f"Microphone test failed: {e}")
            return False

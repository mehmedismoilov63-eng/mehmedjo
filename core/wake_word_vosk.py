"""
Wake Word Detection Module - VOSK Based
Alternative wake word detection using VOSK
"""

import logging
import threading
import time
import numpy as np
import os
from typing import Callable, Optional

try:
    import vosk
except ImportError:
    vosk = None
    logging.warning("vosk not installed. Wake word detection disabled.")

try:
    import pyaudio
except ImportError:
    pyaudio = None
    logging.warning("pyaudio not installed. Audio input disabled.")

from config import Config

logger = logging.getLogger(__name__)

class WakeWordDetectorVOSK:
    """Wake word detector using VOSK"""
    
    def __init__(self, config: Config):
        self.config = config
        self.is_detecting = False
        self.thread = None
        self.audio_stream = None
        
        # Callback function
        self.wake_word_callback = None
        
        # Initialize VOSK model
        self.model = None
        self.initialize_model()
        
        # Audio settings
        self.sample_rate = 16000
        self.frame_length = 1024
        
        # Wake words to detect
        self.wake_words = ["hey ghost", "ghost", "assistant", "yordamchi"]
        
    def initialize_model(self):
        """Initialize VOSK model"""
        try:
            if vosk is None:
                logger.error("VOSK not available")
                return
                
            # Try to find wake word model
            model_path = f"models/vosk/wake_word_{self.config.stt.language}"
            
            if not os.path.exists(model_path):
                logger.warning(f"Wake word model not found at {model_path}")
                logger.info("Using generic VOSK model for wake word detection")
                # Use generic model
                model_path = f"models/vosk/{self.config.stt.language}"
                
            if os.path.exists(model_path):
                self.model = vosk.Model(model_path)
                logger.info(f"VOSK model loaded from: {model_path}")
            else:
                logger.warning("No VOSK model found")
                
        except Exception as e:
            logger.error(f"Failed to initialize VOSK model: {e}")
            
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
            
        if pyaudio is None:
            logger.error("PyAudio not available")
            return False
            
        self.is_detecting = True
        self.thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.thread.start()
        
        logger.info("Wake word detection started (VOSK)")
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
        logger.info("Wake word detection loop started (VOSK)")
        
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
            
            if self.model:
                recognizer = vosk.KaldiRecognizer(self.model, self.sample_rate)
            else:
                logger.error("No VOSK model available")
                return
                
            while self.is_detecting:
                # Read audio frame
                audio_frame = self.audio_stream.read(self.frame_length, exception_on_overflow=False)
                audio_frame = np.frombuffer(audio_frame, dtype=np.int16)
                
                # Process with VOSK
                if recognizer.AcceptWaveform(audio_frame.tobytes()):
                    result = recognizer.Result()
                    text = eval(result)["text"].lower()
                    
                    # Check if wake word detected
                    if self._is_wake_word(text):
                        logger.info(f"Wake word detected: {text}")
                        
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
            
    def _is_wake_word(self, text: str) -> bool:
        """Check if text contains wake word"""
        text = text.lower().strip()
        
        for wake_word in self.wake_words:
            if wake_word in text:
                return True
                
        return False
        
    def is_available(self) -> bool:
        """Check if wake word detection is available"""
        return (vosk is not None and 
                pyaudio is not None and
                self.model is not None)
                
    def get_keyword_list(self) -> list:
        """Get list of available keywords"""
        return self.wake_words
        
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

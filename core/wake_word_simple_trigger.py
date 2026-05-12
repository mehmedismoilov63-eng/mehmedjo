"""
Wake Word Detection Module - Simple Trigger
Simple wake word detection without external services
"""

import logging
import threading
import time
import numpy as np
from typing import Callable

try:
    import pyaudio
except ImportError:
    pyaudio = None
    logging.warning("pyaudio not installed. Audio input disabled.")

from config import Config

logger = logging.getLogger(__name__)

class WakeWordDetectorSimple:
    """Simple wake word detector using energy threshold"""
    
    def __init__(self, config: Config):
        self.config = config
        self.is_detecting = False
        self.thread = None
        self.audio_stream = None
        
        # Callback function
        self.wake_word_callback = None
        
        # Audio settings
        self.sample_rate = 16000
        self.frame_length = 512
        
        # Energy threshold for wake word detection
        self.energy_threshold = 0.01
        self.min_silence_duration = 0.5
        
        # Wake words to detect (simplified)
        self.wake_words = ["hey", "ghost", "assistant", "yordamchi"]
        
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
        
        logger.info("Wake word detection started (Simple)")
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
        logger.info("Wake word detection loop started (Simple)")
        
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
            
            silence_start = None
            
            while self.is_detecting:
                # Read audio frame
                audio_frame = self.audio_stream.read(self.frame_length, exception_on_overflow=False)
                audio_frame = np.frombuffer(audio_frame, dtype=np.int16)
                
                # Calculate energy
                energy = np.mean(np.abs(audio_frame)) / 32768.0
                
                # Check for speech
                if energy > self.energy_threshold:
                    if silence_start is None:
                        silence_start = time.time()
                        logger.debug(f"Speech detected (energy: {energy:.4f})")
                else:
                    # Speech continues
                    silence_start = time.time()
                    
                # Check for end of speech
                elif silence_start is not None:
                    silence_duration = time.time() - silence_start
                    
                    if silence_duration > self.min_silence_duration:
                        logger.info(f"Potential wake word detected (duration: {silence_duration:.2f}s)")
                        
                        # Simulate wake word detection
                        if self.wake_word_callback:
                            self.wake_word_callback()
                            
                        # Reset
                        silence_start = None
                        
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
        return pyaudio is not None
                
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

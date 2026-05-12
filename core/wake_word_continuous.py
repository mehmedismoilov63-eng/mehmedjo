"""
Continuous Wake Word Detection
Always listening for 'ghost' wake word
"""

import os
import sys
import logging
import time
import threading
import queue
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

try:
    import speech_recognition as sr
except ImportError:
    sr = None
    logging.error("speech_recognition not available")

try:
    import pyaudio
except ImportError:
    pyaudio = None
    logging.error("pyaudio not available")

from config import Config

logger = logging.getLogger(__name__)

class ContinuousWakeWordDetector:
    """Continuous wake word detector"""
    
    def __init__(self, config: Config):
        self.config = config
        self.is_listening = False
        self.thread = None
        self.audio_stream = None
        
        # Callback function
        self.wake_word_callback = None
        
        # Wake word settings
        self.wake_word = "ghost"
        self.wake_word_variations = ["ghost", "gost", "goust", "goost"]
        
        # Audio settings
        self.sample_rate = 16000
        self.frame_length = 1024
        self.silence_threshold = 500
        self.silence_duration = 1.0
        
        # Speech recognition
        self.recognizer = sr.Recognizer() if sr else None
        self.microphone = None
        
        # Command queue
        self.command_queue = queue.Queue()
        
    def set_callback(self, callback):
        """Set callback function for wake word detection"""
        self.wake_word_callback = callback
        
    def start(self):
        """Start continuous wake word detection"""
        if self.is_listening:
            return
            
        if not sr or not pyaudio:
            logger.error("Required audio libraries not available")
            return False
            
        self.is_listening = True
        self.thread = threading.Thread(target=self._continuous_listen, daemon=True)
        self.thread.start()
        
        logger.info("Continuous wake word detection started")
        return True
        
    def stop(self):
        """Stop continuous wake word detection"""
        if not self.is_listening:
            return
            
        self.is_listening = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
            
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
            
        logger.info("Continuous wake word detection stopped")
        
    def _continuous_listen(self):
        """Continuous listening loop"""
        logger.info("Starting continuous listening...")
        
        try:
            # Initialize microphone
            self.microphone = sr.Microphone()
            
            with self.microphone as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                logger.info("Ambient noise adjusted")
                
            while self.is_listening:
                try:
                    # Listen for audio
                    with self.microphone as source:
                        audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=5)
                    
                    # Try to recognize speech
                    try:
                        # Try Google Speech Recognition first
                        text = self.recognizer.recognize_google(audio, language="en-US").lower()
                        logger.info(f"Recognized: {text}")
                        
                        # Check for wake word
                        if self._is_wake_word(text):
                            logger.info(f"Wake word detected: {text}")
                            
                            # Call callback
                            if self.wake_word_callback:
                                self.wake_word_callback(text)
                                
                            # Small delay to prevent multiple detections
                            time.sleep(2.0)
                            
                    except sr.UnknownValueError:
                        # Could not understand audio
                        pass
                    except sr.RequestError as e:
                        # Google API error
                        logger.error(f"Google API error: {e}")
                        time.sleep(1.0)
                        
                except sr.WaitTimeoutError:
                    # Timeout, continue listening
                    continue
                except Exception as e:
                    logger.error(f"Error in listening loop: {e}")
                    time.sleep(1.0)
                    
        except Exception as e:
            logger.error(f"Error in continuous listening: {e}")
        finally:
            if self.audio_stream:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
                
        logger.info("Continuous listening ended")
        
    def _is_wake_word(self, text):
        """Check if text contains wake word"""
        text = text.lower().strip()
        
        # Direct match
        if self.wake_word in text:
            return True
            
        # Check variations
        for variation in self.wake_word_variations:
            if variation in text:
                return True
                
        # Fuzzy matching
        words = text.split()
        for word in words:
            if self._fuzzy_match(word, self.wake_word, 0.7):
                return True
                
        return False
        
    def _fuzzy_match(self, word1, word2, threshold=0.7):
        """Simple fuzzy matching"""
        if not word1 or not word2:
            return False
            
        # Simple Levenshtein distance approximation
        longer = max(len(word1), len(word2))
        if longer == 0:
            return True
            
        # Count different characters
        differences = sum(c1 != c2 for c1, c2 in zip(word1, word2))
        differences += abs(len(word1) - len(word2))
        
        similarity = 1 - (differences / longer)
        return similarity >= threshold
        
    def is_available(self) -> bool:
        """Check if wake word detection is available"""
        return sr is not None and pyaudio is not None
        
    def test_microphone(self) -> bool:
        """Test microphone access"""
        try:
            if not sr:
                return False
                
            microphone = sr.Microphone()
            with microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                
            logger.info("Microphone test successful")
            return True
            
        except Exception as e:
            logger.error(f"Microphone test failed: {e}")
            return False

"""
Voice Speaker Module - Simple Version (without PyQt6)
Handles text-to-speech conversion using edge-tts and pyttsx3
"""

import threading
import logging
import asyncio
import tempfile
import os
from typing import Optional

try:
    import edge_tts
except ImportError:
    edge_tts = None
    logging.warning("edge-tts not installed. Using fallback TTS.")

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None
    logging.warning("pyttsx3 not installed. No TTS available.")

import pygame
from config import Config

logger = logging.getLogger(__name__)

class VoiceSpeaker:
    """Text-to-speech converter and player"""
    
    def __init__(self, config: Config):
        self.config = config
        self.is_speaking = False
        self.thread = None
        
        # Initialize pygame mixer
        pygame.mixer.init()
        
        # Initialize TTS engines
        self.edge_tts_available = edge_tts is not None
        self.pyttsx3_engine = None
        
        if pyttsx3:
            try:
                self.pyttsx3_engine = pyttsx3.init()
                # Configure voice
                voices = self.pyttsx3_engine.getProperty('voices')
                if voices:
                    self.pyttsx3_engine.setProperty('voice', voices[0].id)
                self.pyttsx3_engine.setProperty('rate', 150)
                self.pyttsx3_engine.setProperty('volume', self.config.tts.volume)
            except Exception as e:
                logger.error(f"Failed to initialize pyttsx3: {e}")
                self.pyttsx3_engine = None
                
    def speak(self, text: str):
        """Speak text using available TTS engine"""
        if not text or not text.strip():
            return
            
        if self.is_speaking:
            logger.warning("Already speaking, skipping new request")
            return
            
        self.is_speaking = True
        
        self.thread = threading.Thread(target=self._speak_thread, args=(text,), daemon=True)
        self.thread.start()
        
    def _speak_thread(self, text: str):
        """Thread function for speaking"""
        try:
            # Try edge-tts first
            if self.edge_tts_available and self.config.tts.engine == "edge_tts":
                success = self._speak_with_edge_tts(text)
                if success:
                    return
                    
            # Fallback to pyttsx3
            if self.pyttsx3_engine:
                self._speak_with_pyttsx3(text)
            else:
                logger.error("No TTS engine available")
                
        except Exception as e:
            logger.error(f"Error speaking text: {e}")
        finally:
            self.is_speaking = False
            
    def _speak_with_edge_tts(self, text: str) -> bool:
        """Speak using edge-tts"""
        try:
            # Create async event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run async function
            result = loop.run_until_complete(self._async_speak_edge_tts(text))
            loop.close()
            
            return result
            
        except Exception as e:
            logger.error(f"Error with edge-tts: {e}")
            return False
            
    async def _async_speak_edge_tts(self, text: str) -> bool:
        """Async function for edge-tts"""
        try:
            # Create TTS communicator
            communicate = edge_tts.Communicate(
                text, 
                voice=self.config.tts.voice,
                rate=f"{int((self.config.tts.rate - 1.0) * 100):+d}%"
            )
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_file_path = temp_file.name
                
            await communicate.save(temp_file_path)
                
            # Play audio
            self._play_audio_file(temp_file_path)
            
            # Clean up
            os.unlink(temp_file_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in async edge-tts: {e}")
            return False
            
    def _speak_with_pyttsx3(self, text: str):
        """Speak using pyttsx3"""
        try:
            # Update engine properties
            self.pyttsx3_engine.setProperty('rate', int(150 * self.config.tts.rate))
            self.pyttsx3_engine.setProperty('volume', self.config.tts.volume)
            
            # Speak
            self.pyttsx3_engine.say(text)
            self.pyttsx3_engine.runAndWait()
            
        except Exception as e:
            logger.error(f"Error with pyttsx3: {e}")
            
    def _play_audio_file(self, file_path: str):
        """Play audio file using pygame"""
        try:
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.music.unload()
        except Exception as e:
            logger.error(f"Error playing audio file: {e}")
            
    def play_wake_sound(self):
        """Play wake sound effect"""
        try:
            # Generate a simple wake sound
            self._generate_wake_sound()
        except Exception as e:
            logger.error(f"Error playing wake sound: {e}")
            
    def _generate_wake_sound(self):
        """Generate and play wake sound"""
        try:
            import numpy as np
            
            # Generate a pleasant wake sound
            sample_rate = 22050
            duration = 0.3
            frequency = 800
            
            # Generate sine wave
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            wave = np.sin(frequency * t * 2 * np.pi)
            
            # Apply envelope
            envelope = np.exp(-t * 5)  # Exponential decay
            wave = wave * envelope
            
            # Convert to 16-bit integers
            wave = (wave * 32767).astype(np.int16)
            
            # Create stereo
            stereo_wave = np.array([wave, wave]).T
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                import wave
                with wave.open(temp_file.name, 'wb') as wav_file:
                    wav_file.setnchannels(2)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(stereo_wave.tobytes())
                    
                temp_file_path = temp_file.name
                
            # Play sound
            self._play_audio_file(temp_file_path)
            
            # Clean up
            os.unlink(temp_file_path)
            
        except Exception as e:
            logger.error(f"Error generating wake sound: {e}")
            
    def stop(self):
        """Stop current speech"""
        if self.is_speaking:
            self.is_speaking = False
            
            # Stop pygame mixer
            pygame.mixer.music.stop()
            
            # Stop pyttsx3
            if self.pyttsx3_engine:
                self.pyttsx3_engine.stop()
                
            # Wait for thread to finish
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=1.0)
                
    def set_volume(self, volume: float):
        """Set TTS volume (0.0 to 1.0)"""
        self.config.tts.volume = max(0.0, min(1.0, volume))
        
        if self.pyttsx3_engine:
            self.pyttsx3_engine.setProperty('volume', self.config.tts.volume)
            
    def set_rate(self, rate: float):
        """Set TTS speech rate (0.5 to 2.0)"""
        self.config.tts.rate = max(0.5, min(2.0, rate))
        
    def set_voice(self, voice: str):
        """Set TTS voice"""
        self.config.tts.voice = voice
        
    def is_available(self) -> bool:
        """Check if TTS is available"""
        return self.edge_tts_available or self.pyttsx3_engine is not None

"""
Voice Speaker Module - Fixed Version
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
                    # Try to find a good voice
                    for voice in voices:
                        if 'english' in voice.id.lower() or 'en' in voice.id.lower():
                            self.pyttsx3_engine.setProperty('voice', voice.id)
                            break
                    else:
                        self.pyttsx3_engine.setProperty('voice', voices[0].id)
                        
                # Set default properties
                self.pyttsx3_engine.setProperty('rate', 150)
                self.pyttsx3_engine.setProperty('volume', 0.9)
                
                logger.info("pyttsx3 engine initialized")
            except Exception as e:
                logger.error(f"Error initializing pyttsx3: {e}")
                self.pyttsx3_engine = None
                
    def speak(self, text: str) -> bool:
        """Speak text using available TTS engine"""
        if self.is_speaking:
            logger.warning("Already speaking, skipping new request")
            return False
            
        self.is_speaking = True
        
        try:
            # Try edge-tts first
            if self.edge_tts_available:
                return self._speak_with_edge_tts(text)
            elif self.pyttsx3_engine:
                return self._speak_with_pyttsx3(text)
            else:
                logger.error("No TTS engine available")
                return False
                
        except Exception as e:
            logger.error(f"Error speaking: {e}")
            return False
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
            # Create TTS communicator with FIXED rate format
            communicate = edge_tts.Communicate(
                text, 
                voice=self.config.tts.voice,
                rate=f"{self.config.tts.rate:.1f}",  # FIXED: No + sign
            )
            
            # Generate audio
            audio_data = await communicate.stream()
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                async for chunk in audio_data:
                    if chunk["type"] == "audio":
                        temp_file.write(chunk["data"])
                        
                temp_file_path = temp_file.name
                
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
            
            return True
            
        except Exception as e:
            logger.error(f"Error with pyttsx3: {e}")
            return False
            
    def _play_audio_file(self, file_path: str):
        """Play audio file using pygame"""
        try:
            # Load and play audio
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            
            # Wait for playback to finish
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
                
        except Exception as e:
            logger.error(f"Error playing audio file: {e}")
            
    def stop(self):
        """Stop current speech"""
        try:
            if self.pyttsx3_engine:
                self.pyttsx3_engine.stop()
            pygame.mixer.music.stop()
            self.is_speaking = False
        except Exception as e:
            logger.error(f"Error stopping speech: {e}")
            
    def is_available(self) -> bool:
        """Check if TTS is available"""
        return self.edge_tts_available or self.pyttsx3_engine is not None
        
    def get_available_voices(self):
        """Get list of available voices"""
        voices = []
        
        if self.pyttsx3_engine:
            try:
                pyttsx3_voices = self.pyttsx3_engine.getProperty('voices')
                for voice in pyttsx3_voices:
                    voices.append({
                        'id': voice.id,
                        'name': voice.name,
                        'languages': voice.languages,
                        'gender': voice.gender,
                        'engine': 'pyttsx3'
                    })
            except Exception as e:
                logger.error(f"Error getting pyttsx3 voices: {e}")
                
        if self.edge_tts_available:
            try:
                edge_voices = edge_tts.list_voices()
                for voice in edge_voices:
                    voices.append({
                        'id': voice['ShortName'],
                        'name': voice['FriendlyName'],
                        'languages': [voice['Locale']],
                        'gender': voice['Gender'],
                        'engine': 'edge-tts'
                    })
            except Exception as e:
                logger.error(f"Error getting edge-tts voices: {e}")
                
        return voices
        
    def set_voice(self, voice_id: str):
        """Set voice by ID"""
        try:
            if self.pyttsx3_engine:
                voices = self.pyttsx3_engine.getProperty('voices')
                for voice in voices:
                    if voice.id == voice_id:
                        self.pyttsx3_engine.setProperty('voice', voice.id)
                        return True
                        
            # For edge-tts, set in config
            self.config.tts.voice = voice_id
            return True
            
        except Exception as e:
            logger.error(f"Error setting voice: {e}")
            return False
            
    def set_rate(self, rate: float):
        """Set speech rate"""
        try:
            self.config.tts.rate = rate
            
            if self.pyttsx3_engine:
                self.pyttsx3_engine.setProperty('rate', int(150 * rate))
                
            return True
            
        except Exception as e:
            logger.error(f"Error setting rate: {e}")
            return False
            
    def set_volume(self, volume: float):
        """Set speech volume"""
        try:
            self.config.tts.volume = volume
            
            if self.pyttsx3_engine:
                self.pyttsx3_engine.setProperty('volume', volume)
                
            return True
            
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            return False
            
    def play_wake_sound(self):
        """Play wake sound"""
        try:
            # Generate a simple wake sound
            duration = 0.2  # seconds
            sample_rate = 22050
            samples = int(duration * sample_rate)
            
            # Create a simple tone
            import numpy as np
            frequency = 800  # Hz
            t = np.linspace(0, duration, samples)
            wave = 0.3 * np.sin(2 * np.pi * frequency * t)
            
            # Convert to 16-bit integers
            wave = (wave * 32767).astype(np.int16)
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                import wave
                with wave.open(temp_file.name, 'w') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(wave.tobytes())
                    
                # Play the sound
                self._play_audio_file(temp_file.name)
                os.unlink(temp_file.name)
                
        except Exception as e:
            logger.error(f"Error playing wake sound: {e}")
            # Fallback: try to play a simple beep
            try:
                pygame.mixer.Sound.play(pygame.mixer.Sound(buffer=b'\x00'))
            except:
                pass

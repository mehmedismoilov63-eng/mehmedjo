"""
Voice Listener Module - Simple Version (without PyQt6)
Handles speech-to-text conversion using faster-whisper and vosk
"""

import threading
import logging
import queue
import numpy as np
from typing import Optional, Dict, Any

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None
    logging.warning("faster-whisper not installed. Using fallback.")

try:
    import vosk
except ImportError:
    vosk = None
    logging.warning("vosk not installed. No fallback STT available.")

import speech_recognition as sr
import pyaudio

from config import Config

logger = logging.getLogger(__name__)

class VoiceListener:
    """Voice listener for speech-to-text conversion"""
    
    def __init__(self, config: Config):
        self.config = config
        self.is_listening = False
        self.thread = None
        self.recognizer = sr.Recognizer()
        self.microphone = None
        
        # STT models
        self.whisper_model = None
        self.vosk_model = None
        
        # Callback function
        self.speech_callback = None
        
        # Voice profiler reference
        self.voice_profiler = None
        
        # Initialize models
        self._initialize_models()
        
    def set_callback(self, callback):
        """Set callback function for speech detection"""
        self.speech_callback = callback
        
    def _initialize_models(self):
        """Initialize STT models"""
        try:
            # Initialize faster-whisper model
            if WhisperModel and self.config.stt.engine == "faster_whisper":
                logger.info(f"Loading faster-whisper model: {self.config.stt.model_size}")
                self.whisper_model = WhisperModel(
                    self.config.stt.model_size,
                    device="cpu",
                    compute_type="int8"
                )
                logger.info("faster-whisper model loaded successfully")
                
        except Exception as e:
            logger.error(f"Failed to load faster-whisper model: {e}")
            self.whisper_model = None
            
        try:
            # Initialize vosk model
            if vosk and self.config.stt.engine == "vosk":
                model_path = f"models/vosk/{self.config.stt.language}"
                logger.info(f"Loading vosk model from: {model_path}")
                self.vosk_model = vosk.Model(model_path)
                logger.info("vosk model loaded successfully")
                
        except Exception as e:
            logger.error(f"Failed to load vosk model: {e}")
            self.vosk_model = None
            
    def set_voice_profiler(self, voice_profiler):
        """Set voice profiler reference"""
        self.voice_profiler = voice_profiler
        
    def start_listening(self):
        """Start listening for speech"""
        if self.is_listening:
            return
            
        self.is_listening = True
        
        self.thread = threading.Thread(target=self._listening_loop, daemon=True)
        self.thread.start()
        
        logger.info("Started listening for speech")
        
    def stop_listening(self):
        """Stop listening for speech"""
        if not self.is_listening:
            return
            
        self.is_listening = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
            
        logger.info("Stopped listening for speech")
        
    def _listening_loop(self):
        """Main listening loop"""
        logger.info("Voice listening loop started")
        
        try:
            with sr.Microphone() as source:
                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                while self.is_listening:
                    try:
                        # Listen for audio with timeout
                        audio = self.recognizer.listen(
                            source,
                            timeout=self.config.stt.timeout,
                            phrase_time_limit=10
                        )
                        
                        # Convert audio to numpy array for voice profiling
                        audio_data = np.frombuffer(audio.get_raw_data(), dtype=np.int16)
                        
                        # Get voice profile if available
                        user_profile = None
                        if self.voice_profiler:
                            user_profile = self.voice_profiler.identify_user(audio_data)
                            
                        # Convert speech to text
                        text = self._convert_speech_to_text(audio)
                        
                        if text and text.strip():
                            logger.info(f"Detected speech: {text}")
                            
                            # Call callback if set
                            if self.speech_callback:
                                self.speech_callback(text, user_profile or {})
                            
                            break  # Exit after successful detection
                            
                    except sr.WaitTimeoutError:
                        # Timeout is normal, continue listening
                        continue
                    except sr.UnknownValueError:
                        logger.warning("Could not understand audio")
                        continue
                    except Exception as e:
                        logger.error(f"Error in listening loop: {e}")
                        break
                        
        except Exception as e:
            logger.error(f"Error in voice listening: {e}")
            
        logger.info("Voice listening loop ended")
        
    def _convert_speech_to_text(self, audio: sr.AudioData) -> Optional[str]:
        """Convert speech audio to text using available STT engines"""
        
        # Try faster-whisper first
        if self.whisper_model:
            text = self._convert_with_whisper(audio)
            if text:
                return text
                
        # Fallback to vosk
        if self.vosk_model:
            text = self._convert_with_vosk(audio)
            if text:
                return text
                
        # Fallback to Google Speech Recognition (requires internet)
        try:
            text = self.recognizer.recognize_google(
                audio, 
                language=self._get_google_language_code()
            )
            logger.info(f"Google STT result: {text}")
            return text
        except Exception as e:
            logger.error(f"Google STT failed: {e}")
            
        return None
        
    def _convert_with_whisper(self, audio: sr.AudioData) -> Optional[str]:
        """Convert speech using faster-whisper"""
        try:
            import numpy as np

            raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
            audio_np = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

            segments, info = self.whisper_model.transcribe(
                audio_np,
                language=self._get_whisper_language_code()
            )

            text = " ".join([segment.text for segment in segments]).strip()
            logger.info(f"Whisper STT result: {text}")
            return text if text else None

        except Exception as e:
            logger.error(f"Whisper STT failed: {e}")
            return None
            
    def _convert_with_vosk(self, audio: sr.AudioData) -> Optional[str]:
        """Convert speech using vosk"""
        try:
            # Convert audio to required format
            audio_data = np.frombuffer(audio.get_raw_data(), dtype=np.int16)
            
            # Create recognizer
            rec = vosk.KaldiRecognizer(self.vosk_model, self.config.audio.sample_rate)
            
            # Process audio
            if rec.AcceptWaveform(audio_data.tobytes()):
                result = rec.Result()
                text = eval(result)["text"]
                logger.info(f"Vosk STT result: {text}")
                return text
            else:
                # Partial result
                partial = rec.PartialResult()
                if partial:
                    text = eval(partial)["partial"]
                    if text.strip():
                        logger.info(f"Vosk partial result: {text}")
                        return text
                        
        except Exception as e:
            logger.error(f"Vosk STT failed: {e}")
            
        return None
        
    def _get_whisper_language_code(self) -> str:
        """Get language code for whisper"""
        lang_map = {
            "uz": "uz",
            "ru": "ru", 
            "en": "en"
        }
        return lang_map.get(self.config.stt.language, "uz")
        
    def _get_google_language_code(self) -> str:
        """Get language code for Google STT"""
        lang_map = {
            "uz": "uz-UZ",
            "ru": "ru-RU",
            "en": "en-US"
        }
        return lang_map.get(self.config.stt.language, "uz-UZ")
        
    def is_available(self) -> bool:
        """Check if STT is available"""
        return (self.whisper_model is not None or 
                self.vosk_model is not None or
                True)  # Google STT is always available as fallback

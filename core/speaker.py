"""
Voice Speaker - edge-tts (asosiy) + pyttsx3 (fallback)
"""

import threading
import logging
import asyncio
import tempfile
import os
import time
from PyQt6.QtCore import QObject, pyqtSignal

try:
    import edge_tts
    EDGE_TTS_OK = True
except ImportError:
    EDGE_TTS_OK = False

try:
    import pyttsx3
    PYTTSX3_OK = True
except ImportError:
    PYTTSX3_OK = False

try:
    import pygame
    pygame.mixer.init()
    PYGAME_OK = True
except Exception:
    PYGAME_OK = False

from config import Config

logger = logging.getLogger(__name__)


class VoiceSpeaker(QObject):
    speech_started  = pyqtSignal()
    speech_finished = pyqtSignal()

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self._lock = threading.Lock()
        self._speaking = False

        # pyttsx3 fallback
        self._pyttsx3 = None
        if PYTTSX3_OK:
            try:
                self._pyttsx3 = pyttsx3.init()
                self._pyttsx3.setProperty("rate", 160)
                self._pyttsx3.setProperty("volume", 0.9)
            except Exception as e:
                logger.warning(f"pyttsx3 init failed: {e}")
                self._pyttsx3 = None

    # ── Public ──────────────────────────────────────────────────────

    def speak(self, text: str):
        if not text or not text.strip():
            return
        t = threading.Thread(target=self._speak_worker, args=(text,), daemon=True)
        t.start()

    def play_wake_sound(self):
        t = threading.Thread(target=self._play_beep, daemon=True)
        t.start()

    def stop(self):
        self._speaking = False
        if PYGAME_OK:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    def is_available(self) -> bool:
        return EDGE_TTS_OK or self._pyttsx3 is not None

    # ── Workers ─────────────────────────────────────────────────────

    def _speak_worker(self, text: str):
        with self._lock:
            self._speaking = True
            self.speech_started.emit()
            try:
                if EDGE_TTS_OK:
                    ok = self._speak_edge(text)
                    if ok:
                        return
                # Fallback
                if self._pyttsx3:
                    self._speak_pyttsx3(text)
            except Exception as e:
                logger.error(f"speak error: {e}")
            finally:
                self._speaking = False
                self.speech_finished.emit()

    def _speak_edge(self, text: str) -> bool:
        """edge-tts bilan gapirish"""
        tmp = None
        try:
            # Rate: 1.0 → "+0%", 1.2 → "+20%"
            rate_pct = int((self.config.tts.rate - 1.0) * 100)
            rate_str = f"{rate_pct:+d}%"

            communicate = edge_tts.Communicate(
                text,
                voice=self.config.tts.voice,
                rate=rate_str,
            )

            # Temp fayl
            fd, tmp = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)

            # Async save
            loop = asyncio.new_event_loop()
            loop.run_until_complete(communicate.save(tmp))
            loop.close()

            # Pygame bilan ijro etish
            if PYGAME_OK and os.path.getsize(tmp) > 0:
                pygame.mixer.music.load(tmp)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.05)
                pygame.mixer.music.unload()
            return True

        except Exception as e:
            logger.error(f"edge-tts error: {e}")
            return False
        finally:
            if tmp and os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except Exception:
                    pass

    def _speak_pyttsx3(self, text: str):
        try:
            self._pyttsx3.say(text)
            self._pyttsx3.runAndWait()
        except Exception as e:
            logger.error(f"pyttsx3 error: {e}")

    def _play_beep(self):
        """Qisqa beep ovozi"""
        try:
            import numpy as np
            import wave

            sr = 22050
            dur = 0.25
            freq = 880
            t = np.linspace(0, dur, int(sr * dur), False)
            wave_data = (np.sin(2 * np.pi * freq * t) *
                         np.exp(-t * 8) * 32767).astype(np.int16)
            stereo = np.column_stack([wave_data, wave_data])

            fd, tmp = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            with wave.open(tmp, "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(stereo.tobytes())

            if PYGAME_OK:
                pygame.mixer.music.load(tmp)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.02)
                pygame.mixer.music.unload()

            os.unlink(tmp)
        except Exception as e:
            logger.debug(f"beep error: {e}")

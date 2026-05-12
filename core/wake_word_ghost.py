"""
GHOST Wake Word Detector
Whisper orqali "ghost" so'zini aniqlaydi - bepul, offline, API key kerak emas.
"""

import threading
import logging
import time
import queue
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WhisperModel = None
    WHISPER_AVAILABLE = False

from config import Config

logger = logging.getLogger(__name__)

# "ghost" ga o'xshash so'zlar (Whisper turlicha eshitishi mumkin)
GHOST_VARIANTS = {
    "ghost", "gost", "ghosts", "goast", "ghost",
    "гост", "гоуст",  # rus
    "g'ost", "g'ost",  # o'zbek
}

# Shovqin filtri - bu so'zlar kelsa e'tibor berma
NOISE_WORDS = {"", " ", ".", ",", "the", "a", "an", "и", "в", "на"}


class WakeWordDetector(QObject):
    """Whisper asosida 'ghost' wake word detector"""

    wake_word_detected = pyqtSignal()

    SAMPLE_RATE = 16000
    CHUNK = 1024           # ~64ms
    WINDOW_SEC = 2.0       # 2 soniyalik audio oyna
    STEP_SEC = 0.5         # har 0.5 soniyada tekshir

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.is_running = False
        self.thread = None
        self.model = None
        self.pa = None
        self.stream = None
        self._audio_buf = []
        self._buf_lock = threading.Lock()
        self._window_samples = int(self.SAMPLE_RATE * self.WINDOW_SEC)
        self._step_samples = int(self.SAMPLE_RATE * self.STEP_SEC)

    def initialize(self) -> bool:
        if not WHISPER_AVAILABLE:
            logger.error("faster-whisper o'rnatilmagan")
            return False
        if not PYAUDIO_AVAILABLE:
            logger.error("pyaudio o'rnatilmagan")
            return False
        try:
            logger.info("Ghost wake word modeli yuklanmoqda (tiny)...")
            self.model = WhisperModel("tiny", device="cpu", compute_type="int8")
            logger.info("Ghost wake word tayyor: 'ghost' deb ayting")
            return True
        except Exception as e:
            logger.error(f"Whisper modeli yuklanmadi: {e}")
            return False

    def start(self):
        if self.is_running:
            return
        if not self.initialize():
            logger.error("Ghost wake word detector ishga tushmadi")
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._detection_loop, daemon=True)
        self.thread.start()
        logger.info("Ghost wake word detection boshlandi: 'ghost' deb ayting")

    def stop(self):
        self.is_running = False
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass
        if self.pa:
            try:
                self.pa.terminate()
            except Exception:
                pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        logger.info("Ghost wake word detection to'xtatildi")

    def _detection_loop(self):
        logger.info("Ghost wake word loop boshlandi")
        try:
            self.pa = pyaudio.PyAudio()
            self.stream = self.pa.open(
                rate=self.SAMPLE_RATE,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.CHUNK
            )
            logger.info("Mikrofon ochildi. 'ghost' so'zini kuting...")

            buf = []
            samples_since_check = 0

            while self.is_running:
                chunk = self.stream.read(self.CHUNK, exception_on_overflow=False)
                arr = np.frombuffer(chunk, dtype=np.int16)
                buf.extend(arr.tolist())
                samples_since_check += len(arr)

                # Har STEP_SEC da tekshir
                if samples_since_check >= self._step_samples:
                    samples_since_check = 0

                    # Oxirgi WINDOW_SEC ni ol
                    window = np.array(
                        buf[-self._window_samples:], dtype=np.int16
                    )

                    # Shovqin darajasini tekshir (juda past bo'lsa o'tkazib yubor)
                    rms = np.sqrt(np.mean(window.astype(np.float32) ** 2))
                    if rms < 200:
                        continue

                    if self._contains_ghost(window):
                        logger.info("Wake word aniqlandi: 'ghost'!")
                        self.wake_word_detected.emit()
                        buf.clear()
                        time.sleep(1.5)  # qayta aniqlashni oldini ol

                    # Buferni tozala (xotira tejash)
                    if len(buf) > self._window_samples * 3:
                        buf = buf[-self._window_samples:]

        except Exception as e:
            logger.error(f"Ghost detection loop xatosi: {e}")
        finally:
            if self.stream:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except Exception:
                    pass
            if self.pa:
                try:
                    self.pa.terminate()
                except Exception:
                    pass
            logger.info("Ghost wake word loop tugadi")

    def _contains_ghost(self, audio: np.ndarray) -> bool:
        """Audio da 'ghost' so'zi borligini tekshir"""
        try:
            audio_f = audio.astype(np.float32) / 32768.0
            segments, _ = self.model.transcribe(
                audio_f,
                language=None,       # avtomatik til aniqlash
                beam_size=1,         # tezlik uchun
                best_of=1,
                temperature=0.0,
                condition_on_previous_text=False,
                no_speech_threshold=0.6,
                vad_filter=True,
            )
            for seg in segments:
                text = seg.text.strip().lower()
                # Har bir so'zni tekshir
                words = text.replace(",", "").replace(".", "").split()
                for word in words:
                    if word in GHOST_VARIANTS:
                        logger.debug(f"Ghost topildi: '{text}'")
                        return True
            return False
        except Exception as e:
            logger.debug(f"Whisper xatosi: {e}")
            return False

    def is_available(self) -> bool:
        return WHISPER_AVAILABLE and PYAUDIO_AVAILABLE

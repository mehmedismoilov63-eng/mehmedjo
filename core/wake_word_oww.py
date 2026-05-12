"""
Wake Word Detection - openWakeWord
"hey_jarvis" modelini ishlatadi, bepul, offline, API key kerak emas.
Tezroq va ishonchli ishlash uchun optimallashtirilgan.
"""

import threading
import logging
import time
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

try:
    from openwakeword.model import Model as OWWModel
    OWW_AVAILABLE = True
except ImportError:
    OWWModel = None
    OWW_AVAILABLE = False

from config import Config

logger = logging.getLogger(__name__)

AVAILABLE_MODELS = {
    "hey_jarvis":  "hey_jarvis_v0.1.onnx",
    "alexa":       "alexa_v0.1.onnx",
    "hey_mycroft": "hey_mycroft_v0.1.onnx",
    "hey_rhasspy": "hey_rhasspy_v0.1.onnx",
}


class WakeWordDetector(QObject):
    wake_word_detected = pyqtSignal()

    SAMPLE_RATE = 16000
    CHUNK = 1280   # 80ms - OWW tavsiya etgan o'lcham

    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.is_running = False
        self.thread = None
        self.model = None
        self.pa = None
        self.stream = None

        kw = getattr(config.wake_word, 'keyword', 'hey_jarvis')
        self.keyword = kw if kw in AVAILABLE_MODELS else 'hey_jarvis'
        # Sensitivity: 0.3 - tezroq aniqlaydi (false positive ko'proq bo'lishi mumkin)
        self.sensitivity = getattr(config.wake_word, 'sensitivity', 0.35)

    def initialize(self) -> bool:
        if not OWW_AVAILABLE:
            logger.error("openwakeword o'rnatilmagan")
            return False
        if not PYAUDIO_AVAILABLE:
            logger.error("pyaudio o'rnatilmagan")
            return False
        try:
            model_name = AVAILABLE_MODELS[self.keyword]
            logger.info(f"OWW modeli yuklanmoqda: {model_name}")
            self.model = OWWModel(
                wakeword_models=[model_name],
                inference_framework="onnx",
                enable_speex_noise_suppression=False,
            )
            logger.info(f"Wake word tayyor: '{self.keyword}' (sensitivity={self.sensitivity})")
            return True
        except Exception as e:
            logger.error(f"OWW modeli yuklanmadi: {e}")
            return False

    def start(self):
        if self.is_running:
            return
        if not self.initialize():
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        logger.info(f"Wake word boshlandi: '{self.keyword}' deb ayting")

    def stop(self):
        self.is_running = False
        self._close_audio()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)

    def _close_audio(self):
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
        except Exception:
            pass
        try:
            if self.pa:
                self.pa.terminate()
        except Exception:
            pass

    def _loop(self):
        logger.info("Wake word loop boshlandi")
        try:
            self.pa = pyaudio.PyAudio()
            self.stream = self.pa.open(
                rate=self.SAMPLE_RATE,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.CHUNK
            )
            logger.info(f"Mikrofon tayyor. '{self.keyword}' deb ayting...")

            cooldown = False
            cooldown_until = 0.0

            while self.is_running:
                chunk = self.stream.read(self.CHUNK, exception_on_overflow=False)
                audio = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)

                now = time.time()
                if cooldown and now < cooldown_until:
                    continue
                cooldown = False

                preds = self.model.predict(audio)

                for name, score in preds.items():
                    if score >= self.sensitivity:
                        logger.info(f"Wake word: '{self.keyword}' (score={score:.2f})")
                        self.wake_word_detected.emit()
                        self.model.reset()
                        cooldown = True
                        cooldown_until = now + 2.5
                        break

        except Exception as e:
            logger.error(f"Wake word loop xatosi: {e}")
        finally:
            self._close_audio()
            logger.info("Wake word loop tugadi")

    def is_available(self) -> bool:
        return OWW_AVAILABLE and PYAUDIO_AVAILABLE

"""
GHOST Assistant - Main GUI Window
Ekran markazida, shar animatsiyasi bilan
"""

import math
import logging
from PyQt6.QtWidgets import QWidget, QApplication, QLabel, QVBoxLayout, QGraphicsOpacityEffect
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    QRect, QPoint, pyqtSignal, QPointF
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QRadialGradient,
    QLinearGradient, QFont, QPainterPath, QConicalGradient
)

logger = logging.getLogger(__name__)

# Holat ranglari
STATE_COLORS = {
    "idle":       QColor(100, 120, 255),   # ko'k-binafsha
    "listening":  QColor(0,   220, 180),   # yashil-moviy
    "processing": QColor(255, 180,  0),    # sariq
    "speaking":   QColor(120, 80,  255),   # binafsha
    "error":      QColor(255,  60,  60),   # qizil
}

STATE_LABELS = {
    "idle":       "GHOST ASSISTANT",
    "listening":  "🎤  Eshitilmoqda...",
    "processing": "⚙️  Bajarilmoqda...",
    "speaking":   "🔊  Javob berilmoqda...",
    "error":      "❌  Xatolik",
}


class GhostWindow(QWidget):
    """Ekran markazida floating GHOST oynasi"""

    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.config = assistant.config

        self._state = "idle"
        self._response_text = ""
        self._angle = 0.0          # shar aylanish burchagi
        self._pulse = 0.0          # pulsatsiya
        self._orb_scale = 0.0      # kirish animatsiyasi
        self._visible = False

        # Oyna sozlamalari - frameless, always on top, ekran markazida
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # O'lcham: 420x420 (shar + matn)
        self.setFixedSize(420, 420)
        self._center_on_screen()

        # Animatsiya taymer - 60 FPS
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick)
        self._anim_timer.start(16)

        # Auto-yashirish taymer
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide_assistant)

        # Opacity animatsiyasi
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)
        self._opacity_effect.setOpacity(0.0)
        self._target_opacity = 0.0
        self._current_opacity = 0.0

    def _center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    # ── Public API ──────────────────────────────────────────────────

    def show_assistant(self):
        """Assistantni ko'rsatish"""
        if self._visible:
            return
        self._visible = True
        self._orb_scale = 0.0
        self._center_on_screen()
        self.show()
        self.raise_()
        self._target_opacity = 0.92
        self._set_state("idle")
        logger.info("Ghost window ko'rsatildi")

    def hide_assistant(self):
        """Assistantni yashirish"""
        if not self._visible:
            return
        self._visible = False
        self._target_opacity = 0.0
        self._hide_timer.stop()
        # Opacity 0 ga tushgach yashiramiz - _tick da
        logger.info("Ghost window yashirildi")

    def set_listening(self):
        self._set_state("listening")
        self._hide_timer.stop()

    def set_processing(self):
        self._set_state("processing")
        self._hide_timer.stop()

    def set_speaking(self, text: str = ""):
        self._response_text = text
        self._set_state("speaking")

    def display_response(self, text: str):
        """Javobni ko'rsatish (assistant.response_ready signali)"""
        self._response_text = text

        # Holat aniqlash
        if "Eshitilmoqda" in text or "🎤" in text:
            self._set_state("listening")
            self._hide_timer.stop()
        elif "Bajarilmoqda" in text or "⚙️" in text:
            self._set_state("processing")
            self._hide_timer.stop()
        else:
            self._set_state("speaking")
            # Javob ko'rsatilgandan keyin 4 soniya yashir
            self._hide_timer.start(4000)

        if not self._visible:
            self.show_assistant()
        self.update()

    # ── Internal ────────────────────────────────────────────────────

    def _set_state(self, state: str):
        self._state = state
        self.update()

    def _tick(self):
        """60 FPS animatsiya"""
        changed = False

        # Opacity smooth
        diff = self._target_opacity - self._current_opacity
        if abs(diff) > 0.005:
            self._current_opacity += diff * 0.12
            self._opacity_effect.setOpacity(self._current_opacity)
            changed = True
        elif self._current_opacity < 0.01 and not self._visible:
            self.hide()

        # Shar kirish animatsiyasi
        if self._visible and self._orb_scale < 1.0:
            self._orb_scale = min(1.0, self._orb_scale + 0.04)
            changed = True

        # Aylanish
        speed = 1.2 if self._state == "listening" else \
                2.5 if self._state == "processing" else 0.6
        self._angle = (self._angle + speed) % 360
        changed = True

        # Pulsatsiya
        import math
        self._pulse = (math.sin(self._angle * math.pi / 180 * 3) + 1) / 2

        if changed:
            self.update()

    # ── Paint ───────────────────────────────────────────────────────

    def paintEvent(self, event):
        if self._current_opacity < 0.01:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2

        color = STATE_COLORS.get(self._state, STATE_COLORS["idle"])
        scale = self._orb_scale

        # ── Tashqi glow halqalar ──
        for i in range(3):
            r = int((90 + i * 28) * scale)
            alpha = int((40 - i * 12) * self._current_opacity)
            glow = QColor(color.red(), color.green(), color.blue(), max(0, alpha))
            pen = QPen(glow, 1.5)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPoint(cx, cy), r, r)

        # ── Aylanuvchi orbit chiziqlar ──
        painter.save()
        painter.translate(cx, cy)
        for i in range(3):
            angle_offset = self._angle + i * 60
            painter.save()
            painter.rotate(angle_offset)
            orbit_r = int(72 * scale)
            alpha = int(120 * self._current_opacity)
            c2 = QColor(color.red(), color.green(), color.blue(), alpha)
            pen2 = QPen(c2, 1.2)
            pen2.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen2)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(-orbit_r, -int(orbit_r * 0.35),
                                orbit_r * 2, int(orbit_r * 0.7))
            painter.restore()
        painter.restore()

        # ── Asosiy shar ──
        orb_r = int((62 + self._pulse * 5) * scale)
        grad = QRadialGradient(cx - orb_r // 3, cy - orb_r // 3, orb_r * 2)
        c_light = QColor(
            min(255, color.red() + 80),
            min(255, color.green() + 80),
            min(255, color.blue() + 80),
            int(220 * self._current_opacity)
        )
        c_dark = QColor(
            color.red() // 2,
            color.green() // 2,
            color.blue() // 2,
            int(200 * self._current_opacity)
        )
        grad.setColorAt(0.0, c_light)
        grad.setColorAt(0.6, QColor(color.red(), color.green(), color.blue(),
                                    int(200 * self._current_opacity)))
        grad.setColorAt(1.0, c_dark)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawEllipse(QPoint(cx, cy), orb_r, orb_r)

        # ── Shar ichidagi "GHOST" matni ──
        painter.setPen(QColor(255, 255, 255, int(230 * self._current_opacity * scale)))
        f1 = QFont("Segoe UI", 11, QFont.Weight.Bold)
        f1.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        painter.setFont(f1)
        painter.drawText(QRect(cx - 60, cy - 14, 120, 20),
                         Qt.AlignmentFlag.AlignCenter, "GHOST")
        f2 = QFont("Segoe UI", 6)
        f2.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3)
        painter.setFont(f2)
        painter.setPen(QColor(200, 200, 255, int(180 * self._current_opacity * scale)))
        painter.drawText(QRect(cx - 60, cy + 4, 120, 14),
                         Qt.AlignmentFlag.AlignCenter, "ASSISTANT")

        # ── Holat matni (shar ostida) ──
        state_label = STATE_LABELS.get(self._state, "")
        if self._state == "speaking" and self._response_text:
            display_text = self._response_text
        else:
            display_text = state_label

        if display_text:
            text_y = cy + orb_r + 18
            text_rect = QRect(20, text_y, w - 40, 80)

            # Matn foni
            bg = QColor(10, 10, 30, int(180 * self._current_opacity))
            painter.setBrush(QBrush(bg))
            painter.setPen(Qt.PenStyle.NoPen)
            bg_rect = QRect(30, text_y - 8, w - 60, 70)
            painter.drawRoundedRect(bg_rect, 12, 12)

            # Matn
            painter.setPen(QColor(255, 255, 255, int(240 * self._current_opacity)))
            font = QFont("Segoe UI", 11)
            painter.setFont(font)
            painter.drawText(text_rect,
                             Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop |
                             Qt.TextFlag.TextWordWrap,
                             display_text)

        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.hide_assistant()

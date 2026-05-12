"""
GHOST Startup Prompt
Noutbuk yoqilganda chiqadigan professional ON/OFF dialog.
"""

import sys
import math
import logging
from PyQt6.QtWidgets import QWidget, QApplication, QLabel, QPushButton, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QLinearGradient, QBrush,
    QPen, QRadialGradient, QPixmap, QIcon
)

logger = logging.getLogger(__name__)

# Rang palitasi
BG_COLOR       = QColor(8, 8, 20)
ACCENT         = QColor(120, 80, 255)
ACCENT_GLOW    = QColor(120, 80, 255, 60)
BTN_ON_START   = QColor(100, 60, 240)
BTN_ON_END     = QColor(60, 180, 255)
BTN_OFF_BG     = QColor(30, 30, 50)
BTN_OFF_BORDER = QColor(80, 80, 120)
TEXT_PRIMARY   = QColor(240, 240, 255)
TEXT_SECONDARY = QColor(140, 140, 180)


class StartupPrompt(QWidget):
    """
    Noutbuk yoqilganda chiqadigan GHOST ishga tushirish dialogi.

    Foydalanish:
        result = StartupPrompt.ask()   # True = ON, False = OFF
    """

    def __init__(self):
        super().__init__()
        self._angle = 0.0
        self._pulse = 0.0
        self._result = False          # False = OFF (default)
        self._btn_on_hover  = False
        self._btn_off_hover = False
        self._closing = False
        self._opacity = 0.0

        self._setup_window()
        self._setup_ui()

        # Animatsiya
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick)
        self._anim_timer.start(16)

        # Fade-in
        self._fade_in()

        # Auto-yopish: 15 soniya ichida bosilmasa — OFF
        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self._auto_close)
        self._auto_timer.start(15000)

        # Countdown label yangilash
        self._countdown = 15
        self._countdown_timer = QTimer(self)
        self._countdown_timer.timeout.connect(self._update_countdown)
        self._countdown_timer.start(1000)

    # ── Window setup ────────────────────────────────────────────────

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(420, 340)
        self._center()

    def _center(self):
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width()  - self.width())  // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

    # ── UI ──────────────────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(0)

        # Spacer — shar uchun joy
        layout.addSpacing(110)

        # Sarlavha
        self._title = QLabel("GHOST ASSISTANT")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title.setStyleSheet("""
            color: rgba(240,240,255,220);
            font-family: 'Segoe UI';
            font-size: 15px;
            font-weight: 700;
            letter-spacing: 4px;
        """)
        layout.addWidget(self._title)

        layout.addSpacing(4)

        # Tavsif
        self._subtitle = QLabel("Ishga tushirilsinmi?")
        self._subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._subtitle.setStyleSheet("""
            color: rgba(140,140,180,200);
            font-family: 'Segoe UI';
            font-size: 11px;
            letter-spacing: 1px;
        """)
        layout.addWidget(self._subtitle)

        layout.addSpacing(24)

        # Tugmalar qatori
        btn_row = QWidget()
        btn_layout = QVBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(10)

        # ON tugmasi
        self._btn_on = _GradientButton(
            "▶  ISHGA TUSHIRISH",
            BTN_ON_START, BTN_ON_END,
            hover_scale=True
        )
        self._btn_on.clicked.connect(self._on_start)
        btn_layout.addWidget(self._btn_on)

        # OFF tugmasi
        self._btn_off = _GradientButton(
            "✕  O'TKAZIB YUBORISH",
            BTN_OFF_BG, BTN_OFF_BG,
            border_color=BTN_OFF_BORDER,
            text_color=TEXT_SECONDARY
        )
        self._btn_off.clicked.connect(self._on_skip)
        btn_layout.addWidget(self._btn_off)

        layout.addWidget(btn_row)

        layout.addSpacing(12)

        # Countdown
        self._countdown_label = QLabel("15 soniyada avtomatik yopiladi")
        self._countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._countdown_label.setStyleSheet("""
            color: rgba(100,100,140,160);
            font-family: 'Segoe UI';
            font-size: 9px;
            letter-spacing: 1px;
        """)
        layout.addWidget(self._countdown_label)

    # ── Animatsiya ──────────────────────────────────────────────────

    def _fade_in(self):
        self._opacity = 0.0
        self._target_opacity = 1.0

    def _tick(self):
        # Opacity smooth
        diff = self._target_opacity - self._opacity
        if abs(diff) > 0.005:
            self._opacity += diff * 0.1

        # Shar aylanishi
        self._angle = (self._angle + 0.8) % 360
        self._pulse = (math.sin(self._angle * math.pi / 90) + 1) / 2

        self.update()

        # Yopish
        if self._closing and self._opacity < 0.02:
            self._anim_timer.stop()
            self.close()

    def _update_countdown(self):
        self._countdown -= 1
        if self._countdown > 0:
            self._countdown_label.setText(
                f"{self._countdown} soniyada avtomatik yopiladi"
            )
        else:
            self._countdown_timer.stop()

    def _auto_close(self):
        self._countdown_timer.stop()
        self._result = False
        self._start_close()

    def _start_close(self):
        self._closing = True
        self._target_opacity = 0.0
        self._auto_timer.stop()
        self._countdown_timer.stop()

    # ── Tugma handlerlari ───────────────────────────────────────────

    def _on_start(self):
        self._result = True
        self._start_close()

    def _on_skip(self):
        self._result = False
        self._start_close()

    # ── Paint ───────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(self._opacity)

        w, h = self.width(), self.height()

        # Fon — qoramtir shisha
        bg = QColor(8, 8, 20, 230)
        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(QColor(60, 40, 120, 180), 1))
        painter.drawRoundedRect(0, 0, w, h, 20, 20)

        # Yuqori gradient chiziq
        line_grad = QLinearGradient(0, 0, w, 0)
        line_grad.setColorAt(0.0, QColor(0, 0, 0, 0))
        line_grad.setColorAt(0.3, ACCENT)
        line_grad.setColorAt(0.7, QColor(60, 180, 255))
        line_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(QPen(QBrush(line_grad), 1.5))
        painter.drawLine(20, 0, w - 20, 0)

        # Shar (yuqori qism)
        cx, cy = w // 2, 62
        self._draw_orb(painter, cx, cy)

        painter.end()

    def _draw_orb(self, painter, cx, cy):
        r = int(38 + self._pulse * 3)

        # Glow
        for i in range(3):
            gr = r + 14 + i * 10
            alpha = int((35 - i * 10) * self._opacity)
            glow = QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(), max(0, alpha))
            painter.setPen(QPen(glow, 1.2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPoint(cx, cy), gr, gr)

        # Orbit
        painter.save()
        painter.translate(cx, cy)
        for i in range(2):
            painter.save()
            painter.rotate(self._angle + i * 90)
            orb_r = r + 8
            c = QColor(ACCENT.red(), ACCENT.green(), ACCENT.blue(),
                       int(90 * self._opacity))
            pen = QPen(c, 1)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(-orb_r, -int(orb_r * 0.4),
                                orb_r * 2, int(orb_r * 0.8))
            painter.restore()
        painter.restore()

        # Asosiy shar
        grad = QRadialGradient(cx - r // 3, cy - r // 3, r * 2)
        grad.setColorAt(0.0, QColor(180, 140, 255, int(230 * self._opacity)))
        grad.setColorAt(0.5, QColor(100, 60, 220, int(210 * self._opacity)))
        grad.setColorAt(1.0, QColor(40, 20, 100, int(190 * self._opacity)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawEllipse(QPoint(cx, cy), r, r)

        # "G" harfi
        painter.setPen(QColor(255, 255, 255, int(220 * self._opacity)))
        f = QFont("Segoe UI", 18, QFont.Weight.Bold)
        painter.setFont(f)
        painter.drawText(
            QRect(cx - 20, cy - 16, 40, 32),
            Qt.AlignmentFlag.AlignCenter, "G"
        )

    # ── Static helper ───────────────────────────────────────────────

    @staticmethod
    def ask() -> bool:
        """
        Dialogni ko'rsatib natijani qaytaradi.
        True  = foydalanuvchi "ISHGA TUSHIRISH" ni bosdi
        False = o'tkazib yubordi yoki 15 soniya o'tdi
        """
        app = QApplication.instance()
        _own_app = False
        if app is None:
            app = QApplication(sys.argv)
            _own_app = True

        prompt = StartupPrompt()
        prompt.show()

        # Event loop — dialog yopilguncha
        while not prompt._closing or prompt._opacity > 0.02:
            app.processEvents()
            if prompt.isHidden() and prompt._closing:
                break

        # Bir oz kutish (fade-out tugashi uchun)
        import time
        deadline = time.time() + 1.0
        while time.time() < deadline:
            app.processEvents()

        result = prompt._result
        prompt.deleteLater()
        return result


# ── Yordamchi tugma widget ───────────────────────────────────────────

class _GradientButton(QPushButton):
    """Gradient yoki solid fon bilan professional tugma"""

    def __init__(self, text, color_start, color_end,
                 border_color=None, text_color=None, hover_scale=False):
        super().__init__(text)
        self._c1 = color_start
        self._c2 = color_end
        self._border = border_color
        self._text_color = text_color or TEXT_PRIMARY
        self._hover_scale = hover_scale
        self._hovered = False

        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("background: transparent; border: none;")

        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if obj is self:
            if event.type() == QEvent.Type.Enter:
                self._hovered = True
                self.update()
            elif event.type() == QEvent.Type.Leave:
                self._hovered = False
                self.update()
        return super().eventFilter(obj, event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        margin = 2 if self._hovered and self._hover_scale else 0

        rect = QRect(margin, margin, w - margin * 2, h - margin * 2)

        # Fon
        if self._c1 != self._c2:
            grad = QLinearGradient(0, 0, w, 0)
            grad.setColorAt(0, self._c1)
            grad.setColorAt(1, self._c2)
            painter.setBrush(QBrush(grad))
        else:
            painter.setBrush(QBrush(self._c1))

        if self._border:
            painter.setPen(QPen(self._border, 1))
        else:
            painter.setPen(Qt.PenStyle.NoPen)

        painter.drawRoundedRect(rect, 10, 10)

        # Hover overlay
        if self._hovered:
            overlay = QColor(255, 255, 255, 18)
            painter.setBrush(QBrush(overlay))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 10, 10)

        # Matn
        painter.setPen(self._text_color)
        f = QFont("Segoe UI", 10, QFont.Weight.DemiBold)
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
        painter.setFont(f)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())

        painter.end()

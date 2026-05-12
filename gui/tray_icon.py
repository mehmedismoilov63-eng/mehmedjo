"""
System Tray Icon Module
Manages GHOST Assistant system tray functionality
"""

import sys
import logging
from PyQt6.QtWidgets import (
    QSystemTrayIcon, QMenu, QMessageBox, QDialog,
    QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox,
    QSpinBox, QCheckBox, QFormLayout, QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction

from config import Config

logger = logging.getLogger(__name__)

class TrayIcon(QSystemTrayIcon):
    """System tray icon for GHOST Assistant"""
    
    # Signals
    settings_requested = pyqtSignal()
    user_switch_requested = pyqtSignal()
    exit_requested = pyqtSignal()
    
    def __init__(self, assistant, main_window):
        super().__init__()
        self.assistant = assistant
        self.main_window = main_window
        self.config = assistant.config
        
        # Status states
        self.status = "idle"  # idle, listening, processing, error
        
        # Create icon
        self.create_icon()
        
        # Create context menu
        self.create_context_menu()
        
        # Connect signals
        self.activated.connect(self.on_activated)
        self.assistant.listening_started.connect(self.set_listening_status)
        self.assistant.listening_stopped.connect(self.set_idle_status)
        self.assistant.response_ready.connect(self.set_processing_status)
        
        # Status update timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(1000)  # Update every second
        
        logger.info("System tray icon initialized")
        
    def create_icon(self):
        """Create ghost icon"""
        # Create a simple ghost icon
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw ghost shape
        painter.setBrush(QColor(139, 92, 246))  # Purple color
        painter.setPen(QColor(99, 102, 241))  # Border color
        
        # Ghost body (circle)
        painter.drawEllipse(4, 4, 24, 24)
        
        # Ghost eyes
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(10, 10, 4, 4)
        painter.drawEllipse(18, 10, 4, 4)
        
        # Ghost pupils
        painter.setBrush(QColor(0, 0, 0))
        painter.drawEllipse(11, 11, 2, 2)
        painter.drawEllipse(19, 11, 2, 2)
        
        painter.end()
        
        # Create icon
        self.icon = QIcon(pixmap)
        self.setIcon(self.icon)
        
        # Set tooltip
        self.setToolTip("GHOST Assistant - Idle")
        
    def create_context_menu(self):
        """Create context menu"""
        menu = QMenu()
        
        # Status action
        self.status_action = QAction("Status: Idle", self)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)
        
        menu.addSeparator()
        
        # Settings action
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings)
        menu.addAction(settings_action)
        
        # Switch user action
        switch_user_action = QAction("Switch User", self)
        switch_user_action.triggered.connect(self.switch_user)
        menu.addAction(switch_user_action)
        
        menu.addSeparator()
        
        # Test action
        test_action = QAction("Test Voice", self)
        test_action.triggered.connect(self.test_voice)
        menu.addAction(test_action)
        
        menu.addSeparator()
        
        # Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.exit_application)
        menu.addAction(exit_action)
        
        self.setContextMenu(menu)
        
    def on_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # Toggle main window visibility
            if self.main_window.isVisible():
                self.main_window.hide()
            else:
                self.main_window.show_assistant()
                
    def set_idle_status(self):
        """Set idle status"""
        self.status = "idle"
        self.update_icon_color(QColor(139, 92, 246))  # Purple
        self.setToolTip("GHOST Assistant - Idle")
        
    def set_listening_status(self):
        """Set listening status"""
        self.status = "listening"
        self.update_icon_color(QColor(255, 193, 7))  # Yellow
        self.setToolTip("GHOST Assistant - Listening...")
        
    def set_processing_status(self):
        """Set processing status"""
        self.status = "processing"
        self.update_icon_color(QColor(76, 175, 80))  # Green
        self.setToolTip("GHOST Assistant - Processing...")
        
    def set_error_status(self):
        """Set error status"""
        self.status = "error"
        self.update_icon_color(QColor(244, 67, 54))  # Red
        self.setToolTip("GHOST Assistant - Error")
        
    def update_icon_color(self, color):
        """Update icon color based on status"""
        # Create new icon with status color
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw ghost shape with status color
        painter.setBrush(color)
        painter.setPen(color.darker(150))
        
        # Ghost body (circle)
        painter.drawEllipse(4, 4, 24, 24)
        
        # Ghost eyes
        painter.setBrush(QColor(255, 255, 255))
        painter.drawEllipse(10, 10, 4, 4)
        painter.drawEllipse(18, 10, 4, 4)
        
        # Ghost pupils
        painter.setBrush(QColor(0, 0, 0))
        painter.drawEllipse(11, 11, 2, 2)
        painter.drawEllipse(19, 11, 2, 2)
        
        painter.end()
        
        # Update icon
        self.icon = QIcon(pixmap)
        self.setIcon(self.icon)
        
    def update_status(self):
        """Update status display"""
        status_text = f"Status: {self.status.capitalize()}"
        self.status_action.setText(status_text)
        
    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Save configuration
            self.config.save()
            logger.info("Settings saved")
            
    def switch_user(self):
        """Switch user dialog"""
        users = self.assistant.voice_profiler.get_users()
        
        if not users:
            QMessageBox.information(
                None,
                "No Users",
                "No registered users found. Please register users first."
            )
            return
            
        dialog = UserSwitchDialog(users, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_user = dialog.get_selected_user()
            logger.info(f"Switched to user: {selected_user['name']}")
            
    def test_voice(self):
        """Test voice recognition"""
        QMessageBox.information(
            None,
            "Voice Test",
            "Voice test feature coming soon!\n\nSay 'Hey Ghost' to test wake word detection."
        )
        
    def exit_application(self):
        """Exit application"""
        reply = QMessageBox.question(
            None,
            "Exit GHOST",
            "Are you sure you want to exit GHOST Assistant?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.exit_requested.emit()
            import sys
            sys.exit(0)

class SettingsDialog(QDialog):
    """Settings configuration dialog"""
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setup_ui()
        
    def setup_ui(self):
        """Setup settings UI"""
        self.setWindowTitle("GHOST Assistant Settings")
        self.setModal(True)
        self.resize(500, 600)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create form layout
        form_layout = QFormLayout()
        
        # Wake word settings
        self.wake_word_edit = QLineEdit(self.config.wake_word.keyword)
        form_layout.addRow("Wake Word:", self.wake_word_edit)
        
        # Language settings
        self.language_combo = QComboBox()
        self.language_combo.addItems(["uz", "ru", "en"])
        self.language_combo.setCurrentText(self.config.stt.language)
        form_layout.addRow("Language:", self.language_combo)
        
        # TTS Engine
        self.tts_engine_combo = QComboBox()
        self.tts_engine_combo.addItems(["edge_tts", "pyttsx3"])
        self.tts_engine_combo.setCurrentText(self.config.tts.engine)
        form_layout.addRow("TTS Engine:", self.tts_engine_combo)
        
        # STT Engine
        self.stt_engine_combo = QComboBox()
        self.stt_engine_combo.addItems(["faster_whisper", "vosk"])
        self.stt_engine_combo.setCurrentText(self.config.stt.engine)
        form_layout.addRow("STT Engine:", self.stt_engine_combo)
        
        # Voice settings
        self.tts_rate_spin = QSpinBox()
        self.tts_rate_spin.setRange(50, 200)
        self.tts_rate_spin.setValue(int(self.config.tts.rate * 100))
        form_layout.addRow("Speech Rate (%):", self.tts_rate_spin)
        
        self.tts_volume_spin = QSpinBox()
        self.tts_volume_spin.setRange(0, 100)
        self.tts_volume_spin.setValue(int(self.config.tts.volume * 100))
        form_layout.addRow("Speech Volume (%):", self.tts_volume_spin)
        
        # GUI settings
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(50, 100)
        self.opacity_spin.setValue(int(self.config.gui.opacity * 100))
        form_layout.addRow("Window Opacity (%):", self.opacity_spin)
        
        # Security settings
        self.confirm_actions_check = QCheckBox()
        self.confirm_actions_check.setChecked(self.config.security.confirm_dangerous_actions)
        form_layout.addRow("Confirm Dangerous Actions:", self.confirm_actions_check)
        
        # Telegram settings
        self.telegram_token_edit = QLineEdit()
        self.telegram_token_edit.setText(self.config.telegram.token or "")
        self.telegram_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("Telegram Token:", self.telegram_token_edit)
        
        layout.addLayout(form_layout)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def accept(self):
        """Save settings"""
        # Update config
        self.config.wake_word.keyword = self.wake_word_edit.text()
        self.config.stt.language = self.language_combo.currentText()
        self.config.tts.engine = self.tts_engine_combo.currentText()
        self.config.stt.engine = self.stt_engine_combo.currentText()
        self.config.tts.rate = self.tts_rate_spin.value() / 100.0
        self.config.tts.volume = self.tts_volume_spin.value() / 100.0
        self.config.gui.opacity = self.opacity_spin.value() / 100.0
        self.config.security.confirm_dangerous_actions = self.confirm_actions_check.isChecked()
        self.config.telegram.token = self.telegram_token_edit.text()
        
        super().accept()

class UserSwitchDialog(QDialog):
    """User switch dialog"""
    
    def __init__(self, users, parent=None):
        super().__init__(parent)
        self.users = users
        self.selected_user = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup user switch UI"""
        self.setWindowTitle("Switch User")
        self.setModal(True)
        self.resize(300, 200)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # User list
        self.user_combo = QComboBox()
        for user in self.users:
            self.user_combo.addItem(user['name'], user)
        layout.addWidget(QLabel("Select User:"))
        layout.addWidget(self.user_combo)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def accept(self):
        """Accept selection"""
        self.selected_user = self.user_combo.currentData()
        super().accept()
        
    def get_selected_user(self):
        """Get selected user"""
        return self.selected_user

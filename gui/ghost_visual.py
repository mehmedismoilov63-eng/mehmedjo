"""
GHOST Visual Interface
Transparent light sphere effect with animations
"""

import sys
import os
import time
import threading
import math
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

try:
    from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QRectF
    from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QFont, QRadialGradient
    from PyQt6.QtWidgets import QGraphicsScene, QGraphicsView
    from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsTextItem
    from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
    from PyQt6.QtGui import QLinearGradient
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    print("PyQt6 not available, using fallback")

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("Pygame not available")

class GhostVisualPyQt(QWidget):
    """PyQt6 based visual interface"""
    
    signal_command = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.animations = []
        self.is_visible = False
        
    def init_ui(self):
        """Initialize UI"""
        # Window properties
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        # Set window size and position
        self.setGeometry(100, 100, 300, 300)
        
        # Center on screen
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        
        # Animation timer
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(50)  # 20 FPS
        
        self.pulse_phase = 0
        self.rotation_angle = 0
        
    def paintEvent(self, event):
        """Paint the ghost sphere"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Create radial gradient for sphere effect
        center_x = self.width() // 2
        center_y = self.height() // 2
        radius = min(self.width(), self.height()) // 3
        
        # Pulsing effect
        pulse = math.sin(self.pulse_phase) * 10
        current_radius = radius + pulse
        
        # Create gradient
        gradient = QRadialGradient(center_x, center_y, current_radius)
        gradient.setColorAt(0, QColor(100, 200, 255, 180))  # Light blue center
        gradient.setColorAt(0.5, QColor(50, 150, 255, 120))  # Medium blue
        gradient.setColorAt(1, QColor(0, 100, 255, 60))  # Dark blue edge
        
        # Draw main sphere
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(100, 200, 255, 100), 2))
        painter.drawEllipse(center_x - current_radius, center_y - current_radius, 
                         current_radius * 2, current_radius * 2)
        
        # Draw rotating ring
        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(self.rotation_angle)
        
        ring_gradient = QLinearGradient(-current_radius, 0, current_radius, 0)
        ring_gradient.setColorAt(0, QColor(255, 255, 255, 0))
        ring_gradient.setColorAt(0.5, QColor(255, 255, 255, 200))
        ring_gradient.setColorAt(1, QColor(255, 255, 255, 0))
        
        painter.setPen(QPen(QBrush(ring_gradient), 3))
        painter.drawEllipse(-current_radius + 10, -current_radius + 10, 
                         (current_radius - 10) * 2, (current_radius - 10) * 2)
        painter.restore()
        
        # Draw text
        font = QFont("Arial", 14, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor(255, 255, 255, 200)))
        text_rect = painter.boundingRect(0, 0, self.width(), self.height(), 
                                     Qt.AlignCenter, "GHOST")
        painter.drawText(text_rect, Qt.AlignCenter, "GHOST")
        
    def update_animation(self):
        """Update animation"""
        self.pulse_phase += 0.1
        self.rotation_angle += 2
        self.update()
        
    def show_ghost(self):
        """Show ghost with animation"""
        self.is_visible = True
        self.show()
        self.raise_()
        self.activateWindow()
        
    def hide_ghost(self):
        """Hide ghost with animation"""
        self.is_visible = False
        self.hide()
        
    def speak_animation(self):
        """Animate when speaking"""
        # Add speaking animation
        pass
        
    def listen_animation(self):
        """Animate when listening"""
        # Add listening animation
        pass

class GhostVisualPygame:
    """Pygame based visual interface (fallback)"""
    
    def __init__(self):
        if not PYGAME_AVAILABLE:
            raise ImportError("Pygame not available")
            
        pygame.init()
        self.width, self.height = 300, 300
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.NOFRAME)
        pygame.display.set_caption("GHOST Assistant")
        
        # Make window transparent
        self.screen.set_alpha(200)
        
        # Center on screen
        screen_info = pygame.display.Info()
        x = (screen_info.current_w - self.width) // 2
        y = (screen_info.current_h - self.height) // 2
        os.environ['SDL_VIDEO_WINDOW_POS'] = f"{x},{y}"
        
        self.clock = pygame.time.Clock()
        self.running = False
        self.pulse_phase = 0
        
    def draw_sphere(self):
        """Draw the ghost sphere"""
        self.screen.fill((0, 0, 0, 0))  # Transparent background
        
        center_x = self.width // 2
        center_y = self.height // 2
        radius = min(self.width, self.height) // 3
        
        # Pulsing effect
        pulse = math.sin(self.pulse_phase) * 10
        current_radius = int(radius + pulse)
        
        # Draw main sphere with gradient effect
        for i in range(current_radius, 0, -2):
            alpha = int(180 * (1 - i / current_radius))
            color = (100 + i//2, 200 - i//2, 255, alpha)
            pygame.draw.circle(self.screen, color, (center_x, center_y), i)
        
        # Draw text
        font = pygame.font.Font(None, 24)
        text = font.render("GHOST", True, (255, 255, 255))
        text_rect = text.get_rect(center=(center_x, center_y))
        self.screen.blit(text, text_rect)
        
    def show_ghost(self):
        """Show ghost"""
        self.running = True
        
    def hide_ghost(self):
        """Hide ghost"""
        self.running = False
        
    def run(self):
        """Main loop"""
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    
            self.draw_sphere()
            pygame.display.flip()
            self.clock.tick(30)
            
            self.pulse_phase += 0.1
            
        pygame.quit()

class GhostVisualManager:
    """Main visual manager"""
    
    def __init__(self):
        self.visual = None
        self.init_visual()
        
    def init_visual(self):
        """Initialize visual interface"""
        if PYQT_AVAILABLE:
            try:
                app = QApplication.instance()
                if app is None:
                    app = QApplication(sys.argv)
                self.visual = GhostVisualPyQt()
                self.app = app
                return True
            except Exception as e:
                print(f"PyQt6 initialization failed: {e}")
                
        if PYGAME_AVAILABLE:
            try:
                self.visual = GhostVisualPygame()
                return True
            except Exception as e:
                print(f"Pygame initialization failed: {e}")
                
        return False
        
    def show_ghost(self):
        """Show ghost"""
        if self.visual:
            self.visual.show_ghost()
            
    def hide_ghost(self):
        """Hide ghost"""
        if self.visual:
            self.visual.hide_ghost()
            
    def run(self):
        """Run visual interface"""
        if self.visual and hasattr(self.visual, 'run'):
            self.visual.run()
        elif self.visual and hasattr(self.visual, 'show'):
            self.visual.show_ghost()
            if hasattr(self, 'app'):
                self.app.exec()

# Test the visual interface
if __name__ == "__main__":
    manager = GhostVisualManager()
    if manager.init_visual():
        manager.show_ghost()
        manager.run()
    else:
        print("Failed to initialize visual interface")

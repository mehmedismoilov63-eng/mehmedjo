"""
GHOST Visual Interface - Simple Version
Transparent light sphere effect using pygame only
"""

import os
import sys
import math
import time
import threading
import logging
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("Pygame not available")

class GhostVisualPygame:
    """Pygame based visual interface"""
    
    def __init__(self):
        if not PYGAME_AVAILABLE:
            raise ImportError("Pygame not available")
            
        pygame.init()
        self.width, self.height = 300, 300
        
        # Set up display with transparency
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.NOFRAME)
        pygame.display.set_caption("GHOST Assistant")
        
        # Create transparent surface
        self.screen.set_colorkey((0, 0, 0))
        self.screen.set_alpha(200)
        
        # Center on screen
        screen_info = pygame.display.Info()
        x = (screen_info.current_w - self.width) // 2
        y = (screen_info.current_h - self.height) // 2
        
        # Set window position
        os.environ['SDL_VIDEO_WINDOW_POS'] = f"{x},{y}"
        
        self.clock = pygame.time.Clock()
        self.running = False
        self.pulse_phase = 0
        self.rotation_angle = 0
        
    def draw_sphere(self):
        """Draw the ghost sphere with effects"""
        # Clear screen with transparency
        self.screen.fill((0, 0, 0, 0))
        
        center_x = self.width // 2
        center_y = self.height // 2
        base_radius = min(self.width, self.height) // 3
        
        # Pulsing effect
        pulse = math.sin(self.pulse_phase) * 10
        current_radius = int(base_radius + pulse)
        
        # Draw main sphere with gradient effect
        for i in range(current_radius, 0, -2):
            alpha = int(180 * (1 - i / current_radius))
            # Create gradient color
            r = min(255, 100 + i // 2)
            g = min(255, 200 - i // 4)
            b = 255
            color = (r, g, b, alpha)
            
            # Draw circle
            pygame.draw.circle(self.screen, color, (center_x, center_y), i)
        
        # Draw rotating ring
        ring_radius = current_radius + 15
        for angle in range(0, 360, 30):
            x = center_x + int(ring_radius * math.cos(math.radians(angle + self.rotation_angle)))
            y = center_y + int(ring_radius * math.sin(math.radians(angle + self.rotation_angle)))
            pygame.draw.circle(self.screen, (255, 255, 255, 150), (x, y), 3)
        
        # Draw text
        try:
            font = pygame.font.Font(None, 24)
        except:
            font = pygame.font.SysFont('Arial', 24)
            
        text = font.render("GHOST", True, (255, 255, 255))
        text_rect = text.get_rect(center=(center_x, center_y))
        self.screen.blit(text, text_rect)
        
    def show_ghost(self):
        """Show ghost"""
        self.running = True
        self.logger.info("Ghost visual shown")
        
    def hide_ghost(self):
        """Hide ghost"""
        self.running = False
        self.logger.info("Ghost visual hidden")
        
    def run(self):
        """Main pygame loop"""
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    
            self.draw_sphere()
            pygame.display.flip()
            self.clock.tick(30)
            
            # Update animations
            self.pulse_phase += 0.1
            self.rotation_angle += 2
            
        pygame.quit()

class GhostVisualManager:
    """Main visual manager - simplified"""
    
    def __init__(self):
        self.visual = None
        self.logger = logging.getLogger(__name__)
        
    def init_visual(self):
        """Initialize visual interface"""
        try:
            self.visual = GhostVisualPygame()
            return True
        except Exception as e:
            print(f"Visual interface initialization failed: {e}")
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
        if self.visual:
            self.visual.run()

# Test the visual interface
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    manager = GhostVisualManager()
    if manager.init_visual():
        print("Visual interface initialized successfully")
        manager.show_ghost()
        manager.run()
    else:
        print("Failed to initialize visual interface")

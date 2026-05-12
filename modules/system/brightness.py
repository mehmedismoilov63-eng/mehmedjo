"""
Brightness Control Module
Manages Windows screen brightness
"""

import logging
from typing import Optional

try:
    import screen_brightness_control as sbc
except ImportError:
    sbc = None
    logging.warning("screen-brightness-control not installed. Brightness control disabled.")

logger = logging.getLogger(__name__)

class BrightnessController:
    """Controls Windows screen brightness"""
    
    def __init__(self):
        self.is_available = sbc is not None
        
    def get_brightness(self) -> int:
        """Get current brightness level (0-100)"""
        if not self.is_available:
            return 0
            
        try:
            brightness = sbc.get_brightness()
            if isinstance(brightness, list):
                return brightness[0] if brightness else 0
            return brightness
        except Exception as e:
            logger.error(f"Error getting brightness: {e}")
            return 0
            
    def set_brightness(self, level: int) -> bool:
        """Set brightness level (0-100)"""
        if not self.is_available:
            return False
            
        try:
            # Clamp level to valid range
            level = max(0, min(100, level))
            sbc.set_brightness(level)
            logger.info(f"Brightness set to {level}%")
            return True
            
        except Exception as e:
            logger.error(f"Error setting brightness: {e}")
            return False
            
    def increase_brightness(self, amount: int = 10) -> bool:
        """Increase brightness by percentage"""
        current_brightness = self.get_brightness()
        new_brightness = current_brightness + amount
        return self.set_brightness(new_brightness)
        
    def decrease_brightness(self, amount: int = 10) -> bool:
        """Decrease brightness by percentage"""
        current_brightness = self.get_brightness()
        new_brightness = current_brightness - amount
        return self.set_brightness(new_brightness)
        
    def get_brightness_range(self) -> tuple:
        """Get min/max brightness range"""
        if not self.is_available:
            return (0, 100)
            
        try:
            monitors = sbc.list_monitors()
            if monitors:
                # Get brightness range for first monitor
                return sbc.get_brightness(monitors[0])
            return (0, 100)
        except Exception as e:
            logger.error(f"Error getting brightness range: {e}")
            return (0, 100)
            
    def is_supported(self) -> bool:
        """Check if brightness control is supported"""
        return self.is_available

"""
Volume Control Module
Manages Windows system volume using pycaw
"""

import logging
from typing import Optional

try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from pycaw.utils import AudioUtilities as AU
    from comtypes import CLSCTX_ALL
    from ctypes import cast, POINTER
    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False
    logging.warning("pycaw not installed. Volume control disabled.")

logger = logging.getLogger(__name__)

class VolumeController:
    """Controls Windows system volume"""
    
    def __init__(self):
        self.volume = None
        self.initialize()
        
    def initialize(self) -> bool:
        """Initialize volume control"""
        if not PYCAW_AVAILABLE:
            logger.error("pycaw not available")
            return False
            
        try:
            device = AudioUtilities.GetSpeakers()
            self.volume = device.EndpointVolume
            logger.info("Volume control initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize volume control: {e}")
            return False
            
    def get_volume(self) -> float:
        """Get current volume level (0.0 to 1.0)"""
        if not self.volume:
            return 0.0
            
        try:
            return self.volume.GetMasterVolumeLevelScalar()
        except Exception as e:
            logger.error(f"Error getting volume: {e}")
            return 0.0
            
    def set_volume(self, level: float) -> bool:
        """Set volume level (0.0 to 1.0)"""
        if not self.volume:
            return False
            
        try:
            # Clamp level to valid range
            level = max(0.0, min(1.0, level))
            self.volume.SetMasterVolumeLevelScalar(level, None)
            logger.info(f"Volume set to {level * 100:.0f}%")
            return True
            
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            return False
            
    def increase_volume(self, amount: int = 10) -> bool:
        """Increase volume by percentage"""
        current_volume = self.get_volume()
        new_volume = current_volume + (amount / 100.0)
        return self.set_volume(new_volume)
        
    def decrease_volume(self, amount: int = 10) -> bool:
        """Decrease volume by percentage"""
        current_volume = self.get_volume()
        new_volume = current_volume - (amount / 100.0)
        return self.set_volume(new_volume)
        
    def get_mute(self) -> bool:
        """Get mute status"""
        if not self.volume:
            return False
            
        try:
            return self.volume.GetMute()
        except Exception as e:
            logger.error(f"Error getting mute status: {e}")
            return False
            
    def set_mute(self, mute: bool) -> bool:
        """Set mute status"""
        if not self.volume:
            return False
            
        try:
            self.volume.SetMute(mute, None)
            logger.info(f"Mute set to {mute}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting mute: {e}")
            return False
            
    def toggle_mute(self) -> bool:
        """Toggle mute status"""
        current_mute = self.get_mute()
        return self.set_mute(not current_mute)
        
    def is_available(self) -> bool:
        """Check if volume control is available"""
        return self.volume is not None

"""
System Control Modules Package
Contains modules for Windows system control
"""

from .volume import VolumeController
from .brightness import BrightnessController
from .power import PowerManager
from .screenshot import ScreenshotManager
from .applications import AppManager

__all__ = [
    'VolumeController',
    'BrightnessController', 
    'PowerManager',
    'ScreenshotManager',
    'AppManager'
]

"""
Screenshot Module
Captures and manages screenshots
"""

import os
import logging
import time
from datetime import datetime
from typing import Optional

try:
    import pyautogui
except ImportError:
    pyautogui = None
    logging.warning("pyautogui not installed. Screenshot functionality disabled.")

from config import Config

logger = logging.getLogger(__name__)

class ScreenshotManager:
    """Manages screenshot capture and storage"""
    
    def __init__(self, config: Config):
        self.config = config
        self.screenshots_dir = "screenshots"
        self.ensure_screenshots_directory()
        
    def ensure_screenshots_directory(self):
        """Ensure screenshots directory exists"""
        try:
            os.makedirs(self.screenshots_dir, exist_ok=True)
            logger.info(f"Screenshots directory: {self.screenshots_dir}")
        except Exception as e:
            logger.error(f"Error creating screenshots directory: {e}")
            
    def take_screenshot(self, filename: str = None, save_to_desktop: bool = True) -> Optional[str]:
        """Take a screenshot and save it"""
        if pyautogui is None:
            logger.error("pyautogui not available")
            return None
            
        try:
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}.png"
                
            # Ensure .png extension
            if not filename.lower().endswith('.png'):
                filename += '.png'
                
            # Determine save path
            if save_to_desktop:
                # Try to get desktop path
                import os
                desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                if os.path.exists(desktop_path):
                    save_path = os.path.join(desktop_path, filename)
                else:
                    # Fallback to screenshots directory
                    save_path = os.path.join(self.screenshots_dir, filename)
            else:
                save_path = os.path.join(self.screenshots_dir, filename)
                
            # Take screenshot
            screenshot = pyautogui.screenshot()
            screenshot.save(save_path)
            
            logger.info(f"Screenshot saved: {save_path}")
            return save_path
            
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return None
            
    def take_region_screenshot(self, x: int, y: int, width: int, height: int, 
                             filename: str = None) -> Optional[str]:
        """Take screenshot of specific region"""
        if pyautogui is None:
            logger.error("pyautogui not available")
            return None
            
        try:
            # Generate filename if not provided
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"region_{timestamp}.png"
                
            # Ensure .png extension
            if not filename.lower().endswith('.png'):
                filename += '.png'
                
            save_path = os.path.join(self.screenshots_dir, filename)
            
            # Take region screenshot
            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            screenshot.save(save_path)
            
            logger.info(f"Region screenshot saved: {save_path}")
            return save_path
            
        except Exception as e:
            logger.error(f"Error taking region screenshot: {e}")
            return None
            
    def take_active_window_screenshot(self, filename: str = None) -> Optional[str]:
        """Take screenshot of active window"""
        try:
            import pygetwindow as gw
            
            # Get active window
            active_window = gw.getActiveWindow()
            if not active_window:
                logger.warning("No active window found")
                return self.take_screenshot(filename)  # Fallback to full screen
                
            # Get window bounds
            x, y, width, height = active_window.left, active_window.top, active_window.width, active_window.height
            
            # Take region screenshot
            return self.take_region_screenshot(x, y, width, height, filename)
            
        except ImportError:
            logger.warning("pygetwindow not available, taking full screenshot")
            return self.take_screenshot(filename)
        except Exception as e:
            logger.error(f"Error taking active window screenshot: {e}")
            return self.take_screenshot(filename)  # Fallback
            
    def get_screen_size(self) -> tuple:
        """Get screen dimensions"""
        try:
            if pyautogui:
                return pyautogui.size()
            else:
                # Fallback method
                import tkinter as tk
                root = tk.Tk()
                width = root.winfo_screenwidth()
                height = root.winfo_screenheight()
                root.destroy()
                return (width, height)
        except Exception as e:
            logger.error(f"Error getting screen size: {e}")
            return (1920, 1080)  # Default fallback
            
    def list_screenshots(self) -> list:
        """List all screenshots in directory"""
        try:
            screenshots = []
            for filename in os.listdir(self.screenshots_dir):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    filepath = os.path.join(self.screenshots_dir, filename)
                    stat = os.stat(filepath)
                    screenshots.append({
                        'filename': filename,
                        'filepath': filepath,
                        'size': stat.st_size,
                        'created': stat.st_ctime
                    })
                    
            # Sort by creation time (newest first)
            screenshots.sort(key=lambda x: x['created'], reverse=True)
            return screenshots
            
        except Exception as e:
            logger.error(f"Error listing screenshots: {e}")
            return []
            
    def delete_screenshot(self, filename: str) -> bool:
        """Delete a screenshot file"""
        try:
            filepath = os.path.join(self.screenshots_dir, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Screenshot deleted: {filepath}")
                return True
            else:
                logger.warning(f"Screenshot not found: {filepath}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting screenshot: {e}")
            return False
            
    def get_recent_screenshots(self, count: int = 5) -> list:
        """Get recent screenshots"""
        screenshots = self.list_screenshots()
        return screenshots[:count]
        
    def is_available(self) -> bool:
        """Check if screenshot functionality is available"""
        return pyautogui is not None

"""
Power Management Module
Manages Windows power operations (shutdown, restart, sleep)
"""

import os
import logging
import threading
import time
import subprocess
from typing import Optional

try:
    import win32api
    import win32con
    import win32security
except ImportError:
    win32api = None
    win32con = None
    win32security = None
    logging.warning("pywin32 not installed. Some power features may be limited.")

from config import Config

logger = logging.getLogger(__name__)

class PowerManager:
    """Manages Windows power operations"""
    
    def __init__(self, config: Config):
        self.config = config
        self.shutdown_timer = None
        self.shutdown_thread = None
        self.is_shutdown_scheduled = False
        
    def shutdown(self, force: bool = False) -> bool:
        """Shutdown computer immediately"""
        try:
            logger.info("Shutting down computer...")
            subprocess.run(['shutdown', '/s', '/t', '0'], check=True)
            return True
        except Exception as e:
            logger.error(f"Error shutting down: {e}")
            return False

    def restart(self, force: bool = False) -> bool:
        """Restart computer immediately"""
        try:
            logger.info("Restarting computer...")
            subprocess.run(['shutdown', '/r', '/t', '0'], check=True)
            return True
        except Exception as e:
            logger.error(f"Error restarting: {e}")
            return False
            
    def sleep(self) -> bool:
        """Put computer to sleep"""
        try:
            logger.info("Putting computer to sleep...")
            import subprocess
            subprocess.run(
                ["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"],
                check=True
            )
            return True
        except Exception as e:
            logger.error(f"Error sleeping: {e}")
            return False
                
    def hibernate(self) -> bool:
        """Hibernate computer"""
        try:
            logger.info("Hibernating computer...")
            
            if os.name == 'nt':
                subprocess.run(['shutdown', '/h'], check=True)
            else:
                subprocess.run(['systemctl', 'hibernate'], check=True)
                
            return True
            
        except Exception as e:
            logger.error(f"Error hibernating: {e}")
            return False
            
    def schedule_shutdown(self, delay_seconds: int = 30, message: str = None) -> bool:
        """Schedule shutdown with delay"""
        try:
            if self.is_shutdown_scheduled:
                logger.warning("Shutdown already scheduled")
                return False
                
            self.is_shutdown_scheduled = True
            
            # Start shutdown in separate thread
            self.shutdown_thread = threading.Thread(
                target=self._shutdown_worker,
                args=(delay_seconds, message),
                daemon=True
            )
            self.shutdown_thread.start()
            
            logger.info(f"Shutdown scheduled in {delay_seconds} seconds")
            return True
            
        except Exception as e:
            logger.error(f"Error scheduling shutdown: {e}")
            return False
            
    def schedule_restart(self, delay_seconds: int = 30, message: str = None) -> bool:
        """Schedule restart with delay"""
        try:
            if self.is_shutdown_scheduled:
                logger.warning("Restart already scheduled")
                return False
                
            self.is_shutdown_scheduled = True
            
            # Start restart in separate thread
            self.shutdown_thread = threading.Thread(
                target=self._restart_worker,
                args=(delay_seconds, message),
                daemon=True
            )
            self.shutdown_thread.start()
            
            logger.info(f"Restart scheduled in {delay_seconds} seconds")
            return True
            
        except Exception as e:
            logger.error(f"Error scheduling restart: {e}")
            return False
            
    def _shutdown_worker(self, delay_seconds: int, message: str):
        """Worker thread for scheduled shutdown"""
        try:
            # Wait for delay
            for i in range(delay_seconds, 0, -1):
                if not self.is_shutdown_scheduled:
                    logger.info("Shutdown cancelled")
                    return
                    
                time.sleep(1)
                
                # Log countdown every 10 seconds
                if i % 10 == 0 or i <= 5:
                    logger.info(f"Shutdown in {i} seconds...")
                    
            # Execute shutdown
            self.shutdown(force=True)
            
        except Exception as e:
            logger.error(f"Error in shutdown worker: {e}")
        finally:
            self.is_shutdown_scheduled = False
            
    def _restart_worker(self, delay_seconds: int, message: str):
        """Worker thread for scheduled restart"""
        try:
            # Wait for delay
            for i in range(delay_seconds, 0, -1):
                if not self.is_shutdown_scheduled:
                    logger.info("Restart cancelled")
                    return
                    
                time.sleep(1)
                
                # Log countdown every 10 seconds
                if i % 10 == 0 or i <= 5:
                    logger.info(f"Restart in {i} seconds...")
                    
            # Execute restart
            self.restart(force=True)
            
        except Exception as e:
            logger.error(f"Error in restart worker: {e}")
        finally:
            self.is_shutdown_scheduled = False
            
    def cancel_scheduled_action(self) -> bool:
        """Cancel scheduled shutdown/restart"""
        try:
            if not self.is_shutdown_scheduled:
                logger.warning("No action scheduled to cancel")
                return False
                
            self.is_shutdown_scheduled = False
            
            # Cancel system shutdown (Windows)
            if os.name == 'nt':
                subprocess.run(['shutdown', '/a'], check=True)
                
            logger.info("Scheduled action cancelled")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelling scheduled action: {e}")
            return False
            
    def is_scheduled(self) -> bool:
        """Check if shutdown/restart is scheduled"""
        return self.is_shutdown_scheduled
        
    def get_power_state(self) -> str:
        """Get current power state"""
        try:
            import psutil
            battery = psutil.sensors_battery()
            
            if battery:
                if battery.power_plugged:
                    return "plugged_in"
                else:
                    return "on_battery"
            else:
                return "desktop"
                
        except ImportError:
            return "unknown"
        except Exception as e:
            logger.error(f"Error getting power state: {e}")
            return "unknown"
            
    def get_battery_info(self) -> dict:
        """Get battery information"""
        try:
            import psutil
            battery = psutil.sensors_battery()
            
            if battery:
                return {
                    "percent": battery.percent,
                    "plugged": battery.power_plugged,
                    "time_left": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None
                }
            else:
                return {}
                
        except ImportError:
            return {}
        except Exception as e:
            logger.error(f"Error getting battery info: {e}")
            return {}

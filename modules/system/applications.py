"""
Applications Module
Manages Windows applications (open, close, switch)
"""

import os
import logging
import subprocess
import time
from typing import Optional, List, Dict

try:
    import pygetwindow as gw
    import psutil
except ImportError:
    gw = None
    psutil = None
    logging.warning("pygetwindow or psutil not installed. Application control limited.")

from config import Config

logger = logging.getLogger(__name__)

class AppManager:
    """Manages Windows applications"""
    
    def __init__(self, config: Config):
        self.config = config
        self.app_aliases = self._load_app_aliases()
        
    def _load_app_aliases(self) -> Dict[str, str]:
        """Load application name aliases - to'liq yo'llar bilan"""
        appdata   = os.environ.get("APPDATA", "")
        localdata = os.environ.get("LOCALAPPDATA", "")
        progfiles = os.environ.get("ProgramFiles", "C:\\Program Files")
        progx86   = os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")

        return {
            # ── Brauzerlar ──
            "chrome":        f"{progfiles}\\Google\\Chrome\\Application\\chrome.exe",
            "хром":          f"{progfiles}\\Google\\Chrome\\Application\\chrome.exe",
            "google chrome": f"{progfiles}\\Google\\Chrome\\Application\\chrome.exe",
            "гугл хром":     f"{progfiles}\\Google\\Chrome\\Application\\chrome.exe",
            "firefox":       f"{progfiles}\\Mozilla Firefox\\firefox.exe",
            "фаерфокс":      f"{progfiles}\\Mozilla Firefox\\firefox.exe",
            "edge":          f"{progfiles}\\Microsoft\\Edge\\Application\\msedge.exe",
            "эдж":           f"{progfiles}\\Microsoft\\Edge\\Application\\msedge.exe",
            "opera":         f"{appdata}\\Opera Software\\Opera Stable\\opera.exe",
            "опера":         f"{appdata}\\Opera Software\\Opera Stable\\opera.exe",
            "yandex":        f"{localdata}\\Yandex\\YandexBrowser\\Application\\browser.exe",
            "яндекс":        f"{localdata}\\Yandex\\YandexBrowser\\Application\\browser.exe",

            # ── Messenjerlar ──
            "telegram":      f"{appdata}\\Telegram Desktop\\Telegram.exe",
            "телеграм":      f"{appdata}\\Telegram Desktop\\Telegram.exe",
            "телеграмм":     f"{appdata}\\Telegram Desktop\\Telegram.exe",
            "whatsapp":      f"{localdata}\\WhatsApp\\WhatsApp.exe",
            "ватсап":        f"{localdata}\\WhatsApp\\WhatsApp.exe",
            "discord":       f"{localdata}\\Discord\\Update.exe --processStart Discord.exe",
            "дискорд":       f"{localdata}\\Discord\\Update.exe --processStart Discord.exe",
            "skype":         f"{localdata}\\Microsoft\\Skype for Desktop\\Skype.exe",
            "скайп":         f"{localdata}\\Microsoft\\Skype for Desktop\\Skype.exe",
            "zoom":          f"{appdata}\\Zoom\\bin\\Zoom.exe",
            "зум":           f"{appdata}\\Zoom\\bin\\Zoom.exe",

            # ── Media ──
            "spotify":       f"{appdata}\\Spotify\\Spotify.exe",
            "спотифай":      f"{appdata}\\Spotify\\Spotify.exe",
            "vlc":           f"{progfiles}\\VideoLAN\\VLC\\vlc.exe",

            # ── Ofis ──
            "word":          f"{progfiles}\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
            "ворд":          f"{progfiles}\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
            "excel":         f"{progfiles}\\Microsoft Office\\root\\Office16\\EXCEL.EXE",
            "эксель":        f"{progfiles}\\Microsoft Office\\root\\Office16\\EXCEL.EXE",
            "powerpoint":    f"{progfiles}\\Microsoft Office\\root\\Office16\\POWERPNT.EXE",
            "outlook":       f"{progfiles}\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE",

            # ── Tizim (har doim mavjud) ──
            "notepad":       "notepad.exe",
            "блокнот":       "notepad.exe",
            "calculator":    "calc.exe",
            "калькулятор":   "calc.exe",
            "paint":         "mspaint.exe",
            "пейнт":         "mspaint.exe",
            "explorer":      "explorer.exe",
            "проводник":     "explorer.exe",
            "task manager":  "taskmgr.exe",
            "диспетчер задач": "taskmgr.exe",
            "cmd":           "cmd.exe",
            "командная строка": "cmd.exe",
            "powershell":    "powershell.exe",
            "vs code":       "code.exe",
            "visual studio code": "code.exe",
        }
        
    def open_app(self, app_name: str) -> bool:
        """Open an application"""
        if not app_name:
            return False
        try:
            normalized = app_name.lower().strip()

            # 1. To'g'ridan-to'g'ri alias
            exe_path = self.app_aliases.get(normalized)

            # 2. Fuzzy alias qidirish
            if not exe_path:
                from rapidfuzz import fuzz
                best_score, best_alias = 0, None
                for alias in self.app_aliases:
                    s = fuzz.partial_ratio(normalized, alias)
                    if s > best_score and s >= 75:
                        best_score, best_alias = s, alias
                if best_alias:
                    exe_path = self.app_aliases[best_alias]
                    logger.info(f"Fuzzy match: '{normalized}' -> '{best_alias}' ({best_score}%)")

            # 3. Fallback - to'g'ridan-to'g'ri nom bilan
            if not exe_path:
                exe_path = normalized if normalized.endswith(".exe") else normalized + ".exe"

            logger.info(f"Launching: {exe_path}")

            # Fayl mavjudligini tekshirish
            if os.path.isfile(exe_path):
                subprocess.Popen([exe_path])
            else:
                # shell=True bilan PATH dan qidirish
                subprocess.Popen(exe_path, shell=True)

            return True

        except Exception as e:
            logger.error(f"Error opening app '{app_name}': {e}")
            return False
            
    def close_app(self, app_name: str) -> bool:
        """Close an application"""
        if gw is None or psutil is None:
            logger.error("pygetwindow or psutil not available")
            return False
            
        try:
            # Normalize app name
            normalized_name = app_name.lower().strip()
            
            # Get windows matching the app name
            windows = self._find_app_windows(normalized_name)
            
            if not windows:
                logger.warning(f"No windows found for: {app_name}")
                return False
                
            # Close all matching windows
            closed_count = 0
            for window in windows:
                try:
                    if window.title:
                        window.close()
                        closed_count += 1
                        time.sleep(0.5)  # Give time for window to close
                except Exception as e:
                    logger.error(f"Error closing window {window.title}: {e}")
                    
            if closed_count > 0:
                logger.info(f"Closed {closed_count} windows for: {app_name}")
                return True
            else:
                logger.warning(f"No windows closed for: {app_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error closing app {app_name}: {e}")
            return False
            
    def switch_to_app(self, app_name: str) -> bool:
        """Switch to an application"""
        if gw is None:
            logger.error("pygetwindow not available")
            return False
            
        try:
            # Normalize app name
            normalized_name = app_name.lower().strip()
            
            # Get windows matching the app name
            windows = self._find_app_windows(normalized_name)
            
            if not windows:
                logger.warning(f"No windows found for: {app_name}")
                return False
                
            # Switch to first matching window
            window = windows[0]
            try:
                window.restore()
                window.activate()
                logger.info(f"Switched to: {app_name}")
                return True
            except Exception as e:
                logger.error(f"Error switching to window {window.title}: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error switching to app {app_name}: {e}")
            return False
            
    def get_running_apps(self) -> List[Dict]:
        """Get list of running applications"""
        if gw is None:
            return []
            
        try:
            apps = []
            windows = gw.getAllWindows()
            
            for window in windows:
                if window.title and not window.title.isspace():
                    apps.append({
                        'title': window.title,
                        'process': self._get_window_process(window),
                        'left': window.left,
                        'top': window.top,
                        'width': window.width,
                        'height': window.height,
                        'visible': window.visible
                    })
                    
            return apps
            
        except Exception as e:
            logger.error(f"Error getting running apps: {e}")
            return []
            
    def _find_executable(self, app_name: str) -> Optional[str]:
        """Find executable for application name"""
        try:
            # Common paths to search
            search_paths = [
                os.path.join(os.environ.get('ProgramFiles', 'C:\\Program Files'), ''),
                os.path.join(os.environ.get('ProgramFiles(x86)', 'C:\\Program Files (x86)'), ''),
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs'),
                os.path.join(os.environ.get('APPDATA', ''), 'Microsoft\\Windows\\Start Menu\\Programs'),
                'C:\\Windows\\System32'
            ]
            
            # Try to find .exe file
            for path in search_paths:
                if not os.path.exists(path):
                    continue
                    
                for root, dirs, files in os.walk(path):
                    for file in files:
                        if file.lower().endswith('.exe'):
                            file_lower = file.lower()
                            app_lower = app_name.lower()
                            
                            # Check for exact match
                            if app_lower in file_lower:
                                return os.path.join(root, file)
                                
            return None
            
        except Exception as e:
            logger.error(f"Error finding executable: {e}")
            return None
            
    def _launch_executable(self, exe_name: str) -> bool:
        """Launch executable by name"""
        try:
            # Try to launch directly
            subprocess.Popen([exe_name], shell=True)
            return True
            
        except FileNotFoundError:
            # Try to find in PATH
            try:
                subprocess.Popen([exe_name], shell=False)
                return True
            except FileNotFoundError:
                logger.error(f"Executable not found: {exe_name}")
                return False
        except Exception as e:
            logger.error(f"Error launching {exe_name}: {e}")
            return False
            
    def _find_app_windows(self, app_name: str) -> List:
        """Find windows matching app name"""
        if gw is None:
            return []
            
        try:
            windows = gw.getAllWindows()
            matching_windows = []
            
            # Check aliases
            exe_name = self.app_aliases.get(app_name, app_name)
            
            for window in windows:
                if not window.title:
                    continue
                    
                # Check if window title contains app name
                title_lower = window.title.lower()
                if (app_name in title_lower or 
                    exe_name.replace('.exe', '') in title_lower):
                    matching_windows.append(window)
                    
            return matching_windows
            
        except Exception as e:
            logger.error(f"Error finding app windows: {e}")
            return []
            
    def _get_window_process(self, window) -> str:
        """Get process name for window"""
        try:
            if psutil is None:
                return ""
                
            # Find process by window title (approximate)
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    # This is a simplified approach
                    if proc.info['name']:
                        proc_name = proc.info['name'].lower()
                        window_title = window.title.lower()
                        
                        # Check if process name is in window title or vice versa
                        if (proc_name in window_title or 
                            any(word in proc_name for word in window_title.split())):
                            return proc.info['name']
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
            return ""
            
        except Exception as e:
            logger.error(f"Error getting window process: {e}")
            return ""
            
    def is_app_running(self, app_name: str) -> bool:
        """Check if application is running"""
        windows = self._find_app_windows(app_name)
        return len(windows) > 0
        
    def get_app_info(self, app_name: str) -> Optional[Dict]:
        """Get detailed information about an application"""
        windows = self._find_app_windows(app_name)
        
        if not windows:
            return None
            
        window = windows[0]
        return {
            'name': app_name,
            'title': window.title,
            'process': self._get_window_process(window),
            'position': (window.left, window.top),
            'size': (window.width, window.height),
            'visible': window.visible,
            'minimized': window.isMinimized if hasattr(window, 'isMinimized') else False
        }
        
    def add_app_alias(self, alias: str, exe_name: str):
        """Add new application alias"""
        self.app_aliases[alias.lower()] = exe_name
        logger.info(f"Added app alias: {alias} -> {exe_name}")
        
    def is_available(self) -> bool:
        """Check if application management is available"""
        return gw is not None

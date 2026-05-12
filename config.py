"""
GHOST Configuration Module
Handles all configuration settings
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class AudioConfig:
    """Audio configuration settings"""
    sample_rate: int = 16000
    chunk_size: int = 1024
    channels: int = 1
    format: str = "int16"
    
@dataclass
class WakeWordConfig:
    """Wake word detection settings"""
    keyword: str = "hey_jarvis"   # hey_jarvis | alexa | hey_mycroft | hey_rhasspy
    sensitivity: float = 0.35     # past = tezroq aniqlaydi
    access_key: Optional[str] = None
    
@dataclass
class STTConfig:
    """Speech-to-Text configuration"""
    engine: str = "faster_whisper"  # faster_whisper, vosk
    model_size: str = "base"  # tiny, base, small, medium, large
    language: str = "ru"   # ru yaxshiroq taniydi (o'zbek so'zlarini ham)
    timeout: int = 5
    
@dataclass
class TTSConfig:
    """Text-to-Speech configuration"""
    engine: str = "edge_tts"
    voice: str = "ru-RU-SvetlanaNeural"   # rus tili
    rate: float = 1.0
    volume: float = 0.9
    
@dataclass
class GUIConfig:
    """GUI configuration settings"""
    width: int = 600
    height: int = 120
    opacity: float = 0.85
    animation_duration: int = 300
    theme: str = "dark"
    
@dataclass
class TelegramConfig:
    """Telegram integration settings"""
    token: Optional[str] = None
    enabled: bool = False
    
@dataclass
class SecurityConfig:
    """Security settings"""
    confirm_dangerous_actions: bool = True
    max_voice_profiles: int = 10
    log_sensitive_data: bool = False

@dataclass
class GroqConfig:
    """Groq AI settings"""
    enabled: bool = True
    model: str = "llama-3.3-70b-versatile"
    temperature: float = 0.3
    max_tokens: int = 300

class Config:
    """Main configuration manager"""
    
    def __init__(self, config_file: str = "data/config.json"):
        self.config_file = Path(config_file)
        self.data_dir = Path("data")
        
        # Initialize configurations
        self.audio = AudioConfig()
        self.wake_word = WakeWordConfig(
            access_key=os.getenv("PICOVOICE_ACCESS_KEY")
        )
        self.stt = STTConfig()
        self.tts = TTSConfig()
        self.gui = GUIConfig()
        self.telegram = TelegramConfig(
            token=os.getenv("TELEGRAM_BOT_TOKEN")
        )
        self.security = SecurityConfig()
        self.groq = GroqConfig()
        
        # Load configuration
        self.load()
        
    def load(self):
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Update configurations
                if 'audio' in data:
                    self.audio = AudioConfig(**data['audio'])
                if 'wake_word' in data:
                    self.wake_word = WakeWordConfig(**data['wake_word'])
                if 'stt' in data:
                    self.stt = STTConfig(**data['stt'])
                if 'tts' in data:
                    self.tts = TTSConfig(**data['tts'])
                if 'gui' in data:
                    self.gui = GUIConfig(**data['gui'])
                if 'telegram' in data:
                    self.telegram = TelegramConfig(**data['telegram'])
                if 'security' in data:
                    self.security = SecurityConfig(**data['security'])
                    
                print(f"Configuration loaded from {self.config_file}")
            else:
                print("No configuration file found, using defaults")
                
        except Exception as e:
            print(f"Error loading configuration: {e}")
            
    def save(self):
        """Save configuration to file"""
        try:
            # Ensure data directory exists
            self.data_dir.mkdir(exist_ok=True)
            
            # Prepare configuration data
            config_data = {
                'audio': asdict(self.audio),
                'wake_word': asdict(self.wake_word),
                'stt': asdict(self.stt),
                'tts': asdict(self.tts),
                'gui': asdict(self.gui),
                'telegram': asdict(self.telegram),
                'security': asdict(self.security)
            }
            
            # Save to file
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
                
            print(f"Configuration saved to {self.config_file}")
            
        except Exception as e:
            print(f"Error saving configuration: {e}")
            
    def get_intents_file(self, language: str) -> str:
        """Get intents file path for language"""
        return f"data/intents_{language}.json"
        
    def get_voice_profiles_dir(self) -> Path:
        """Get voice profiles directory"""
        return self.data_dir / "voice_profiles"
        
    def get_logs_dir(self) -> Path:
        """Get logs directory"""
        return Path("logs")
        
    def is_debug_mode(self) -> bool:
        """Check if debug mode is enabled"""
        return os.getenv("GHOST_DEBUG", "false").lower() == "true"

# Global configuration instance
config = Config()

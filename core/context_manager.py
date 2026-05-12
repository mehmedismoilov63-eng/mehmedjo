"""
Context Manager Module
Manages conversation context and history
"""

import logging
from typing import List, Dict, Any, Optional
from collections import deque
import json
import os
import time

logger = logging.getLogger(__name__)

class ContextManager:
    """Manages conversation context and command history"""
    
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self.command_history = deque(maxlen=max_history)
        self.context_data = {}
        
    def add_command(self, command: str, intent: Dict[str, Any] = None):
        """Add command to history"""
        timestamp = time.time()
        
        entry = {
            "command": command,
            "intent": intent,
            "timestamp": timestamp
        }
        
        self.command_history.append(entry)
        logger.info(f"Added command to context: {command}")
        
    def get_recent_commands(self, count: int = 3) -> List[Dict[str, Any]]:
        """Get recent commands from history"""
        return list(self.command_history)[-count:]
        
    def get_last_command(self) -> Optional[Dict[str, Any]]:
        """Get the last command"""
        if self.command_history:
            return self.command_history[-1]
        return None
        
    def get_context_for_intent(self) -> Dict[str, Any]:
        """Get context data for intent parsing"""
        recent_commands = self.get_recent_commands(3)
        
        context = {
            "recent_commands": [cmd["command"] for cmd in recent_commands],
            "recent_intents": [cmd["intent"] for cmd in recent_commands if cmd["intent"]],
            "command_count": len(self.command_history)
        }
        
        return context
        
    def set_context_data(self, key: str, value: Any):
        """Set context data"""
        self.context_data[key] = value
        
    def get_context_data(self, key: str, default: Any = None) -> Any:
        """Get context data"""
        return self.context_data.get(key, default)
        
    def clear_history(self):
        """Clear command history"""
        self.command_history.clear()
        logger.info("Command history cleared")
        
    def save_context(self, file_path: str):
        """Save context to file"""
        try:
            context_data = {
                "command_history": list(self.command_history),
                "context_data": self.context_data
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(context_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Context saved to {file_path}")
            
        except Exception as e:
            logger.error(f"Error saving context: {e}")
            
    def load_context(self, file_path: str):
        """Load context from file"""
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    context_data = json.load(f)
                    
                self.command_history = deque(
                    context_data.get("command_history", []), 
                    maxlen=self.max_history
                )
                self.context_data = context_data.get("context_data", {})
                
                logger.info(f"Context loaded from {file_path}")
            else:
                logger.info(f"Context file not found: {file_path}")
                
        except Exception as e:
            logger.error(f"Error loading context: {e}")

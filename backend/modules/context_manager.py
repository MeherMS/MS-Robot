# modules/context_manager.py
from typing import List, Dict

class ContextManager:
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self.history: List[Dict] = []
    
    def add_message(self, role: str, content: str):
        """Add user or assistant message"""
        self.history.append({"role": role, "content": content})
        
        # Keep only recent messages
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_history(self) -> List[Dict]:
        """Return conversation history"""
        return self.history
    
    def get_context_string(self) -> str:
        """Format history as string for LLM context"""
        context = ""
        for msg in self.history:
            role = "User" if msg["role"] == "user" else "MSRobot"
            context += f"{role}: {msg['content']}\n"
        return context
    
    def clear(self):
        """Clear history"""
        self.history = []
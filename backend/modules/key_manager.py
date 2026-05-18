# backend/modules/key_manager.py

from config import GEMINI_API_KEYS
from typing import Optional


class KeyManager:
    """
    Manages multiple Gemini API keys with round-robin rotation
    
    Tracks:
    - Current key index (for round-robin)
    - Failed keys (quota exceeded)
    - Log key switches
    """
    
    def __init__(self):
        """Initialize KeyManager with keys from config"""
        self.keys = GEMINI_API_KEYS
        self.total_keys = len(self.keys)
        self.current_index = 0
        self.exhausted_keys = set()  # Track which keys hit quota
        
        print(f"[KeyManager] ✅ Initialized with {self.total_keys} API key(s)")
    
    def get_current_key(self) -> str:
        """
        Get current API key (round-robin)
        
        Returns:
            Current API key string
        """
        key = self.keys[self.current_index]
        key_num = self.current_index + 1
        print(f"[KeyManager] 🔑 Using key {key_num}/{self.total_keys}")
        return key
    
    def switch_to_next_key(self) -> Optional[str]:
        """
        Switch to next key in round-robin
        Skips keys that have already hit quota
        
        Returns:
            Next available key, or None if all keys exhausted
        """
        # Move to next index
        self.current_index = (self.current_index + 1) % self.total_keys
        
        # Count how many keys are available
        available_keys = self.total_keys - len(self.exhausted_keys)
        
        if available_keys <= 0:
            print(f"[KeyManager] ❌ All {self.total_keys} API keys exhausted!")
            return None
        
        # If current key is exhausted, skip to next available
        while self.current_index in self.exhausted_keys:
            self.current_index = (self.current_index + 1) % self.total_keys
        
        key = self.keys[self.current_index]
        key_num = self.current_index + 1
        print(f"[KeyManager] 🔄 Switched to key {key_num}/{self.total_keys} (available: {available_keys}/{self.total_keys})")
        return key
    
    def mark_key_exhausted(self) -> None:
        """
        Mark current key as quota exhausted
        Called when receiving 429 error
        """
        self.exhausted_keys.add(self.current_index)
        key_num = self.current_index + 1
        print(f"[KeyManager] ⚠️  Key {key_num}/{self.total_keys} quota exceeded. Marking as exhausted.")
    
    def get_status(self) -> dict:
        """
        Get current status of all keys
        
        Returns:
            Dict with key stats
        """
        available = self.total_keys - len(self.exhausted_keys)
        return {
            "total_keys": self.total_keys,
            "available_keys": available,
            "exhausted_keys": list(self.exhausted_keys),
            "current_index": self.current_index,
            "current_key_num": self.current_index + 1,
        }
    
    def reset(self) -> None:
        """
        Reset all keys (use with caution - assumes quota has reset)
        """
        self.exhausted_keys.clear()
        self.current_index = 0
        print(f"[KeyManager] 🔄 Reset all keys. Starting from key 1/{self.total_keys}")


# Singleton instance
key_manager = KeyManager()
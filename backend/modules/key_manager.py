# backend/modules/key_manager.py

#from config import GEMINI_API_KEYS
from config import GROQ_API_KEYS
from typing import Optional, Tuple
from datetime import datetime, timedelta


class KeyManager:
    """
    Manages multiple Gemini API keys with smart error handling.
    
    Tracks:
    - Current key index (round-robin)
    - Key states: available, in_cooldown, daily_quota_exhausted
    - Cooldown timestamps (70 sec for RPM errors)
    - Permanent exhaustion (until midnight for daily quota)
    """
    
    def __init__(self):
        """Initialize KeyManager with keys from config"""
        self.keys = GROQ_API_KEYS
        self.total_keys = len(self.keys)
        self.current_index = 0
        
        # Track state of each key: {key_index: "available" | "cooldown" | "daily_exhausted"}
        self.key_states = {i: "available" for i in range(self.total_keys)}
        
        # Track when cooldown started: {key_index: datetime}
        self.cooldown_timestamps = {}
        
        print(f"[KeyManager] ✅ Initialized with {self.total_keys} API key(s)")
        for i in range(self.total_keys):
            print(f"            Key {i+1}: Available")
    
    def _get_available_keys(self) -> list:
        """Get list of currently available key indices (not in cooldown, not daily exhausted)"""
        available = []
        now = datetime.utcnow()
        
        for i in range(self.total_keys):
            state = self.key_states[i]
            
            # Skip permanently exhausted
            if state == "daily_exhausted":
                continue
            
            # Check if cooldown expired
            if state == "cooldown":
                cooldown_start = self.cooldown_timestamps.get(i)
                if cooldown_start and (now - cooldown_start).total_seconds() < 70:
                    # Still in cooldown
                    continue
                else:
                    # Cooldown expired, mark available
                    self.key_states[i] = "available"
                    del self.cooldown_timestamps[i]
                    print(f"[KeyManager] ✅ Key {i+1} cooldown expired, back online")
            
            # At this point, state is "available"
            available.append(i)
        
        return available
    
    def get_current_key(self) -> Tuple[str, int]:
        """
        Get current API key (round-robin rotation).
        Auto-skips keys in cooldown or exhausted.
        
        Returns:
            (key_string, key_number_1indexed)
        """
        available = self._get_available_keys()
        
        if not available:
            # All keys unavailable
            return None, 0
        
        # Find next available key starting from current_index
        for i in range(self.total_keys):
            candidate = (self.current_index + i) % self.total_keys
            if candidate in available:
                self.current_index = candidate
                key_num = self.current_index + 1
                print(f"[KeyManager] 🔑 Using key {key_num}/{self.total_keys}")
                return self.keys[self.current_index], key_num
        
        # Should not reach here
        return None, 0
    
    def mark_key_with_error(self, error_type: str) -> None:
        """
        Mark current key based on error type.
        
        Args:
            error_type: "rpm_limit" (temporary) | "daily_quota" (permanent) | "other"
        """
        key_num = self.current_index + 1
        
        if error_type == "rpm_limit":
            # Temporary: RPM limit, cooldown for 70 seconds
            self.key_states[self.current_index] = "cooldown"
            self.cooldown_timestamps[self.current_index] = datetime.utcnow()
            print(f"[KeyManager] ⏱️  Key {key_num} rate-limited. Cooling down 70 seconds...")
            
        elif error_type == "daily_quota":
            # Permanent: Daily quota exhausted until midnight
            self.key_states[self.current_index] = "daily_exhausted"
            midnight_utc = (datetime.utcnow() + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            time_until_reset = (midnight_utc - datetime.utcnow()).total_seconds() / 3600
            print(f"[KeyManager] 📅 Key {key_num} daily quota exhausted. Resets in {time_until_reset:.1f} hours.")
            
        else:
            # Other error: don't mark as failed, just log
            print(f"[KeyManager] ⚠️  Key {key_num} had error: {error_type}")
    
    def get_status(self) -> dict:
        """
        Get current status of all keys and cooldowns.
        
        Returns:
            Dict with detailed status
        """
        self._get_available_keys()  # Refresh cooldown states
        
        available = [i for i in range(self.total_keys) if self.key_states[i] == "available"]
        cooldown = [i for i in range(self.total_keys) if self.key_states[i] == "cooldown"]
        exhausted = [i for i in range(self.total_keys) if self.key_states[i] == "daily_exhausted"]
        
        status_breakdown = []
        for i in range(self.total_keys):
            key_num = i + 1
            state = self.key_states[i]
            
            if state == "available":
                status_breakdown.append(f"Key {key_num}: ✅ Available")
            elif state == "cooldown":
                cooldown_start = self.cooldown_timestamps.get(i)
                elapsed = (datetime.utcnow() - cooldown_start).total_seconds()
                remaining = max(0, 70 - elapsed)
                status_breakdown.append(f"Key {key_num}: ⏱️  Cooldown ({remaining:.0f}s remaining)")
            elif state == "daily_exhausted":
                status_breakdown.append(f"Key {key_num}: 📅 Daily quota exhausted (until midnight UTC)")
        
        return {
            "total_keys": self.total_keys,
            "available_keys": len(available),
            "keys_in_cooldown": len(cooldown),
            "keys_daily_exhausted": len(exhausted),
            "current_key_num": self.current_index + 1,
            "breakdown": status_breakdown,
        }
    
    def reset(self) -> None:
        """Reset all keys (use when daily quota resets at midnight)"""
        self.key_states = {i: "available" for i in range(self.total_keys)}
        self.cooldown_timestamps = {}
        self.current_index = 0
        print(f"[KeyManager] 🔄 Reset all keys. Starting fresh.")


# Singleton instance
key_manager = KeyManager()
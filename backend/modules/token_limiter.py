# backend/modules/token_limiter.py

from datetime import datetime, timedelta
from typing import Dict, Tuple
import threading

class TokenLimiter:
    """
    IP-based daily message limiter with soft limits.
    
    - Hard limit: 100 messages per day
    - Soft warning: 80 messages per day
    - Resets daily at midnight UTC
    """

    def __init__(self, daily_limit: int = 100):
        self.daily_limit = daily_limit
        self.warning_threshold = int(daily_limit * 0.8)  # 80 messages
        
        # Store: {ip_address: {date: YYYY-MM-DD, count: int}}
        self.usage: Dict[str, Dict] = {}
        self._lock = threading.Lock()  # Thread-safe
        # Store request timestamps for burst limiting: {ip: [timestamp1, timestamp2, ...]}
        self.burst_timestamps: Dict[str, list] = {}

    def _get_today(self) -> str:
        """Get today's date as string (YYYY-MM-DD)"""
        return datetime.utcnow().strftime("%Y-%m-%d")

    def check_and_increment(self, ip_address: str) -> dict:
        """
        Check if IP has quota remaining, and increment usage.
        
        Returns:
            {
                "allowed": bool,           # Can user send message?
                "count": int,              # Messages used today
                "limit": int,              # Daily limit
                "remaining": int,          # Messages left
                "status": str,             # "ok" | "warning" | "limit_reached"
                "reset_time": str,         # When limit resets (ISO format)
                "message": str             # Human-readable status
            }
        """
        today = self._get_today()

        with self._lock:
            # Initialize if new IP
            if ip_address not in self.usage:
                self.usage[ip_address] = {"date": today, "count": 0}

            # Reset if it's a new day
            if self.usage[ip_address]["date"] != today:
                self.usage[ip_address] = {"date": today, "count": 0}

            current_count = self.usage[ip_address]["count"]

            # Check if limit reached (HARD LIMIT)
            if current_count >= self.daily_limit:
                return {
                    "allowed": False,
                    "count": current_count,
                    "limit": self.daily_limit,
                    "remaining": 0,
                    "status": "limit_reached",
                    "reset_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                    "message": f"⚠️ Daily limit reached ({self.daily_limit} messages). Resets at midnight UTC.",
                }

            # Increment count
            self.usage[ip_address]["count"] += 1
            new_count = self.usage[ip_address]["count"]
            remaining = self.daily_limit - new_count

            # Check if warning threshold reached (SOFT LIMIT)
            if new_count >= self.warning_threshold:
                return {
                    "allowed": True,
                    "count": new_count,
                    "limit": self.daily_limit,
                    "remaining": remaining,
                    "status": "warning",
                    "reset_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                    "message": f"⚠️ You have {remaining} messages remaining today.",
                }

            # Normal case (plenty of quota)
            return {
                "allowed": True,
                "count": new_count,
                "limit": self.daily_limit,
                "remaining": remaining,
                "status": "ok",
                "reset_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "message": None,  # No warning needed
            }

    def get_status(self, ip_address: str) -> dict:
        """Check status without incrementing"""
        today = self._get_today()

        with self._lock:
            if ip_address not in self.usage:
                return {
                    "count": 0,
                    "limit": self.daily_limit,
                    "remaining": self.daily_limit,
                    "reset_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                }

            if self.usage[ip_address]["date"] != today:
                return {
                    "count": 0,
                    "limit": self.daily_limit,
                    "remaining": self.daily_limit,
                    "reset_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                }

            count = self.usage[ip_address]["count"]
            return {
                "count": count,
                "limit": self.daily_limit,
                "remaining": self.daily_limit - count,
                "reset_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            }
            
    def check_burst_limit(self, ip_address: str, max_requests: int = 10, window_seconds: int = 60) -> Tuple[bool, str]:
        """
        Check if IP exceeded burst limit (e.g., 10 msgs per 60 seconds).
        
        Returns:
            (is_allowed, status_message)
        """
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)

        with self._lock:
            # Initialize if new IP
            if ip_address not in self.burst_timestamps:
                self.burst_timestamps[ip_address] = []

            # Clean old timestamps (older than window)
            self.burst_timestamps[ip_address] = [
                ts for ts in self.burst_timestamps[ip_address]
                if ts > window_start
            ]

            # Get current count in window
            current_count = len(self.burst_timestamps[ip_address])

            # If at limit, reject
            if current_count >= max_requests:
                return False, f"Rate limit: max {max_requests} messages per {window_seconds} seconds. Wait before retrying."

            # Add current timestamp
            self.burst_timestamps[ip_address].append(now)
            new_count = current_count + 1

            return True, f"Ok ({new_count}/{max_requests} in last minute)"

# Singleton instance (shared across requests)
token_limiter = TokenLimiter(daily_limit=100)
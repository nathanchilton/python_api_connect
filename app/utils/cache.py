"""
Cache manager for storing frequently accessed data in memory
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import threading
from dataclasses import dataclass


@dataclass
class CacheEntry:
    """Represents a cached item with timestamp"""
    data: Any
    timestamp: datetime
    expires_at: datetime

    def is_expired(self) -> bool:
        """Check if the cache entry has expired"""
        return datetime.now() > self.expires_at


class MemoryCache:
    """Thread-safe in-memory cache with expiration"""

    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if it exists and hasn't expired"""
        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                return None

            return entry.data

    def set(self, key: str, value: Any, ttl_seconds: int = 10) -> None:
        """Set value in cache with time-to-live"""
        with self._lock:
            expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
            self._cache[key] = CacheEntry(
                data=value,
                timestamp=datetime.now(),
                expires_at=expires_at
            )

    def invalidate(self, key: str) -> None:
        """Remove specific key from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self) -> None:
        """Clear all cache entries"""
        with self._lock:
            self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_entries = len(self._cache)
            expired_entries = sum(1 for entry in self._cache.values() if entry.is_expired())
            return {
                "total_entries": total_entries,
                "expired_entries": expired_entries,
                "active_entries": total_entries - expired_entries
            }


# Global cache instance
cache = MemoryCache()

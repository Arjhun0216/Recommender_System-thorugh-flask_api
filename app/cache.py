# app/cache.py
import heapq
import time
from collections import OrderedDict


# ═══════════════════════════════════════════════════
# DATA STRUCTURE 1 — LRU Cache
#
# LRU = Least Recently Used
# Stores the last N computed results in memory.
# When cache is full, evicts the least recently
# used entry first.
#
# Built on: OrderedDict (maintains insertion order)
# Time complexity:
#   get()  → O(1)
#   put()  → O(1)
#   evict  → O(1)
# ═══════════════════════════════════════════════════

class LRUCache:
    """
    Generic LRU Cache.
    Use it to cache recommendation results, API key
    lookups, or any expensive computation.

    Example:
        cache = LRUCache(capacity=100, ttl=300)
        cache.put("user_123", [rec1, rec2, rec3])
        result = cache.get("user_123")  # instant
    """

    def __init__(self, capacity: int = 100, ttl: int = 300):
        """
        capacity — max number of entries to store
        ttl      — time to live in seconds (default 5 min)
                   after this time the entry is considered stale
        """
        self.capacity  = capacity
        self.ttl       = ttl
        self.cache     = OrderedDict()  # key → (value, timestamp)

    def get(self, key: str):
        """
        Retrieve a value by key.
        Returns None if key not found or entry expired.
        Moves accessed key to end (most recently used).
        """
        if key not in self.cache:
            return None

        value, timestamp = self.cache[key]

        # Check if entry has expired
        if time.time() - timestamp > self.ttl:
            del self.cache[key]
            return None

        # Move to end — mark as most recently used
        self.cache.move_to_end(key)
        return value

    def put(self, key: str, value) -> None:
        """
        Store a value.
        If key exists, update it.
        If cache is full, evict least recently used entry.
        """
        if key in self.cache:
            self.cache.move_to_end(key)

        self.cache[key] = (value, time.time())

        # Evict least recently used if over capacity
        # OrderedDict.popitem(last=False) removes
        # the FIRST item (least recently used)
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

    def invalidate(self, key: str) -> None:
        """Remove a specific entry — call this when data changes."""
        if key in self.cache:
            del self.cache[key]

    def invalidate_prefix(self, prefix: str) -> None:
        """
        Remove all entries whose key starts with prefix.
        Use this to clear all cached data for one developer:
            cache.invalidate_prefix("rec_abc123:")
        """
        keys_to_delete = [k for k in self.cache if k.startswith(prefix)]
        for key in keys_to_delete:
            del self.cache[key]

    def __len__(self):
        return len(self.cache)

    def __repr__(self):
        return f"<LRUCache size={len(self.cache)}/{self.capacity}>"


# ═══════════════════════════════════════════════════
# DATA STRUCTURE 2 — Hash Set for Duplicate Detection
#
# Tracks recently seen interactions to prevent
# the same action inflating recommendation scores.
#
# Built on: Python set (hash table internally)
# Time complexity:
#   add()      → O(1)
#   contains() → O(1)
# ═══════════════════════════════════════════════════

class InteractionDeduplicator:
    """
    Prevents the same user-item-action combination
    from being counted multiple times within a
    short window (default 1 hour).

    Example:
        dedup = InteractionDeduplicator(window=3600)
        dedup.is_duplicate("rec_abc", "user_1", "item_1", "view")
        → False (first time)
        dedup.is_duplicate("rec_abc", "user_1", "item_1", "view")
        → True  (duplicate within window)
    """

    def __init__(self, window: int = 3600):
        """
        window — seconds within which same interaction
                 is considered a duplicate (default 1 hour)
        """
        self.window = window
        # Hash set stores (key, timestamp) tuples
        # key = "api_key:user_id:item_id:action"
        self._seen: dict = {}

    def is_duplicate(self, api_key: str, user_id: str,
                     item_id: str, action: str) -> bool:
        """
        Returns True if this exact interaction was
        seen within the time window.
        """
        key = f"{api_key}:{user_id}:{item_id}:{action}"
        now = time.time()

        if key in self._seen:
            last_seen = self._seen[key]
            if now - last_seen < self.window:
                return True  # duplicate

        # Not a duplicate — record it
        self._seen[key] = now
        return False

    def cleanup(self) -> int:
        """
        Remove expired entries to free memory.
        Call this periodically.
        Returns number of entries removed.
        """
        now = time.time()
        expired = [k for k, t in self._seen.items()
                   if now - t >= self.window]
        for key in expired:
            del self._seen[key]
        return len(expired)

    def __len__(self):
        return len(self._seen)


# ═══════════════════════════════════════════════════
# DATA STRUCTURE 3 — Min Heap for Top-N Selection
#
# Finds the top N highest scoring items without
# sorting the entire list.
#
# Built on: Python heapq (binary min heap)
# Time complexity:
#   get_top_n() → O(n log k) vs O(n log n) for sort
#   where k = number of results wanted (e.g. 10)
#   Much faster when n is large (100,000+ items)
# ═══════════════════════════════════════════════════

def get_top_n(scores: dict, n: int) -> list:
    """
    Returns the top N items by score using a min heap.
    Faster than sorting when N is much smaller than
    total number of items.

    Args:
        scores — dict of {item_id: score}
        n      — how many top items to return

    Returns:
        list of (item_id, score) sorted by score desc

    How the min heap works:
        We maintain a heap of size N.
        For each item:
            if heap has < N items → push it
            if item score > heap minimum → replace minimum
        At the end, heap contains the N highest scores.
        We never sort more than N items.
    """
    if not scores:
        return []

    # heapq is a min heap — smallest value at top
    # We store (score, item_id) so heap orders by score
    heap = []

    for item_id, score in scores.items():
        if len(heap) < n:
            # Heap not full yet — just push
            heapq.heappush(heap, (score, item_id))
        elif score > heap[0][0]:
            # New score beats current minimum
            # Replace the minimum with this item
            heapq.heapreplace(heap, (score, item_id))

    # Sort descending by score for final output
    return sorted(heap, key=lambda x: x[0], reverse=True)


# ═══════════════════════════════════════════════════
# DATA STRUCTURE 4 — API Key Hash Map Cache
#
# Caches developer objects by api_key so we don't
# hit the database on every single request.
#
# Built on: LRUCache above
# Time complexity:
#   lookup → O(1) for cached keys
#             O(db query) for first lookup only
# ═══════════════════════════════════════════════════

class APIKeyCache:
    """
    Caches validated API keys in memory.
    First request for a key hits the database.
    All subsequent requests are served from memory.

    TTL of 5 minutes — if a developer's key is
    deleted or regenerated, cache clears within 5 min.
    """

    def __init__(self):
        # capacity=500 — store up to 500 developer keys
        # ttl=300      — refresh every 5 minutes
        self._cache = LRUCache(capacity=500, ttl=300)

    def get(self, api_key: str):
        """Returns cached developer or None."""
        return self._cache.get(api_key)

    def set(self, api_key: str, developer) -> None:
        """Cache a developer object."""
        self._cache.put(api_key, developer)

    def invalidate(self, api_key: str) -> None:
        """Call this when a developer regenerates their key."""
        self._cache.invalidate(api_key)

    def __repr__(self):
        return f"<APIKeyCache {self._cache}>"


# ═══════════════════════════════════════════════════
# Global instances — shared across the entire app
# Created once when the module is first imported
# ═══════════════════════════════════════════════════

# Caches recommendation results per user per developer
# Key format: "api_key:user_id"
recommendation_cache = LRUCache(capacity=1000, ttl=300)

# Caches validated API keys
api_key_cache = APIKeyCache()

# Detects duplicate interactions within 1 hour
interaction_deduplicator = InteractionDeduplicator(window=3600)
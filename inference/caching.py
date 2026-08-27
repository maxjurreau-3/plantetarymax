"""
Inference Caching Layer
Rebuild 3: Performance Optimization

Caches inference results to avoid recomputation.
Uses LRU + semantic similarity for smart caching.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from collections import OrderedDict
import hashlib
import time


@dataclass
class CachedInference:
    """A cached inference result"""
    key: str
    query: Dict[str, Any]
    result: Any
    timestamp: float
    hit_count: int = 0
    ttl_seconds: int = 3600
    
    def is_expired(self) -> bool:
        """Check if cache entry expired"""
        return time.time() - self.timestamp > self.ttl_seconds


class InferenceCache:
    """
    LRU cache for inference results.
    Automatically evicts oldest/least-used entries.
    """
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        self.cache: OrderedDict[str, CachedInference] = OrderedDict()
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.hits = 0
        self.misses = 0
    
    def get(self, query: Dict[str, Any]) -> Optional[Any]:
        """
        Get cached result for query.
        Returns None if not cached or expired.
        """
        key = self._query_key(query)
        
        if key not in self.cache:
            self.misses += 1
            return None
        
        cached = self.cache[key]
        if cached.is_expired():
            del self.cache[key]
            self.misses += 1
            return None
        
        # Move to end (LRU)
        self.cache.move_to_end(key)
        cached.hit_count += 1
        self.hits += 1
        
        return cached.result
    
    def set(self, query: Dict[str, Any], result: Any, ttl: Optional[int] = None) -> None:
        """
        Cache an inference result.
        """
        key = self._query_key(query)
        
        # Evict oldest if at capacity
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)
        
        cached = CachedInference(
            key=key,
            query=query,
            result=result,
            timestamp=time.time(),
            ttl_seconds=ttl or self.ttl_seconds,
        )
        
        self.cache[key] = cached
    
    def clear(self) -> None:
        """Clear entire cache"""
        self.cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
        }
    
    def _query_key(self, query: Dict[str, Any]) -> str:
        """Generate cache key from query"""
        query_str = str(sorted(query.items()))
        return hashlib.md5(query_str.encode()).hexdigest()


class SemanticCache:
    """
    Semantic similarity-based caching.
    Matches queries that are similar in meaning, not just identical.
    """
    
    def __init__(self, similarity_threshold: float = 0.8):
        self.entries: List[CachedInference] = []
        self.threshold = similarity_threshold
    
    def find_similar(self, query: Dict[str, Any]) -> Optional[Any]:
        """
        Find cached result for similar query.
        """
        # TODO: Implement semantic similarity matching
        # Use embeddings or fuzzy matching
        return None
    
    def add(self, query: Dict[str, Any], result: Any) -> None:
        """Add entry to semantic cache"""
        key = hashlib.md5(str(query).encode()).hexdigest()
        self.entries.append(
            CachedInference(
                key=key,
                query=query,
                result=result,
                timestamp=time.time(),
            )
        )

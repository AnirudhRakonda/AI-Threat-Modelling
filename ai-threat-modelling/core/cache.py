"""
Request caching layer for LLM responses.
Caches responses based on prompt hash to avoid redundant LLM calls.
"""

import hashlib
import json
import os
from typing import Optional, Dict, Any
import time


CACHE_DIR = "outputs/cache"
CACHE_METADATA = "outputs/cache/metadata.json"


def _ensure_cache_dir():
    """Create cache directory if it doesn't exist."""
    os.makedirs(CACHE_DIR, exist_ok=True)


def _hash_prompt(prompt: str) -> str:
    """Generate SHA256 hash of prompt for cache key."""
    return hashlib.sha256(prompt.encode()).hexdigest()


def get_cached_response(prompt: str, ttl_seconds: int = 86400) -> Optional[str]:
    """
    Retrieve cached LLM response if available and not expired.
    
    Args:
        prompt: The prompt text to look up
        ttl_seconds: Time-to-live in seconds (default: 24 hours)
    
    Returns:
        Cached response string, or None if not found/expired
    """
    _ensure_cache_dir()
    
    prompt_hash = _hash_prompt(prompt)
    cache_file = os.path.join(CACHE_DIR, f"{prompt_hash}.json")
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        with open(cache_file, "r") as f:
            cache_entry = json.load(f)
        
        # Check TTL
        timestamp = cache_entry.get("timestamp", 0)
        if time.time() - timestamp > ttl_seconds:
            return None  # Cache expired
        
        return cache_entry.get("response")
    except Exception as e:
        print(f"Cache read error: {e}")
        return None


def cache_response(prompt: str, response: str) -> None:
    """
    Store LLM response in cache.
    
    Args:
        prompt: The prompt that generated this response
        response: The response from LLM
    """
    _ensure_cache_dir()
    
    prompt_hash = _hash_prompt(prompt)
    cache_file = os.path.join(CACHE_DIR, f"{prompt_hash}.json")
    
    cache_entry = {
        "prompt_hash": prompt_hash,
        "response": response,
        "timestamp": time.time()
    }
    
    try:
        with open(cache_file, "w") as f:
            json.dump(cache_entry, f)
    except Exception as e:
        print(f"Cache write error: {e}")


def clear_cache() -> None:
    """Remove all cache entries."""
    _ensure_cache_dir()
    
    try:
        for file in os.listdir(CACHE_DIR):
            if file.endswith(".json") and file != "metadata.json":
                os.remove(os.path.join(CACHE_DIR, file))
    except Exception as e:
        print(f"Cache clear error: {e}")


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    _ensure_cache_dir()
    
    cache_files = [f for f in os.listdir(CACHE_DIR) if f.endswith(".json") and f != "metadata.json"]
    
    return {
        "cached_items": len(cache_files),
        "cache_dir": os.path.abspath(CACHE_DIR)
    }

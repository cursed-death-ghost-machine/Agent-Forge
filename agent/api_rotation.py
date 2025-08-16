"""
API Key Rotation Manager for Chimera CLI.

Handles rotation of multiple API keys with rate limiting to avoid
hitting API limits (1 call per 15 seconds per key for pollinations.ai).
"""

import time
import threading
from typing import List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class APIKeyState:
    """State tracking for an individual API key."""
    key: str
    last_used: float = 0.0
    is_available: bool = True
    error_count: int = 0

class APIKeyRotationManager:
    """Manages rotation of API keys with rate limiting."""
    
    def __init__(self, api_keys: List[str], rate_limit_seconds: float = 15.0):
        """
        Initialize the rotation manager.
        
        Args:
            api_keys: List of API keys to rotate through
            rate_limit_seconds: Minimum seconds between uses of the same key
        """
        self.rate_limit_seconds = rate_limit_seconds
        self.lock = threading.Lock()
        
        # Initialize key states
        self.key_states = [APIKeyState(key=key) for key in api_keys]
        self.current_index = 0
        
        if not self.key_states:
            logger.warning("No API keys provided for rotation")
        else:
            logger.info(f"Initialized API key rotation with {len(self.key_states)} keys")
    
    def get_available_key(self) -> Optional[str]:
        """
        Get the next available API key that hasn't hit rate limits.
        
        Returns:
            API key string if available, None if all keys are rate limited
        """
        if not self.key_states:
            logger.error("No API keys configured")
            return None
        
        with self.lock:
            current_time = time.time()
            
            # First, try to find a key that's ready to use
            start_index = self.current_index
            for attempt in range(len(self.key_states)):
                key_state = self.key_states[self.current_index]
                
                # Check if this key is available (not rate limited)
                time_since_last_use = current_time - key_state.last_used
                
                if (key_state.is_available and 
                    time_since_last_use >= self.rate_limit_seconds):
                    
                    # Don't mark as used yet - wait until actual API call
                    selected_key = key_state.key
                    selected_index = self.current_index
                    
                    # Move to next key for next request
                    self.current_index = (self.current_index + 1) % len(self.key_states)
                    
                    logger.debug(f"Selected API key ending in ...{selected_key[-4:]} "
                               f"(waited {time_since_last_use:.1f}s)")
                    return selected_key
                
                # Try next key
                self.current_index = (self.current_index + 1) % len(self.key_states)
            
            # If we get here, all keys are rate limited
            # Find the key that will be available soonest
            min_wait_time = float('inf')
            for key_state in self.key_states:
                if key_state.is_available:
                    wait_time = self.rate_limit_seconds - (current_time - key_state.last_used)
                    if wait_time < min_wait_time:
                        min_wait_time = wait_time
            
            if min_wait_time > 0:
                logger.warning(f"All API keys are rate limited. "
                             f"Next key available in {min_wait_time:.1f} seconds")
            
            return None
    
    def wait_for_available_key(self, max_wait_seconds: float = 60.0) -> Optional[str]:
        """
        Wait for an available API key, with timeout.
        
        Args:
            max_wait_seconds: Maximum time to wait for a key
            
        Returns:
            API key string if available within timeout, None otherwise
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_seconds:
            key = self.get_available_key()
            if key:
                return key
            
            # Calculate optimal wait time instead of fixed 0.5s
            with self.lock:
                current_time = time.time()
                min_wait_time = float('inf')
                for key_state in self.key_states:
                    if key_state.is_available:
                        wait_time = self.rate_limit_seconds - (current_time - key_state.last_used)
                        if wait_time > 0 and wait_time < min_wait_time:
                            min_wait_time = wait_time
                
                # Sleep for the minimum wait time, capped at 0.5s
                sleep_time = min(min_wait_time, 0.5) if min_wait_time != float('inf') else 0.5
                time.sleep(sleep_time)
        
        logger.error(f"Timeout waiting for available API key after {max_wait_seconds}s")
        return None
    
    def mark_key_used(self, api_key: str):
        """
        Mark an API key as used (set last_used timestamp).
        
        Args:
            api_key: The API key that was successfully used
        """
        with self.lock:
            current_time = time.time()
            for key_state in self.key_states:
                if key_state.key == api_key:
                    key_state.last_used = current_time
                    logger.debug(f"Marked API key ending in ...{api_key[-4:]} as used")
                    break
    
    def mark_key_error(self, api_key: str, disable_temporarily: bool = False):
        """
        Mark an API key as having encountered an error.
        
        Args:
            api_key: The API key that encountered an error
            disable_temporarily: Whether to temporarily disable the key
        """
        with self.lock:
            for key_state in self.key_states:
                if key_state.key == api_key:
                    key_state.error_count += 1
                    
                    if disable_temporarily:
                        key_state.is_available = False
                        logger.warning(f"Temporarily disabled API key ending in "
                                     f"...{api_key[-4:]} due to error")
                    
                    logger.debug(f"API key ending in ...{api_key[-4:]} "
                               f"error count: {key_state.error_count}")
                    break
    
    def enable_all_keys(self):
        """Re-enable all API keys (useful for recovery from temporary issues)."""
        with self.lock:
            for key_state in self.key_states:
                key_state.is_available = True
                key_state.error_count = 0
            logger.info("Re-enabled all API keys")
    
    def get_status(self) -> dict:
        """Get current status of all API keys."""
        with self.lock:
            current_time = time.time()
            status = {
                'total_keys': len(self.key_states),
                'available_keys': 0,
                'rate_limited_keys': 0,
                'disabled_keys': 0,
                'keys': []
            }
            
            for i, key_state in enumerate(self.key_states):
                time_since_last_use = current_time - key_state.last_used
                time_until_available = max(0, self.rate_limit_seconds - time_since_last_use)
                
                key_info = {
                    'index': i,
                    'key_suffix': f"...{key_state.key[-4:]}",
                    'is_available': key_state.is_available,
                    'error_count': key_state.error_count,
                    'time_until_available': time_until_available,
                    'ready_now': (key_state.is_available and time_until_available == 0)
                }
                
                if not key_state.is_available:
                    status['disabled_keys'] += 1
                elif time_until_available > 0:
                    status['rate_limited_keys'] += 1
                else:
                    status['available_keys'] += 1
                
                status['keys'].append(key_info)
            
            return status

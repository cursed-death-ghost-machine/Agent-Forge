"""
Configuration management for Chimera CLI.

Handles loading configuration from TOML files and environment variables,
with environment variables taking precedence.
"""

import os
import toml
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    """Singleton configuration manager."""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._load_config()
        return cls._instance
    
    @classmethod
    def _load_config(cls):
        """Load configuration from file and environment variables."""
        cls._config = {}
        
        # Load from config.toml if it exists
        config_path = Path("config.toml")
        if config_path.exists():
            with open(config_path, 'r') as f:
                file_config = toml.load(f)
                cls._config.update(file_config)
        
        # Override with environment variables (higher priority)
        env_overrides = {
            'LLM_API_BASE_URL': os.getenv('LLM_API_BASE_URL'),
            'LLM_MODEL_NAME': os.getenv('LLM_MODEL_NAME'),
            'TOOLS_DIRECTORY_PATH': os.getenv('TOOLS_DIRECTORY_PATH'),
            'LOG_LEVEL': os.getenv('LOG_LEVEL'),
            'POLLINATIONS_API_KEYS': os.getenv('POLLINATIONS_API_KEYS'),
        }
        
        for key, value in env_overrides.items():
            if value is not None:
                cls._config[key] = value
    
    def get(self, key: str, default=None):
        """Get configuration value with optional default."""
        return self._config.get(key, default)
    
    @property
    def llm_api_base_url(self) -> str:
        """LLM API base URL."""
        return self.get('LLM_API_BASE_URL', 'https://text.pollinations.ai/openai')
    
    @property
    def llm_model_name(self) -> str:
        """LLM model name."""
        return self.get('LLM_MODEL_NAME', 'openai')
    
    @property
    def pollinations_api_keys(self) -> List[str]:
        """List of Pollinations API keys for rotation."""
        keys_str = self.get('POLLINATIONS_API_KEYS', '')
        if keys_str:
            # Support both comma-separated and newline-separated keys
            keys = [key.strip() for key in keys_str.replace('\n', ',').split(',') if key.strip()]
            return keys
        return []
    
    @property
    def tools_directory_path(self) -> str:
        """Path to tools directory."""
        return self.get('TOOLS_DIRECTORY_PATH', 'tools')
    
    @property
    def log_level(self) -> str:
        """Logging level."""
        return self.get('LOG_LEVEL', 'INFO')

# Global config instance
config = Config()

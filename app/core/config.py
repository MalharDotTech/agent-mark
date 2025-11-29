"""Configuration settings for Meta Ads API Service."""

import os
from typing import List

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Fallback: manually load .env file
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())


class Settings:
    """Application settings loaded from environment variables."""
    
    def __init__(self):
        # Meta API Configuration
        self.meta_api_version: str = os.getenv("META_API_VERSION", "v23.0")
        self.meta_access_tokens: str = os.getenv("META_ACCESS_TOKENS", "")
        
        # Rate Limiting
        self.max_concurrent_requests: int = int(os.getenv("MAX_CONCURRENT_REQUESTS", "5"))
        self.base_backoff_seconds: int = int(os.getenv("BASE_BACKOFF_SECONDS", "2"))
        self.max_backoff_seconds: int = int(os.getenv("MAX_BACKOFF_SECONDS", "300"))
        
        # Database Configuration
        self.sqlite_db_path: str = os.getenv("SQLITE_DB_PATH", "data/meta_ads.db")
        self.enable_csv_debug: bool = os.getenv("ENABLE_CSV_DEBUG", "false").lower() == "true"
        self.enable_auto_schema_creation: bool = os.getenv("ENABLE_AUTO_SCHEMA_CREATION", "true").lower() == "true"
        
        # Job Processing
        self.max_job_workers: int = int(os.getenv("MAX_JOB_WORKERS", "3"))
        self.job_timeout_minutes: int = int(os.getenv("JOB_TIMEOUT_MINUTES", "60"))
        
        # Logging
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.log_format: str = os.getenv("LOG_FORMAT", "json")
        
        # Validate configuration
        self._validate_configuration()
    
    def _validate_configuration(self):
        """Validate configuration settings."""
        # Validate Meta API tokens
        if self.meta_access_tokens and not self.meta_access_tokens.strip():
            raise ValueError("At least one Meta access token must be provided")
        
        # Validate SQLite database path
        if self.sqlite_db_path and not self.sqlite_db_path.endswith('.db'):
            raise ValueError("SQLITE_DB_PATH must end with '.db'")
    
    def get_access_tokens(self) -> List[str]:
        """Parse comma-separated tokens into a list."""
        if not self.meta_access_tokens:
            return []
        return [token.strip() for token in self.meta_access_tokens.split(',') if token.strip()]
    
    def get_database_config(self) -> dict:
        """Get database configuration as dictionary."""
        return {
            'sqlite_db_path': self.sqlite_db_path,
            'enable_csv_debug': self.enable_csv_debug,
            'enable_auto_schema_creation': self.enable_auto_schema_creation
        }


# Global settings instance
settings = Settings()
"""Configuration management for MCP Odoo Server."""

import os
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with validation."""
    
    odoo_url: str = Field(default="", description="Odoo instance URL")
    odoo_db: str = Field(default="", description="Odoo database name")
    odoo_username: str = Field(default="", description="Odoo username")
    odoo_password: str = Field(default="", description="Odoo password")
    odoo_timeout: int = Field(default=30, description="Odoo API timeout in seconds")
    odoo_max_retries: int = Field(default=3, description="Max retries for Odoo API calls")
    
    server_mode: str = Field(default="http", description="Server mode: http or stdio")
    host: str = Field(default="0.0.0.0", description="Host to bind to (HTTP mode)")
    port: int = Field(default=5000, description="Port to bind to (HTTP mode)")
    
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for JWT tokens"
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration in minutes"
    )
    
    api_keys: str = Field(default="", description="Comma-separated list of API keys")
    
    redis_enabled: bool = Field(default=False, description="Enable Redis cache")
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    cache_ttl: int = Field(default=300, description="Cache TTL in seconds")
    
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format: json or console")
    
    rate_limit: int = Field(default=60, description="Rate limit per minute")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def get_api_keys(self) -> List[str]:
        """Parse and return API keys as a list."""
        if not self.api_keys:
            return []
        return [key.strip() for key in self.api_keys.split(",") if key.strip()]


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()

"""
Configuration management for WebCrawlApp.

This module handles all configuration settings including defaults,
environment variable overrides, and validation.
"""

import os
from typing import Optional, Dict, Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from .schemas import CrawlConfig, AdapterConfig


class Settings(BaseSettings):
    """Main application settings with environment variable support."""
    
    # Core crawling configuration
    max_depth: int = Field(default=1, description="Maximum crawl depth (docs=2)")
    page_budget: int = Field(default=8, description="Maximum pages to visit")
    char_budget: int = Field(default=10000, description="Maximum characters in response")
    per_page_timeout: int = Field(default=10, description="Timeout per page in seconds")
    global_timeout: int = Field(default=75, description="Global timeout in seconds")
    js_render_limit: int = Field(default=2, description="Maximum pages to render JavaScript")
    
    # HTTP and network settings
    respect_robots: bool = Field(default=True, description="Whether to respect robots.txt")
    user_agent: str = Field(default="WebCrawlApp/1.0", description="User agent string")
    max_redirects: int = Field(default=5, description="Maximum redirects to follow")
    connection_timeout: int = Field(default=10, description="Connection timeout in seconds")
    
    # Content processing settings
    min_content_length: int = Field(default=100, description="Minimum content length to consider")
    max_content_size: int = Field(default=1024*1024, description="Maximum content size to process (1MB)")
    content_quality_threshold: float = Field(default=0.3, description="Minimum content quality score")
    
    # BM25 and scoring settings
    bm25_k1: float = Field(default=1.5, description="BM25 k1 parameter")
    bm25_b: float = Field(default=0.75, description="BM25 b parameter")
    depth_penalty: float = Field(default=0.8, description="Score penalty for deeper links")
    
    # Adapter settings
    enable_cache: bool = Field(default=True, description="Enable content caching")
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")
    
    # LLM settings (when implemented)
    llm_model: Optional[str] = Field(default=None, description="LLM model to use")
    llm_api_key: Optional[str] = Field(default=None, description="LLM API key")
    llm_max_tokens: int = Field(default=2000, description="Maximum tokens for LLM response")
    llm_temperature: float = Field(default=0.1, description="LLM temperature setting")
    
    # Logging and debugging
    log_level: str = Field(default="INFO", description="Logging level")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_requests: bool = Field(default=True, description="Log HTTP requests")
    
    # Performance settings
    max_concurrent_requests: int = Field(default=5, description="Maximum concurrent HTTP requests")
    request_delay: float = Field(default=0.1, description="Delay between requests in seconds")
    
    # Feature flags
    enable_javascript_rendering: bool = Field(default=False, description="Enable JavaScript rendering")
    enable_video_transcripts: bool = Field(default=True, description="Enable video transcript extraction")
    enable_github_api: bool = Field(default=True, description="Enable GitHub API integration")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "env_prefix": "WEBCRAWL_",
        "extra": "ignore"
    }
    
    @field_validator("max_depth")
    @classmethod
    def validate_max_depth(cls, v):
        """Validate max_depth is reasonable."""
        if v < 0 or v > 10:
            raise ValueError("max_depth must be between 0 and 10")
        return v
    
    @field_validator("page_budget")
    @classmethod
    def validate_page_budget(cls, v):
        """Validate page_budget is reasonable."""
        if v < 1 or v > 100:
            raise ValueError("page_budget must be between 1 and 100")
        return v
    
    @field_validator("char_budget")
    @classmethod
    def validate_char_budget(cls, v):
        """Validate char_budget is reasonable."""
        if v < 1000 or v > 100000:
            raise ValueError("char_budget must be between 1000 and 100000")
        return v
    
    @field_validator("per_page_timeout")
    @classmethod
    def validate_per_page_timeout(cls, v):
        """Validate per_page_timeout is reasonable."""
        if v < 1 or v > 60:
            raise ValueError("per_page_timeout must be between 1 and 60 seconds")
        return v
    
    @field_validator("global_timeout")
    @classmethod
    def validate_global_timeout(cls, v):
        """Validate global_timeout is reasonable."""
        if v < 10 or v > 300:
            raise ValueError("global_timeout must be between 10 and 300 seconds")
        return v
    
    @field_validator("content_quality_threshold")
    @classmethod
    def validate_content_quality_threshold(cls, v):
        """Validate content_quality_threshold is between 0 and 1."""
        if v < 0.0 or v > 1.0:
            raise ValueError("content_quality_threshold must be between 0.0 and 1.0")
        return v
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log_level is valid."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()
    
    @field_validator("debug", "log_requests", "respect_robots", "enable_cache", 
                     "enable_javascript_rendering", "enable_video_transcripts", "enable_github_api")
    @classmethod
    def validate_bool_fields(cls, v):
        """Convert string boolean values to actual booleans."""
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return v
    
    def get_crawl_config(self) -> CrawlConfig:
        """Get CrawlConfig object from settings."""
        return CrawlConfig(
            max_depth=self.max_depth,
            page_budget=self.page_budget,
            char_budget=self.char_budget,
            per_page_timeout=self.per_page_timeout,
            global_timeout=self.global_timeout,
            js_render_limit=self.js_render_limit,
            respect_robots=self.respect_robots,
            user_agent=self.user_agent
        )
    
    def get_adapter_config(self) -> AdapterConfig:
        """Get AdapterConfig object from settings."""
        return AdapterConfig(
            enable_cache=self.enable_cache,
            max_content_size=self.max_content_size,
            min_content_length=self.min_content_length,
            content_quality_threshold=self.content_quality_threshold
        )
    
    def get_bm25_config(self) -> Dict[str, float]:
        """Get BM25 configuration parameters."""
        return {
            "k1": self.bm25_k1,
            "b": self.bm25_b,
            "depth_penalty": self.depth_penalty
        }
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration parameters."""
        return {
            "model": self.llm_model,
            "api_key": self.llm_api_key,
            "max_tokens": self.llm_max_tokens,
            "temperature": self.llm_temperature
        }
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        feature_flags = {
            "javascript_rendering": self.enable_javascript_rendering,
            "video_transcripts": self.enable_video_transcripts,
            "github_api": self.enable_github_api,
            "debug": self.debug,
            "cache": self.enable_cache,
            "robots": self.respect_robots
        }
        return feature_flags.get(feature, False)
    
    def get_http_config(self) -> Dict[str, Any]:
        """Get HTTP client configuration."""
        return {
            "timeout": self.connection_timeout,
            "max_redirects": self.max_redirects,
            "user_agent": self.user_agent,
            "respect_robots": self.respect_robots
        }
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance-related configuration."""
        return {
            "max_concurrent_requests": self.max_concurrent_requests,
            "request_delay": self.request_delay,
            "cache_ttl": self.cache_ttl
        }


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment variables."""
    global settings
    settings = Settings()
    return settings


# Convenience functions for common configurations
def get_crawl_config() -> CrawlConfig:
    """Get the current crawl configuration."""
    return settings.get_crawl_config()


def get_adapter_config() -> AdapterConfig:
    """Get the current adapter configuration."""
    return settings.get_adapter_config()


def get_bm25_config() -> Dict[str, float]:
    """Get the current BM25 configuration."""
    return settings.get_bm25_config()


def get_llm_config() -> Dict[str, Any]:
    """Get the current LLM configuration."""
    return settings.get_llm_config()


def is_feature_enabled(feature: str) -> bool:
    """Check if a feature is enabled."""
    return settings.is_feature_enabled(feature)


def get_http_config() -> Dict[str, Any]:
    """Get HTTP client configuration."""
    return settings.get_http_config()


def get_performance_config() -> Dict[str, Any]:
    """Get performance configuration."""
    return settings.get_performance_config()


# Environment-specific configurations
class DevelopmentSettings(Settings):
    """Development-specific settings."""
    debug: bool = True
    log_level: str = "DEBUG"
    page_budget: int = 5  # Lower for faster development
    char_budget: int = 5000  # Lower for faster development


class ProductionSettings(Settings):
    """Production-specific settings."""
    debug: bool = False
    log_level: str = "INFO"
    max_concurrent_requests: int = 10  # Higher for production


class TestingSettings(Settings):
    """Testing-specific settings."""
    debug: bool = True
    log_level: str = "DEBUG"
    page_budget: int = 2  # Very low for fast tests
    char_budget: int = 1000  # Very low for fast tests
    global_timeout: int = 30  # Shorter timeout for tests
    enable_cache: bool = False  # Disable cache for tests


def get_environment_settings() -> Settings:
    """Get environment-specific settings based on WEBCRAWL_ENV."""
    env = os.getenv("WEBCRAWL_ENV", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    elif env == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()


# Export the main settings instance
__all__ = [
    "Settings",
    "settings",
    "get_settings",
    "reload_settings",
    "get_crawl_config",
    "get_adapter_config",
    "get_bm25_config",
    "get_llm_config",
    "is_feature_enabled",
    "get_http_config",
    "get_performance_config",
    "DevelopmentSettings",
    "ProductionSettings",
    "TestingSettings",
    "get_environment_settings"
]

"""
Test script for app/settings.py to validate configuration management.

Run this with: python tests/test_settings.py
"""

import os
import tempfile
from app.settings import (
    Settings, settings, get_settings, reload_settings,
    get_crawl_config, get_adapter_config, get_bm25_config,
    get_llm_config, is_feature_enabled, get_http_config,
    get_performance_config, DevelopmentSettings, ProductionSettings,
    TestingSettings, get_environment_settings
)
from app.schemas import CrawlConfig, AdapterConfig


def test_default_settings():
    """Test that default settings are correctly set."""
    print("Testing Default Settings...")
    
    # Test core crawling defaults from .cursorrules
    assert settings.max_depth == 1
    assert settings.page_budget == 8
    assert settings.char_budget == 10000
    assert settings.per_page_timeout == 10
    assert settings.global_timeout == 75
    assert settings.js_render_limit == 2
    
    # Test other defaults
    assert settings.respect_robots == True
    assert settings.user_agent == "WebCrawlApp/1.0"
    assert settings.min_content_length == 100
    assert settings.content_quality_threshold == 0.3
    assert settings.bm25_k1 == 1.5
    assert settings.bm25_b == 0.75
    assert settings.depth_penalty == 0.8
    
    print("Default settings working correctly")


def test_validation():
    """Test that validation works correctly."""
    print("Testing Settings Validation...")
    
    try:
        # Test invalid max_depth
        Settings(max_depth=15)
        assert False, "Should have raised validation error for max_depth"
    except ValueError as e:
        assert "max_depth must be between 0 and 10" in str(e)
        print("max_depth validation working")
    
    try:
        # Test invalid page_budget
        Settings(page_budget=150)
        assert False, "Should have raised validation error for page_budget"
    except ValueError as e:
        assert "page_budget must be between 1 and 100" in str(e)
        print("page_budget validation working")
    
    try:
        # Test invalid char_budget
        Settings(char_budget=50)
        assert False, "Should have raised validation error for char_budget"
    except ValueError as e:
        assert "char_budget must be between 1000 and 100000" in str(e)
        print("char_budget validation working")
    
    try:
        # Test invalid log_level
        Settings(log_level="INVALID")
        assert False, "Should have raised validation error for log_level"
    except ValueError as e:
        assert "log_level must be one of" in str(e)
        print("log_level validation working")
    
    print("Settings validation working correctly")


def test_configuration_objects():
    """Test that configuration objects are created correctly."""
    print("Testing Configuration Objects...")
    
    # Test CrawlConfig
    crawl_config = settings.get_crawl_config()
    assert isinstance(crawl_config, CrawlConfig)
    assert crawl_config.max_depth == 1
    assert crawl_config.page_budget == 8
    assert crawl_config.char_budget == 10000
    assert crawl_config.per_page_timeout == 10
    assert crawl_config.global_timeout == 75
    assert crawl_config.js_render_limit == 2
    assert crawl_config.respect_robots == True
    assert crawl_config.user_agent == "WebCrawlApp/1.0"
    
    # Test AdapterConfig
    adapter_config = settings.get_adapter_config()
    assert isinstance(adapter_config, AdapterConfig)
    assert adapter_config.enable_cache == True
    assert adapter_config.max_content_size == 1024*1024
    assert adapter_config.min_content_length == 100
    assert adapter_config.content_quality_threshold == 0.3
    
    # Test BM25 config
    bm25_config = settings.get_bm25_config()
    assert bm25_config["k1"] == 1.5
    assert bm25_config["b"] == 0.75
    assert bm25_config["depth_penalty"] == 0.8
    
    # Test LLM config
    llm_config = settings.get_llm_config()
    assert llm_config["model"] is None  # Default
    assert llm_config["max_tokens"] == 2000
    assert llm_config["temperature"] == 0.1
    
    print("Configuration objects working correctly")


def test_feature_flags():
    """Test feature flag functionality."""
    print("Testing Feature Flags...")
    
    # Test default feature flags
    assert settings.is_feature_enabled("cache") == True
    assert settings.is_feature_enabled("robots") == True
    assert settings.is_feature_enabled("video_transcripts") == True
    assert settings.is_feature_enabled("github_api") == True
    assert settings.is_feature_enabled("javascript_rendering") == False
    assert settings.is_feature_enabled("debug") == False
    
    # Test invalid feature
    assert settings.is_feature_enabled("invalid_feature") == False
    
    print("Feature flags working correctly")


def test_http_config():
    """Test HTTP configuration."""
    print("Testing HTTP Configuration...")
    
    http_config = settings.get_http_config()
    assert http_config["timeout"] == 10
    assert http_config["max_redirects"] == 5
    assert http_config["user_agent"] == "WebCrawlApp/1.0"
    assert http_config["respect_robots"] == True
    
    print("HTTP configuration working correctly")


def test_performance_config():
    """Test performance configuration."""
    print("Testing Performance Configuration...")
    
    perf_config = settings.get_performance_config()
    assert perf_config["max_concurrent_requests"] == 5
    assert perf_config["request_delay"] == 0.1
    assert perf_config["cache_ttl"] == 3600
    
    print("Performance configuration working correctly")


def test_environment_settings():
    """Test environment-specific settings."""
    print("Testing Environment Settings...")
    
    # Test development settings
    dev_settings = DevelopmentSettings()
    assert dev_settings.debug == True
    assert dev_settings.log_level == "DEBUG"
    assert dev_settings.page_budget == 5
    assert dev_settings.char_budget == 5000
    
    # Test production settings
    prod_settings = ProductionSettings()
    assert prod_settings.debug == False
    assert prod_settings.log_level == "INFO"
    assert prod_settings.max_concurrent_requests == 10
    
    # Test testing settings
    test_settings = TestingSettings()
    assert test_settings.debug == True
    assert test_settings.log_level == "DEBUG"
    assert test_settings.page_budget == 2
    assert test_settings.char_budget == 1000
    assert test_settings.global_timeout == 30
    assert test_settings.enable_cache == False
    
    print("Environment settings working correctly")


def test_environment_variable_override():
    """Test environment variable overrides."""
    print("Testing Environment Variable Overrides...")
    
    # Save original environment
    original_env = {}
    test_vars = {
        "WEBCRAWL_MAX_DEPTH": "3",
        "WEBCRAWL_PAGE_BUDGET": "15",
        "WEBCRAWL_DEBUG": "true",
        "WEBCRAWL_LOG_LEVEL": "WARNING"
    }
    
    try:
        # Set test environment variables
        for key, value in test_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        # Create a new Settings instance to test environment variables
        test_settings = Settings()
        
        # Test that environment variables override defaults
        assert test_settings.max_depth == 3
        assert test_settings.page_budget == 15
        assert test_settings.debug == True
        assert test_settings.log_level == "WARNING"
        
        print("Environment variable overrides working correctly")
        
    finally:
        # Restore original environment
        for key, original_value in original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value


def test_convenience_functions():
    """Test convenience functions."""
    print("Testing Convenience Functions...")
    
    # Test get_settings
    current_settings = get_settings()
    assert current_settings is settings
    
    # Test get_crawl_config
    crawl_config = get_crawl_config()
    assert isinstance(crawl_config, CrawlConfig)
    assert crawl_config.max_depth == 1
    
    # Test get_adapter_config
    adapter_config = get_adapter_config()
    assert isinstance(adapter_config, AdapterConfig)
    assert adapter_config.enable_cache == True
    
    # Test get_bm25_config
    bm25_config = get_bm25_config()
    assert bm25_config["k1"] == 1.5
    
    # Test get_llm_config
    llm_config = get_llm_config()
    assert llm_config["max_tokens"] == 2000
    
    # Test is_feature_enabled
    assert is_feature_enabled("cache") == True
    assert is_feature_enabled("invalid") == False
    
    # Test get_http_config
    http_config = get_http_config()
    assert http_config["timeout"] == 10
    
    # Test get_performance_config
    perf_config = get_performance_config()
    assert perf_config["max_concurrent_requests"] == 5
    
    print("Convenience functions working correctly")


def test_get_environment_settings():
    """Test get_environment_settings function."""
    print("Testing get_environment_settings...")
    
    # Save original environment
    original_env = os.environ.get("WEBCRAWL_ENV")
    
    try:
        # Test development environment (default)
        if "WEBCRAWL_ENV" in os.environ:
            del os.environ["WEBCRAWL_ENV"]
        dev_settings = get_environment_settings()
        assert dev_settings.debug == True
        assert dev_settings.page_budget == 5
        
        # Test production environment
        os.environ["WEBCRAWL_ENV"] = "production"
        prod_settings = get_environment_settings()
        assert prod_settings.debug == False
        assert prod_settings.max_concurrent_requests == 10
        
        # Test testing environment
        os.environ["WEBCRAWL_ENV"] = "testing"
        test_settings = get_environment_settings()
        assert test_settings.page_budget == 2
        assert test_settings.enable_cache == False
        
        print("get_environment_settings working correctly")
        
    finally:
        # Restore original environment
        if original_env is not None:
            os.environ["WEBCRAWL_ENV"] = original_env
        elif "WEBCRAWL_ENV" in os.environ:
            del os.environ["WEBCRAWL_ENV"]


def main():
    """Run all settings tests."""
    print("Testing WebCrawlApp Settings...")
    print("=" * 50)
    
    try:
        test_default_settings()
        test_validation()
        test_configuration_objects()
        test_feature_flags()
        test_http_config()
        test_performance_config()
        test_environment_settings()
        test_environment_variable_override()
        test_convenience_functions()
        test_get_environment_settings()
        
        print("=" * 50)
        print("All settings tests passed successfully!")
        print("The configuration system is working correctly.")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

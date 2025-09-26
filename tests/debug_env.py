"""
Debug script to see what's happening with environment variables
"""
import os
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator

# Create a simple test settings class
class TestSettings(BaseSettings):
    max_depth: int = Field(default=1)
    page_budget: int = Field(default=8)
    debug_mode: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO")
    
    @field_validator("debug_mode")
    @classmethod
    def validate_debug_mode(cls, v):
        """Convert string boolean values to actual booleans."""
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return v
    
    model_config = {
        "env_prefix": "WEBCRAWL_",
        "case_sensitive": False,
        "extra": "ignore"
    }

# Set test environment variables
os.environ["WEBCRAWL_MAX_DEPTH"] = "3"
os.environ["WEBCRAWL_PAGE_BUDGET"] = "15"
os.environ["WEBCRAWL_DEBUG"] = "true"
os.environ["WEBCRAWL_LOG_LEVEL"] = "WARNING"

print("Environment variables set:")
print(f"  WEBCRAWL_MAX_DEPTH: {os.environ.get('WEBCRAWL_MAX_DEPTH')}")
print(f"  WEBCRAWL_PAGE_BUDGET: {os.environ.get('WEBCRAWL_PAGE_BUDGET')}")
print(f"  WEBCRAWL_DEBUG: {os.environ.get('WEBCRAWL_DEBUG')}")
print(f"  WEBCRAWL_LOG_LEVEL: {os.environ.get('WEBCRAWL_LOG_LEVEL')}")

# Create settings instance
settings = TestSettings()

print("\nSettings values:")
print(f"  max_depth: {settings.max_depth}")
print(f"  page_budget: {settings.page_budget}")
print(f"  debug_mode: {settings.debug_mode}")
print(f"  log_level: {settings.log_level}")

# Check if they match
print("\nValidation:")
print(f"  max_depth == 3: {settings.max_depth == 3}")
print(f"  page_budget == 15: {settings.page_budget == 15}")
print(f"  debug_mode == True: {settings.debug_mode == True}")
print(f"  log_level == 'WARNING': {settings.log_level == 'WARNING'}")

# Test without alias
print("\n" + "="*50)
print("Testing without alias:")

class TestSettings2(BaseSettings):
    max_depth: int = Field(default=1)
    page_budget: int = Field(default=8)
    debug: bool = Field(default=False)  # Direct field name match
    log_level: str = Field(default="INFO")
    
    @field_validator("debug")
    @classmethod
    def validate_debug(cls, v):
        """Convert string boolean values to actual booleans."""
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes", "on")
        return v
    
    model_config = {
        "env_prefix": "WEBCRAWL_",
        "case_sensitive": False,
        "extra": "ignore"
    }

settings2 = TestSettings2()
print(f"  debug: {settings2.debug}")
print(f"  debug == True: {settings2.debug == True}")

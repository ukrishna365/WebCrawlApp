"""
Clean debug script to test environment variables
"""
import os
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator

# Clear any existing environment variables first
for key in list(os.environ.keys()):
    if key.startswith("WEBCRAWL_"):
        del os.environ[key]

# Set fresh test environment variables
os.environ["WEBCRAWL_MAX_DEPTH"] = "3"
os.environ["WEBCRAWL_PAGE_BUDGET"] = "15"
os.environ["WEBCRAWL_DEBUG"] = "true"
os.environ["WEBCRAWL_LOG_LEVEL"] = "WARNING"

print("Environment variables set:")
for key in ["WEBCRAWL_MAX_DEPTH", "WEBCRAWL_PAGE_BUDGET", "WEBCRAWL_DEBUG", "WEBCRAWL_LOG_LEVEL"]:
    print(f"  {key}: {os.environ.get(key)}")

# Test 1: With alias
print("\n" + "="*50)
print("Test 1: With alias (WEBCRAWL_DEBUG -> debug_mode)")

class TestSettings1(BaseSettings):
    max_depth: int = Field(default=1)
    page_budget: int = Field(default=8)
    debug_mode: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO")
    
    @field_validator("debug_mode")
    @classmethod
    def validate_debug_mode(cls, v):
        print(f"    Validator called with: {v} (type: {type(v)})")
        if isinstance(v, str):
            result = v.lower() in ("true", "1", "yes", "on")
            print(f"    Converted '{v}' to {result}")
            return result
        print(f"    Returning as-is: {v}")
        return v
    
    model_config = {
        "env_prefix": "WEBCRAWL_",
        "case_sensitive": False,
        "extra": "ignore"
    }

settings1 = TestSettings1()
print(f"  debug_mode: {settings1.debug_mode}")

# Test 2: Direct field name
print("\n" + "="*50)
print("Test 2: Direct field name (WEBCRAWL_DEBUG -> debug)")

class TestSettings2(BaseSettings):
    max_depth: int = Field(default=1)
    page_budget: int = Field(default=8)
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    
    @field_validator("debug")
    @classmethod
    def validate_debug(cls, v):
        print(f"    Validator called with: {v} (type: {type(v)})")
        if isinstance(v, str):
            result = v.lower() in ("true", "1", "yes", "on")
            print(f"    Converted '{v}' to {result}")
            return result
        print(f"    Returning as-is: {v}")
        return v
    
    model_config = {
        "env_prefix": "WEBCRAWL_",
        "case_sensitive": False,
        "extra": "ignore"
    }

settings2 = TestSettings2()
print(f"  debug: {settings2.debug}")

print("\n" + "="*50)
print("Summary:")
print(f"  Test 1 (alias) debug_mode: {settings1.debug_mode}")
print(f"  Test 2 (direct) debug: {settings2.debug}")

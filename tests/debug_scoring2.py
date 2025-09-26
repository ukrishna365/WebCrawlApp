"""
Debug script to check content quality scoring with more details
"""
from adapters.base import BaseAdapter
from app.schemas import ContentType
from app.settings import get_adapter_config

class MockAdapter(BaseAdapter):
    @property
    def adapter_type(self):
        return "html"
    
    @property
    def supported_capabilities(self):
        return set()
    
    async def can_handle(self, url, content_type=None, content_preview=None):
        pass
    
    async def extract_content(self, url, capabilities, max_depth=1):
        pass

adapter = MockAdapter()

# Check the configuration
config = get_adapter_config()
print(f"Min content length: {config.min_content_length}")
print(f"Content quality threshold: {config.content_quality_threshold}")

# Test the content that's failing
content = "# Header\n\nThis is a well-structured document with headers and content."
print(f"\nContent: {repr(content)}")
print(f"Content length: {len(content)}")

# Check if content meets minimum length
if len(content.strip()) < config.min_content_length:
    print(f"Content too short: {len(content)} < {config.min_content_length}")
else:
    print(f"Content length OK: {len(content)} >= {config.min_content_length}")

# Test the scoring
score = adapter.score_content_quality(content, ContentType.SECTION)
print(f"Score: {score}")

# Test with longer content
long_content = "# Header\n\nThis is a well-structured document with headers and content. " * 10
print(f"\nLong content length: {len(long_content)}")
long_score = adapter.score_content_quality(long_content, ContentType.SECTION)
print(f"Long content score: {long_score}")

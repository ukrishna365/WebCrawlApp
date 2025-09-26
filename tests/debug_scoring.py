"""
Debug script to check content quality scoring
"""
from adapters.base import BaseAdapter
from app.schemas import ContentType

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

# Test the content that's failing
content = "# Header\n\nThis is a well-structured document with headers and content."
score = adapter.score_content_quality(content, ContentType.SECTION)

print(f"Content: {repr(content)}")
print(f"Content length: {len(content)}")
print(f"Score: {score}")
print(f"Expected: > 0.8")
print(f"Actual: {score}")

# Test with different content
test_contents = [
    "# Header\n\nThis is a well-structured document with headers and content.",
    "Short",
    "def function_name():\n    return 'hello world'",
    "This is a very long content block with lots of text that should score well because it has sufficient length and appears to be well-structured content that would meet the quality threshold requirements."
]

for i, test_content in enumerate(test_contents):
    score = adapter.score_content_quality(test_content, ContentType.SECTION)
    print(f"\nTest {i+1}:")
    print(f"  Content: {repr(test_content[:50])}...")
    print(f"  Length: {len(test_content)}")
    print(f"  Score: {score}")

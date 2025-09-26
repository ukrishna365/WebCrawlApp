"""
Debug script to check URL handling in content blocks
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

# Test the actual URL handling
test_url = "https://example.com/page"
content = "This is a valid content block with sufficient length and quality. " * 2

print(f"Input URL: {test_url}")
print(f"Input URL type: {type(test_url)}")

try:
    block = adapter.create_content_block(
        content_type=ContentType.SECTION,
        content=content,
        url=test_url,
        title="Test Page",
        metadata={"test": True}
    )
    
    print(f"Block URL: {block.url}")
    print(f"Block URL type: {type(block.url)}")
    print(f"Block URL string: {str(block.url)}")
    print(f"Block URL repr: {repr(block.url)}")
    
except Exception as e:
    print(f"Error: {e}")

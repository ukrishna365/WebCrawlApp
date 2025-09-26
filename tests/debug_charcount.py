"""
Debug script to check char count in content blocks
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

# Test the actual char count
content = "This is a valid content block with sufficient length and quality. " * 2
expected_length = len(content)

print(f"Content: {repr(content)}")
print(f"Expected length: {expected_length}")

try:
    block = adapter.create_content_block(
        content_type=ContentType.SECTION,
        content=content,
        url="https://example.com/page",
        title="Test Page",
        metadata={"test": True}
    )
    
    print(f"Block char_count: {block.char_count}")
    print(f"Block content length: {len(block.content)}")
    print(f"Match: {block.char_count == expected_length}")
    
except Exception as e:
    print(f"Error: {e}")

"""
Debug script to check link extraction
"""
import asyncio
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

async def test_link_extraction():
    adapter = MockAdapter()
    
    html_content = '''
    <html>
        <body>
            <a href="/page1">Page 1</a>
            <a href="https://external.com">External</a>
            <a href="#anchor">Anchor</a>
            <a href="mailto:test@example.com">Email</a>
        </body>
    </html>
    '''
    
    print("HTML content:")
    print(html_content)
    
    links = await adapter.extract_links(html_content, "https://example.com")
    
    print(f"\nExtracted links ({len(links)}):")
    for i, link in enumerate(links):
        print(f"  {i+1}: {link}")
    
    print(f"\nExpected: 2 links")
    print(f"Actual: {len(links)} links")

if __name__ == "__main__":
    asyncio.run(test_link_extraction())

#!/usr/bin/env python3
"""
Tests for HTML Adapter.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import AsyncMock, patch

from adapters.html import HTMLAdapter
from app.schemas import ContentType, AdapterType, Capability
from app.settings import Settings


def test_html_adapter_initialization():
    """Test HTML adapter initialization."""
    print("Testing HTML Adapter Initialization...")
    
    adapter = HTMLAdapter()
    assert adapter.adapter_type == AdapterType.HTML
    assert Capability.SECTION in adapter.supported_capabilities
    assert Capability.NAV_GRAPH in adapter.supported_capabilities
    
    print("HTML Adapter initialization working correctly")


def test_html_adapter_can_handle():
    """Test HTML adapter content detection."""
    print("Testing HTML Content Detection...")
    
    adapter = HTMLAdapter()
    
    # Test with HTML content
    html_content = "<html><body><h1>Test</h1><p>Content</p></body></html>"
    
    # Mock the async method
    async def run_test():
        can_handle = await adapter.can_handle("https://example.com", html_content, "text/html")
        assert can_handle == True
        
        # Test with non-HTML content
        can_handle_non_html = await adapter.can_handle("https://example.com", "plain text", "text/plain")
        assert can_handle_non_html == False
        
        # Test with empty content
        can_handle_empty = await adapter.can_handle("https://example.com", "", "text/html")
        assert can_handle_empty == False
    
    import asyncio
    asyncio.run(run_test())
    
    print("HTML content detection working correctly")


def test_html_adapter_extract_navigation():
    """Test navigation extraction."""
    print("Testing Navigation Extraction...")
    
    adapter = HTMLAdapter()
    
    html_content = """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <nav class="main-nav">
                <a href="/home">Home</a>
                <a href="/about">About</a>
                <a href="/contact">Contact</a>
            </nav>
            <main>
                <h1>Main Content</h1>
                <p>This is the main content of the page with substantial information. 
                It contains detailed explanations and examples that provide value to readers. 
                The content is comprehensive and covers multiple aspects of the topic.</p>
            </main>
        </body>
    </html>
    """
    
    async def run_test():
        blocks = await adapter.extract_content("https://example.com", html_content, "text/html")
        
        # Should extract navigation and content
        assert len(blocks) > 0
        
        # Check for navigation block
        nav_blocks = [b for b in blocks if b.content_type == ContentType.NAV_BAR]
        assert len(nav_blocks) > 0
        
        nav_block = nav_blocks[0]
        assert "Home" in nav_block.content
        assert "About" in nav_block.content
        assert "Contact" in nav_block.content
        assert str(nav_block.url) == "https://example.com/"
        
        # Check for content block
        content_blocks = [b for b in blocks if b.content_type == ContentType.SECTION]
        assert len(content_blocks) > 0
        
        content_block = content_blocks[0]
        assert "Main Content" in content_block.content
        assert "substantial information" in content_block.content
    
    import asyncio
    asyncio.run(run_test())
    
    print("Navigation extraction working correctly")


def test_html_adapter_extract_sections():
    """Test section extraction."""
    print("Testing Section Extraction...")
    
    adapter = HTMLAdapter()
    
    html_content = """
    <html>
        <body>
            <h1>Introduction</h1>
            <p>This is the introduction section with detailed content that provides comprehensive information about the topic. It includes multiple paragraphs with substantial explanations and background information that helps readers understand the context.</p>
            <p>More content in the introduction section that expands on the previous points and provides additional details and examples to illustrate the concepts being discussed.</p>
            
            <h2>Features</h2>
            <p>Here are the main features of our product with detailed descriptions and explanations. Each feature is thoroughly documented with examples and use cases to help users understand how to utilize them effectively.</p>
            <ul>
                <li>Feature 1 with comprehensive description</li>
                <li>Feature 2 with detailed explanations</li>
            </ul>
            
            <h2>Conclusion</h2>
            <p>This concludes our documentation with a comprehensive summary of all the information presented. It provides final thoughts and recommendations for users who want to implement these solutions.</p>
        </body>
    </html>
    """
    
    async def run_test():
        blocks = await adapter.extract_content("https://example.com", html_content, "text/html")
        
        # Should extract sections
        section_blocks = [b for b in blocks if b.content_type == ContentType.SECTION]
        assert len(section_blocks) >= 1
        
        # Check section content
        content_text = ' '.join([b.content for b in section_blocks])
        assert "Introduction" in content_text
        assert "Features" in content_text
        assert "Feature 1" in content_text
        assert "Conclusion" in content_text
    
    import asyncio
    asyncio.run(run_test())
    
    print("Section extraction working correctly")


def test_html_adapter_extract_links():
    """Test link graph extraction."""
    print("Testing Link Graph Extraction...")
    
    adapter = HTMLAdapter()
    
    html_content = """
    <html>
        <body>
            <nav>
                <a href="/docs">Documentation</a>
                <a href="/api">API Reference</a>
            </nav>
            <main>
                <h1>Main Content</h1>
                <p>Read our <a href="/guide">user guide</a> for more information.</p>
                <p>Check out the <a href="/examples">examples</a> section.</p>
            </main>
            <footer>
                <a href="/privacy">Privacy Policy</a>
                <a href="/terms">Terms of Service</a>
            </footer>
        </body>
    </html>
    """
    
    async def run_test():
        blocks = await adapter.extract_content("https://example.com", html_content, "text/html")
        
        # Should extract link graph blocks
        link_blocks = [b for b in blocks if b.content_type == ContentType.NAV_BAR]
        assert len(link_blocks) > 0
        
        # Check link content
        link_content = ' '.join([b.content for b in link_blocks])
        assert "Documentation" in link_content
        assert "API Reference" in link_content
        assert "user guide" in link_content
        assert "examples" in link_content
    
    import asyncio
    asyncio.run(run_test())
    
    print("Link graph extraction working correctly")


def test_html_adapter_content_filtering():
    """Test content quality filtering."""
    print("Testing Content Quality Filtering...")
    
    adapter = HTMLAdapter()
    
    # Test with low-quality content
    poor_html = "<html><body><p>Short</p></body></html>"
    
    async def run_test():
        blocks = await adapter.extract_content("https://example.com", poor_html, "text/html")
        
        # Should filter out low-quality content
        assert len(blocks) == 0
        
        # Test with good content
        good_html = """
        <html>
            <body>
                <h1>Comprehensive Documentation</h1>
                <p>This is a comprehensive piece of documentation that contains 
                substantial information about the topic. It includes multiple 
                paragraphs with detailed explanations and examples.</p>
                <p>Here is another substantial paragraph with more detailed 
                information that provides value to the reader.</p>
            </body>
        </html>
        """
        
        blocks = await adapter.extract_content("https://example.com", good_html, "text/html")
        
        # Should extract good content
        assert len(blocks) > 0
        assert all(len(block.content) > 50 for block in blocks)
    
    import asyncio
    asyncio.run(run_test())
    
    print("Content quality filtering working correctly")


def test_generic_adapter():
    """Test generic adapter as fallback."""
    print("Testing Generic Adapter...")
    
    from adapters.generic import GenericAdapter
    
    adapter = GenericAdapter()
    
    # Test with plain text
    plain_text = """
    This is a plain text document with substantial content.
    It contains multiple paragraphs of information.
    
    Here is another paragraph with more details.
    The content is structured and meaningful.
    """
    
    async def run_test():
        can_handle = await adapter.can_handle("https://example.com", plain_text, "text/plain")
        assert can_handle == True
        
        blocks = await adapter.extract_content("https://example.com", plain_text, "text/plain")
        assert len(blocks) > 0
        
        block = blocks[0]
        assert block.content_type == ContentType.SECTION
        assert "plain text document" in block.content
        assert "substantial content" in block.content
    
    import asyncio
    asyncio.run(run_test())
    
    print("Generic adapter working correctly")


if __name__ == "__main__":
    test_html_adapter_initialization()
    test_html_adapter_can_handle()
    test_html_adapter_extract_navigation()
    test_html_adapter_extract_sections()
    test_html_adapter_extract_links()
    test_html_adapter_content_filtering()
    test_generic_adapter()
    print("\n✅ All HTML adapter tests passed!")

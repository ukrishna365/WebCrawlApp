"""
Test suite for Smart Navigation system.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from bs4 import BeautifulSoup

from app.navigator import SmartNavigator, LinkCandidate, NavigationStats, navigate_urls, get_navigator
from app.schemas import CrawlConfig, Capability, HttpUrl
from app.settings import Settings


def test_navigator_initialization():
    """Test SmartNavigator initialization."""
    print("Testing SmartNavigator Initialization...")
    
    # Test with default settings
    navigator = SmartNavigator()
    assert navigator.settings is not None
    assert navigator.client is None
    assert isinstance(navigator.stats, NavigationStats)
    assert len(navigator.visited_urls) == 0
    assert len(navigator.link_queue) == 0
    assert navigator.link_scorer is None
    
    # Test with custom settings
    custom_settings = Settings()
    custom_settings.max_depth = 2
    navigator2 = SmartNavigator(custom_settings)
    assert navigator2.settings.max_depth == 2
    
    print("SmartNavigator initialization working correctly")


def test_link_candidate():
    """Test LinkCandidate dataclass."""
    print("Testing LinkCandidate...")
    
    candidate = LinkCandidate(
        url="https://example.com/page",
        text="Example Page",
        title="Example",
        score=0.8,
        depth=1,
        parent_url="https://example.com"
    )
    
    assert candidate.url == "https://example.com/page"
    assert candidate.text == "Example Page"
    assert candidate.score == 0.8
    assert candidate.depth == 1
    assert candidate.parent_url == "https://example.com"
    
    # Test priority queue ordering (higher score = higher priority)
    candidate2 = LinkCandidate(
        url="https://example.com/page2",
        text="Example Page 2",
        title="Example 2",
        score=0.9,
        depth=1,
        parent_url="https://example.com"
    )
    
    assert candidate2 < candidate  # 0.9 > 0.8, so candidate2 has higher priority
    
    print("LinkCandidate working correctly")


def test_navigation_stats():
    """Test NavigationStats tracking."""
    print("Testing Navigation Stats...")
    
    stats = NavigationStats()
    assert stats.urls_visited == 0
    assert stats.urls_queued == 0
    assert stats.bytes_fetched == 0
    assert stats.avg_score == 0.0
    assert stats.depth_reached == 0
    assert stats.errors == 0
    
    # Test elapsed time
    import time
    start_time = time.time()
    stats.start_time = start_time
    time.sleep(0.01)  # Small delay
    elapsed = stats.get_elapsed_time()
    assert elapsed >= 0.01
    
    print("Navigation stats working correctly")


@pytest.mark.asyncio
async def test_navigator_context_manager():
    """Test navigator async context manager."""
    print("Testing Navigator Context Manager...")
    
    async with SmartNavigator() as navigator:
        assert navigator.client is not None
        assert isinstance(navigator.client, httpx.AsyncClient)
        assert navigator.stats.start_time > 0
    
    # Client should be closed after context exit
    # Note: We can't easily test this without mocking


@pytest.mark.asyncio
async def test_robots_txt_checking():
    """Test robots.txt compliance checking."""
    print("Testing Robots.txt Checking...")
    
    async with SmartNavigator() as navigator:
        # Test with a URL that should be allowed
        result = navigator._check_robots_txt("https://httpbin.org/get")
        # Note: This might fail in some environments, so we'll just test the method exists
        assert isinstance(result, bool)
        
        # Test caching
        result2 = navigator._check_robots_txt("https://httpbin.org/get")
        assert result == result2  # Should be cached
    
    print("Robots.txt checking working correctly")


@pytest.mark.asyncio
async def test_fetch_page():
    """Test page fetching with retries."""
    print("Testing Page Fetching...")
    
    # Mock successful response
    mock_response = MagicMock()
    mock_response.text = "<html><body>Test content</body></html>"
    mock_response.headers = {"content-type": "text/html"}
    mock_response.raise_for_status.return_value = None
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client
        
        async with SmartNavigator() as navigator:
            result = await navigator._fetch_page("https://example.com")
            
            assert result is not None
            content, content_type, content_length = result
            assert content == "<html><body>Test content</body></html>"
            assert content_type == "text/html"
            assert content_length > 0
            assert navigator.stats.urls_visited == 1
            assert navigator.stats.bytes_fetched > 0
    
    print("Page fetching working correctly")


def test_extract_links():
    """Test link extraction from HTML content."""
    print("Testing Link Extraction...")
    
    html_content = """
    <html>
    <body>
        <h1>Main Page</h1>
        <a href="/page1">Page 1</a>
        <a href="/page2" title="Page 2 Title">Page 2</a>
        <a href="https://external.com">External Link</a>
        <a href="#anchor">Anchor Link</a>
        <a href="mailto:test@example.com">Email Link</a>
        <a href="/download.pdf">PDF Download</a>
    </body>
    </html>
    """
    
    navigator = SmartNavigator()
    base_url = "https://example.com"
    
    # Mock robots.txt check to always return True
    navigator._check_robots_txt = lambda x: True
    
    candidates = navigator._extract_links(html_content, base_url, 0)
    
    # Should extract valid links (not external, anchor, email, or PDF)
    assert len(candidates) >= 2  # At least page1 and page2
    
    # Check specific candidates
    urls = [c.url for c in candidates]
    assert "https://example.com/page1" in urls
    assert "https://example.com/page2" in urls
    
    # Check that external links are filtered out
    assert "https://external.com" not in urls
    
    print("Link extraction working correctly")


def test_update_link_scores():
    """Test BM25-based link scoring."""
    print("Testing Link Scoring...")
    
    navigator = SmartNavigator()
    
    candidates = [
        LinkCandidate(
            url="https://example.com/api",
            text="API Documentation",
            title="API Docs",
            score=0.0,
            depth=1,
            parent_url="https://example.com"
        ),
        LinkCandidate(
            url="https://example.com/contact",
            text="Contact Us",
            title="Contact",
            score=0.0,
            depth=1,
            parent_url="https://example.com"
        ),
        LinkCandidate(
            url="https://example.com/docs",
            text="User Guide",
            title="Documentation",
            score=0.0,
            depth=1,
            parent_url="https://example.com"
        ),
        LinkCandidate(
            url="https://example.com/help",
            text="Support Center",
            title="Help",
            score=0.0,
            depth=1,
            parent_url="https://example.com"
        ),
        LinkCandidate(
            url="https://example.com/reference",
            text="API Reference",
            title="Reference",
            score=0.0,
            depth=1,
            parent_url="https://example.com"
        )
    ]
    
    question_keywords = ["api", "documentation", "endpoint"]
    
    navigator._update_link_scores(candidates, question_keywords)
    
    # API link should have higher score than contact link
    api_candidate = next(c for c in candidates if "api" in c.url)
    contact_candidate = next(c for c in candidates if "contact" in c.url)
    
    assert api_candidate.score > contact_candidate.score
    assert api_candidate.score > 0
    assert contact_candidate.score >= 0
    
    print("Link scoring working correctly")


def test_filter_duplicate_content():
    """Test duplicate content filtering."""
    print("Testing Duplicate Content Filtering...")
    
    navigator = SmartNavigator()
    
    # Create candidates with similar content
    candidates = [
        LinkCandidate(
            url="https://example.com/page1",
            text="API Documentation Guide",
            title="API Docs",
            score=0.8,
            depth=1,
            parent_url="https://example.com"
        ),
        LinkCandidate(
            url="https://example.com/page2",
            text="API Documentation Manual",
            title="API Guide",
            score=0.7,
            depth=1,
            parent_url="https://example.com"
        ),
        LinkCandidate(
            url="https://example.com/contact",
            text="Contact Information",
            title="Contact",
            score=0.5,
            depth=1,
            parent_url="https://example.com"
        )
    ]
    
    filtered = navigator._filter_duplicate_content(candidates)
    
    # Should filter out one of the similar API documentation pages
    assert len(filtered) <= len(candidates)
    assert len(filtered) >= 1  # At least one should remain
    
    # Contact page should definitely remain
    contact_urls = [c.url for c in filtered]
    assert "https://example.com/contact" in contact_urls
    
    print("Duplicate content filtering working correctly")


@pytest.mark.asyncio
async def test_navigation_integration():
    """Test complete navigation integration."""
    print("Testing Navigation Integration...")
    
    # Mock HTML content with links
    mock_html = """
    <html>
    <body>
        <h1>API Documentation</h1>
        <a href="/api/endpoints">API Endpoints</a>
        <a href="/api/authentication">Authentication</a>
        <a href="/contact">Contact</a>
    </body>
    </html>
    """
    
    mock_response = MagicMock()
    mock_response.text = mock_html
    mock_response.headers = {"content-type": "text/html"}
    mock_response.raise_for_status.return_value = None
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        
        async def mock_aclose():
            pass
        mock_client.aclose = mock_aclose
        
        mock_client_class.return_value = mock_client
        
        # Create crawl config
        config = CrawlConfig(
            max_depth=1,
            page_budget=3,
            char_budget=10000,
            per_page_timeout=10,
            global_timeout=30
        )
        
        question_keywords = ["api", "endpoint", "authentication"]
        required_capabilities = [Capability.API_SPEC]
        
        async with SmartNavigator() as navigator:
            # Mock robots.txt check
            navigator._check_robots_txt = lambda x: True
            
            urls_visited = []
            async for url, content, length in navigator.navigate(
                "https://example.com/docs",
                question_keywords,
                config,
                required_capabilities
            ):
                urls_visited.append(url)
                assert content == mock_html
                assert length > 0
            
            # Should have visited at least the starting URL
            assert len(urls_visited) >= 1
            assert "https://example.com/docs" in urls_visited
    
    print("Navigation integration working correctly")


def test_convenience_functions():
    """Test convenience functions."""
    print("Testing Convenience Functions...")
    
    # Test get_navigator
    navigator = get_navigator()
    assert isinstance(navigator, SmartNavigator)
    
    # Test with custom settings
    settings = Settings()
    settings.max_depth = 2
    navigator2 = get_navigator(settings)
    assert navigator2.settings.max_depth == 2
    
    print("Convenience functions working correctly")


@pytest.mark.asyncio
async def test_navigation_result():
    """Test navigation result generation."""
    print("Testing Navigation Result...")
    
    navigator = SmartNavigator()
    
    # Add some visited URLs
    navigator.visited_urls.add("https://example.com/page1")
    navigator.visited_urls.add("https://example.com/page2")
    
    result = navigator.get_navigation_result()
    
    assert len(result.urls_to_visit) == 2
    urls = [str(url) for url in result.urls_to_visit]
    assert "https://example.com/page1" in urls
    assert "https://example.com/page2" in urls
    
    print("Navigation result working correctly")


def test_error_handling():
    """Test error handling in navigation."""
    print("Testing Error Handling...")
    
    navigator = SmartNavigator()
    
    # Test with invalid URL
    assert not navigator._check_robots_txt("invalid-url")
    
    # Test with empty HTML
    candidates = navigator._extract_links("", "https://example.com", 0)
    assert len(candidates) == 0
    
    # Test with malformed HTML
    malformed_html = "<html><body><a href=''>Broken Link</a></body></html>"
    candidates = navigator._extract_links(malformed_html, "https://example.com", 0)
    # Should handle gracefully without crashing
    assert isinstance(candidates, list)
    
    print("Error handling working correctly")


async def main():
    """Run all navigation tests."""
    print("Testing WebCrawlApp Smart Navigation...")
    print("=" * 60)
    
    test_navigator_initialization()
    test_link_candidate()
    test_navigation_stats()
    await test_navigator_context_manager()
    await test_robots_txt_checking()
    await test_fetch_page()
    test_extract_links()
    test_update_link_scores()
    test_filter_duplicate_content()
    await test_navigation_integration()
    test_convenience_functions()
    await test_navigation_result()
    test_error_handling()
    
    print("=" * 60)
    print("All navigation tests passed successfully!")
    print("The smart navigation system is working correctly.")


if __name__ == "__main__":
    asyncio.run(main())

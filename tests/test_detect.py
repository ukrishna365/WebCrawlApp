"""
Test suite for URL detection module.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from urllib.parse import urlparse
import httpx

from app.detect import URLDetector, detect_url, detect_urls
from app.schemas import DetectionResult, AdapterType, ContentType
from app.settings import Settings


def test_url_detector_initialization():
    """Test URLDetector initialization."""
    print("Testing URLDetector Initialization...")
    
    # Test with default settings
    detector = URLDetector()
    assert detector.settings is not None
    assert detector.client is None
    
    # Test with custom settings
    settings = Settings()
    detector = URLDetector(settings)
    assert detector.settings == settings
    
    print("URLDetector initialization working correctly")


def test_host_pattern_analysis():
    """Test host pattern analysis."""
    print("Testing Host Pattern Analysis...")
    
    detector = URLDetector()
    
    # Test GitHub detection
    github_analysis = detector._analyze_host_patterns("github.com", "https://github.com/user/repo")
    assert github_analysis["adapter_type"] == AdapterType.CODE_REPO
    assert github_analysis["content_type"] == ContentType.CODE_MAP
    assert github_analysis["confidence"] == 0.9
    assert github_analysis["metadata"]["platform"] == "github"
    
    # Test API docs detection
    api_analysis = detector._analyze_host_patterns("api-docs.example.com", "https://api-docs.example.com")
    assert api_analysis["adapter_type"] == AdapterType.API_DOC
    assert api_analysis["content_type"] == ContentType.API_SPEC
    assert api_analysis["confidence"] == 0.8
    
    # Test YouTube detection
    youtube_analysis = detector._analyze_host_patterns("youtube.com", "https://youtube.com/watch?v=123")
    assert youtube_analysis["adapter_type"] == AdapterType.VIDEO
    assert youtube_analysis["content_type"] == ContentType.TRANSCRIPT
    assert youtube_analysis["confidence"] == 0.95
    
    # Test default HTML detection
    default_analysis = detector._analyze_host_patterns("example.com", "https://example.com")
    assert default_analysis["adapter_type"] == AdapterType.HTML
    assert default_analysis["content_type"] == ContentType.SECTION
    assert default_analysis["confidence"] == 0.5
    
    print("Host pattern analysis working correctly")


def test_content_type_sufficiency():
    """Test content type sufficiency checking."""
    print("Testing Content Type Sufficiency...")
    
    detector = URLDetector()
    
    # Test sufficient content types
    assert detector._is_sufficient_content_type("application/json") == True
    assert detector._is_sufficient_content_type("application/xml") == True
    assert detector._is_sufficient_content_type("text/plain") == True
    assert detector._is_sufficient_content_type("application/pdf") == True
    
    # Test insufficient content types
    assert detector._is_sufficient_content_type("text/html") == False
    assert detector._is_sufficient_content_type("image/jpeg") == False
    assert detector._is_sufficient_content_type("") == False
    assert detector._is_sufficient_content_type(None) == False
    
    print("Content type sufficiency checking working correctly")


def test_content_analysis():
    """Test content sample analysis."""
    print("Testing Content Analysis...")
    
    detector = URLDetector()
    
    # Test HTML content
    html_content = "<html><head><title>Test Page</title></head><body><h1>Hello World</h1></body></html>"
    analysis = detector._analyze_content_sample(html_content)
    assert analysis["has_html"] == True
    assert analysis["title"] == "Test Page"
    assert "hello" in analysis["keywords"]
    
    # Test JSON content
    json_content = '{"name": "test", "value": 123}'
    analysis = detector._analyze_content_sample(json_content)
    assert analysis["has_json"] == True
    assert analysis["has_html"] == False
    
    # Test Markdown content
    markdown_content = "# Title\n## Subtitle\n```python\nprint('hello')\n```"
    analysis = detector._analyze_content_sample(markdown_content)
    assert analysis["has_markdown"] == True
    
    # Test code content
    code_content = "def hello_world():\n    print('Hello, World!')\n    return True"
    analysis = detector._analyze_content_sample(code_content)
    assert analysis["has_code"] == True
    
    print("Content analysis working correctly")


def test_detection_result_combination():
    """Test detection result combination."""
    print("Testing Detection Result Combination...")
    
    detector = URLDetector()
    
    # Test basic combination
    host_analysis = {
        "adapter_type": AdapterType.CODE_REPO,
        "content_type": ContentType.CODE_MAP,
        "confidence": 0.9,
        "metadata": {"platform": "github"}
    }
    
    http_analysis = {
        "content_type_header": "text/html",
        "status_code": 200,
        "method": "get",
        "confidence": 0.9,
        "content_analysis": {
            "has_html": True,
            "title": "GitHub Repository",
            "keywords": ["github", "repository", "code"]
        }
    }
    
    result = detector._combine_detection_results(
        "https://github.com/user/repo",
        "github.com",
        host_analysis,
        http_analysis
    )
    
    assert result.url == "https://github.com/user/repo"
    assert result.host == "github.com"
    assert result.adapter_type == AdapterType.CODE_REPO
    assert result.content_type == ContentType.CODE_MAP
    assert result.confidence > 0.8
    assert result.title == "GitHub Repository"
    assert result.detection_method == "combined_analysis"
    
    print("Detection result combination working correctly")


@pytest.mark.asyncio
async def test_http_response_analysis():
    """Test HTTP response analysis."""
    print("Testing HTTP Response Analysis...")
    
    detector = URLDetector()
    
    # Mock successful HEAD response
    mock_response = MagicMock()
    mock_response.headers = {"content-type": "application/json"}
    mock_response.status_code = 200
    
    with patch.object(detector, 'client') as mock_client:
        # Mock the head method as an async function
        async def mock_head(url):
            return mock_response
        mock_client.head = mock_head
        
        analysis = await detector._analyze_http_response("https://api.example.com")
        
        assert analysis["content_type_header"] == "application/json"
        assert analysis["status_code"] == 200
        assert analysis["method"] == "head"
        assert analysis["confidence"] == 0.8
    
    print("HTTP response analysis working correctly")


@pytest.mark.asyncio
async def test_url_detection():
    """Test complete URL detection."""
    print("Testing URL Detection...")
    
    # Mock HTTP responses
    mock_response = MagicMock()
    mock_response.headers = {"content-type": "text/html"}
    mock_response.status_code = 200
    mock_response.text = "<html><head><title>Test Page</title></head><body>Content</body></html>"
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.head.return_value = mock_response
        mock_client.get.return_value = mock_response
        
        # Mock the aclose method as an async function
        async def mock_aclose():
            pass
        mock_client.aclose = mock_aclose
        
        mock_client_class.return_value = mock_client
        
        async with URLDetector() as detector:
            result = await detector.detect_url("https://example.com")
            
            assert isinstance(result, DetectionResult)
            assert result.url == "https://example.com"
            assert result.host == "example.com"
            assert result.adapter_type == AdapterType.HTML
            assert result.content_type == ContentType.SECTION
            assert result.confidence > 0.0
            assert result.title is not None
    
    print("URL detection working correctly")


@pytest.mark.asyncio
async def test_detection_error_handling():
    """Test detection error handling."""
    print("Testing Detection Error Handling...")
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        def mock_head_side_effect(url):
            raise Exception("Connection failed")
        
        def mock_get_side_effect(url, **kwargs):
            raise Exception("Connection failed")
        
        mock_client.head.side_effect = mock_head_side_effect
        mock_client.get.side_effect = mock_get_side_effect
        
        # Mock the aclose method as an async function
        async def mock_aclose():
            pass
        mock_client.aclose = mock_aclose
        
        mock_client_class.return_value = mock_client
        
        async with URLDetector() as detector:
            result = await detector.detect_url("https://invalid-url")
            
            assert isinstance(result, DetectionResult)
            assert result.url == "https://invalid-url"
            assert result.confidence == 0.1
            assert result.detection_method == "error_fallback"
            assert "error" in result.metadata
    
    print("Detection error handling working correctly")


@pytest.mark.asyncio
async def test_convenience_functions():
    """Test convenience functions."""
    print("Testing Convenience Functions...")
    
    # Mock HTTP responses
    mock_response = MagicMock()
    mock_response.headers = {"content-type": "text/html"}
    mock_response.status_code = 200
    mock_response.text = "<html><head><title>Test</title></head><body>Content</body></html>"
    
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.head.return_value = mock_response
        mock_client.get.return_value = mock_response
        
        # Mock the aclose method as an async function
        async def mock_aclose():
            pass
        mock_client.aclose = mock_aclose
        
        mock_client_class.return_value = mock_client
        
        # Test single URL detection
        result = await detect_url("https://example.com")
        assert isinstance(result, DetectionResult)
        
        # Test multiple URL detection
        results = await detect_urls(["https://example.com", "https://github.com/user/repo"])
        assert len(results) == 2
        assert all(isinstance(r, DetectionResult) for r in results)
    
    print("Convenience functions working correctly")


def test_specific_url_patterns():
    """Test detection of specific URL patterns."""
    print("Testing Specific URL Patterns...")
    
    detector = URLDetector()
    
    test_cases = [
        ("https://github.com/microsoft/vscode", AdapterType.CODE_REPO, ContentType.CODE_MAP),
        ("https://swagger.io/docs/", AdapterType.API_DOC, ContentType.API_SPEC),
        ("https://youtube.com/watch?v=123", AdapterType.VIDEO, ContentType.TRANSCRIPT),
        ("https://api.example.com/v1/endpoints", AdapterType.API_DOC, ContentType.API_SPEC),
        ("https://example.com/docs", AdapterType.HTML, ContentType.SECTION),
    ]
    
    for url, expected_adapter, expected_content in test_cases:
        host_analysis = detector._analyze_host_patterns(urlparse(url).netloc.lower(), url)
        assert host_analysis["adapter_type"] == expected_adapter
        assert host_analysis["content_type"] == expected_content
    
    print("Specific URL patterns working correctly")


async def main():
    """Run all detection tests."""
    print("Testing WebCrawlApp URL Detection...")
    print("=" * 60)
    
    try:
        test_url_detector_initialization()
        test_host_pattern_analysis()
        test_content_type_sufficiency()
        test_content_analysis()
        test_detection_result_combination()
        await test_http_response_analysis()
        await test_url_detection()
        await test_detection_error_handling()
        await test_convenience_functions()
        test_specific_url_patterns()
        
        print("=" * 60)
        print("All detection tests passed successfully!")
        print("The URL detection system is working correctly.")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    asyncio.run(main())

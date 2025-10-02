"""
URL Detection Module

Implements light URL sniffing to determine content type, host patterns,
and minimal DOM analysis for intelligent adapter selection.
"""

import asyncio
import re
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse, urljoin
import httpx
from bs4 import BeautifulSoup

from app.schemas import DetectionResult, AdapterType, ContentType
from app.settings import Settings


class URLDetector:
    """Lightweight URL detection and content type analysis."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize detector with settings."""
        self.settings = settings or Settings()
        self.client = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            timeout=self.settings.get_http_config()["timeout"],
            follow_redirects=True,
            headers={"User-Agent": self.settings.get_http_config()["user_agent"]}
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    async def detect_url(self, url: str) -> DetectionResult:
        """
        Perform light detection on a URL to determine content type and adapter.
        
        Args:
            url: URL to analyze
            
        Returns:
            DetectionResult with host, content_type, confidence, and metadata
        """
        try:
            # Parse URL components
            parsed = urlparse(url)
            host = parsed.netloc.lower()
            
            # Initial detection based on host patterns
            host_analysis = self._analyze_host_patterns(host, url)
            
            # Perform light HTTP analysis
            http_analysis = await self._analyze_http_response(url)
            
            # Combine results for final detection
            detection = self._combine_detection_results(
                url, host, host_analysis, http_analysis
            )
            
            return detection
            
        except Exception as e:
            # Return minimal detection result on error
            return DetectionResult(
                url=url,
                host=urlparse(url).netloc.lower(),
                content_type=ContentType.SECTION,
                adapter_type=AdapterType.HTML,
                confidence=0.1,
                title="Detection Error",
                metadata={"error": str(e)},
                detection_method="error_fallback"
            )
    
    def _analyze_host_patterns(self, host: str, url: str) -> Dict:
        """Analyze host patterns to determine likely content type."""
        patterns = {
            # Code repositories
            "github.com": {
                "adapter_type": AdapterType.CODE_REPO,
                "content_type": ContentType.CODE_MAP,
                "confidence": 0.9,
                "metadata": {"platform": "github"}
            },
            "gitlab.com": {
                "adapter_type": AdapterType.CODE_REPO,
                "content_type": ContentType.CODE_MAP,
                "confidence": 0.9,
                "metadata": {"platform": "gitlab"}
            },
            "bitbucket.org": {
                "adapter_type": AdapterType.CODE_REPO,
                "content_type": ContentType.CODE_MAP,
                "confidence": 0.9,
                "metadata": {"platform": "bitbucket"}
            },
            
            # API Documentation
            "swagger.io": {
                "adapter_type": AdapterType.API_DOC,
                "content_type": ContentType.API_SPEC,
                "confidence": 0.95,
                "metadata": {"platform": "swagger"}
            },
            "api-docs": {
                "adapter_type": AdapterType.API_DOC,
                "content_type": ContentType.API_SPEC,
                "confidence": 0.8,
                "metadata": {"platform": "api_docs"}
            },
            "api-docs.example.com": {
                "adapter_type": AdapterType.API_DOC,
                "content_type": ContentType.API_SPEC,
                "confidence": 0.8,
                "metadata": {"platform": "api_docs"}
            },
            "api.example.com": {
                "adapter_type": AdapterType.API_DOC,
                "content_type": ContentType.API_SPEC,
                "confidence": 0.8,
                "metadata": {"platform": "api_docs"}
            },
            
            # Video platforms
            "youtube.com": {
                "adapter_type": AdapterType.VIDEO,
                "content_type": ContentType.TRANSCRIPT,
                "confidence": 0.95,
                "metadata": {"platform": "youtube"}
            },
            "youtu.be": {
                "adapter_type": AdapterType.VIDEO,
                "content_type": ContentType.TRANSCRIPT,
                "confidence": 0.95,
                "metadata": {"platform": "youtube"}
            },
            "vimeo.com": {
                "adapter_type": AdapterType.VIDEO,
                "content_type": ContentType.TRANSCRIPT,
                "confidence": 0.9,
                "metadata": {"platform": "vimeo"}
            }
        }
        
        # Check for exact host matches
        if host in patterns:
            return patterns[host]
        
        # Check for partial matches (subdomains)
        for pattern_host, config in patterns.items():
            if pattern_host in host:
                return {**config, "confidence": config["confidence"] * 0.8}
        
        # Check URL path patterns
        url_lower = url.lower()
        if "/api/" in url_lower or "/docs/" in url_lower:
            return {
                "adapter_type": AdapterType.API_DOC,
                "content_type": ContentType.API_SPEC,
                "confidence": 0.7,
                "metadata": {"pattern": "api_path"}
            }
        
        if "/watch" in url_lower or "/v/" in url_lower:
            return {
                "adapter_type": AdapterType.VIDEO,
                "content_type": ContentType.TRANSCRIPT,
                "confidence": 0.6,
                "metadata": {"pattern": "video_path"}
            }
        
        # Default to HTML
        return {
            "adapter_type": AdapterType.HTML,
            "content_type": ContentType.SECTION,
            "confidence": 0.5,
            "metadata": {"pattern": "default"}
        }
    
    async def _analyze_http_response(self, url: str) -> Dict:
        """Analyze HTTP response for content type detection."""
        try:
            # First try HEAD request for efficiency
            try:
                response = await self.client.head(url)
                content_type = response.headers.get("content-type", "").lower()
                
                # If HEAD works and gives us enough info, use it
                if self._is_sufficient_content_type(content_type):
                    return {
                        "content_type_header": content_type,
                        "status_code": response.status_code,
                        "method": "head",
                        "confidence": 0.8
                    }
            except:
                pass
            
            # Fall back to GET request with limited content
            response = await self.client.get(url, timeout=5.0)
            content_type = response.headers.get("content-type", "").lower()
            
            # Analyze content for additional signals
            content_analysis = self._analyze_content_sample(response.text[:2000])
            
            return {
                "content_type_header": content_type,
                "status_code": response.status_code,
                "method": "get",
                "confidence": 0.9,
                "content_analysis": content_analysis
            }
            
        except Exception as e:
            return {
                "content_type_header": "",
                "status_code": 0,
                "method": "failed",
                "confidence": 0.1,
                "error": str(e)
            }
    
    def _is_sufficient_content_type(self, content_type: str) -> bool:
        """Check if content type header provides sufficient information."""
        if not content_type:
            return False
        
        # These content types give us enough info
        sufficient_types = [
            "application/json",
            "application/xml",
            "text/plain",
            "application/pdf"
        ]
        
        return any(ct in content_type for ct in sufficient_types)
    
    def _analyze_content_sample(self, content: str) -> Dict:
        """Analyze a sample of content for additional signals."""
        analysis = {
            "has_html": False,
            "has_json": False,
            "has_markdown": False,
            "has_code": False,
            "title": "",
            "keywords": []
        }
        
        # Check for HTML
        if "<html" in content.lower() or "<!doctype" in content.lower():
            analysis["has_html"] = True
            
            # Try to extract title
            try:
                soup = BeautifulSoup(content, 'html.parser')
                title_tag = soup.find('title')
                if title_tag:
                    analysis["title"] = title_tag.get_text().strip()
            except:
                pass
        
        # Check for JSON
        if content.strip().startswith('{') or content.strip().startswith('['):
            analysis["has_json"] = True
        
        # Check for Markdown indicators
        markdown_indicators = ['# ', '## ', '### ', '```', '**', '*']
        if any(indicator in content for indicator in markdown_indicators):
            analysis["has_markdown"] = True
        
        # Check for code indicators
        code_indicators = ['def ', 'function ', 'class ', 'import ', 'from ']
        if any(indicator in content for indicator in code_indicators):
            analysis["has_code"] = True
        
        # Extract potential keywords from content
        words = re.findall(r'\b\w{4,}\b', content.lower())
        analysis["keywords"] = list(set(words))[:10]  # Top 10 unique words
        
        return analysis
    
    def _combine_detection_results(
        self, 
        url: str, 
        host: str, 
        host_analysis: Dict, 
        http_analysis: Dict
    ) -> DetectionResult:
        """Combine host and HTTP analysis into final detection result."""
        
        # Start with host analysis as base
        adapter_type = host_analysis.get("adapter_type", AdapterType.HTML)
        content_type = host_analysis.get("content_type", ContentType.SECTION)
        confidence = host_analysis.get("confidence", 0.5)
        metadata = host_analysis.get("metadata", {})
        detection_method = "combined_analysis"  # Default method
        
        # Adjust based on HTTP analysis
        http_confidence = http_analysis.get("confidence", 0)
        http_method = http_analysis.get("method", "")
        
        # If HTTP analysis failed, use its low confidence
        if http_method == "failed":
            confidence = http_confidence
            metadata["error"] = http_analysis.get("error", "HTTP analysis failed")
            detection_method = "error_fallback"
        elif http_confidence > 0.5:
            content_type_header = http_analysis.get("content_type_header", "")
            
            # Override content type based on HTTP headers
            if "application/json" in content_type_header:
                content_type = ContentType.API_SPEC
                adapter_type = AdapterType.API_DOC
                confidence = min(confidence + 0.2, 1.0)
            elif "text/plain" in content_type_header:
                content_type = ContentType.SECTION
                confidence = min(confidence + 0.1, 1.0)
        
        # Use content analysis for additional signals
        content_analysis = http_analysis.get("content_analysis", {})
        if content_analysis:
            if content_analysis.get("has_json"):
                content_type = ContentType.API_SPEC
                adapter_type = AdapterType.API_DOC
                confidence = min(confidence + 0.1, 1.0)
            
            if content_analysis.get("has_code"):
                content_type = ContentType.CODE_MAP
                if adapter_type == AdapterType.HTML:
                    adapter_type = AdapterType.CODE_REPO
                confidence = min(confidence + 0.1, 1.0)
            
            # Add content analysis to metadata
            metadata.update({
                "content_analysis": content_analysis,
                "http_status": http_analysis.get("status_code", 0),
                "detection_method": http_analysis.get("method", "unknown")
            })
        
        # Extract title from content analysis or use host
        title = content_analysis.get("title", "") if content_analysis else ""
        if not title:
            title = f"{host} - {content_type.value.replace('_', ' ').title()}"
        
        return DetectionResult(
            url=url,
            host=host,
            content_type=content_type,
            adapter_type=adapter_type,
            confidence=confidence,
            title=title,
            metadata=metadata,
            detection_method=detection_method
        )


# Convenience functions for easy usage
async def detect_url(url: str, settings: Optional[Settings] = None) -> DetectionResult:
    """
    Convenience function to detect a single URL.
    
    Args:
        url: URL to detect
        settings: Optional settings instance
        
    Returns:
        DetectionResult with detection information
    """
    async with URLDetector(settings) as detector:
        return await detector.detect_url(url)


async def detect_urls(urls: List[str], settings: Optional[Settings] = None) -> List[DetectionResult]:
    """
    Convenience function to detect multiple URLs concurrently.
    
    Args:
        urls: List of URLs to detect
        settings: Optional settings instance
        
    Returns:
        List of DetectionResult objects
    """
    async with URLDetector(settings) as detector:
        tasks = [detector.detect_url(url) for url in urls]
        return await asyncio.gather(*tasks, return_exceptions=True)


# Main function for testing
async def main():
    """Test the detection system."""
    print("Testing WebCrawlApp URL Detection...")
    print("=" * 50)
    
    test_urls = [
        "https://github.com/microsoft/vscode",
        "https://swagger.io/docs/",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "https://example.com/docs",
        "https://api.example.com/v1/endpoints"
    ]
    
    try:
        results = await detect_urls(test_urls)
        
        for result in results:
            if isinstance(result, Exception):
                print(f"Error: {result}")
                continue
                
            print(f"\nURL: {result.url}")
            print(f"Host: {result.host}")
            print(f"Content Type: {result.content_type}")
            print(f"Adapter Type: {result.adapter_type}")
            print(f"Confidence: {result.confidence:.2f}")
            print(f"Title: {result.title}")
            print(f"Method: {result.detection_method}")
            print("-" * 30)
        
        print("\nAll detection tests completed successfully!")
        
    except Exception as e:
        print(f"Detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    asyncio.run(main())
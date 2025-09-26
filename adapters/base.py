"""
Base adapter infrastructure for WebCrawlApp.

This module defines the abstract base class and infrastructure for all content adapters.
Adapters are capability-based and provide specific content extraction capabilities.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set, Union
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

from app.schemas import (
    ContentBlock, ContentType, Capability, AdapterType,
    DetectionResult, ExtractionResult, AdapterConfig
)
from app.settings import get_adapter_config, get_http_config


logger = logging.getLogger(__name__)


class BaseAdapter(ABC):
    """
    Abstract base class for all content adapters.
    
    Adapters are capability-based and provide specific content extraction
    capabilities for different types of web content.
    """
    
    def __init__(self, config: Optional[AdapterConfig] = None):
        """Initialize the adapter with configuration."""
        self.config = config or get_adapter_config()
        self.http_config = get_http_config()
        self.robot_parser: Optional[RobotFileParser] = None
        self._capabilities_cache: Optional[Set[Capability]] = None
        
    @property
    @abstractmethod
    def adapter_type(self) -> AdapterType:
        """Return the type of this adapter."""
        pass
    
    @property
    @abstractmethod
    def supported_capabilities(self) -> Set[Capability]:
        """
        Return the set of capabilities this adapter can provide.
        
        Capabilities define what types of content the adapter can extract:
        - NAV_GRAPH: Navigation structure and links
        - CODE_MAP: Code structure and file organization
        - ROUTES: API routes and endpoints
        - TRANSCRIPT: Video/audio transcripts
        - SECTION: Document sections and content blocks
        - API_SPEC: API specifications and schemas
        - MANIFEST: Package manifests and dependencies
        - README: Documentation and README content
        """
        pass
    
    @abstractmethod
    async def can_handle(self, url: str, content_type: Optional[str] = None, 
                        content_preview: Optional[str] = None) -> DetectionResult:
        """
        Determine if this adapter can handle the given URL and content.
        
        Args:
            url: The URL to analyze
            content_type: HTTP content-type header (optional)
            content_preview: First few KB of content (optional)
            
        Returns:
            DetectionResult with confidence score and metadata
        """
        pass
    
    @abstractmethod
    async def extract_content(self, url: str, capabilities: List[Capability],
                            max_depth: int = 1) -> ExtractionResult:
        """
        Extract content blocks for the specified capabilities.
        
        Args:
            url: The URL to extract content from
            capabilities: List of capabilities to extract
            max_depth: Maximum crawl depth
            
        Returns:
            ExtractionResult with content blocks and metadata
        """
        pass
    
    async def check_robots_txt(self, url: str) -> bool:
        """
        Check if robots.txt allows crawling the given URL.
        
        Args:
            url: The URL to check
            
        Returns:
            True if crawling is allowed, False otherwise
        """
        if not self.http_config.get("respect_robots", True):
            return True
            
        try:
            parsed_url = urlparse(url)
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
            
            if self.robot_parser is None:
                self.robot_parser = RobotFileParser()
                self.robot_parser.set_url(robots_url)
                self.robot_parser.read()
            
            user_agent = self.http_config.get("user_agent", "WebCrawlApp/1.0")
            return self.robot_parser.can_fetch(user_agent, url)
            
        except Exception as e:
            logger.warning(f"Failed to check robots.txt for {url}: {e}")
            return True  # Default to allowing if check fails
    
    async def fetch_content(self, url: str, timeout: int = 10) -> Optional[str]:
        """
        Fetch content from a URL with proper error handling.
        
        Args:
            url: The URL to fetch
            timeout: Request timeout in seconds
            
        Returns:
            Content as string, or None if fetch failed
        """
        try:
            import httpx
            
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                headers={"User-Agent": self.http_config.get("user_agent", "WebCrawlApp/1.0")}
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Check content size limit
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > self.config.max_content_size:
                    logger.warning(f"Content too large for {url}: {content_length} bytes")
                    return None
                
                content = response.text
                if len(content) > self.config.max_content_size:
                    content = content[:self.config.max_content_size]
                    logger.warning(f"Truncated content for {url} to {self.config.max_content_size} bytes")
                
                return content
                
        except Exception as e:
            logger.error(f"Failed to fetch content from {url}: {e}")
            return None
    
    def score_content_quality(self, content: str, content_type: ContentType) -> float:
        """
        Score the quality of extracted content.
        
        Args:
            content: The content to score
            content_type: Type of content
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        if not content or len(content.strip()) < self.config.min_content_length:
            return 0.0
        
        # Basic quality heuristics
        score = 1.0
        
        # Length penalty for very short content
        if len(content) < 50:
            score *= 0.3
        elif len(content) < 100:
            score *= 0.6
        elif len(content) < 200:
            score *= 0.8
        
        # Bonus for structured content (headers, lists, etc.)
        structure_indicators = ["#", "*", "-", "1.", "2.", "<h", "<ul", "<ol", "```"]
        structure_count = sum(1 for indicator in structure_indicators if indicator in content)
        if structure_count > 0:
            score = min(1.0, score + 0.2)
        
        # Penalty for mostly whitespace or repeated characters
        non_whitespace = len([c for c in content if not c.isspace()])
        if non_whitespace < len(content) * 0.7:
            score *= 0.7
        
        # Content-type specific scoring
        if content_type == ContentType.CODE_MAP:
            # Code content should have some structure
            if any(keyword in content.lower() for keyword in ["def ", "class ", "function", "import"]):
                score = min(1.0, score + 0.3)
        
        elif content_type == ContentType.API_SPEC:
            # API content should have endpoint-like patterns
            if any(pattern in content for pattern in ["GET", "POST", "PUT", "DELETE", "/api/"]):
                score = min(1.0, score + 0.3)
        
        return max(0.0, min(1.0, score))
    
    def create_content_block(self, content_type: ContentType, content: str, 
                           url: str, title: Optional[str] = None,
                           metadata: Optional[Dict[str, Any]] = None) -> ContentBlock:
        """
        Create a ContentBlock with quality scoring and validation.
        
        Args:
            content_type: Type of content
            content: The content text
            url: Source URL
            title: Optional title
            metadata: Optional metadata
            
        Returns:
            ContentBlock instance
        """
        # Clean and validate content
        content = content.strip()
        if len(content) < self.config.min_content_length:
            raise ValueError(f"Content too short: {len(content)} < {self.config.min_content_length}")
        
        # Score content quality
        quality_score = self.score_content_quality(content, content_type)
        if quality_score < self.config.content_quality_threshold:
            raise ValueError(f"Content quality too low: {quality_score} < {self.config.content_quality_threshold}")
        
        return ContentBlock(
            content_type=content_type,
            content=content,
            url=url,
            title=title,
            metadata=metadata or {},
            score=quality_score,
            char_count=len(content)
        )
    
    async def extract_links(self, content: str, base_url: str) -> List[str]:
        """
        Extract and normalize links from HTML content.
        
        Args:
            content: HTML content
            base_url: Base URL for resolving relative links
            
        Returns:
            List of normalized absolute URLs
        """
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(content, 'html.parser')
            links = []
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Convert relative URLs to absolute
                absolute_url = urljoin(base_url, href)
                
                # Only include HTTP/HTTPS URLs
                if absolute_url.startswith(('http://', 'https://')):
                    links.append(absolute_url)
            
            return links
            
        except Exception as e:
            logger.error(f"Failed to extract links from content: {e}")
            return []
    
    def get_capabilities_for_question(self, question: str) -> List[Capability]:
        """
        Determine which capabilities are needed for a given question.
        
        Args:
            question: The user's question
            
        Returns:
            List of relevant capabilities
        """
        question_lower = question.lower()
        needed_capabilities = []
        
        # Map question keywords to capabilities
        capability_keywords = {
            Capability.NAV_GRAPH: ["navigate", "navigation", "menu", "link", "page"],
            Capability.CODE_MAP: ["code", "function", "class", "method", "file", "structure"],
            Capability.ROUTES: ["route", "endpoint", "api", "url", "path"],
            Capability.TRANSCRIPT: ["video", "transcript", "audio", "captions"],
            Capability.SECTION: ["section", "chapter", "documentation", "guide", "tutorial"],
            Capability.API_SPEC: ["api", "specification", "schema", "swagger", "openapi"],
            Capability.MANIFEST: ["package", "dependency", "install", "requirements"],
            Capability.README: ["readme", "documentation", "setup", "install", "getting started"]
        }
        
        for capability, keywords in capability_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                if capability in self.supported_capabilities:
                    needed_capabilities.append(capability)
        
        return needed_capabilities
    
    async def validate_url(self, url: str) -> bool:
        """
        Validate that a URL is accessible and appropriate.
        
        Args:
            url: The URL to validate
            
        Returns:
            True if URL is valid, False otherwise
        """
        try:
            parsed = urlparse(url)
            
            # Check scheme
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Check if URL is accessible (quick HEAD request)
            import httpx
            
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.head(url)
                return response.status_code < 400
                
        except Exception:
            return False


class AdapterRegistry:
    """
    Registry for managing and selecting content adapters.
    """
    
    def __init__(self):
        self._adapters: Dict[AdapterType, BaseAdapter] = {}
        self._initialized = False
    
    def register_adapter(self, adapter: BaseAdapter) -> None:
        """Register an adapter in the registry."""
        self._adapters[adapter.adapter_type] = adapter
        logger.info(f"Registered adapter: {adapter.adapter_type}")
    
    async def get_best_adapter(self, url: str, content_type: Optional[str] = None,
                             content_preview: Optional[str] = None) -> Optional[BaseAdapter]:
        """
        Find the best adapter for the given URL and content.
        
        Args:
            url: The URL to analyze
            content_type: HTTP content-type header
            content_preview: First few KB of content
            
        Returns:
            Best matching adapter, or None if no suitable adapter found
        """
        if not self._adapters:
            logger.warning("No adapters registered")
            return None
        
        best_adapter = None
        best_confidence = 0.0
        
        for adapter in self._adapters.values():
            try:
                detection_result = await adapter.can_handle(url, content_type, content_preview)
                
                if detection_result.confidence > best_confidence:
                    best_confidence = detection_result.confidence
                    best_adapter = adapter
                    
            except Exception as e:
                logger.error(f"Error testing adapter {adapter.adapter_type}: {e}")
                continue
        
        if best_adapter and best_confidence > 0.5:  # Minimum confidence threshold
            logger.info(f"Selected adapter {best_adapter.adapter_type} with confidence {best_confidence}")
            return best_adapter
        
        logger.warning(f"No suitable adapter found for {url} (best confidence: {best_confidence})")
        return None
    
    def get_adapter_by_type(self, adapter_type: AdapterType) -> Optional[BaseAdapter]:
        """Get an adapter by its type."""
        return self._adapters.get(adapter_type)
    
    def list_adapters(self) -> List[AdapterType]:
        """List all registered adapter types."""
        return list(self._adapters.keys())
    
    async def initialize_adapters(self) -> None:
        """Initialize all registered adapters."""
        if self._initialized:
            return
        
        for adapter in self._adapters.values():
            try:
                # Any initialization logic can go here
                logger.info(f"Initialized adapter: {adapter.adapter_type}")
            except Exception as e:
                logger.error(f"Failed to initialize adapter {adapter.adapter_type}: {e}")
        
        self._initialized = True


# Global adapter registry instance
adapter_registry = AdapterRegistry()


def register_adapter(adapter: BaseAdapter) -> None:
    """Register an adapter in the global registry."""
    adapter_registry.register_adapter(adapter)


async def get_best_adapter(url: str, content_type: Optional[str] = None,
                          content_preview: Optional[str] = None) -> Optional[BaseAdapter]:
    """Get the best adapter for a URL from the global registry."""
    return await adapter_registry.get_best_adapter(url, content_type, content_preview)


def get_adapter_by_type(adapter_type: AdapterType) -> Optional[BaseAdapter]:
    """Get an adapter by type from the global registry."""
    return adapter_registry.get_adapter_by_type(adapter_type)


async def initialize_adapters() -> None:
    """Initialize all adapters in the global registry."""
    await adapter_registry.initialize_adapters()


# Export the main classes and functions
__all__ = [
    "BaseAdapter",
    "AdapterRegistry", 
    "adapter_registry",
    "register_adapter",
    "get_best_adapter",
    "get_adapter_by_type",
    "initialize_adapters"
]

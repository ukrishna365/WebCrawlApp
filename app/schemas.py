"""
Core data models and schemas for the WebCrawlApp.

This module defines all the Pydantic models used throughout the application,
including content types, capabilities, request/response schemas, and diagnostics.
"""

from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime


class ContentType(str, Enum):
    """Types of content blocks that can be extracted."""
    NAV_BAR = "nav_bar"
    MAIN_BODY = "main_body"
    SECTION = "section"
    TRANSCRIPT = "transcript"
    CODE_MAP = "code_map"
    ROUTE = "route"
    API_SPEC = "api_spec"
    MANIFEST = "manifest"
    README = "readme"
    GENERIC = "generic"


class Capability(str, Enum):
    """Capabilities that adapters can provide."""
    NAV_GRAPH = "nav_graph"
    CODE_MAP = "code_map"
    ROUTES = "routes"
    TRANSCRIPT = "transcript"
    SECTION = "section"
    API_SPEC = "api_spec"
    MANIFEST = "manifest"
    README = "readme"


class AdapterType(str, Enum):
    """Types of content adapters."""
    HTML = "html"
    CODE_REPO = "code_repo"
    API_DOC = "api_doc"
    VIDEO = "video"
    GENERIC = "generic"


class ContentBlock(BaseModel):
    """A block of extracted content with metadata."""
    content_type: ContentType = Field(..., description="Type of content block")
    content: str = Field(..., description="The actual text content")
    url: HttpUrl = Field(..., description="Source URL of the content")
    title: Optional[str] = Field(None, description="Title or heading of the content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    score: float = Field(default=0.0, description="Relevance score for this block")
    char_count: int = Field(..., description="Character count of the content")
    
    class Config:
        json_encoders = {
            HttpUrl: str
        }


class Citation(BaseModel):
    """Citation information for a source."""
    url: HttpUrl = Field(..., description="Source URL")
    title: Optional[str] = Field(None, description="Page or section title")
    snippet: str = Field(..., description="Relevant text snippet")
    content_type: ContentType = Field(..., description="Type of content cited")
    
    class Config:
        json_encoders = {
            HttpUrl: str
        }


class Diagnostics(BaseModel):
    """Performance and diagnostic information."""
    pages_visited: int = Field(default=0, description="Number of pages crawled")
    blocks_extracted: int = Field(default=0, description="Total content blocks extracted")
    blocks_used: int = Field(default=0, description="Blocks used in final answer")
    bytes_fetched: int = Field(default=0, description="Total bytes downloaded")
    tokens_in: int = Field(default=0, description="Input tokens to LLM")
    tokens_out: int = Field(default=0, description="Output tokens from LLM")
    latency_ms: int = Field(default=0, description="Total processing time in milliseconds")
    capped: Dict[str, bool] = Field(default_factory=dict, description="Which limits were reached")
    adapter_used: Optional[AdapterType] = Field(None, description="Primary adapter used")
    capabilities_met: List[Capability] = Field(default_factory=list, description="Capabilities satisfied")


class AnswerRequest(BaseModel):
    """Request schema for the /answer endpoint."""
    url: HttpUrl = Field(..., description="URL to analyze")
    question: str = Field(..., description="Question to answer about the URL")
    max_depth: int = Field(default=1, description="Maximum crawl depth")
    page_budget: int = Field(default=8, description="Maximum pages to visit")
    char_budget: int = Field(default=10000, description="Maximum characters in response")
    timeout_s: int = Field(default=60, description="Global timeout in seconds")
    
    class Config:
        json_encoders = {
            HttpUrl: str
        }


class AnswerResponse(BaseModel):
    """Response schema for the /answer endpoint."""
    answer: str = Field(..., description="Generated answer")
    citations: List[Citation] = Field(default_factory=list, description="Source citations")
    diagnostics: Diagnostics = Field(..., description="Processing diagnostics")
    success: bool = Field(default=True, description="Whether the request was successful")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class DetectionResult(BaseModel):
    """Result of URL content type detection."""
    adapter_type: AdapterType = Field(..., description="Recommended adapter type")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    content_type: Optional[str] = Field(None, description="Detected content type")
    host: str = Field(..., description="Hostname of the URL")
    title: Optional[str] = Field(None, description="Page title if available")
    description: Optional[str] = Field(None, description="Page description if available")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional detection metadata")


class PlanningResult(BaseModel):
    """Result of question analysis and capability planning."""
    required_capabilities: List[Capability] = Field(..., description="Capabilities needed to answer question")
    capability_scores: Dict[Capability, float] = Field(..., description="Importance scores for each capability")
    keywords: List[str] = Field(default_factory=list, description="Extracted keywords from question")
    question_type: str = Field(..., description="Type of question (e.g., 'how_to', 'what_is', 'api_usage')")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in capability analysis")


class NavigationResult(BaseModel):
    """Result of smart navigation phase."""
    urls_to_visit: List[HttpUrl] = Field(..., description="URLs selected for crawling")
    url_scores: Dict[str, float] = Field(..., description="BM25 relevance scores for URLs")
    total_links_found: int = Field(default=0, description="Total links discovered")
    robots_allowed: bool = Field(default=True, description="Whether robots.txt allows crawling")
    
    class Config:
        json_encoders = {
            HttpUrl: str
        }


class ExtractionResult(BaseModel):
    """Result of content extraction phase."""
    content_blocks: List[ContentBlock] = Field(..., description="Extracted content blocks")
    extraction_stats: Dict[str, Union[int, float]] = Field(default_factory=dict, description="Extraction statistics")
    adapter_used: AdapterType = Field(..., description="Adapter that performed extraction")
    capabilities_provided: List[Capability] = Field(..., description="Capabilities provided by extracted content")


class AssemblyResult(BaseModel):
    """Result of content assembly phase."""
    selected_blocks: List[ContentBlock] = Field(..., description="Blocks selected for synthesis")
    assembly_stats: Dict[str, Any] = Field(default_factory=dict, description="Assembly statistics")
    capability_coverage: Dict[Capability, bool] = Field(..., description="Whether each capability is covered")
    char_count: int = Field(..., description="Total character count of selected blocks")
    duplicates_removed: int = Field(default=0, description="Number of duplicate blocks removed")


class SynthesisResult(BaseModel):
    """Result of answer synthesis phase."""
    answer: str = Field(..., description="Generated answer")
    citations: List[Citation] = Field(default_factory=list, description="Citations used in answer")
    synthesis_stats: Dict[str, Any] = Field(default_factory=dict, description="Synthesis statistics")
    llm_model: Optional[str] = Field(None, description="LLM model used for synthesis")
    tokens_used: int = Field(default=0, description="Total tokens used in LLM call")


# Configuration schemas
class CrawlConfig(BaseModel):
    """Configuration for crawling behavior."""
    max_depth: int = Field(default=1, description="Maximum crawl depth")
    page_budget: int = Field(default=8, description="Maximum pages to visit")
    char_budget: int = Field(default=10000, description="Maximum characters in response")
    per_page_timeout: int = Field(default=10, description="Timeout per page in seconds")
    global_timeout: int = Field(default=75, description="Global timeout in seconds")
    js_render_limit: int = Field(default=2, description="Maximum pages to render JavaScript")
    respect_robots: bool = Field(default=True, description="Whether to respect robots.txt")
    user_agent: str = Field(default="WebCrawlApp/1.0", description="User agent string")


class AdapterConfig(BaseModel):
    """Configuration for adapter behavior."""
    enable_cache: bool = Field(default=True, description="Enable content caching")
    max_content_size: int = Field(default=1024*1024, description="Maximum content size to process")
    min_content_length: int = Field(default=100, description="Minimum content length to consider")
    content_quality_threshold: float = Field(default=0.3, description="Minimum content quality score")

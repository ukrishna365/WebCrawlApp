#!/usr/bin/env python3
"""
Tests for Content Assembly Module.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from unittest.mock import Mock

from app.assembly import ContentAssembler, assemble_content_blocks
from app.schemas import (
    ContentBlock, ContentType, Capability, PlanningResult,
    Citation
)
from app.settings import Settings


def test_assembly_initialization():
    """Test content assembler initialization."""
    print("Testing Content Assembler Initialization...")
    
    assembler = ContentAssembler()
    assert assembler is not None
    
    # Test with custom settings
    settings = Settings(char_budget=5000)
    assembler = ContentAssembler(settings)
    assert assembler.settings.char_budget == 5000
    
    print("Content assembler initialization working correctly")


def test_keyword_scoring():
    """Test keyword scoring functionality."""
    print("Testing Keyword Scoring...")
    
    assembler = ContentAssembler()
    
    # Test exact keyword matches
    content = "This is about API documentation and endpoints"
    keywords = ["api", "documentation", "endpoints"]
    score = assembler._calculate_keyword_score(content, keywords)
    assert score > 0.8  # Should be high for exact matches
    
    # Test partial matches
    content = "This is about documentation"
    keywords = ["api", "documentation", "endpoints"]
    score = assembler._calculate_keyword_score(content, keywords)
    assert 0.3 < score < 0.7  # Should be moderate for partial matches
    
    # Test no matches
    content = "This is about something else"
    keywords = ["api", "documentation", "endpoints"]
    score = assembler._calculate_keyword_score(content, keywords)
    assert score == 0.0  # Should be zero for no matches
    
    print("Keyword scoring working correctly")


def test_capability_scoring():
    """Test capability scoring functionality."""
    print("Testing Capability Scoring...")
    
    assembler = ContentAssembler()
    
    capability_scores = {
        Capability.SECTION: 0.8,
        Capability.API_SPEC: 0.9,
        Capability.CODE_MAP: 0.7
    }
    
    # Test API spec scoring
    score = assembler._calculate_capability_score(ContentType.API_SPEC, capability_scores)
    assert score == 0.9
    
    # Test section scoring
    score = assembler._calculate_capability_score(ContentType.SECTION, capability_scores)
    assert score == 0.8
    
    # Test unknown content type
    score = assembler._calculate_capability_score(ContentType.TRANSCRIPT, capability_scores)
    assert score == 0.0
    
    print("Capability scoring working correctly")


def test_url_scoring():
    """Test URL scoring functionality."""
    print("Testing URL Scoring...")
    
    assembler = ContentAssembler()
    
    from app.schemas import HttpUrl
    
    # Test URL with keywords
    url = HttpUrl("https://example.com/api/documentation")
    keywords = ["api", "documentation"]
    score = assembler._calculate_url_score(str(url), keywords)
    assert score > 0.8  # Should be high for keyword matches
    
    # Test URL without keywords
    url = HttpUrl("https://example.com/contact")
    keywords = ["api", "documentation"]
    score = assembler._calculate_url_score(str(url), keywords)
    assert score == 0.0  # Should be zero for no matches
    
    print("URL scoring working correctly")


def test_content_deduplication():
    """Test content deduplication."""
    print("Testing Content Deduplication...")
    
    assembler = ContentAssembler()
    
    # Create blocks with similar content
    content1 = "This is API documentation with detailed information about endpoints and authentication methods."
    content2 = "This is API documentation with detailed information about endpoints and authentication methods."
    content3 = "This is completely different content about user guides and tutorials."
    
    block1 = ContentBlock(
        content_type=ContentType.SECTION,
        content=content1,
        url="https://example.com/api-docs",
        title="API Documentation",
        char_count=len(content1)
    )
    
    block2 = ContentBlock(
        content_type=ContentType.SECTION,
        content=content2,
        url="https://example.com/api-reference",
        title="API Reference",
        char_count=len(content2)
    )
    
    block3 = ContentBlock(
        content_type=ContentType.SECTION,
        content=content3,
        url="https://example.com/user-guide",
        title="User Guide",
        char_count=len(content3)
    )
    
    async def run_test():
        blocks = [block1, block2, block3]
        deduplicated = await assembler._deduplicate_blocks(blocks)
        
        # Should remove one duplicate
        assert len(deduplicated) == 2
        
        # Check that different content is preserved
        content_texts = [block.content for block in deduplicated]
        assert "API documentation" in ' '.join(content_texts)
        assert "user guides" in ' '.join(content_texts)
    
    asyncio.run(run_test())
    print("Content deduplication working correctly")


def test_character_budget():
    """Test character budget application."""
    print("Testing Character Budget...")
    
    # Create settings with small budget
    settings = Settings(char_budget=1000)
    assembler = ContentAssembler(settings)
    
    # Create blocks that exceed budget
    content1 = "This is a moderately sized block with several hundred characters to test the character budget functionality. It contains detailed information about various topics and should be long enough to test the budget limits effectively."
    content2 = "This is another longer block that when combined with the previous block will exceed the 1000 character budget limit. It contains extensive documentation about different aspects of the system including configuration, usage patterns, troubleshooting guides, and best practices for implementation."
    
    block1 = ContentBlock(
        content_type=ContentType.SECTION,
        content=content1,
        url="https://example.com/short",
        title="Short Block",
        char_count=len(content1)
    )
    
    block2 = ContentBlock(
        content_type=ContentType.SECTION,
        content=content2,
        url="https://example.com/long",
        title="Long Block",
        char_count=len(content2)
    )
    
    async def run_test():
        blocks = [block1, block2]
        budgeted = assembler._apply_character_budget(blocks)
        
        # Should only include blocks within budget
        total_chars = sum(len(block.content) for block in budgeted)
        assert total_chars <= settings.char_budget
        
        # Should include at least the first block
        assert len(budgeted) >= 1
    
    asyncio.run(run_test())
    print("Character budget working correctly")


def test_citation_preparation():
    """Test citation preparation."""
    print("Testing Citation Preparation...")
    
    assembler = ContentAssembler()
    
    content1 = "This is the first block with substantial content that provides detailed information about the topic."
    content2 = "This is the second block with different content about API specifications and endpoints."
    
    blocks = [
        ContentBlock(
            content_type=ContentType.SECTION,
            content=content1,
            url="https://example.com/first",
            title="First Block",
            char_count=len(content1)
        ),
        ContentBlock(
            content_type=ContentType.API_SPEC,
            content=content2,
            url="https://example.com/second",
            title="Second Block",
            char_count=len(content2)
        )
    ]
    
    citations = assembler._prepare_citations(blocks)
    
    # Should create citations for all blocks
    assert len(citations) == 2
    
    # Check citation content
    citation_urls = [str(citation.url) for citation in citations]
    assert "https://example.com/first" in citation_urls
    assert "https://example.com/second" in citation_urls
    
    # Check snippets
    for citation in citations:
        assert len(citation.snippet) > 0
        assert citation.title is not None
    
    print("Citation preparation working correctly")


def test_capability_coverage():
    """Test capability coverage calculation."""
    print("Testing Capability Coverage...")
    
    assembler = ContentAssembler()
    
    content1 = "Section content"
    content2 = "API content"
    
    blocks = [
        ContentBlock(
            content_type=ContentType.SECTION,
            content=content1,
            url="https://example.com/section",
            title="Section",
            char_count=len(content1)
        ),
        ContentBlock(
            content_type=ContentType.API_SPEC,
            content=content2,
            url="https://example.com/api",
            title="API",
            char_count=len(content2)
        )
    ]
    
    required_capabilities = [Capability.SECTION, Capability.API_SPEC, Capability.CODE_MAP]
    coverage = assembler._calculate_coverage(blocks, required_capabilities)
    
    # Should cover SECTION and API_SPEC but not CODE_MAP
    assert coverage[Capability.SECTION] == True
    assert coverage[Capability.API_SPEC] == True
    assert coverage[Capability.CODE_MAP] == False
    
    print("Capability coverage working correctly")


def test_full_assembly_process():
    """Test the complete assembly process."""
    print("Testing Full Assembly Process...")
    
    # Create mock planning result
    planning_result = PlanningResult(
        question="How do I use the API?",
        normalized_question="how do i use api",
        required_capabilities=[Capability.API_SPEC, Capability.SECTION],
        capability_scores={
            Capability.API_SPEC: 0.9,
            Capability.SECTION: 0.7
        },
        capability_priority=[Capability.API_SPEC, Capability.SECTION],
        keywords=["api", "use"],
        question_type="how_to",
        confidence=0.8,
        planning_method="keyword_analysis"
    )
    
    # Create test blocks
    content1 = "This is general documentation about the system and how to get started with basic usage patterns."
    content2 = "This is detailed API documentation with endpoints, authentication, and request/response examples."
    content3 = "This is duplicate content that should be removed during assembly."
    
    blocks = [
        ContentBlock(
            content_type=ContentType.SECTION,
            content=content1,
            url="https://example.com/docs",
            title="Documentation",
            char_count=len(content1),
            metadata={"quality_score": 0.8}
        ),
        ContentBlock(
            content_type=ContentType.API_SPEC,
            content=content2,
            url="https://example.com/api-docs",
            title="API Documentation",
            char_count=len(content2),
            metadata={"quality_score": 0.9}
        ),
        ContentBlock(
            content_type=ContentType.SECTION,
            content=content3,
            url="https://example.com/docs-copy",
            title="Documentation Copy",
            char_count=len(content3),
            metadata={"quality_score": 0.8}
        )
    ]
    
    async def run_test():
        assembler = ContentAssembler()
        result = await assembler.assemble_content(blocks, planning_result)
        
        # Should have processed blocks
        assert len(result.selected_blocks) > 0
        
        # Should have coverage information
        assert len(result.capability_coverage) > 0
        
        # Should have assembly stats
        assert "blocks_original" in result.assembly_stats
        assert "blocks_final" in result.assembly_stats
        
        # API_SPEC should be covered
        assert result.capability_coverage[Capability.API_SPEC] == True
    
    asyncio.run(run_test())
    print("Full assembly process working correctly")


def test_convenience_functions():
    """Test convenience functions."""
    print("Testing Convenience Functions...")
    
    from app.assembly import get_assembler
    
    # Test get_assembler
    assembler = get_assembler()
    assert isinstance(assembler, ContentAssembler)
    
    # Test with settings
    settings = Settings(char_budget=1000)
    assembler = get_assembler(settings)
    assert assembler.settings.char_budget == 1000
    
    print("Convenience functions working correctly")


if __name__ == "__main__":
    test_assembly_initialization()
    test_keyword_scoring()
    test_capability_scoring()
    test_url_scoring()
    test_content_deduplication()
    test_character_budget()
    test_citation_preparation()
    test_capability_coverage()
    test_full_assembly_process()
    test_convenience_functions()
    print("\nAll assembly tests passed!")

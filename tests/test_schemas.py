"""
Test script for app/schemas.py to validate all data models work correctly.

Run this with: python test_schemas.py
"""

import json
from datetime import datetime
from app.schemas import (
    ContentType, Capability, AdapterType,
    ContentBlock, Citation, Diagnostics,
    AnswerRequest, AnswerResponse,
    DetectionResult, PlanningResult, NavigationResult,
    ExtractionResult, AssemblyResult, SynthesisResult,
    CrawlConfig, AdapterConfig
)


def test_enums():
    """Test that all enums work correctly."""
    print("Testing Enums...")
    
    # Test ContentType
    assert ContentType.NAV_BAR == "nav_bar"
    assert ContentType.MAIN_BODY == "main_body"
    assert ContentType.TRANSCRIPT == "transcript"
    
    # Test Capability
    assert Capability.NAV_GRAPH == "nav_graph"
    assert Capability.CODE_MAP == "code_map"
    assert Capability.ROUTES == "routes"
    
    # Test AdapterType
    assert AdapterType.HTML == "html"
    assert AdapterType.CODE_REPO == "code_repo"
    assert AdapterType.API_DOC == "api_doc"
    
    print("All enums working correctly")


def test_content_block():
    """Test ContentBlock creation and validation."""
    print("Testing ContentBlock...")
    
    # Valid ContentBlock
    block = ContentBlock(
        content_type=ContentType.MAIN_BODY,
        content="This is some sample content for testing.",
        url="https://example.com/page",
        title="Test Page",
        score=0.85,
        char_count=42
    )
    
    assert block.content_type == ContentType.MAIN_BODY
    assert block.content == "This is some sample content for testing."
    assert str(block.url) == "https://example.com/page"
    assert block.title == "Test Page"
    assert block.score == 0.85
    assert block.char_count == 42
    
    # Test JSON serialization
    json_data = block.model_dump()
    assert json_data["content_type"] == "main_body"
    assert json_data["score"] == 0.85
    
    print("ContentBlock working correctly")


def test_citation():
    """Test Citation creation and validation."""
    print("Testing Citation...")
    
    citation = Citation(
        url="https://example.com/docs",
        title="API Documentation",
        snippet="This API endpoint returns user data.",
        content_type=ContentType.API_SPEC
    )
    
    assert str(citation.url) == "https://example.com/docs"
    assert citation.title == "API Documentation"
    assert citation.snippet == "This API endpoint returns user data."
    assert citation.content_type == ContentType.API_SPEC
    
    print("Citation working correctly")


def test_diagnostics():
    """Test Diagnostics creation and validation."""
    print("Testing Diagnostics...")
    
    diagnostics = Diagnostics(
        pages_visited=5,
        blocks_extracted=12,
        blocks_used=8,
        bytes_fetched=50000,
        tokens_in=1500,
        tokens_out=200,
        latency_ms=3000,
        capped={"page_budget": False, "char_budget": True},
        adapter_used=AdapterType.HTML,
        capabilities_met=[Capability.SECTION, Capability.NAV_GRAPH]
    )
    
    assert diagnostics.pages_visited == 5
    assert diagnostics.blocks_extracted == 12
    assert diagnostics.blocks_used == 8
    assert diagnostics.adapter_used == AdapterType.HTML
    assert Capability.SECTION in diagnostics.capabilities_met
    assert diagnostics.capped["char_budget"] == True
    
    print("Diagnostics working correctly")


def test_answer_request():
    """Test AnswerRequest creation and validation."""
    print("Testing AnswerRequest...")
    
    request = AnswerRequest(
        url="https://github.com/user/repo",
        question="How do I install this project?",
        max_depth=2,
        page_budget=10,
        char_budget=15000,
        timeout_s=90
    )
    
    assert str(request.url) == "https://github.com/user/repo"
    assert request.question == "How do I install this project?"
    assert request.max_depth == 2
    assert request.page_budget == 10
    assert request.char_budget == 15000
    assert request.timeout_s == 90
    
    # Test default values
    request_default = AnswerRequest(
        url="https://example.com",
        question="What is this?"
    )
    assert request_default.max_depth == 1
    assert request_default.page_budget == 8
    assert request_default.char_budget == 10000
    assert request_default.timeout_s == 60
    
    print("AnswerRequest working correctly")


def test_answer_response():
    """Test AnswerResponse creation and validation."""
    print("Testing AnswerResponse...")
    
    citation = Citation(
        url="https://example.com/docs",
        title="Installation Guide",
        snippet="Run pip install package",
        content_type=ContentType.SECTION
    )
    
    diagnostics = Diagnostics(
        pages_visited=3,
        blocks_extracted=5,
        blocks_used=3,
        bytes_fetched=25000,
        latency_ms=1500,
        adapter_used=AdapterType.CODE_REPO
    )
    
    response = AnswerResponse(
        answer="To install this project, run 'pip install package' as shown in the documentation.",
        citations=[citation],
        diagnostics=diagnostics,
        success=True
    )
    
    assert response.answer.startswith("To install this project")
    assert len(response.citations) == 1
    assert response.citations[0].title == "Installation Guide"
    assert response.diagnostics.pages_visited == 3
    assert response.success == True
    
    print("AnswerResponse working correctly")


def test_detection_result():
    """Test DetectionResult creation and validation."""
    print("Testing DetectionResult...")
    
    result = DetectionResult(
        adapter_type=AdapterType.CODE_REPO,
        confidence=0.95,
        content_type="text/html",
        host="github.com",
        title="User/Repo: A Python Project",
        description="A sample Python project with documentation",
        metadata={"stars": 150, "language": "Python"}
    )
    
    assert result.adapter_type == AdapterType.CODE_REPO
    assert result.confidence == 0.95
    assert result.host == "github.com"
    assert result.title == "User/Repo: A Python Project"
    assert result.metadata["stars"] == 150
    assert result.metadata["language"] == "Python"
    
    print("DetectionResult working correctly")


def test_planning_result():
    """Test PlanningResult creation and validation."""
    print("Testing PlanningResult...")
    
    result = PlanningResult(
        required_capabilities=[Capability.README, Capability.CODE_MAP],
        capability_scores={
            Capability.README: 0.9,
            Capability.CODE_MAP: 0.7,
            Capability.ROUTES: 0.3
        },
        keywords=["install", "setup", "requirements"],
        question_type="how_to",
        confidence=0.85
    )
    
    assert Capability.README in result.required_capabilities
    assert Capability.CODE_MAP in result.required_capabilities
    assert result.capability_scores[Capability.README] == 0.9
    assert "install" in result.keywords
    assert result.question_type == "how_to"
    assert result.confidence == 0.85
    
    print("PlanningResult working correctly")


def test_navigation_result():
    """Test NavigationResult creation and validation."""
    print("Testing NavigationResult...")
    
    result = NavigationResult(
        urls_to_visit=[
            "https://example.com/docs",
            "https://example.com/install",
            "https://example.com/api"
        ],
        url_scores={
            "https://example.com/docs": 0.95,
            "https://example.com/install": 0.88,
            "https://example.com/api": 0.72
        },
        total_links_found=25,
        robots_allowed=True
    )
    
    assert len(result.urls_to_visit) == 3
    assert "https://example.com/docs" in [str(url) for url in result.urls_to_visit]
    assert result.url_scores["https://example.com/docs"] == 0.95
    assert result.total_links_found == 25
    assert result.robots_allowed == True
    
    print("NavigationResult working correctly")


def test_extraction_result():
    """Test ExtractionResult creation and validation."""
    print("Testing ExtractionResult...")
    
    block1 = ContentBlock(
        content_type=ContentType.README,
        content="Installation instructions here...",
        url="https://example.com/readme",
        title="README",
        char_count=500
    )
    
    block2 = ContentBlock(
        content_type=ContentType.CODE_MAP,
        content="Project structure...",
        url="https://example.com/structure",
        title="Project Structure",
        char_count=300
    )
    
    result = ExtractionResult(
        content_blocks=[block1, block2],
        extraction_stats={"total_blocks": 2, "avg_score": 0.75},
        adapter_used=AdapterType.CODE_REPO,
        capabilities_provided=[Capability.README, Capability.CODE_MAP]
    )
    
    assert len(result.content_blocks) == 2
    assert result.content_blocks[0].content_type == ContentType.README
    assert result.extraction_stats["total_blocks"] == 2
    assert result.adapter_used == AdapterType.CODE_REPO
    assert Capability.README in result.capabilities_provided
    
    print("ExtractionResult working correctly")


def test_assembly_result():
    """Test AssemblyResult creation and validation."""
    print("Testing AssemblyResult...")
    
    block = ContentBlock(
        content_type=ContentType.SECTION,
        content="Selected content block",
        url="https://example.com/section",
        title="Selected Section",
        char_count=800
    )
    
    result = AssemblyResult(
        selected_blocks=[block],
        assembly_stats={"initial_blocks": 5, "final_blocks": 1},
        capability_coverage={
            Capability.SECTION: True,
            Capability.NAV_GRAPH: False
        },
        char_count=800,
        duplicates_removed=4
    )
    
    assert len(result.selected_blocks) == 1
    assert result.assembly_stats["final_blocks"] == 1
    assert result.capability_coverage[Capability.SECTION] == True
    assert result.capability_coverage[Capability.NAV_GRAPH] == False
    assert result.char_count == 800
    assert result.duplicates_removed == 4
    
    print("AssemblyResult working correctly")


def test_synthesis_result():
    """Test SynthesisResult creation and validation."""
    print("Testing SynthesisResult...")
    
    citation = Citation(
        url="https://example.com/docs",
        title="Documentation",
        snippet="Key information here",
        content_type=ContentType.SECTION
    )
    
    result = SynthesisResult(
        answer="Based on the documentation, here's how to proceed...",
        citations=[citation],
        synthesis_stats={"blocks_used": 3, "quality_score": 0.9},
        llm_model="gpt-3.5-turbo",
        tokens_used=1250
    )
    
    assert result.answer.startswith("Based on the documentation")
    assert len(result.citations) == 1
    assert result.synthesis_stats["blocks_used"] == 3
    assert result.llm_model == "gpt-3.5-turbo"
    assert result.tokens_used == 1250
    
    print("SynthesisResult working correctly")


def test_config_schemas():
    """Test configuration schemas."""
    print("Testing Configuration Schemas...")
    
    # Test CrawlConfig
    crawl_config = CrawlConfig(
        max_depth=3,
        page_budget=15,
        char_budget=20000,
        per_page_timeout=15,
        global_timeout=120,
        js_render_limit=5,
        respect_robots=False,
        user_agent="CustomBot/1.0"
    )
    
    assert crawl_config.max_depth == 3
    assert crawl_config.page_budget == 15
    assert crawl_config.char_budget == 20000
    assert crawl_config.respect_robots == False
    assert crawl_config.user_agent == "CustomBot/1.0"
    
    # Test AdapterConfig
    adapter_config = AdapterConfig(
        enable_cache=False,
        max_content_size=2*1024*1024,
        min_content_length=200,
        content_quality_threshold=0.5
    )
    
    assert adapter_config.enable_cache == False
    assert adapter_config.max_content_size == 2*1024*1024
    assert adapter_config.min_content_length == 200
    assert adapter_config.content_quality_threshold == 0.5
    
    print("Configuration schemas working correctly")


def test_json_serialization():
    """Test JSON serialization and deserialization."""
    print("Testing JSON Serialization...")
    
    # Create a complex object
    request = AnswerRequest(
        url="https://example.com",
        question="Test question?",
        max_depth=2
    )
    
    # Serialize to JSON
    json_str = request.model_dump_json()
    json_data = json.loads(json_str)
    
    # Check that URL is properly serialized (Pydantic normalizes URLs with trailing slash)
    assert str(json_data["url"]) == "https://example.com/"
    assert json_data["question"] == "Test question?"
    assert json_data["max_depth"] == 2
    
    # Deserialize back
    request_restored = AnswerRequest.model_validate(json_data)
    assert str(request_restored.url) == str(request.url)
    assert request_restored.question == request.question
    assert request_restored.max_depth == request.max_depth
    
    print("JSON serialization working correctly")


def test_validation_errors():
    """Test that validation works correctly for invalid data."""
    print("Testing Validation Errors...")
    
    try:
        # Invalid URL should raise validation error
        AnswerRequest(
            url="not-a-valid-url",
            question="Test?"
        )
        assert False, "Should have raised validation error for invalid URL"
    except Exception as e:
        print(f"Correctly caught validation error: {type(e).__name__}")
    
    try:
        # Invalid confidence score should raise validation error
        DetectionResult(
            adapter_type=AdapterType.HTML,
            confidence=1.5,  # Should be <= 1.0
            host="example.com"
        )
        assert False, "Should have raised validation error for invalid confidence"
    except Exception as e:
        print(f"Correctly caught validation error: {type(e).__name__}")
    
    print("Validation errors working correctly")


def main():
    """Run all tests."""
    print("Testing WebCrawlApp Schemas...")
    print("=" * 50)
    
    try:
        test_enums()
        test_content_block()
        test_citation()
        test_diagnostics()
        test_answer_request()
        test_answer_response()
        test_detection_result()
        test_planning_result()
        test_navigation_result()
        test_extraction_result()
        test_assembly_result()
        test_synthesis_result()
        test_config_schemas()
        test_json_serialization()
        test_validation_errors()
        
        print("=" * 50)
        print("All schema tests passed successfully!")
        print("The schemas block of the pipeline is working correctly.")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

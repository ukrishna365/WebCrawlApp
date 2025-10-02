"""
Test suite for question planning module.
"""

import pytest

from app.planner import QuestionPlanner, plan_question, get_capabilities_for_question
from app.schemas import Capability, PlanningResult
from app.settings import Settings


def test_planner_initialization():
    """Test QuestionPlanner initialization."""
    print("Testing QuestionPlanner Initialization...")
    
    # Test with default settings
    planner = QuestionPlanner()
    assert planner.settings is not None
    assert len(planner.capability_keywords) > 0
    assert len(planner.question_types) > 0
    
    # Test with custom settings
    settings = Settings()
    planner = QuestionPlanner(settings)
    assert planner.settings == settings
    
    print("QuestionPlanner initialization working correctly")


def test_question_normalization():
    """Test question normalization."""
    print("Testing Question Normalization...")
    
    planner = QuestionPlanner()
    
    test_cases = [
        ("How do I navigate the code?", "how do i navigate code?"),
        ("  What is the API endpoint?  ", "what is api endpoint?"),
        ("The quick brown fox jumps", "quick brown fox jumps"),
        ("How to use the navigation menu?", "how use navigation menu?")
    ]
    
    for input_question, expected in test_cases:
        result = planner._normalize_question(input_question)
        assert result == expected
    
    print("Question normalization working correctly")


def test_keyword_extraction():
    """Test keyword extraction."""
    print("Testing Keyword Extraction...")
    
    planner = QuestionPlanner()
    
    test_cases = [
        ("How do I navigate the code structure?", ["navigate", "code", "structure"]),
        ("What is the API endpoint for authentication?", ["api", "endpoint", "authentication"]),
        ("Where can I find the documentation?", ["where", "find", "documentation"]),
        ("How to set up the development environment?", ["set", "development", "environment"])
    ]
    
    for question, expected_keywords in test_cases:
        keywords = planner._extract_keywords(question)
        # Check that most expected keywords are present
        assert len(set(keywords) & set(expected_keywords)) >= len(expected_keywords) // 2
    
    print("Keyword extraction working correctly")


def test_question_type_classification():
    """Test question type classification."""
    print("Testing Question Type Classification...")
    
    planner = QuestionPlanner()
    
    test_cases = [
        ("How do I navigate the code?", "how_to"),
        ("What is the API endpoint?", "what_is"),
        ("Where can I find the documentation?", "where_is"),
        ("Why is this important?", "why"),
        ("When should I use this?", "when"),
        ("Tell me about the project", "general")
    ]
    
    for question, expected_type in test_cases:
        result = planner._classify_question_type(question)
        assert result == expected_type
    
    print("Question type classification working correctly")


def test_capability_scoring():
    """Test capability scoring."""
    print("Testing Capability Scoring...")
    
    planner = QuestionPlanner()
    
    # Test code-related question
    code_question = "How do I navigate the code structure?"
    code_scores = planner._score_capabilities(code_question, ["code", "structure"])
    assert code_scores[Capability.CODE_MAP] > 0.3
    assert code_scores[Capability.ROUTES] > 0.2
    
    # Test API-related question
    api_question = "What is the API endpoint for authentication?"
    api_scores = planner._score_capabilities(api_question, ["api", "endpoint"])
    assert api_scores[Capability.API_SPEC] > 0.4
    
    # Test documentation question
    doc_question = "Where can I find the documentation?"
    doc_keywords = planner._extract_keywords(doc_question)
    doc_scores = planner._score_capabilities(doc_question, doc_keywords)
    assert doc_scores[Capability.SECTION] > 0.3
    assert doc_scores[Capability.NAV_GRAPH] > 0.2
    
    print("Capability scoring working correctly")


def test_fallback_capabilities():
    """Test fallback capabilities."""
    print("Testing Fallback Capabilities...")
    
    planner = QuestionPlanner()
    
    test_cases = [
        ("how_to", {Capability.SECTION: 0.6, Capability.README: 0.4}),
        ("what_is", {Capability.SECTION: 0.7, Capability.README: 0.3}),
        ("where_is", {Capability.NAV_GRAPH: 0.5, Capability.ROUTES: 0.5}),
        ("why", {Capability.SECTION: 0.8}),
        ("when", {Capability.SECTION: 0.6, Capability.MANIFEST: 0.4}),
        ("general", {Capability.SECTION: 0.5, Capability.README: 0.3})
    ]
    
    for question_type, expected_fallbacks in test_cases:
        fallbacks = planner._get_fallback_capabilities(question_type)
        assert fallbacks == expected_fallbacks
    
    print("Fallback capabilities working correctly")


def test_confidence_calculation():
    """Test confidence calculation."""
    print("Testing Confidence Calculation...")
    
    planner = QuestionPlanner()
    
    # Test high confidence case
    high_capabilities = {Capability.CODE_MAP: 0.8, Capability.ROUTES: 0.6}
    high_confidence = planner._calculate_confidence(high_capabilities, "how_to", 5)
    assert high_confidence > 0.7
    
    # Test low confidence case
    low_capabilities = {Capability.SECTION: 0.3}
    low_confidence = planner._calculate_confidence(low_capabilities, "general", 1)
    assert low_confidence < 0.5
    
    # Test empty capabilities
    empty_confidence = planner._calculate_confidence({}, "general", 0)
    assert empty_confidence == 0.1
    
    print("Confidence calculation working correctly")


def test_capability_priority():
    """Test capability priority ordering."""
    print("Testing Capability Priority...")
    
    planner = QuestionPlanner()
    
    capabilities = {
        Capability.CODE_MAP: 0.8,
        Capability.ROUTES: 0.6,
        Capability.SECTION: 0.4
    }
    
    priority = planner._get_capability_priority(capabilities)
    assert priority[0] == Capability.CODE_MAP
    assert priority[1] == Capability.ROUTES
    assert priority[2] == Capability.SECTION
    
    print("Capability priority working correctly")


def test_plan_question():
    """Test complete question planning."""
    print("Testing Question Planning...")
    
    planner = QuestionPlanner()
    
    test_questions = [
        "How do I navigate the code structure?",
        "What is the API endpoint for authentication?",
        "Where can I find the documentation?",
        "How to set up the development environment?",
        "What are the installation requirements?"
    ]
    
    for question in test_questions:
        result = planner.plan_question(question)
        
        assert isinstance(result, PlanningResult)
        assert result.question == question
        assert result.normalized_question is not None
        assert len(result.required_capabilities) > 0
        assert len(result.capability_scores) > 0
        assert len(result.keywords) > 0
        assert result.question_type is not None
        assert 0.0 <= result.confidence <= 1.0
        assert result.planning_method == "keyword_analysis"
    
    print("Question planning working correctly")


def test_specific_question_types():
    """Test planning for specific question types."""
    print("Testing Specific Question Types...")
    
    planner = QuestionPlanner()
    
    # Test code-related question
    code_result = planner.plan_question("How do I navigate the code structure?")
    assert Capability.CODE_MAP in code_result.required_capabilities
    assert code_result.question_type == "how_to"
    assert code_result.confidence > 0.5
    
    # Test API-related question
    api_result = planner.plan_question("What is the API endpoint for authentication?")
    assert Capability.API_SPEC in api_result.required_capabilities
    assert api_result.question_type == "what_is"
    assert api_result.confidence > 0.5
    
    # Test navigation question
    nav_result = planner.plan_question("Where can I find the documentation?")
    assert Capability.NAV_GRAPH in nav_result.required_capabilities or Capability.ROUTES in nav_result.required_capabilities
    assert nav_result.question_type == "where_is"
    assert nav_result.confidence > 0.5
    
    # Test video question
    video_result = planner.plan_question("What does the video say about authentication?")
    assert Capability.TRANSCRIPT in video_result.required_capabilities
    assert video_result.confidence > 0.5
    
    print("Specific question types working correctly")


def test_convenience_functions():
    """Test convenience functions."""
    print("Testing Convenience Functions...")
    
    # Test plan_question function
    result = plan_question("How do I navigate the code?")
    assert isinstance(result, PlanningResult)
    assert result.question == "How do I navigate the code?"
    
    # Test get_capabilities_for_question function
    capabilities = get_capabilities_for_question("What is the API endpoint?")
    assert isinstance(capabilities, list)
    assert len(capabilities) > 0
    assert all(isinstance(cap, Capability) for cap in capabilities)
    
    print("Convenience functions working correctly")


def test_edge_cases():
    """Test edge cases and error handling."""
    print("Testing Edge Cases...")
    
    planner = QuestionPlanner()
    
    # Test empty question
    empty_result = planner.plan_question("")
    assert empty_result.question == ""
    assert len(empty_result.required_capabilities) > 0  # Should have fallback
    
    # Test very short question
    short_result = planner.plan_question("Hi")
    assert short_result.question == "Hi"
    assert len(short_result.required_capabilities) > 0  # Should have fallback
    
    # Test question with special characters
    special_result = planner.plan_question("How do I use the API? (with examples)")
    assert special_result.question == "How do I use the API? (with examples)"
    assert Capability.API_SPEC in special_result.required_capabilities
    
    # Test question with numbers
    number_result = planner.plan_question("How to configure port 8080?")
    assert number_result.question == "How to configure port 8080?"
    assert len(number_result.keywords) > 0
    
    print("Edge cases working correctly")


def test_capability_keyword_mappings():
    """Test that capability keyword mappings are comprehensive."""
    print("Testing Capability Keyword Mappings...")
    
    planner = QuestionPlanner()
    
    # Test that all capabilities have keyword mappings
    expected_capabilities = [
        Capability.CODE_MAP, Capability.ROUTES, Capability.NAV_GRAPH,
        Capability.TRANSCRIPT, Capability.SECTION, Capability.API_SPEC,
        Capability.MANIFEST, Capability.README
    ]
    
    for capability in expected_capabilities:
        assert capability in planner.capability_keywords
        config = planner.capability_keywords[capability]
        assert "keywords" in config
        assert "patterns" in config
        assert len(config["keywords"]) > 0
        assert len(config["patterns"]) > 0
    
    print("Capability keyword mappings working correctly")


def test_question_type_patterns():
    """Test that question type patterns are comprehensive."""
    print("Testing Question Type Patterns...")
    
    planner = QuestionPlanner()
    
    # Test that all question types have patterns
    expected_types = ["how_to", "what_is", "where_is", "why", "when"]
    
    for question_type in expected_types:
        assert question_type in planner.question_types
        patterns = planner.question_types[question_type]
        assert len(patterns) > 0
    
    print("Question type patterns working correctly")


def main():
    """Run all planning tests."""
    print("Testing WebCrawlApp Question Planning...")
    print("=" * 60)
    
    try:
        test_planner_initialization()
        test_question_normalization()
        test_keyword_extraction()
        test_question_type_classification()
        test_capability_scoring()
        test_fallback_capabilities()
        test_confidence_calculation()
        test_capability_priority()
        test_plan_question()
        test_specific_question_types()
        test_convenience_functions()
        test_edge_cases()
        test_capability_keyword_mappings()
        test_question_type_patterns()
        
        print("=" * 60)
        print("All planning tests passed successfully!")
        print("The question planning system is working correctly.")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    main()

"""
Question Planning Module

Analyzes user questions to determine required capabilities and map them
to appropriate adapters and content types.
"""

import re
from typing import Dict, List, Set, Tuple, Optional
from collections import Counter

from app.schemas import PlanningResult, Capability, ContentType, AdapterType
from app.settings import Settings


class QuestionPlanner:
    """Analyzes questions to determine required capabilities and priorities."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize planner with settings."""
        self.settings = settings or Settings()
        
        # Keyword mappings to capabilities
        self.capability_keywords = {
            Capability.CODE_MAP: {
                "keywords": [
                    "code", "function", "class", "method", "implementation",
                    "source", "repository", "repo", "github", "gitlab",
                    "programming", "development", "coding", "script",
                    "api", "endpoint", "service", "module", "package"
                ],
                "patterns": [
                    r"\b(code|function|class|method)\b",
                    r"\b(how to|how does|implement|write)\b.*\b(code|function)\b",
                    r"\b(repository|repo|github|gitlab)\b",
                    r"\b(programming|development|coding)\b"
                ]
            },
            
            Capability.ROUTES: {
                "keywords": [
                    "route", "routing", "navigation", "url", "path", "endpoint",
                    "link", "menu", "navigation", "site map", "structure",
                    "page", "section", "directory", "folder", "hierarchy"
                ],
                "patterns": [
                    r"\b(route|routing|navigation|url|path)\b",
                    r"\b(how to|where is|navigate|find)\b.*\b(page|section)\b",
                    r"\b(menu|link|structure|hierarchy)\b"
                ]
            },
            
            Capability.NAV_GRAPH: {
                "keywords": [
                    "navigation", "navigate", "menu", "sidebar", "header", "footer",
                    "breadcrumb", "site map", "structure", "layout",
                    "interface", "ui", "user interface", "design",
                    "find", "where", "locate", "access"
                ],
                "patterns": [
                    r"\b(navigation|menu|sidebar|header|footer)\b",
                    r"\b(how to|where is|navigate)\b.*\b(menu|navigation)\b",
                    r"\b(interface|ui|layout|design)\b"
                ]
            },
            
            Capability.TRANSCRIPT: {
                "keywords": [
                    "video", "transcript", "caption", "subtitle", "audio",
                    "speech", "talk", "presentation", "tutorial", "lecture",
                    "youtube", "vimeo", "watch", "listen", "hear"
                ],
                "patterns": [
                    r"\b(video|transcript|caption|subtitle)\b",
                    r"\b(what does|what is said|what is mentioned)\b.*\b(video|audio)\b",
                    r"\b(youtube|vimeo|watch|listen)\b"
                ]
            },
            
            Capability.SECTION: {
                "keywords": [
                    "documentation", "guide", "tutorial", "help", "manual",
                    "instructions", "steps", "how to", "explanation", "description",
                    "article", "blog", "post", "content", "text", "information"
                ],
                "patterns": [
                    r"\b(documentation|guide|tutorial|help|manual)\b",
                    r"\b(how to|what is|explain|describe)\b",
                    r"\b(article|blog|post|content|information)\b"
                ]
            },
            
            Capability.API_SPEC: {
                "keywords": [
                    "api", "endpoint", "request", "response", "parameter",
                    "authentication", "authorization", "token", "key",
                    "swagger", "openapi", "rest", "graphql", "soap"
                ],
                "patterns": [
                    r"\b(api|endpoint|request|response)\b",
                    r"\b(how to|what is|use|call)\b.*\b(api|endpoint)\b",
                    r"\b(swagger|openapi|rest|graphql)\b"
                ]
            },
            
            Capability.MANIFEST: {
                "keywords": [
                    "package", "dependency", "install", "requirements",
                    "manifest", "config", "configuration", "setup",
                    "environment", "version", "compatibility"
                ],
                "patterns": [
                    r"\b(package|dependency|install|requirements)\b",
                    r"\b(how to|what is|setup|configure)\b.*\b(package|dependency)\b",
                    r"\b(manifest|config|configuration)\b"
                ]
            },
            
            Capability.README: {
                "keywords": [
                    "readme", "overview", "introduction", "getting started",
                    "quick start", "setup", "installation", "usage",
                    "example", "demo", "sample", "tutorial"
                ],
                "patterns": [
                    r"\b(readme|overview|introduction|getting started)\b",
                    r"\b(what is|explain|describe)\b.*\b(project|library|tool)\b",
                    r"\b(setup|installation|usage|example)\b"
                ]
            }
        }
        
        # Question type patterns
        self.question_types = {
            "how_to": [
                r"how to", r"how do", r"how can", r"how should",
                r"steps to", r"way to", r"process to"
            ],
            "what_is": [
                r"what is", r"what are", r"what does", r"what do",
                r"explain", r"describe", r"define", r"meaning of"
            ],
            "where_is": [
                r"where is", r"where are", r"where can", r"where do",
                r"find", r"locate", r"located", r"position"
            ],
            "why": [
                r"why", r"reason", r"purpose", r"benefit",
                r"advantage", r"disadvantage", r"pros", r"cons"
            ],
            "when": [
                r"when", r"time", r"schedule", r"timeline",
                r"deadline", r"duration", r"frequency"
            ]
        }
    
    def plan_question(self, question: str) -> PlanningResult:
        """
        Analyze a question to determine required capabilities and priorities.
        
        Args:
            question: User question to analyze
            
        Returns:
            PlanningResult with required capabilities, keywords, and confidence
        """
        # Normalize question
        normalized_question = self._normalize_question(question)
        
        # Extract keywords
        keywords = self._extract_keywords(normalized_question)
        
        # Determine question type
        question_type = self._classify_question_type(normalized_question)
        
        # Map keywords to capabilities
        capability_scores = self._score_capabilities(normalized_question, keywords)
        
        # Determine required capabilities (score > 0.3)
        required_capabilities = {
            cap: score for cap, score in capability_scores.items() 
            if score > 0.3
        }
        
        # If no capabilities found, use fallback
        if not required_capabilities:
            required_capabilities = self._get_fallback_capabilities(question_type)
        
        # Calculate overall confidence
        confidence = self._calculate_confidence(
            required_capabilities, question_type, len(keywords)
        )
        
        # Get priority order
        capability_priority = self._get_capability_priority(required_capabilities)
        
        return PlanningResult(
            question=question,
            normalized_question=normalized_question,
            required_capabilities=list(required_capabilities.keys()),
            capability_scores=capability_scores,
            capability_priority=capability_priority,
            keywords=keywords,
            question_type=question_type,
            confidence=confidence,
            planning_method="keyword_analysis"
        )
    
    def _normalize_question(self, question: str) -> str:
        """Normalize question text for analysis."""
        # Convert to lowercase
        normalized = question.lower().strip()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove common question words that don't add meaning
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = normalized.split()
        words = [word for word in words if word not in stop_words]
        
        return ' '.join(words)
    
    def _extract_keywords(self, question: str) -> List[str]:
        """Extract meaningful keywords from question."""
        # Extract words of 3+ characters
        words = re.findall(r'\b\w{3,}\b', question)
        
        # Remove common stop words
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'man', 'men', 'put', 'say', 'she', 'too', 'use'
        }
        
        keywords = [word for word in words if word not in stop_words]
        
        # Count frequency and return unique keywords
        return list(set(keywords))
    
    def _classify_question_type(self, question: str) -> str:
        """Classify the type of question being asked."""
        for question_type, patterns in self.question_types.items():
            for pattern in patterns:
                if re.search(pattern, question, re.IGNORECASE):
                    return question_type
        
        return "general"
    
    def _score_capabilities(self, question: str, keywords: List[str]) -> Dict[Capability, float]:
        """Score each capability based on question content."""
        scores = {}
        
        for capability, config in self.capability_keywords.items():
            score = 0.0
            
            # Score based on keyword matches
            keyword_matches = 0
            for keyword in config["keywords"]:
                if keyword in keywords:
                    keyword_matches += 1
                    score += 0.3
            
            # Score based on pattern matches
            pattern_matches = 0
            for pattern in config["patterns"]:
                if re.search(pattern, question, re.IGNORECASE):
                    pattern_matches += 1
                    score += 0.4
            
            # Normalize score
            if keyword_matches > 0 or pattern_matches > 0:
                score = min(score, 1.0)
                # Boost score for multiple matches
                if keyword_matches > 1:
                    score += 0.1
                if pattern_matches > 1:
                    score += 0.1
                score = min(score, 1.0)
            
            scores[capability] = score
        
        return scores
    
    def _get_fallback_capabilities(self, question_type: str) -> Dict[Capability, float]:
        """Get fallback capabilities based on question type."""
        fallbacks = {
            "how_to": {Capability.SECTION: 0.6, Capability.README: 0.4},
            "what_is": {Capability.SECTION: 0.7, Capability.README: 0.3},
            "where_is": {Capability.NAV_GRAPH: 0.5, Capability.ROUTES: 0.5},
            "why": {Capability.SECTION: 0.8},
            "when": {Capability.SECTION: 0.6, Capability.MANIFEST: 0.4},
            "general": {Capability.SECTION: 0.5, Capability.README: 0.3}
        }
        
        return fallbacks.get(question_type, {Capability.SECTION: 0.5})
    
    def _calculate_confidence(
        self, 
        capabilities: Dict[Capability, float], 
        question_type: str, 
        keyword_count: int
    ) -> float:
        """Calculate overall confidence in the planning result."""
        if not capabilities:
            return 0.1
        
        # Base confidence from capability scores
        max_capability_score = max(capabilities.values()) if capabilities else 0
        base_confidence = max_capability_score
        
        # Boost for specific question types
        type_boosts = {
            "how_to": 0.1,
            "what_is": 0.1,
            "where_is": 0.05,
            "why": 0.05,
            "when": 0.05
        }
        
        type_boost = type_boosts.get(question_type, 0)
        
        # Boost for multiple keywords (indicates specific question)
        keyword_boost = min(keyword_count * 0.02, 0.1)
        
        # Boost for multiple capabilities (indicates complex question)
        capability_boost = min(len(capabilities) * 0.05, 0.1)
        
        confidence = base_confidence + type_boost + keyword_boost + capability_boost
        return min(confidence, 1.0)
    
    def _get_capability_priority(self, capabilities: Dict[Capability, float]) -> List[Capability]:
        """Get capabilities ordered by priority (highest score first)."""
        return sorted(capabilities.keys(), key=lambda cap: capabilities[cap], reverse=True)
    
    def get_capabilities_for_question(self, question: str) -> List[Capability]:
        """
        Convenience method to get just the required capabilities.
        
        Args:
            question: User question
            
        Returns:
            List of required capabilities
        """
        result = self.plan_question(question)
        return result.required_capabilities


# Convenience functions
def plan_question(question: str, settings: Optional[Settings] = None) -> PlanningResult:
    """
    Convenience function to plan a single question.
    
    Args:
        question: Question to plan
        settings: Optional settings instance
        
    Returns:
        PlanningResult with planning information
    """
    planner = QuestionPlanner(settings)
    return planner.plan_question(question)


def get_capabilities_for_question(question: str, settings: Optional[Settings] = None) -> List[Capability]:
    """
    Convenience function to get capabilities for a question.
    
    Args:
        question: Question to analyze
        settings: Optional settings instance
        
    Returns:
        List of required capabilities
    """
    planner = QuestionPlanner(settings)
    return planner.get_capabilities_for_question(question)


# Main function for testing
def main():
    """Test the planning system."""
    print("Testing WebCrawlApp Question Planning...")
    print("=" * 50)
    
    test_questions = [
        "How do I navigate the code structure?",
        "What is the API endpoint for user authentication?",
        "Where can I find the documentation?",
        "How does the frontend talk to the backend?",
        "What are the installation requirements?",
        "How to set up the development environment?",
        "What is the video about?",
        "How to use the navigation menu?",
        "What are the main features?",
        "How to configure the settings?"
    ]
    
    try:
        for question in test_questions:
            result = plan_question(question)
            
            print(f"\nQuestion: {question}")
            print(f"Normalized: {result.normalized_question}")
            print(f"Type: {result.question_type}")
            print(f"Keywords: {result.keywords}")
            print(f"Capabilities: {[cap.value for cap in result.required_capabilities]}")
            print(f"Priority: {[cap.value for cap in result.capability_priority]}")
            print(f"Confidence: {result.confidence:.2f}")
            print("-" * 40)
        
        print("\nAll planning tests completed successfully!")
        
    except Exception as e:
        print(f"Planning test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    main()
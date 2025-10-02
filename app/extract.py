#!/usr/bin/env python3
"""
Content Extraction Pipeline.

This module orchestrates the extraction of content using capability-based adapters.
It handles:
- Adapter selection based on URL detection
- Content block extraction
- Block deduplication and scoring
- Character budget management
- Capability coverage verification
"""

import logging
from typing import List, Dict, Optional, Set
from collections import defaultdict

from app.schemas import (
    ContentBlock, ContentType, Capability, DetectionResult, 
    PlanningResult, ExtractionResult, AdapterType
)
from app.settings import Settings
from app.detect import detect_url
from app.planner import plan_question

# Import adapters
from adapters.html import HTMLAdapter
from adapters.generic import GenericAdapter
from adapters.base import AdapterRegistry

logger = logging.getLogger(__name__)


class ContentExtractor:
    """Main content extraction orchestrator."""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.registry = AdapterRegistry()
        self._setup_adapters()
    
    def _setup_adapters(self):
        """Set up available adapters."""
        # Register adapters
        self.registry.register(HTMLAdapter(self.settings))
        self.registry.register(GenericAdapter(self.settings))
        
        # TODO: Register other adapters when implemented
        # self.registry.register(CodeRepoAdapter(self.settings))
        # self.registry.register(APIDocAdapter(self.settings))
        # self.registry.register(VideoAdapter(self.settings))
    
    async def extract_from_urls(
        self,
        urls: List[str],
        question: str,
        detection_results: Optional[List[DetectionResult]] = None,
        planning_result: Optional[PlanningResult] = None
    ) -> ExtractionResult:
        """Extract content from a list of URLs."""
        try:
            # Get detection results if not provided
            if not detection_results:
                detection_results = []
                for url in urls:
                    result = await detect_url(url)
                    detection_results.append(result)
            
            # Get planning result if not provided
            if not planning_result:
                planning_result = plan_question(question)
            
            # Extract content from each URL
            all_blocks = []
            extraction_stats = defaultdict(int)
            
            for i, url in enumerate(urls):
                detection_result = detection_results[i] if i < len(detection_results) else detection_results[0]
                
                try:
                    blocks = await self._extract_from_single_url(
                        url, detection_result, planning_result
                    )
                    all_blocks.extend(blocks)
                    extraction_stats["urls_processed"] += 1
                    extraction_stats["blocks_extracted"] += len(blocks)
                    
                except Exception as e:
                    logger.error(f"Error extracting from {url}: {e}")
                    extraction_stats["urls_failed"] += 1
            
            # Process and filter blocks
            processed_blocks = await self._process_blocks(
                all_blocks, planning_result
            )
            
            # Verify capability coverage
            coverage = self._verify_capability_coverage(
                processed_blocks, planning_result.required_capabilities
            )
            
            extraction_stats["blocks_processed"] = len(processed_blocks)
            extraction_stats["capability_coverage"] = coverage
            
            return ExtractionResult(
                content_blocks=processed_blocks,
                extraction_stats=extraction_stats,
                capability_coverage=coverage,
                total_bytes=sum(len(block.content) for block in processed_blocks)
            )
            
        except Exception as e:
            logger.error(f"Error in content extraction: {e}")
            return ExtractionResult(
                content_blocks=[],
                extraction_stats={"error": str(e)},
                capability_coverage={},
                total_bytes=0
            )
    
    async def _extract_from_single_url(
        self,
        url: str,
        detection_result: DetectionResult,
        planning_result: PlanningResult
    ) -> List[ContentBlock]:
        """Extract content from a single URL."""
        
        # Get the appropriate adapter
        adapter = self.registry.get_adapter_for_type(detection_result.adapter_type)
        
        if not adapter:
            logger.warning(f"No adapter found for type {detection_result.adapter_type}")
            return []
        
        # Check if adapter can handle the content
        if not await adapter.can_handle(url, "", detection_result.content_type.value):
            logger.warning(f"Adapter {adapter.adapter_type} cannot handle {url}")
            return []
        
        # TODO: Fetch actual content from URL
        # For now, we'll return empty blocks as we need to implement HTTP fetching
        # This is a placeholder that shows the structure
        
        logger.info(f"Would extract content from {url} using {adapter.adapter_type}")
        
        # Placeholder: Return empty blocks for now
        # In the next iteration, we'll implement actual HTTP fetching
        return []
    
    async def _process_blocks(
        self,
        blocks: List[ContentBlock],
        planning_result: PlanningResult
    ) -> List[ContentBlock]:
        """Process and filter content blocks."""
        if not blocks:
            return []
        
        # Deduplicate blocks
        deduplicated = self._deduplicate_blocks(blocks)
        
        # Score blocks based on question relevance
        scored = self._score_blocks_for_question(deduplicated, planning_result)
        
        # Apply character budget
        budgeted = self._apply_character_budget(scored)
        
        return budgeted
    
    def _deduplicate_blocks(self, blocks: List[ContentBlock]) -> List[ContentBlock]:
        """Remove duplicate content blocks using simhash."""
        if len(blocks) <= 1:
            return blocks
        
        unique_blocks = []
        seen_hashes = set()
        
        for block in blocks:
            # Calculate simhash for content
            content_hash = self._calculate_content_hash(block.content)
            
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                unique_blocks.append(block)
            else:
                logger.debug(f"Skipping duplicate block from {block.url}")
        
        logger.info(f"Deduplicated {len(blocks)} blocks to {len(unique_blocks)}")
        return unique_blocks
    
    def _calculate_content_hash(self, content: str) -> str:
        """Calculate a simple hash for content deduplication."""
        # Simple approach: use first 100 characters + length
        # In production, use simhash library
        key_content = content[:100] + str(len(content))
        return str(hash(key_content))
    
    def _score_blocks_for_question(
        self,
        blocks: List[ContentBlock],
        planning_result: PlanningResult
    ) -> List[ContentBlock]:
        """Score blocks based on question relevance."""
        keywords = planning_result.keywords
        required_capabilities = planning_result.required_capabilities
        
        for block in blocks:
            # Base score from content quality
            base_score = block.metadata.get("quality_score", 0.5)
            
            # Boost score for required capabilities
            capability_boost = 0.0
            if block.content_type.value in [cap.value for cap in required_capabilities]:
                capability_boost = 0.3
            
            # Boost score for keyword matches
            keyword_boost = 0.0
            content_lower = block.content.lower()
            for keyword in keywords:
                if keyword.lower() in content_lower:
                    keyword_boost += 0.1
            
            # Combine scores
            total_score = min(1.0, base_score + capability_boost + keyword_boost)
            block.metadata["question_relevance_score"] = total_score
        
        # Sort by score
        blocks.sort(key=lambda b: b.metadata.get("question_relevance_score", 0), reverse=True)
        
        return blocks
    
    def _apply_character_budget(self, blocks: List[ContentBlock]) -> List[ContentBlock]:
        """Apply character budget limit to blocks."""
        budget = self.settings.char_budget
        selected_blocks = []
        total_chars = 0
        
        for block in blocks:
            block_chars = len(block.content)
            
            if total_chars + block_chars <= budget:
                selected_blocks.append(block)
                total_chars += block_chars
            else:
                # Try to fit partial block
                remaining_budget = budget - total_chars
                if remaining_budget > 100:  # Only if meaningful amount left
                    truncated_content = block.content[:remaining_budget] + "..."
                    block.content = truncated_content
                    selected_blocks.append(block)
                break
        
        logger.info(f"Selected {len(selected_blocks)} blocks within {budget} char budget")
        return selected_blocks
    
    def _verify_capability_coverage(
        self,
        blocks: List[ContentBlock],
        required_capabilities: List[Capability]
    ) -> Dict[Capability, bool]:
        """Verify that all required capabilities are covered."""
        coverage = {}
        available_capabilities = set()
        
        # Get capabilities from blocks
        for block in blocks:
            # Map content types to capabilities
            if block.content_type == ContentType.SECTION:
                available_capabilities.add(Capability.SECTION)
            elif block.content_type == ContentType.NAV_BAR:
                available_capabilities.add(Capability.NAV_GRAPH)
            elif block.content_type == ContentType.CODE_MAP:
                available_capabilities.add(Capability.CODE_MAP)
            elif block.content_type == ContentType.API_SPEC:
                available_capabilities.add(Capability.API_SPEC)
            elif block.content_type == ContentType.TRANSCRIPT:
                available_capabilities.add(Capability.TRANSCRIPT)
            elif block.content_type == ContentType.ROUTE:
                available_capabilities.add(Capability.ROUTES)
        
        # Check coverage for each required capability
        for capability in required_capabilities:
            coverage[capability] = capability in available_capabilities
        
        return coverage


# Convenience functions
async def extract_content_from_urls(
    urls: List[str],
    question: str,
    settings: Optional[Settings] = None
) -> ExtractionResult:
    """Extract content from URLs for a given question."""
    extractor = ContentExtractor(settings)
    return await extractor.extract_from_urls(urls, question)


def get_extractor(settings: Optional[Settings] = None) -> ContentExtractor:
    """Get a content extractor instance."""
    return ContentExtractor(settings)

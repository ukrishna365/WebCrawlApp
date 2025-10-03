#!/usr/bin/env python3
"""
Content Assembly and Processing Module.

This module handles the assembly of content blocks from multiple sources:
- Deduplication using simhash
- Character budget enforcement
- Capability coverage verification
- Citation preparation
- Content quality optimization
"""

import logging
from typing import List, Dict, Optional, Set, Tuple
from collections import defaultdict
import hashlib

from app.schemas import (
    ContentBlock, ContentType, Capability, PlanningResult, 
    AssemblyResult, Citation, Diagnostics
)
from app.settings import Settings
from app.util import calculate_simhash, calculate_content_similarity

logger = logging.getLogger(__name__)


class ContentAssembler:
    """Assembles and processes content blocks from multiple sources."""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
    
    async def assemble_content(
        self,
        content_blocks: List[ContentBlock],
        planning_result: PlanningResult,
        max_blocks: Optional[int] = None
    ) -> AssemblyResult:
        """
        Assemble content blocks into final result.
        
        Args:
            content_blocks: Raw content blocks from extraction
            planning_result: Question planning information
            max_blocks: Maximum number of blocks to include
            
        Returns:
            AssemblyResult with processed blocks and metadata
        """
        try:
            logger.info(f"Starting assembly with {len(content_blocks)} blocks")
            
            # Step 1: Deduplicate blocks
            deduplicated = await self._deduplicate_blocks(content_blocks)
            logger.info(f"After deduplication: {len(deduplicated)} blocks")
            
            # Step 2: Score blocks for question relevance
            scored_blocks = self._score_blocks_for_question(deduplicated, planning_result)
            
            # Step 3: Ensure capability coverage
            coverage_blocks = self._ensure_capability_coverage(
                scored_blocks, planning_result.required_capabilities
            )
            
            # Step 4: Apply character budget
            budgeted_blocks = self._apply_character_budget(coverage_blocks)
            
            # Step 5: Limit by block count if specified
            if max_blocks:
                final_blocks = budgeted_blocks[:max_blocks]
            else:
                final_blocks = budgeted_blocks
            
            # Step 6: Prepare citations
            citations = self._prepare_citations(final_blocks)
            
            # Step 7: Generate diagnostics
            diagnostics = self._generate_diagnostics(
                content_blocks, final_blocks, planning_result
            )
            
            logger.info(f"Assembly complete: {len(final_blocks)} final blocks, "
                       f"{len(citations)} citations")
            
            return AssemblyResult(
                selected_blocks=final_blocks,
                capability_coverage=self._calculate_coverage(final_blocks, planning_result.required_capabilities),
                assembly_stats=diagnostics,
                char_count=sum(len(block.content) for block in final_blocks),
                duplicates_removed=len(content_blocks) - len(deduplicated)
            )
            
        except Exception as e:
            logger.error(f"Error in content assembly: {e}")
            return AssemblyResult(
                selected_blocks=[],
                capability_coverage={},
                assembly_stats={"error": str(e)},
                char_count=0,
                duplicates_removed=0
            )
    
    async def _deduplicate_blocks(self, blocks: List[ContentBlock]) -> List[ContentBlock]:
        """Remove duplicate content blocks using simhash and similarity detection."""
        if len(blocks) <= 1:
            return blocks
        
        unique_blocks = []
        seen_hashes = set()
        similarity_threshold = 0.8  # Configurable threshold
        
        for block in blocks:
            # Calculate simhash for content
            content_hash = calculate_simhash(block.content)
            
            # Check for exact duplicates
            if content_hash in seen_hashes:
                logger.debug(f"Skipping exact duplicate block from {block.url}")
                continue
            
            # Check for similar content
            is_duplicate = False
            for existing_block in unique_blocks:
                similarity = calculate_content_similarity(block.content, existing_block.content)
                if similarity > similarity_threshold:
                    logger.debug(f"Skipping similar content block from {block.url}")
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                seen_hashes.add(content_hash)
                unique_blocks.append(block)
        
        return unique_blocks
    
    def _score_blocks_for_question(
        self,
        blocks: List[ContentBlock],
        planning_result: PlanningResult
    ) -> List[ContentBlock]:
        """Score blocks based on question relevance and capability importance."""
        keywords = planning_result.keywords
        capability_scores = planning_result.capability_scores
        
        for block in blocks:
            # Base content quality score
            base_score = block.metadata.get("quality_score", 0.5)
            
            # Keyword relevance score
            keyword_score = self._calculate_keyword_score(block.content, keywords)
            
            # Capability importance score
            capability_score = self._calculate_capability_score(
                block.content_type, capability_scores
            )
            
            # URL relevance score (if URL contains keywords)
            url_score = self._calculate_url_score(block.url, keywords)
            
            # Combine scores with weights
            total_score = (
                base_score * 0.3 +
                keyword_score * 0.4 +
                capability_score * 0.2 +
                url_score * 0.1
            )
            
            # Store scores in metadata
            block.metadata.update({
                "question_relevance_score": total_score,
                "keyword_score": keyword_score,
                "capability_score": capability_score,
                "url_score": url_score,
                "base_quality_score": base_score
            })
        
        # Sort by total score (highest first)
        blocks.sort(key=lambda b: b.metadata.get("question_relevance_score", 0), reverse=True)
        
        return blocks
    
    def _calculate_keyword_score(self, content: str, keywords: List[str]) -> float:
        """Calculate relevance score based on keyword matches."""
        if not keywords or not content:
            return 0.0
        
        content_lower = content.lower()
        matches = 0
        total_keywords = len(keywords)
        
        for keyword in keywords:
            if keyword.lower() in content_lower:
                matches += 1
        
        # Bonus for multiple matches of the same keyword
        keyword_frequency = sum(content_lower.count(keyword.lower()) for keyword in keywords)
        frequency_bonus = min(0.2, keyword_frequency * 0.05)
        
        base_score = matches / total_keywords
        return min(1.0, base_score + frequency_bonus)
    
    def _calculate_capability_score(
        self, 
        content_type: ContentType, 
        capability_scores: Dict[Capability, float]
    ) -> float:
        """Calculate score based on content type and capability importance."""
        # Map content types to capabilities
        content_to_capability = {
            ContentType.SECTION: Capability.SECTION,
            ContentType.NAV_BAR: Capability.NAV_GRAPH,
            ContentType.CODE_MAP: Capability.CODE_MAP,
            ContentType.API_SPEC: Capability.API_SPEC,
            ContentType.TRANSCRIPT: Capability.TRANSCRIPT,
            ContentType.ROUTE: Capability.ROUTES,
            ContentType.MANIFEST: Capability.MANIFEST,
            ContentType.README: Capability.README,
        }
        
        capability = content_to_capability.get(content_type)
        if capability and capability in capability_scores:
            return capability_scores[capability]
        
        return 0.0
    
    def _calculate_url_score(self, url: str, keywords: List[str]) -> float:
        """Calculate relevance score based on URL keywords."""
        if not keywords or not url:
            return 0.0
        
        url_lower = str(url).lower()
        matches = 0
        
        for keyword in keywords:
            if keyword.lower() in url_lower:
                matches += 1
        
        return min(1.0, matches / len(keywords))
    
    def _ensure_capability_coverage(
        self,
        blocks: List[ContentBlock],
        required_capabilities: List[Capability]
    ) -> List[ContentBlock]:
        """Ensure at least one block covers each required capability."""
        if not required_capabilities:
            return blocks
        
        # Map content types to capabilities
        content_to_capability = {
            ContentType.SECTION: Capability.SECTION,
            ContentType.NAV_BAR: Capability.NAV_GRAPH,
            ContentType.CODE_MAP: Capability.CODE_MAP,
            ContentType.API_SPEC: Capability.API_SPEC,
            ContentType.TRANSCRIPT: Capability.TRANSCRIPT,
            ContentType.ROUTE: Capability.ROUTES,
            ContentType.MANIFEST: Capability.MANIFEST,
            ContentType.README: Capability.README,
        }
        
        # Find blocks that cover each capability
        capability_coverage = defaultdict(list)
        for block in blocks:
            capability = content_to_capability.get(block.content_type)
            if capability:
                capability_coverage[capability].append(block)
        
        # Ensure coverage for required capabilities
        final_blocks = blocks.copy()
        covered_capabilities = set()
        
        # First, mark capabilities that are already covered
        for capability in required_capabilities:
            if capability in capability_coverage and capability_coverage[capability]:
                covered_capabilities.add(capability)
        
        # Add blocks for missing capabilities
        for capability in required_capabilities:
            if capability not in covered_capabilities:
                # Try to find a block that could cover this capability
                best_block = None
                best_score = 0
                
                for block in blocks:
                    if block not in final_blocks:
                        continue
                    
                    # Check if block could be relevant to this capability
                    score = self._estimate_capability_relevance(block, capability)
                    if score > best_score:
                        best_score = score
                        best_block = block
                
                if best_block and best_score > 0.3:  # Minimum relevance threshold
                    final_blocks.append(best_block)
                    covered_capabilities.add(capability)
                    logger.info(f"Added block for capability {capability.value}")
        
        return final_blocks
    
    def _estimate_capability_relevance(
        self, 
        block: ContentBlock, 
        capability: Capability
    ) -> float:
        """Estimate how relevant a block might be for a capability."""
        # Simple heuristic based on content and keywords
        content_lower = block.content.lower()
        
        capability_keywords = {
            Capability.SECTION: ['section', 'content', 'documentation'],
            Capability.NAV_GRAPH: ['navigation', 'menu', 'link'],
            Capability.CODE_MAP: ['code', 'function', 'class', 'method'],
            Capability.API_SPEC: ['api', 'endpoint', 'request', 'response'],
            Capability.TRANSCRIPT: ['transcript', 'video', 'audio'],
            Capability.ROUTES: ['route', 'path', 'url'],
            Capability.MANIFEST: ['manifest', 'package', 'dependency'],
            Capability.README: ['readme', 'guide', 'instructions']
        }
        
        keywords = capability_keywords.get(capability, [])
        matches = sum(1 for keyword in keywords if keyword in content_lower)
        
        return matches / len(keywords) if keywords else 0.0
    
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
                # Try to fit partial block if there's meaningful budget left
                remaining_budget = budget - total_chars
                if remaining_budget > 200:  # Only if meaningful amount left
                    # Truncate content and add ellipsis
                    truncated_content = block.content[:remaining_budget-3] + "..."
                    
                    # Create new block with truncated content
                    truncated_block = ContentBlock(
                        content_type=block.content_type,
                        content=truncated_content,
                        url=block.url,
                        title=block.title,
                        char_count=len(truncated_content),
                        metadata={
                            **block.metadata,
                            "truncated": True,
                            "original_length": len(block.content)
                        }
                    )
                    selected_blocks.append(truncated_block)
                    total_chars += len(truncated_content)
                
                break  # Budget exhausted
        
        logger.info(f"Applied character budget: {total_chars}/{budget} chars used")
        return selected_blocks
    
    def _prepare_citations(self, blocks: List[ContentBlock]) -> List[Citation]:
        """Prepare citations for the assembled content."""
        citations = []
        seen_urls = set()
        
        for block in blocks:
            url = str(block.url)
            
            # Avoid duplicate citations
            if url in seen_urls:
                continue
            
            seen_urls.add(url)
            
            # Extract snippet from content (first 200 chars)
            snippet = block.content[:200].strip()
            if len(block.content) > 200:
                snippet += "..."
            
            citation = Citation(
                url=block.url,
                title=block.title or f"Content from {url}",
                snippet=snippet,
                content_type=block.content_type
            )
            
            citations.append(citation)
        
        return citations
    
    def _calculate_coverage(
        self,
        blocks: List[ContentBlock],
        required_capabilities: List[Capability]
    ) -> Dict[Capability, bool]:
        """Calculate capability coverage for the assembled blocks."""
        coverage = {}
        
        # Map content types to capabilities
        content_to_capability = {
            ContentType.SECTION: Capability.SECTION,
            ContentType.NAV_BAR: Capability.NAV_GRAPH,
            ContentType.CODE_MAP: Capability.CODE_MAP,
            ContentType.API_SPEC: Capability.API_SPEC,
            ContentType.TRANSCRIPT: Capability.TRANSCRIPT,
            ContentType.ROUTE: Capability.ROUTES,
            ContentType.MANIFEST: Capability.MANIFEST,
            ContentType.README: Capability.README,
        }
        
        available_capabilities = set()
        for block in blocks:
            capability = content_to_capability.get(block.content_type)
            if capability:
                available_capabilities.add(capability)
        
        # Check coverage for each required capability
        for capability in required_capabilities:
            coverage[capability] = capability in available_capabilities
        
        return coverage
    
    def _generate_diagnostics(
        self,
        original_blocks: List[ContentBlock],
        final_blocks: List[ContentBlock],
        planning_result: PlanningResult
    ) -> Dict:
        """Generate assembly diagnostics."""
        return {
            "blocks_original": len(original_blocks),
            "blocks_final": len(final_blocks),
            "blocks_filtered": len(original_blocks) - len(final_blocks),
            "total_bytes": sum(len(block.content) for block in final_blocks),
            "avg_block_length": sum(len(block.content) for block in final_blocks) / max(1, len(final_blocks)),
            "capabilities_requested": len(planning_result.required_capabilities),
            "keywords_used": len(planning_result.keywords),
            "assembly_method": "simhash_deduplication_with_capability_coverage"
        }


# Convenience functions
async def assemble_content_blocks(
    content_blocks: List[ContentBlock],
    planning_result: PlanningResult,
    settings: Optional[Settings] = None
) -> AssemblyResult:
    """Assemble content blocks into final result."""
    assembler = ContentAssembler(settings)
    return await assembler.assemble_content(content_blocks, planning_result)


def get_assembler(settings: Optional[Settings] = None) -> ContentAssembler:
    """Get a content assembler instance."""
    return ContentAssembler(settings)

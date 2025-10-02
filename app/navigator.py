"""
Smart Navigation system for WebCrawlApp.

Implements BM25-based link scoring, priority crawling, and intelligent URL selection.
"""

import asyncio
import logging
from typing import List, Dict, Set, Optional, Tuple, Any, AsyncGenerator
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
import time
from dataclasses import dataclass
from collections import defaultdict, deque
import heapq

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.schemas import ContentBlock, Capability, NavigationResult, CrawlConfig
from app.settings import Settings
from app.util import (
    BM25Scorer, extract_url_keywords, preprocess_text, normalize_url,
    should_follow_link, calculate_link_score, extract_link_text,
    extract_link_title, log_navigation_stats, calculate_simhash,
    calculate_similarity_threshold
)

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

logger = logging.getLogger(__name__)


@dataclass
class LinkCandidate:
    """Represents a candidate link for crawling."""
    url: str
    text: str
    title: str
    score: float
    depth: int
    parent_url: str
    
    def __lt__(self, other):
        """For heapq priority queue (higher score = higher priority)."""
        return self.score > other.score


@dataclass
class NavigationStats:
    """Statistics for navigation process."""
    urls_visited: int = 0
    urls_queued: int = 0
    bytes_fetched: int = 0
    avg_score: float = 0.0
    depth_reached: int = 0
    start_time: float = 0.0
    errors: int = 0
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        return time.time() - self.start_time


class SmartNavigator:
    """Intelligent URL navigation system with BM25-based scoring."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize navigator with settings."""
        self.settings = settings or Settings()
        self.client = None
        self.stats = NavigationStats()
        self.visited_urls: Set[str] = set()
        self.url_scores: Dict[str, float] = {}
        self.simhash_cache: Dict[str, int] = {}
        self.robots_cache: Dict[str, RobotFileParser] = {}
        
        # BM25 scorer for link text
        self.link_scorer: Optional[BM25Scorer] = None
        
        # Priority queue for link candidates
        self.link_queue: List[LinkCandidate] = []
        
        # Content similarity threshold
        self.similarity_threshold = 3
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            timeout=self.settings.get_http_config()["timeout"],
            follow_redirects=True,
            headers={"User-Agent": self.settings.get_http_config()["user_agent"]}
        )
        self.stats.start_time = time.time()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    def _check_robots_txt(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        try:
            parsed = urlparse(url)
            
            # Check if URL is valid (has scheme and netloc)
            if not parsed.scheme or not parsed.netloc:
                return False
            
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            
            if base_url not in self.robots_cache:
                robots_url = urljoin(base_url, "/robots.txt")
                rp = RobotFileParser()
                rp.set_url(robots_url)
                
                try:
                    rp.read()
                    self.robots_cache[base_url] = rp
                except Exception as e:
                    logger.warning(f"Could not read robots.txt for {base_url}: {e}")
                    # Assume allowed if robots.txt is not accessible
                    self.robots_cache[base_url] = None
            
            robots_parser = self.robots_cache[base_url]
            if robots_parser is None:
                return True  # No robots.txt restrictions
            
            user_agent = self.settings.get_http_config()["user_agent"]
            return robots_parser.can_fetch(user_agent, url)
            
        except Exception as e:
            logger.warning(f"Error checking robots.txt for {url}: {e}")
            return True  # Assume allowed on error
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException))
    )
    async def _fetch_page(self, url: str) -> Optional[Tuple[str, str, int]]:
        """Fetch page content with retries."""
        try:
            logger.debug(f"Fetching {url}")
            response = await self.client.get(url)
            response.raise_for_status()
            
            content = response.text
            content_type = response.headers.get("content-type", "").lower()
            content_length = len(content.encode('utf-8'))
            
            self.stats.bytes_fetched += content_length
            self.stats.urls_visited += 1
            
            logger.debug(f"Fetched {url}: {content_length} bytes, type: {content_type}")
            return content, content_type, content_length
            
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            self.stats.errors += 1
            return None
    
    def _extract_links(self, content: str, base_url: str, depth: int) -> List[LinkCandidate]:
        """Extract and score links from HTML content."""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            candidates = []
            
            # Find all links
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link['href']
                if not href or href.startswith('#'):
                    continue
                
                # Normalize URL
                full_url = normalize_url(href, base_url)
                
                # Skip if already visited or not allowed
                if full_url in self.visited_urls or not self._check_robots_txt(full_url):
                    continue
                
                # Check if should follow link
                if not should_follow_link(full_url, base_url, self.settings.max_depth):
                    continue
                
                # Extract link text and title
                link_text = extract_link_text(link)
                link_title = extract_link_title(link)
                
                # Combine text sources
                combined_text = f"{link_text} {link_title}".strip()
                
                if not combined_text:
                    # Try to get text from parent elements
                    parent = link.parent
                    if parent:
                        combined_text = extract_link_text(parent)
                
                if not combined_text:
                    # Use URL keywords as fallback
                    combined_text = ' '.join(extract_url_keywords(full_url))
                
                # Calculate score (will be updated with BM25 later)
                score = 0.0
                
                candidate = LinkCandidate(
                    url=full_url,
                    text=combined_text,
                    title=link_title,
                    score=score,
                    depth=depth,
                    parent_url=base_url
                )
                
                candidates.append(candidate)
            
            return candidates
            
        except Exception as e:
            logger.warning(f"Failed to extract links from {base_url}: {e}")
            return []
    
    def _update_link_scores(self, candidates: List[LinkCandidate], question_keywords: List[str]):
        """Update link scores using BM25 and other factors."""
        if not candidates or not question_keywords:
            return
        
        # Prepare corpus for BM25
        corpus = []
        for candidate in candidates:
            # Combine text sources for scoring
            text_parts = [candidate.text, candidate.title]
            text_parts.extend(extract_url_keywords(candidate.url))
            
            combined_text = ' '.join(text_parts)
            processed_text = preprocess_text(combined_text)
            corpus.append(processed_text)
        
        # Initialize BM25 scorer if needed or update with new corpus
        if not self.link_scorer:
            self.link_scorer = BM25Scorer(corpus)
        else:
            # Update the corpus for this batch
            self.link_scorer.corpus = corpus
            if self.link_scorer.bm25:
                # Recreate BM25 with new corpus
                self.link_scorer.bm25 = BM25Okapi(corpus)
        
        # Score documents
        if self.link_scorer.bm25:
            scores = self.link_scorer.score_documents(question_keywords)
        else:
            # Fallback scoring
            scores = []
            for candidate in candidates:
                score = calculate_link_score(
                    candidate.text, candidate.url, question_keywords,
                    candidate.parent_url, candidate.depth, self.settings.max_depth
                )
                scores.append(score)
        
        # Update candidate scores
        for i, candidate in enumerate(candidates):
            if i < len(scores):
                candidate.score = scores[i]
            else:
                candidate.score = 0.0
    
    def _filter_duplicate_content(self, candidates: List[LinkCandidate]) -> List[LinkCandidate]:
        """Filter candidates with similar content using simhash."""
        if not candidates:
            return []
        
        filtered = []
        
        for candidate in candidates:
            # Calculate simhash for candidate text
            combined_text = f"{candidate.text} {candidate.title}"
            candidate_hash = calculate_simhash(combined_text)
            
            # Check against existing hashes
            is_duplicate = False
            for existing_hash in self.simhash_cache.values():
                if calculate_similarity_threshold(candidate_hash, existing_hash, self.similarity_threshold):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                # Add to cache and filtered list
                self.simhash_cache[candidate.url] = candidate_hash
                filtered.append(candidate)
        
        return filtered
    
    def _add_to_queue(self, candidates: List[LinkCandidate], config: CrawlConfig):
        """Add candidates to priority queue, respecting budget limits."""
        # Sort by score (highest first)
        candidates.sort(key=lambda x: x.score, reverse=True)
        
        # Add to queue up to budget limit
        for candidate in candidates:
            if len(self.link_queue) >= config.page_budget:
                break
            
            # Only add if score meets minimum threshold
            if candidate.score >= 0.1:  # Minimum relevance threshold
                heapq.heappush(self.link_queue, candidate)
                self.stats.urls_queued += 1
    
    async def navigate(
        self,
        start_url: str,
        question_keywords: List[str],
        config: CrawlConfig,
        required_capabilities: List[Capability]
    ) -> AsyncGenerator[Tuple[str, str, int], None]:
        """
        Navigate from start URL, yielding (url, content, content_length) tuples.
        
        Args:
            start_url: Starting URL for navigation
            question_keywords: Keywords extracted from user question
            config: Crawl configuration with budgets and limits
            required_capabilities: List of required capabilities
            
        Yields:
            Tuple of (url, content, content_length) for each visited page
        """
        logger.info(f"Starting navigation from {start_url} with keywords: {question_keywords}")
        
        # Initialize queue with start URL
        start_candidate = LinkCandidate(
            url=start_url,
            text="",
            title="",
            score=1.0,  # Start URL gets highest priority
            depth=0,
            parent_url=""
        )
        
        heapq.heappush(self.link_queue, start_candidate)
        self.stats.urls_queued += 1
        
        # Process queue until empty or budget exhausted
        while self.link_queue and self.stats.urls_visited < config.page_budget:
            # Check timeout
            if self.stats.get_elapsed_time() > config.global_timeout:
                logger.warning("Navigation timeout reached")
                break
            
            # Get next candidate
            try:
                candidate = heapq.heappop(self.link_queue)
            except IndexError:
                break
            
            # Skip if already visited
            if candidate.url in self.visited_urls:
                continue
            
            # Mark as visited
            self.visited_urls.add(candidate.url)
            
            # Fetch page content
            result = await self._fetch_page(candidate.url)
            if not result:
                continue
            
            content, content_type, content_length = result
            
            # Update depth reached
            self.stats.depth_reached = max(self.stats.depth_reached, candidate.depth)
            
            # Yield content for processing
            yield candidate.url, content, content_length
            
            # Extract and score new links if not at max depth
            if candidate.depth < self.settings.max_depth:
                new_candidates = self._extract_links(content, candidate.url, candidate.depth + 1)
                
                if new_candidates:
                    # Update scores with BM25
                    self._update_link_scores(new_candidates, question_keywords)
                    
                    # Filter duplicates
                    filtered_candidates = self._filter_duplicate_content(new_candidates)
                    
                    # Add to queue
                    self._add_to_queue(filtered_candidates, config)
            
            # Update average score
            if self.link_queue:
                total_score = sum(c.score for c in self.link_queue)
                self.stats.avg_score = total_score / len(self.link_queue)
            
            # Log progress periodically
            if self.stats.urls_visited % 5 == 0:
                log_navigation_stats(
                    self.stats.urls_visited,
                    len(self.link_queue),
                    self.stats.bytes_fetched,
                    self.stats.avg_score,
                    self.stats.depth_reached
                )
        
        logger.info(f"Navigation complete: {self.stats.urls_visited} pages visited, "
                   f"{len(self.link_queue)} remaining in queue")
    
    def get_navigation_result(self) -> NavigationResult:
        """Get final navigation results."""
        # Convert visited URLs to HttpUrl objects
        from app.schemas import HttpUrl
        
        urls_to_visit = []
        url_scores = {}
        
        for url in sorted(self.visited_urls):
            try:
                urls_to_visit.append(HttpUrl(url))
                # Get score from link queue if available
                for candidate in self.link_queue:
                    if str(candidate.url) == url:
                        url_scores[url] = candidate.score
                        break
                else:
                    url_scores[url] = 0.0  # Default score if not found
            except ValueError:
                logger.warning(f"Invalid URL in visited set: {url}")
        
        return NavigationResult(
            urls_to_visit=urls_to_visit,
            url_scores=url_scores,
            total_links_found=self.stats.urls_queued,
            robots_allowed=True  # Assume allowed if we got this far
        )


# Convenience functions
async def navigate_urls(
    start_url: str,
    question_keywords: List[str],
    config: CrawlConfig,
    required_capabilities: List[Capability],
    settings: Optional[Settings] = None
) -> AsyncGenerator[Tuple[str, str, int], None]:
    """Convenience function for URL navigation."""
    async with SmartNavigator(settings) as navigator:
        async for url, content, length in navigator.navigate(
            start_url, question_keywords, config, required_capabilities
        ):
            yield url, content, length


def get_navigator(settings: Optional[Settings] = None) -> SmartNavigator:
    """Get a configured navigator instance."""
    return SmartNavigator(settings)

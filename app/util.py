"""
Utility functions for WebCrawlApp navigation and content processing.
"""

import re
import asyncio
import hashlib
from typing import List, Dict, Set, Optional, Tuple, Any
from urllib.parse import urljoin, urlparse, parse_qs
from collections import Counter
import logging

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None
    logging.warning("rank-bm25 not available, falling back to basic TF-IDF")

from app.schemas import ContentBlock, Capability
from app.settings import Settings

logger = logging.getLogger(__name__)


class BM25Scorer:
    """BM25-based scoring for text relevance."""
    
    def __init__(self, corpus: Optional[List[List[str]]] = None):
        """Initialize BM25 scorer with optional corpus."""
        if BM25Okapi and corpus:
            self.bm25 = BM25Okapi(corpus)
        else:
            self.bm25 = None
            self.corpus = corpus or []
    
    def score_documents(self, query: List[str]) -> List[float]:
        """Score documents against query using BM25."""
        if self.bm25:
            return self.bm25.get_scores(query)
        
        # Fallback to basic TF-IDF
        return self._basic_tfidf_score(query)
    
    def _basic_tfidf_score(self, query: List[str]) -> List[float]:
        """Basic TF-IDF scoring fallback."""
        if not self.corpus:
            return []
        
        query_counter = Counter(query)
        scores = []
        
        for doc in self.corpus:
            doc_counter = Counter(doc)
            score = 0
            
            for term, query_freq in query_counter.items():
                doc_freq = doc_counter.get(term, 0)
                if doc_freq > 0:
                    # Simple TF-IDF: tf * idf
                    tf = 1 + (doc_freq / len(doc))
                    idf = 1 + (len(self.corpus) / (1 + sum(1 for d in self.corpus if term in d)))
                    score += query_freq * tf * idf
            
            scores.append(score)
        
        return scores


def extract_url_keywords(url: str) -> List[str]:
    """Extract meaningful keywords from URL path and query parameters."""
    parsed = urlparse(url)
    keywords = []
    
    # Extract from path segments
    path_segments = [seg for seg in parsed.path.split('/') if seg and not seg.isdigit()]
    keywords.extend(path_segments)
    
    # Extract from query parameters
    query_params = parse_qs(parsed.query)
    for param_name, param_values in query_params.items():
        keywords.append(param_name)
        keywords.extend([val for val in param_values if val and not val.isdigit()])
    
    # Extract from fragment
    if parsed.fragment:
        fragment_parts = [part for part in parsed.fragment.split('-') if part]
        keywords.extend(fragment_parts)
    
    # Clean and filter keywords
    cleaned_keywords = []
    for keyword in keywords:
        # Remove common file extensions
        keyword = re.sub(r'\.(html?|php|asp|jsp|py|js|css)$', '', keyword, flags=re.IGNORECASE)
        
        # Split camelCase and snake_case
        keyword = re.sub(r'([a-z])([A-Z])', r'\1 \2', keyword)
        keyword = re.sub(r'_', ' ', keyword)
        
        # Split into words
        words = re.findall(r'\b[a-zA-Z]{2,}\b', keyword.lower())
        cleaned_keywords.extend(words)
    
    return cleaned_keywords


def preprocess_text(text: str) -> List[str]:
    """Preprocess text for BM25 scoring."""
    if not text:
        return []
    
    # Convert to lowercase and extract words
    words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
    
    # Remove common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
        'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these',
        'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
    }
    
    return [word for word in words if word not in stop_words and len(word) > 1]


def calculate_content_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two text strings using Jaccard similarity."""
    if not text1 or not text2:
        return 0.0
    
    words1 = set(preprocess_text(text1))
    words2 = set(preprocess_text(text2))
    
    if not words1 or not words2:
        return 0.0
    
    intersection = len(words1.intersection(words2))
    union = len(words1.union(words2))
    
    return intersection / union if union > 0 else 0.0


def extract_link_text(link_element: Any) -> str:
    """Extract meaningful text from a link element."""
    if hasattr(link_element, 'get_text'):
        # BeautifulSoup element
        text = link_element.get_text(strip=True)
    elif hasattr(link_element, 'text'):
        # Other element types
        text = link_element.text.strip()
    elif isinstance(link_element, str):
        # Already text
        text = link_element.strip()
    else:
        text = str(link_element).strip()
    
    return text


def extract_link_title(link_element: Any) -> str:
    """Extract title attribute from a link element."""
    if hasattr(link_element, 'get'):
        return link_element.get('title', '').strip()
    elif hasattr(link_element, 'attrs') and 'title' in link_element.attrs:
        return link_element.attrs['title'].strip()
    return ''


def normalize_url(url: str, base_url: str) -> str:
    """Normalize URL by resolving relative URLs and cleaning parameters."""
    try:
        # Resolve relative URLs
        full_url = urljoin(base_url, url)
        
        # Parse and reconstruct to normalize
        parsed = urlparse(full_url)
        
        # Remove common tracking parameters
        tracking_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'fbclid', 'gclid', 'ref', 'source', 'campaign', 'affiliate'
        }
        
        if parsed.query:
            query_params = parse_qs(parsed.query)
            cleaned_params = {
                k: v for k, v in query_params.items() 
                if k.lower() not in tracking_params
            }
            
            # Reconstruct query string
            query_parts = []
            for key, values in cleaned_params.items():
                for value in values:
                    query_parts.append(f"{key}={value}")
            
            new_query = '&'.join(query_parts)
        else:
            new_query = ''
        
        # Reconstruct URL
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if new_query:
            normalized += f"?{new_query}"
        if parsed.fragment:
            normalized += f"#{parsed.fragment}"
        
        return normalized
        
    except Exception as e:
        logger.warning(f"Failed to normalize URL {url}: {e}")
        return url


def should_follow_link(url: str, base_url: str, max_depth: int = 1) -> bool:
    """Determine if a link should be followed based on various criteria."""
    try:
        base_parsed = urlparse(base_url)
        link_parsed = urlparse(url)
        
        # Must have same scheme and netloc
        if link_parsed.scheme != base_parsed.scheme or link_parsed.netloc != base_parsed.netloc:
            return False
        
        # Check depth by counting path segments
        base_depth = len([seg for seg in base_parsed.path.split('/') if seg])
        link_depth = len([seg for seg in link_parsed.path.split('/') if seg])
        
        if link_depth > base_depth + max_depth:
            return False
        
        # Skip common non-content URLs
        skip_patterns = [
            r'\.(pdf|doc|docx|xls|xlsx|ppt|pptx|zip|rar|tar|gz)$',
            r'\.(jpg|jpeg|png|gif|bmp|svg|webp)$',
            r'\.(mp4|avi|mov|wmv|flv|webm)$',
            r'\.(mp3|wav|ogg|aac)$',
            r'/download/',
            r'/attachment/',
            r'/file/',
            r'/media/',
            r'/static/',
            r'/assets/',
            r'javascript:',
            r'mailto:',
            r'tel:'
        ]
        
        for pattern in skip_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        return True
        
    except Exception as e:
        logger.warning(f"Failed to evaluate link {url}: {e}")
        return False


def calculate_link_score(
    link_text: str,
    link_url: str,
    question_keywords: List[str],
    base_url: str,
    depth: int = 0,
    max_depth: int = 1
) -> float:
    """Calculate relevance score for a link based on multiple factors."""
    score = 0.0
    
    # Extract keywords from link text and URL
    link_keywords = preprocess_text(link_text)
    url_keywords = extract_url_keywords(link_url)
    all_link_keywords = link_keywords + url_keywords
    
    # BM25-style scoring for keyword matches
    if question_keywords and all_link_keywords:
        # Simple keyword matching with frequency weighting
        link_counter = Counter(all_link_keywords)
        question_counter = Counter(question_keywords)
        
        for term, freq in question_counter.items():
            if term in link_counter:
                # BM25-inspired scoring
                tf = link_counter[term]
                score += freq * (tf / (tf + 1.2)) * (1 + 0.75)
    
    # Boost score for exact phrase matches
    question_text = ' '.join(question_keywords)
    if question_text and link_text:
        if question_text.lower() in link_text.lower():
            score += 2.0
    
    # Boost score for URL keyword matches
    if url_keywords and question_keywords:
        url_match_count = sum(1 for kw in question_keywords if kw in url_keywords)
        score += url_match_count * 0.5
    
    # Apply depth penalty
    if depth > 0:
        depth_penalty = 0.5 ** depth
        score *= depth_penalty
    
    # Boost score for certain URL patterns
    boost_patterns = [
        (r'/api/', 1.5),
        (r'/docs?/', 1.3),
        (r'/documentation/', 1.3),
        (r'/guide/', 1.2),
        (r'/tutorial/', 1.2),
        (r'/help/', 1.1),
        (r'/about/', 0.8),
        (r'/contact/', 0.5),
    ]
    
    for pattern, boost in boost_patterns:
        if re.search(pattern, link_url, re.IGNORECASE):
            score *= boost
            break
    
    return max(0.0, score)


def create_http_client(settings: Settings) -> Dict[str, Any]:
    """Create HTTP client configuration."""
    return {
        "timeout": settings.get_http_config()["timeout"],
        "headers": settings.get_http_config()["user_agent"],
        "follow_redirects": True,
        "max_redirects": 5,
        "verify": True
    }


def log_navigation_stats(
    urls_visited: int,
    urls_queued: int,
    bytes_fetched: int,
    avg_score: float,
    depth_reached: int
) -> None:
    """Log navigation statistics."""
    logger.info(f"Navigation stats: {urls_visited} visited, {urls_queued} queued, "
                f"{bytes_fetched} bytes, avg_score={avg_score:.3f}, depth={depth_reached}")


# Content similarity using simhash (simplified version)
def calculate_simhash(text: str, hash_bits: int = 64) -> int:
    """Calculate simhash for text deduplication."""
    if not text:
        return 0
    
    words = preprocess_text(text)
    if not words:
        return 0
    
    # Create hash vector
    hash_vector = [0] * hash_bits
    
    for word in words:
        word_hash = hashlib.md5(word.encode()).hexdigest()
        # Convert hex to binary
        binary = bin(int(word_hash, 16))[2:].zfill(128)[:hash_bits]
        
        for i, bit in enumerate(binary):
            if bit == '1':
                hash_vector[i] += 1
            else:
                hash_vector[i] -= 1
    
    # Create simhash
    simhash = 0
    for i, val in enumerate(hash_vector):
        if val > 0:
            simhash |= (1 << i)
    
    return simhash


def calculate_similarity_threshold(simhash1: int, simhash2: int, threshold: int = 3) -> bool:
    """Check if two simhashes are similar within threshold."""
    if simhash1 == 0 or simhash2 == 0:
        return False
    
    # Calculate Hamming distance
    xor_result = simhash1 ^ simhash2
    hamming_distance = bin(xor_result).count('1')
    
    return hamming_distance <= threshold

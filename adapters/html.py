#!/usr/bin/env python3
"""
HTML Adapter for extracting content from HTML pages.

This adapter handles:
- Navigation bar detection and extraction
- Main content area identification  
- Section-based content parsing
- Link graph construction
"""

import logging
import re
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag
import trafilatura
from readability import Document

from adapters.base import BaseAdapter
from app.schemas import ContentBlock, ContentType, Capability, AdapterType
from app.settings import Settings

logger = logging.getLogger(__name__)


class HTMLAdapter(BaseAdapter):
    """Adapter for extracting content from HTML pages."""
    
    def __init__(self, settings: Optional[Settings] = None):
        super().__init__(settings)
        
        # Common navigation selectors
        self.nav_selectors = [
            'nav', 'nav[role="navigation"]', '.navigation', '.navbar', '.nav',
            '.menu', '.main-menu', '.header-nav', '.site-nav',
            '[role="navigation"]', '.breadcrumb', '.breadcrumbs'
        ]
        
        # Common content selectors
        self.content_selectors = [
            'main', 'article', '.content', '.main-content', '.post-content',
            '.entry-content', '.page-content', '.documentation-content',
            '#content', '#main', '.container', '.wrapper'
        ]
        
        # Section selectors
        self.section_selectors = [
            'section', '.section', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            '.chapter', '.part', '.subsection'
        ]
    
    @property
    def adapter_type(self) -> AdapterType:
        return AdapterType.HTML
    
    @property
    def supported_capabilities(self) -> List[Capability]:
        return [Capability.SECTION, Capability.NAV_GRAPH]
    
    async def can_handle(self, url: str, content: str, content_type: str) -> bool:
        """Check if this adapter can handle the content."""
        # Check content type
        if not content_type.lower().startswith('text/html'):
            return False
        
        # Check for HTML content
        if not content.strip():
            return False
        
        # Basic HTML validation
        try:
            soup = BeautifulSoup(content, 'html.parser')
            return soup.find() is not None
        except Exception:
            return False
    
    async def extract_content(
        self, 
        url: str, 
        content: str, 
        content_type: str
    ) -> List[ContentBlock]:
        """Extract content blocks from HTML."""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            base_url = self._get_base_url(url)
            
            blocks = []
            
            # Extract navigation
            nav_blocks = self._extract_navigation(soup, url, base_url)
            blocks.extend(nav_blocks)
            
            # Extract main content sections
            content_blocks = self._extract_content_sections(soup, url, base_url)
            blocks.extend(content_blocks)
            
            # Extract link graph
            link_blocks = self._extract_link_graph(soup, url, base_url)
            blocks.extend(link_blocks)
            
            # Filter and score blocks
            filtered_blocks = self._filter_blocks(blocks)
            
            logger.info(f"Extracted {len(filtered_blocks)} content blocks from {url}")
            return filtered_blocks
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            return []
    
    def _get_base_url(self, url: str) -> str:
        """Get base URL for resolving relative links."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    def _extract_navigation(self, soup: BeautifulSoup, url: str, base_url: str) -> List[ContentBlock]:
        """Extract navigation elements."""
        blocks = []
        
        for selector in self.nav_selectors:
            nav_elements = soup.select(selector)
            for nav in nav_elements:
                if not isinstance(nav, Tag):
                    continue
                
                # Extract text content
                text_content = nav.get_text(separator=' ', strip=True)
                if not text_content or len(text_content) < 10:
                    continue
                
                # Extract links from navigation
                links = []
                for link in nav.find_all('a', href=True):
                    href = link.get('href')
                    link_text = link.get_text(strip=True)
                    if href and link_text:
                        full_url = urljoin(base_url, href)
                        links.append(f"{link_text}: {full_url}")
                
                # Create navigation block
                nav_text = text_content
                if links:
                    nav_text += f"\n\nLinks: {'; '.join(links)}"
                
                block = self.create_content_block(
                    content_type=ContentType.NAV_BAR,
                    content=nav_text,
                    url=url,
                    title=f"Navigation: {nav.get('class', [''])[0] if nav.get('class') else 'nav'}",
                    metadata={
                        "selector": selector,
                        "link_count": len(links),
                        "nav_type": "navigation"
                    }
                )
                
                if block:
                    blocks.append(block)
        
        return blocks
    
    def _extract_content_sections(self, soup: BeautifulSoup, url: str, base_url: str) -> List[ContentBlock]:
        """Extract main content sections."""
        blocks = []
        
        # Try to find main content area
        main_content = None
        for selector in self.content_selectors:
            element = soup.select_one(selector)
            if element and isinstance(element, Tag):
                main_content = element
                break
        
        if not main_content:
            main_content = soup.body or soup
        
        # Extract sections
        sections = self._find_sections(main_content)
        
        for i, section in enumerate(sections):
            text_content = section.get_text(separator=' ', strip=True)
            if not text_content or len(text_content) < 50:
                continue
            
            # Get section title
            title = self._extract_section_title(section)
            if not title:
                title = f"Section {i + 1}"
            
            block = self.create_content_block(
                content_type=ContentType.SECTION,
                content=text_content,
                url=url,
                title=title,
                metadata={
                    "section_index": i,
                    "section_type": section.name if hasattr(section, 'name') else 'div',
                    "word_count": len(text_content.split())
                }
            )
            
            if block:
                blocks.append(block)
        
        # If no sections found, try to extract readable content
        if not blocks:
            readable_content = self._extract_readable_content(soup)
            if readable_content:
                block = self.create_content_block(
                    content_type=ContentType.SECTION,
                    content=readable_content,
                    url=url,
                    title="Main Content",
                    metadata={
                        "extraction_method": "readability",
                        "word_count": len(readable_content.split())
                    }
                )
                
                if block:
                    blocks.append(block)
        
        return blocks
    
    def _find_sections(self, element: Tag) -> List[Tag]:
        """Find logical sections in the content."""
        sections = []
        
        # Look for explicit section elements
        for selector in self.section_selectors:
            elements = element.select(selector)
            for el in elements:
                if isinstance(el, Tag):
                    # Include the element and its content
                    sections.append(el)
        
        # If no explicit sections, try to split by headings
        if not sections:
            headings = element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            for heading in headings:
                if isinstance(heading, Tag):
                    # Get content until next heading of same or higher level
                    section_content = self._get_content_until_next_heading(heading)
                    if section_content:
                        sections.append(section_content)
        
        return sections
    
    def _get_content_until_next_heading(self, heading: Tag) -> Optional[Tag]:
        """Get content from heading until next heading of same or higher level."""
        current_level = int(heading.name[1])
        content_elements = []
        
        # Walk through siblings
        for sibling in heading.next_siblings:
            if isinstance(sibling, Tag):
                if sibling.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    sibling_level = int(sibling.name[1])
                    if sibling_level <= current_level:
                        break
                
                content_elements.append(sibling)
        
        if content_elements:
            # Create a wrapper div with the content
            wrapper = BeautifulSoup('<div></div>', 'html.parser').div
            wrapper.append(heading)
            for el in content_elements:
                wrapper.append(el)
            return wrapper
        
        return None
    
    def _extract_section_title(self, section: Tag) -> Optional[str]:
        """Extract title from a section element."""
        # Look for heading elements
        heading = section.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if heading:
            return heading.get_text(strip=True)
        
        # Look for title attribute
        if section.get('title'):
            return section.get('title')
        
        # Look for aria-label
        if section.get('aria-label'):
            return section.get('aria-label')
        
        return None
    
    def _extract_readable_content(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract readable content using readability library."""
        try:
            # Try readability first
            doc = Document(str(soup))
            readable_text = doc.summary()
            
            if readable_text:
                # Clean up the HTML and extract text
                readable_soup = BeautifulSoup(readable_text, 'html.parser')
                return readable_soup.get_text(separator=' ', strip=True)
            
            # Fallback to trafilatura
            html_content = str(soup)
            extracted = trafilatura.extract(html_content)
            if extracted:
                return extracted
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting readable content: {e}")
            return None
    
    def _extract_link_graph(self, soup: BeautifulSoup, url: str, base_url: str) -> List[ContentBlock]:
        """Extract link graph information."""
        blocks = []
        
        # Find all links
        links = soup.find_all('a', href=True)
        if not links:
            return blocks
        
        # Group links by context
        link_groups = self._group_links_by_context(links, base_url)
        
        for context, link_list in link_groups.items():
            if len(link_list) < 3:  # Skip small groups
                continue
            
            # Create link graph content
            link_texts = []
            for link in link_list[:20]:  # Limit to 20 links per group
                href = link.get('href')
                text = link.get_text(strip=True)
                if href and text:
                    full_url = urljoin(base_url, href)
                    link_texts.append(f"{text}: {full_url}")
            
            if link_texts:
                content = f"Link Graph - {context}:\n" + "\n".join(link_texts)
                
                block = self.create_content_block(
                    content_type=ContentType.NAV_BAR,
                    content=content,
                    url=url,
                    title=f"Link Graph: {context}",
                    metadata={
                        "context": context,
                        "link_count": len(link_texts),
                        "graph_type": "navigation"
                    }
                )
                
                if block:
                    blocks.append(block)
        
        return blocks
    
    def _group_links_by_context(self, links: List[Tag], base_url: str) -> Dict[str, List[Tag]]:
        """Group links by their context (navigation, content, footer, etc.)."""
        groups = {
            "navigation": [],
            "content": [],
            "footer": [],
            "sidebar": [],
            "other": []
        }
        
        for link in links:
            # Determine context based on parent elements
            parent_classes = []
            current = link.parent
            
            # Walk up the DOM tree to find context
            for _ in range(5):  # Limit depth
                if not current or not hasattr(current, 'get'):
                    break
                
                if hasattr(current, 'get'):
                    classes = current.get('class', [])
                    if classes:
                        parent_classes.extend(classes)
                
                current = current.parent
            
            # Classify based on parent classes
            parent_class_str = ' '.join(parent_classes).lower()
            
            if any(nav_word in parent_class_str for nav_word in ['nav', 'menu', 'header']):
                groups["navigation"].append(link)
            elif any(content_word in parent_class_str for content_word in ['content', 'main', 'article']):
                groups["content"].append(link)
            elif any(footer_word in parent_class_str for footer_word in ['footer', 'bottom']):
                groups["footer"].append(link)
            elif any(sidebar_word in parent_class_str for sidebar_word in ['sidebar', 'aside']):
                groups["sidebar"].append(link)
            else:
                groups["other"].append(link)
        
        # Remove empty groups
        return {k: v for k, v in groups.items() if v}
    
    def _filter_blocks(self, blocks: List[ContentBlock]) -> List[ContentBlock]:
        """Filter and score content blocks."""
        if not blocks:
            return []
        
        # Score blocks
        scored_blocks = []
        for block in blocks:
            score = self.score_content_quality(
                block.content, 
                block.content_type
            )
            if score > 0.3:  # Minimum quality threshold
                scored_blocks.append(block)
        
        # Sort by score
        scored_blocks.sort(key=lambda b: self.score_content_quality(
            b.content, b.content_type
        ), reverse=True)
        
        return scored_blocks

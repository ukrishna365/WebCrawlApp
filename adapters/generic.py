#!/usr/bin/env python3
"""
Generic Page Adapter for fallback content extraction.

This adapter handles:
- Unknown content types
- Basic text extraction using readability
- Simple section detection
- Text quality assessment
"""

import logging
import re
from typing import List, Optional

import trafilatura
from readability import Document
from bs4 import BeautifulSoup

from adapters.base import BaseAdapter
from app.schemas import ContentBlock, ContentType, Capability, AdapterType
from app.settings import Settings

logger = logging.getLogger(__name__)


class GenericAdapter(BaseAdapter):
    """Generic adapter for unknown content types."""
    
    def __init__(self, settings: Optional[Settings] = None):
        super().__init__(settings)
    
    @property
    def adapter_type(self) -> AdapterType:
        return AdapterType.HTML  # Treat as HTML for generic processing
    
    @property
    def supported_capabilities(self) -> List[Capability]:
        return [Capability.SECTION]
    
    async def can_handle(self, url: str, content: str, content_type: str) -> bool:
        """Check if this adapter can handle the content."""
        # Generic adapter should handle anything that other adapters can't
        # This will be called as a fallback
        
        # Basic checks
        if not content or not content.strip():
            return False
        
        # Check if it looks like text content
        if content_type and content_type.lower().startswith('text/'):
            return True
        
        # Check if it's HTML-like
        if '<' in content and '>' in content:
            return True
        
        # Check if it's plain text with reasonable length
        if len(content.strip()) > 100 and '\n' in content:
            return True
        
        return False
    
    async def extract_content(
        self, 
        url: str, 
        content: str, 
        content_type: str
    ) -> List[ContentBlock]:
        """Extract content blocks using generic methods."""
        try:
            blocks = []
            
            # Try different extraction methods
            extracted_text = None
            
            # Method 1: Try readability if it looks like HTML
            if '<' in content and '>' in content:
                extracted_text = self._extract_with_readability(content)
            
            # Method 2: Try trafilatura
            if not extracted_text:
                extracted_text = self._extract_with_trafilatura(content)
            
            # Method 3: Basic HTML parsing
            if not extracted_text:
                extracted_text = self._extract_with_bs4(content)
            
            # Method 4: Plain text processing
            if not extracted_text:
                extracted_text = self._extract_plain_text(content)
            
            if extracted_text:
                # Split into sections if long
                sections = self._split_into_sections(extracted_text)
                
                for i, section in enumerate(sections):
                    if len(section.strip()) < 50:  # Skip very short sections
                        continue
                    
                    title = self._extract_section_title(section, i)
                    
                    block = self.create_content_block(
                        content_type=ContentType.SECTION,
                        content=section,
                        url=url,
                        title=title,
                        metadata={
                            "extraction_method": "generic",
                            "section_index": i,
                            "content_type": content_type,
                            "word_count": len(section.split())
                        }
                    )
                    
                    if block:
                        blocks.append(block)
            
            logger.info(f"Extracted {len(blocks)} content blocks using generic adapter from {url}")
            return blocks
            
        except Exception as e:
            logger.error(f"Error extracting content with generic adapter from {url}: {e}")
            return []
    
    def _extract_with_readability(self, content: str) -> Optional[str]:
        """Extract content using readability library."""
        try:
            doc = Document(content)
            summary = doc.summary()
            
            if summary:
                # Parse HTML and extract text
                soup = BeautifulSoup(summary, 'html.parser')
                return soup.get_text(separator=' ', strip=True)
            
            return None
            
        except Exception as e:
            logger.debug(f"Readability extraction failed: {e}")
            return None
    
    def _extract_with_trafilatura(self, content: str) -> Optional[str]:
        """Extract content using trafilatura."""
        try:
            extracted = trafilatura.extract(content)
            if extracted and len(extracted.strip()) > 100:
                return extracted.strip()
            
            return None
            
        except Exception as e:
            logger.debug(f"Trafilatura extraction failed: {e}")
            return None
    
    def _extract_with_bs4(self, content: str) -> Optional[str]:
        """Extract content using BeautifulSoup."""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text(separator=' ', strip=True)
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text)
            
            if len(text.strip()) > 100:
                return text.strip()
            
            return None
            
        except Exception as e:
            logger.debug(f"BeautifulSoup extraction failed: {e}")
            return None
    
    def _extract_plain_text(self, content: str) -> Optional[str]:
        """Extract content from plain text."""
        try:
            # Basic text cleaning
            text = content.strip()
            
            # Remove excessive whitespace
            text = re.sub(r'\s+', ' ', text)
            
            # Remove common non-content patterns
            text = re.sub(r'^\s*[\[\]\{\}()]+\s*$', '', text, flags=re.MULTILINE)
            
            if len(text) > 100:
                return text
            
            return None
            
        except Exception as e:
            logger.debug(f"Plain text extraction failed: {e}")
            return None
    
    def _split_into_sections(self, text: str, max_section_length: int = 2000) -> List[str]:
        """Split text into logical sections."""
        if len(text) <= max_section_length:
            return [text]
        
        sections = []
        
        # Try to split by paragraphs first
        paragraphs = text.split('\n\n')
        current_section = ""
        
        for paragraph in paragraphs:
            if len(current_section + paragraph) > max_section_length:
                if current_section:
                    sections.append(current_section.strip())
                current_section = paragraph
            else:
                current_section += "\n\n" + paragraph if current_section else paragraph
        
        if current_section:
            sections.append(current_section.strip())
        
        # If sections are still too long, split by sentences
        final_sections = []
        for section in sections:
            if len(section) > max_section_length:
                sentence_sections = self._split_by_sentences(section, max_section_length)
                final_sections.extend(sentence_sections)
            else:
                final_sections.append(section)
        
        return final_sections
    
    def _split_by_sentences(self, text: str, max_length: int) -> List[str]:
        """Split text by sentences when sections are too long."""
        sentences = re.split(r'[.!?]+\s+', text)
        sections = []
        current_section = ""
        
        for sentence in sentences:
            if len(current_section + sentence) > max_length:
                if current_section:
                    sections.append(current_section.strip())
                current_section = sentence
            else:
                current_section += ". " + sentence if current_section else sentence
        
        if current_section:
            sections.append(current_section.strip())
        
        return sections
    
    def _extract_section_title(self, section: str, index: int) -> str:
        """Extract or generate a title for a section."""
        # Try to find a title in the first few lines
        lines = section.split('\n')[:3]
        
        for line in lines:
            line = line.strip()
            # Look for lines that might be titles
            if (len(line) < 100 and 
                len(line) > 10 and 
                not line.endswith('.') and 
                not line.endswith('?') and
                not line.endswith('!')):
                return line
        
        # Generate a title based on content
        words = section.split()[:5]
        title = ' '.join(words)
        
        if len(title) > 50:
            title = title[:47] + "..."
        
        return title or f"Section {index + 1}"

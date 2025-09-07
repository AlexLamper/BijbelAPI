"""
Verse formatting utilities for Bible text.

Handles HTML formatting of Bible verses with proper structure
and styling for display in web applications.
"""

import re
from typing import List, Dict, Any

class VerseFormatter:
    """Formats Bible verses into HTML with proper structure."""
    
    def __init__(self):
        """Initialize the verse formatter."""
        pass
    
    def format_verses(self, verses: List[Dict[str, Any]]) -> str:
        """
        Format a list of verses into HTML.
        
        Args:
            verses: List of verse dictionaries with 'verse' and 'text' keys
            
        Returns:
            Formatted HTML string
        """
        if not verses:
            return ""
        
        # Group verses into paragraphs based on pilcrow (¶) markers
        paragraphs = self._group_into_paragraphs(verses)
        
        # Format each paragraph
        formatted_paragraphs = []
        for paragraph in paragraphs:
            formatted_paragraph = self._format_paragraph(paragraph)
            if formatted_paragraph:
                formatted_paragraphs.append(formatted_paragraph)
        
        return "".join(formatted_paragraphs)
    
    def _group_into_paragraphs(self, verses: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Group verses into paragraphs based on pilcrow markers.
        
        Args:
            verses: List of verse dictionaries
            
        Returns:
            List of paragraph groups (each group is a list of verses)
        """
        if not verses:
            return []
        
        # If no pilcrow markers, treat all verses as one paragraph
        has_pilcrows = any('¶' in verse.get('text', '') for verse in verses)
        if not has_pilcrows:
            return [verses]
        
        # Group by pilcrow markers
        paragraphs = []
        current_paragraph = []
        
        for verse in verses:
            text = verse.get('text', '')
            if '¶' in text:
                # Remove pilcrow and add to current paragraph
                clean_text = text.replace('¶', '').strip()
                if clean_text:
                    verse_copy = verse.copy()
                    verse_copy['text'] = clean_text
                    current_paragraph.append(verse_copy)
                
                # Start new paragraph
                if current_paragraph:
                    paragraphs.append(current_paragraph)
                    current_paragraph = []
            else:
                current_paragraph.append(verse)
        
        # Add remaining verses as final paragraph
        if current_paragraph:
            paragraphs.append(current_paragraph)
        
        return paragraphs
    
    def _format_paragraph(self, verses: List[Dict[str, Any]]) -> str:
        """
        Format a single paragraph of verses.
        
        Args:
            verses: List of verse dictionaries for one paragraph
            
        Returns:
            Formatted HTML paragraph
        """
        if not verses:
            return ""
        
        # Format each verse
        formatted_verses = []
        for verse in verses:
            verse_num = verse.get('verse', '')
            text = verse.get('text', '')
            
            if verse_num and text:
                # Wrap verse number and first two words in nowrap span
                formatted_verse = self._format_single_verse(verse_num, text)
                formatted_verses.append(formatted_verse)
        
        if not formatted_verses:
            return ""
        
        # Join verses and wrap in paragraph
        verse_content = "".join(formatted_verses)
        return f'<p>{verse_content}</p>'
    
    def _format_single_verse(self, verse_num: str, text: str) -> str:
        """
        Format a single verse with proper HTML structure.
        
        Args:
            verse_num: Verse number
            text: Verse text
            
        Returns:
            Formatted HTML verse
        """
        # Split text into words
        words = text.split()
        if len(words) < 2:
            # Not enough words for nowrap span
            return f'<span class="verse"><span class="verse-number">{verse_num}</span> {text}</span>'
        
        # Wrap verse number and first two words in nowrap span
        first_two_words = " ".join(words[:2])
        remaining_words = " ".join(words[2:])
        
        return f'<span class="verse"><span class="nowrap"><span class="verse-number">{verse_num}</span> {first_two_words}</span> {remaining_words}</span>'
    
    def clean_verse_suffix(self, verse_part: str) -> str:
        """
        Clean verse suffixes like 'a', 'b' from verse references.
        
        Args:
            verse_part: Verse part with possible suffix
            
        Returns:
            Cleaned verse part
        """
        # Remove common suffixes
        suffixes = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        for suffix in suffixes:
            if verse_part.endswith(suffix):
                return verse_part[:-1]
        
        return verse_part

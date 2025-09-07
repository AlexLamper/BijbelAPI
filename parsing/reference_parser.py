"""
Main reference parser for complex Bible references.

Handles parsing of complex Bible references including:
- Discontinuous ranges (Psalm 139:1-5, 12-17)
- Cross-chapter references (John 3:16-4:1)
- Complex ranges (Mark 2:4, (6-10), 11-end)
- Verse suffixes (Habakkuk 3:2-19a)
"""

import re
import requests
from typing import Dict, List, Any, Optional, Tuple
from .book_normalizer import BookNormalizer

class ReferenceParser:
    """Parses complex Bible references and fetches formatted text."""
    
    def __init__(self, base_url: str = "http://localhost:8081", version: str = "asv"):
        """
        Initialize the reference parser.
        
        Args:
            base_url: Base URL for Scriptura API
            version: Default Bible version
        """
        self.base_url = base_url
        self.version = version
        self.book_normalizer = BookNormalizer()
    
    def parse(self, reference: str, version: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse a Bible reference and return formatted text.
        
        Args:
            reference: Bible reference to parse
            version: Bible version (optional, uses default if not provided)
            
        Returns:
            Dictionary with parsing results and formatted text
        """
        if not reference:
            return {
                "reference": reference,
                "parsed": False,
                "error": "Empty reference",
                "formatted_text": f"[Reading: {reference}]"
            }
        
        version = version or self.version
        
        try:
            # Clean the reference
            clean_reference = self._clean_reference(reference)
            
            # Check for complex references
            if self._is_complex_reference(clean_reference):
                return self._handle_complex_reference(clean_reference, version)
            else:
                return self._handle_simple_reference(clean_reference, version)
                
        except Exception as e:
            return {
                "reference": reference,
                "parsed": False,
                "error": str(e),
                "formatted_text": f"[Reading: {reference}]"
            }
    
    def _clean_reference(self, reference: str) -> str:
        """Clean up a reference string."""
        return reference.strip()
    
    def _is_complex_reference(self, reference: str) -> bool:
        """Check if a reference requires complex parsing."""
        # Check for discontinuous ranges (commas)
        if ',' in reference:
            return True
        
        # Check for cross-chapter references (multiple colons)
        if '-' in reference and reference.count(':') >= 2:
            return True
        
        # Check for complex syntax (parentheses)
        if '(' in reference and ')' in reference:
            return True
        
        
        # Check for optional verses in brackets
        if '[' in reference and ']' in reference:
            return True
        
        return False
    
    def _handle_simple_reference(self, reference: str, version: str) -> Dict[str, Any]:
        """Handle simple references like 'John 3:16' or 'Psalm 23:1-6'."""
        try:
            # Parse book, chapter, verse range
            book, chapter, verse_range = self._parse_simple_reference(reference)
            if not book or not chapter:
                raise ValueError("Could not parse reference")
            
            # Normalize book name
            book = self.book_normalizer.normalize(book)
            
            # Get chapter data
            chapter_data = self._get_chapter_data(book, chapter, version)
            if not chapter_data:
                raise ValueError("Could not fetch chapter data")
            
            # Extract verses
            verses = self._extract_verses_from_chapter(chapter_data, verse_range)
            if not verses:
                raise ValueError("No verses found")
            
            # Return raw verses (formatting will be done by liturgical_display)
            formatted_text = self._format_verses_simple(verses)
            
            return {
                "reference": reference,
                "parsed": True,
                "book": book,
                "chapter": chapter,
                "verses": verses,
                "formatted_text": formatted_text
            }
            
        except Exception as e:
            return {
                "reference": reference,
                "parsed": False,
                "error": str(e),
                "formatted_text": f"[Reading: {reference}]"
            }
    
    def _handle_complex_reference(self, reference: str, version: str) -> Dict[str, Any]:
        """Handle complex references with special parsing logic."""
        try:
            
            # Check for optional verses in brackets
            if '[' in reference and ']' in reference:
                return self._handle_optional_verses(reference, version)
            
            # Check for discontinuous ranges
            if ',' in reference:
                return self._handle_discontinuous_range(reference, version)
            
            # Check for cross-chapter references
            if '-' in reference and reference.count(':') >= 2:
                return self._handle_cross_chapter_reference(reference, version)
            
            # Check for complex syntax
            if '(' in reference and ')' in reference:
                return self._handle_complex_syntax(reference, version)
            
            # Fallback to simple parsing
            return self._handle_simple_reference(reference, version)
            
        except Exception as e:
            return {
                "reference": reference,
                "parsed": False,
                "error": str(e),
                "formatted_text": f"[Reading: {reference}]"
            }
    
    def _handle_discontinuous_range(self, reference: str, version: str) -> Dict[str, Any]:
        """Handle discontinuous ranges like 'Psalm 139:1-5, 12-17'."""
        try:
            # Split by comma to get individual ranges
            parts = reference.split(',')
            all_verses = []
            
            # Parse the first part to get book and chapter
            first_part = parts[0].strip()
            if ':' not in first_part:
                raise ValueError("Invalid reference format")
            
            book_chapter, verse_part = first_part.split(':', 1)
            book_chapter_parts = book_chapter.rsplit(' ', 1)
            
            if len(book_chapter_parts) == 2:
                book = book_chapter_parts[0].strip()
                chapter = book_chapter_parts[1].strip()
            else:
                book = book_chapter
                chapter = "1"
            
            # Normalize book name
            book = self.book_normalizer.normalize(book)
            
            # Process all parts
            for part in parts:
                part = part.strip()
                
                if ':' in part:
                    # Parse each part as a separate reference
                    book_chapter, verse_part = part.split(':', 1)
                    book_chapter_parts = book_chapter.rsplit(' ', 1)
                    
                    if len(book_chapter_parts) == 2:
                        part_book = book_chapter_parts[0].strip()
                        part_chapter = book_chapter_parts[1].strip()
                    else:
                        part_book = book_chapter
                        part_chapter = "1"
                    
                    # Normalize book name
                    part_book = self.book_normalizer.normalize(part_book)
                else:
                    # Reuse book and chapter from first part
                    part_book = book
                    part_chapter = chapter
                    verse_part = part
                
                # Get chapter data
                chapter_data = self._get_chapter_data(part_book, part_chapter, version)
                if not chapter_data:
                    continue
                
                # Parse verse range
                verse_part = self._clean_verse_suffix(verse_part)
                verses = self._extract_verses_from_chapter(chapter_data, verse_part)
                all_verses.extend(verses)
            
            if not all_verses:
                raise ValueError("No verses found")
            
            # Format text
            formatted_text = self._format_verses_simple(all_verses)
            
            return {
                "reference": reference,
                "parsed": True,
                "book": book,
                "chapter": chapter,
                "verses": all_verses,
                "formatted_text": formatted_text
            }
            
        except Exception as e:
            return {
                "reference": reference,
                "parsed": False,
                "error": str(e),
                "formatted_text": f"[Reading: {reference}]"
            }
    
    def _handle_cross_chapter_reference(self, reference: str, version: str) -> Dict[str, Any]:
        """Handle cross-chapter references like 'John 3:16-4:1'."""
        try:
            # Parse cross-chapter reference
            pattern = r'^(.+?)\s+(\d+):(\d+)-(\d+):(\d+)$'
            match = re.match(pattern, reference.strip())
            
            if not match:
                raise ValueError("Invalid cross-chapter reference format")
            
            book = match.group(1).strip()
            start_chapter = int(match.group(2))
            start_verse = int(match.group(3))
            end_chapter = int(match.group(4))
            end_verse = int(match.group(5))
            
            # Normalize book name
            book = self.book_normalizer.normalize(book)
            
            all_verses = []
            
            # Handle verses from start chapter
            if start_chapter == end_chapter:
                # Same chapter - just get the range
                chapter_data = self._get_chapter_data(book, str(start_chapter), version)
                if chapter_data:
                    verses = self._extract_verses_from_range(chapter_data, start_verse, end_verse)
                    all_verses.extend(verses)
            else:
                # Cross-chapter - get verses from start chapter to end
                # First, get remaining verses from start chapter
                chapter_data = self._get_chapter_data(book, str(start_chapter), version)
                if chapter_data:
                    # Get all verses from start_verse to end of chapter
                    verse_numbers = [int(v) for v in chapter_data['verses'].keys() if v.isdigit()]
                    if verse_numbers:
                        max_verse = max(verse_numbers)
                        verses = self._extract_verses_from_range(chapter_data, start_verse, max_verse)
                        all_verses.extend(verses)
                
                # Then get verses from end chapter
                chapter_data = self._get_chapter_data(book, str(end_chapter), version)
                if chapter_data:
                    verses = self._extract_verses_from_range(chapter_data, 1, end_verse)
                    all_verses.extend(verses)
            
            if not all_verses:
                raise ValueError("No verses found")
            
            # Format text
            formatted_text = self._format_verses_simple(all_verses)
            
            return {
                "reference": reference,
                "parsed": True,
                "book": book,
                "start_chapter": start_chapter,
                "end_chapter": end_chapter,
                "verses": all_verses,
                "formatted_text": formatted_text
            }
            
        except Exception as e:
            return {
                "reference": reference,
                "parsed": False,
                "error": str(e),
                "formatted_text": f"[Reading: {reference}]"
            }
    
    
    def _handle_optional_verses(self, reference: str, version: str) -> Dict[str, Any]:
        """Handle optional verses like 'Luke 1:39-45[46-55]'."""
        try:
            # Extract the main reference and optional part
            if '[' in reference and ']' in reference:
                main_part = reference.split('[')[0].strip()
                optional_part = reference.split('[')[1].split(']')[0].strip()
                
                # Parse the main reference
                main_result = self._handle_simple_reference(main_part, version)
                
                if main_result["parsed"]:
                    # Parse optional verses separately
                    # Extract book and chapter from main part
                    book_chapter, verse_part = main_part.split(':', 1)
                    book_chapter_parts = book_chapter.rsplit(' ', 1)
                    
                    if len(book_chapter_parts) == 2:
                        book = book_chapter_parts[0].strip()
                        chapter = book_chapter_parts[1].strip()
                    else:
                        book = book_chapter
                        chapter = "1"
                    
                    # Normalize book name
                    book = self.book_normalizer.normalize(book)
                    
                    # Get chapter data for optional verses
                    chapter_data = self._get_chapter_data(book, chapter, version)
                    if chapter_data:
                        optional_verses = self._extract_verses_from_chapter(chapter_data, optional_part)
                        main_result["optional_verses"] = optional_verses
                    
                    main_result["reference"] = reference  # Keep original reference
                
                return main_result
            else:
                raise ValueError("Invalid optional verse format")
                
        except Exception as e:
            return {
                "reference": reference,
                "parsed": False,
                "error": str(e),
                "formatted_text": f"[Reading: {reference}]"
            }
    
    def _handle_complex_syntax(self, reference: str, version: str) -> Dict[str, Any]:
        """Handle complex syntax with parentheses and other special characters."""
        # For now, treat as simple reference after cleaning
        # This can be enhanced later for more complex parsing
        clean_reference = re.sub(r'[()]', '', reference)
        return self._handle_simple_reference(clean_reference, version)
    
    def _parse_simple_reference(self, reference: str) -> Tuple[str, str, str]:
        """Parse a simple reference into book, chapter, verse range."""
        if ':' not in reference:
            # This might be a chapter-only reference like "Philemon 1-21"
            # or a book-only reference like "Psalm 146"
            return self._parse_chapter_only_reference(reference)
        
        parts = reference.split(':')
        if len(parts) != 2:
            raise ValueError("Invalid reference format")
        
        book_chapter = parts[0].strip()
        verse_range = parts[1].strip()
        
        # Split book and chapter
        book_chapter_parts = book_chapter.rsplit(' ', 1)
        if len(book_chapter_parts) == 2:
            book = book_chapter_parts[0].strip()
            chapter = book_chapter_parts[1].strip()
        else:
            book = book_chapter
            chapter = "1"
        
        return book, chapter, verse_range
    
    def _parse_chapter_only_reference(self, reference: str) -> Tuple[str, str, str]:
        """Parse chapter-only references like 'Philemon 1-21' or 'Psalm 146'."""
        # Split by space to get book and chapter info
        parts = reference.split()
        if len(parts) < 2:
            raise ValueError("Invalid reference format")
        
        book = parts[0].strip()
        chapter_info = parts[1].strip()
        
        # Check if it's a range like "1-21"
        if '-' in chapter_info:
            # This is a chapter range like "Philemon 1-21"
            start_chapter, end_chapter = chapter_info.split('-', 1)
            return book, start_chapter, f"1-{end_chapter}"  # Get all verses from start to end chapter
        else:
            # This is a single chapter like "Psalm 146"
            return book, chapter_info, "1-end"  # Get all verses in the chapter
    
    def _get_chapter_data(self, book: str, chapter: str, version: str) -> Optional[Dict[str, Any]]:
        """Get chapter data from Scriptura API."""
        try:
            url = f"{self.base_url}/api/chapter"
            params = {
                'book': book,
                'chapter': chapter,
                'version': version
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            print(f"Error fetching chapter data: {e}")
            return None
    
    def _extract_verses_from_chapter(self, chapter_data: Dict[str, Any], verse_range: str) -> List[Dict[str, Any]]:
        """Extract specific verses from chapter data."""
        verses = []
        
        if '-' in verse_range:
            # Range of verses
            start_verse, end_verse = verse_range.split('-', 1)
            start_verse = self._clean_verse_suffix(start_verse.strip())
            start_verse = int(start_verse)
            
            if end_verse.strip().lower() == 'end':
                # Find the last verse in the chapter
                verse_numbers = [int(v) for v in chapter_data['verses'].keys() if v.isdigit()]
                if verse_numbers:
                    end_verse = max(verse_numbers)
                else:
                    end_verse = start_verse
            else:
                # Clean verse suffix before converting to int
                end_verse = self._clean_verse_suffix(end_verse.strip())
                end_verse = int(end_verse)
            
            # Extract verses from range
            for verse_num in range(start_verse, end_verse + 1):
                verse_text = chapter_data['verses'].get(str(verse_num))
                if verse_text:
                    verses.append({
                        'verse': str(verse_num),
                        'text': verse_text
                    })
        else:
            # Single verse
            clean_verse_range = self._clean_verse_suffix(verse_range)
            verse_text = chapter_data['verses'].get(clean_verse_range)
            if verse_text:
                verses.append({
                    'verse': clean_verse_range,
                    'text': verse_text
                })
        
        return verses
    
    def _extract_verses_from_range(self, chapter_data: Dict[str, Any], start_verse: int, end_verse: int) -> List[Dict[str, Any]]:
        """Extract verses from a specific range."""
        verses = []
        for verse_num in range(start_verse, end_verse + 1):
            verse_text = chapter_data['verses'].get(str(verse_num))
            if verse_text:
                verses.append({
                    'verse': str(verse_num),
                    'text': verse_text
                })
        return verses
    
    def _clean_verse_suffix(self, verse_part: str) -> str:
        """Clean verse suffixes like 'a', 'b' from verse references."""
        # Remove common suffixes
        suffixes = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']
        for suffix in suffixes:
            if verse_part.endswith(suffix):
                return verse_part[:-1]
        
        return verse_part
    
    def _format_verses_simple(self, verses: List[Dict[str, Any]]) -> str:
        """Simple formatting for verses (just join with spaces)."""
        if not verses:
            return ""
        
        formatted_verses = []
        for verse in verses:
            verse_num = verse.get('verse', '')
            text = verse.get('text', '')
            if verse_num and text:
                formatted_verses.append(f"{verse_num} {text}")
        
        return " ".join(formatted_verses)

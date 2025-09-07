"""
Book name normalization for Bible references.

Handles mapping between different book name formats and the
standardized names expected by the Scriptura API.
"""

class BookNormalizer:
    """Normalizes book names to match Scriptura API expectations."""
    
    def __init__(self):
        """Initialize the book normalizer with common mappings."""
        self.book_mappings = {
            # Psalms variations
            'Psalm': 'Psalms',
            'Ps': 'Psalms',
            'PSALM': 'Psalms',
            'PSALMS': 'Psalms',
            
            # Add more mappings as needed
            # Common abbreviations can be added here
        }
    
    def normalize(self, book: str) -> str:
        """
        Normalize a book name to match API expectations.
        
        Args:
            book: Book name from liturgical calendar
            
        Returns:
            Normalized book name for API
        """
        if not book:
            return book
            
        # Strip whitespace and normalize case
        book = book.strip()
        
        # Check for exact match in mappings
        if book in self.book_mappings:
            return self.book_mappings[book]
        
        # Return original if no mapping found
        return book
    
    def add_mapping(self, from_name: str, to_name: str) -> None:
        """
        Add a custom book name mapping.
        
        Args:
            from_name: Source book name
            to_name: Target book name
        """
        self.book_mappings[from_name] = to_name

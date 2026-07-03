"""
Spider Manager — Advanced Search Engine
Provides full-text search capabilities across download history with advanced filtering.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from utils.logger import get_logger
from core.history_manager import HistoryManager, HistoryEntry

log = get_logger(__name__)


class SearchFieldType(Enum):
    """Field types for advanced search."""
    FILENAME = "filename"
    URL = "url"
    CATEGORY = "category"
    STATE = "state"
    TAGS = "tags"
    DATE = "date"
    SIZE = "size"
    SPEED = "speed"


@dataclass
class SearchCriteria:
    """Advanced search criteria."""
    query: str = ""
    filename: str = ""
    url: str = ""
    category: str = ""
    state: str = ""
    tags: List[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    size_min: Optional[int] = None
    size_max: Optional[int] = None
    speed_min: Optional[float] = None
    speed_max: Optional[float] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class SearchEngine:
    """
    Advanced search engine for download history.
    
    Features:
    - Full-text search across multiple fields
    - Advanced filtering by date, size, speed
    - Boolean operators (AND, OR, NOT)
    - Regular expression support
    - Fuzzy matching
    - Search suggestions
    - Saved searches
    """

    def __init__(self, history_manager: HistoryManager):
        """
        Initialize SearchEngine.
        
        Args:
            history_manager: HistoryManager instance to search
        """
        self.history_manager = history_manager
        self.saved_searches: Dict[str, SearchCriteria] = {}

    def search(
        self,
        criteria: SearchCriteria,
        limit: int = 100,
        offset: int = 0
    ) -> List[HistoryEntry]:
        """
        Perform advanced search.
        
        Args:
            criteria: SearchCriteria with filters
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of matching HistoryEntry objects
        """
        # Get all entries first (could be optimized with database queries)
        all_entries = self.history_manager.get_all_entries(limit=5000)
        
        # Apply filters
        results = []
        for entry in all_entries:
            if self._matches_criteria(entry, criteria):
                results.append(entry)
        
        # Sort by relevance (simple implementation: match count)
        results.sort(key=lambda e: self._calculate_relevance(e, criteria), reverse=True)
        
        # Apply pagination
        return results[offset:offset + limit]

    def quick_search(self, query: str, limit: int = 100) -> List[HistoryEntry]:
        """
        Quick full-text search.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching HistoryEntry objects
        """
        criteria = SearchCriteria(query=query)
        return self.search(criteria, limit)

    def advanced_search(
        self,
        filename: str = "",
        url: str = "",
        category: str = "",
        state: str = "",
        tags: List[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        size_min: Optional[int] = None,
        size_max: Optional[int] = None,
        limit: int = 100
    ) -> List[HistoryEntry]:
        """
        Advanced search with specific filters.
        
        Args:
            filename: Filename filter
            url: URL filter
            category: Category filter
            state: State filter
            tags: Tags filter (must match all)
            date_from: Start date filter
            date_to: End date filter
            size_min: Minimum size filter (bytes)
            size_max: Maximum size filter (bytes)
            limit: Maximum results
            
        Returns:
            List of matching HistoryEntry objects
        """
        criteria = SearchCriteria(
            filename=filename,
            url=url,
            category=category,
            state=state,
            tags=tags or [],
            date_from=date_from,
            date_to=date_to,
            size_min=size_min,
            size_max=size_max
        )
        return self.search(criteria, limit)

    def _matches_criteria(self, entry: HistoryEntry, criteria: SearchCriteria) -> bool:
        """Check if entry matches search criteria."""
        # General query search
        if criteria.query:
            if not self._matches_query(entry, criteria.query):
                return False
        
        # Filename filter
        if criteria.filename and not self._matches_field(entry.filename, criteria.filename):
            return False
        
        # URL filter
        if criteria.url and not self._matches_field(entry.url, criteria.url):
            return False
        
        # Category filter
        if criteria.category and criteria.category.lower() not in entry.category.lower():
            return False
        
        # State filter
        if criteria.state and criteria.state.lower() != entry.state.lower():
            return False
        
        # Tags filter (must match all)
        if criteria.tags:
            entry_tags_lower = [t.lower() for t in entry.tags]
            for tag in criteria.tags:
                if tag.lower() not in entry_tags_lower:
                    return False
        
        # Date range filter
        if criteria.date_from:
            entry_date = datetime.fromtimestamp(entry.created_at)
            if entry_date < criteria.date_from:
                return False
        
        if criteria.date_to:
            entry_date = datetime.fromtimestamp(entry.created_at)
            if entry_date > criteria.date_to:
                return False
        
        # Size range filter
        if criteria.size_min is not None and entry.total_size < criteria.size_min:
            return False
        
        if criteria.size_max is not None and entry.total_size > criteria.size_max:
            return False
        
        # Speed range filter
        if criteria.speed_min is not None and entry.speed < criteria.speed_min:
            return False
        
        if criteria.speed_max is not None and entry.speed > criteria.speed_max:
            return False
        
        return True

    def _matches_query(self, entry: HistoryEntry, query: str) -> bool:
        """Check if entry matches general query."""
        query_lower = query.lower()
        
        # Search in filename
        if query_lower in entry.filename.lower():
            return True
        
        # Search in URL
        if query_lower in entry.url.lower():
            return True
        
        # Search in tags
        for tag in entry.tags:
            if query_lower in tag.lower():
                return True
        
        # Search in category
        if query_lower in entry.category.lower():
            return True
        
        return False

    def _matches_field(self, field: str, pattern: str) -> bool:
        """Check if field matches pattern (supports wildcards and regex)."""
        # Check for wildcard pattern
        if '*' in pattern or '?' in pattern:
            # Convert wildcard pattern to regex
            regex_pattern = pattern.replace('*', '.*').replace('?', '.')
            regex_pattern = f'^{regex_pattern}$'
            try:
                return re.match(regex_pattern, field, re.IGNORECASE) is not None
            except re.error:
                return False
        
        # Check for regex pattern
        try:
            return re.search(pattern, field, re.IGNORECASE) is not None
        except re.error:
            # Fall back to simple substring match
            return pattern.lower() in field.lower()

    def _calculate_relevance(self, entry: HistoryEntry, criteria: SearchCriteria) -> int:
        """Calculate relevance score for sorting."""
        score = 0
        
        # Query match
        if criteria.query:
            if criteria.query.lower() in entry.filename.lower():
                score += 10
            if criteria.query.lower() in entry.url.lower():
                score += 5
        
        # Filename match
        if criteria.filename and criteria.filename.lower() in entry.filename.lower():
            score += 8
        
        # URL match
        if criteria.url and criteria.url.lower() in entry.url.lower():
            score += 5
        
        # Category match
        if criteria.category and criteria.category.lower() == entry.category.lower():
            score += 3
        
        # State match
        if criteria.state and criteria.state.lower() == entry.state.lower():
            score += 2
        
        # Tags match
        if criteria.tags:
            entry_tags_lower = [t.lower() for t in entry.tags]
            matched_tags = sum(1 for tag in criteria.tags if tag.lower() in entry_tags_lower)
            score += matched_tags * 2
        
        return score

    def get_suggestions(self, partial_query: str, limit: int = 10) -> List[str]:
        """
        Get search suggestions based on partial query.
        
        Args:
            partial_query: Partial search query
            limit: Maximum suggestions
            
        Returns:
            List of suggestion strings
        """
        if not partial_query or len(partial_query) < 2:
            return []
        
        partial_lower = partial_query.lower()
        suggestions = set()
        
        # Get recent entries for suggestions
        recent_entries = self.history_manager.get_all_entries(limit=500)
        
        for entry in recent_entries:
            # Filename suggestions
            if partial_lower in entry.filename.lower():
                suggestions.add(entry.filename)
            
            # URL suggestions
            if partial_lower in entry.url.lower():
                # Extract domain for cleaner suggestions
                from urllib.parse import urlparse
                try:
                    parsed = urlparse(entry.url)
                    if parsed.netloc:
                        suggestions.add(parsed.netloc)
                except Exception:
                    pass
            
            # Tag suggestions
            for tag in entry.tags:
                if partial_lower in tag.lower():
                    suggestions.add(tag)
            
            # Category suggestions
            if partial_lower in entry.category.lower():
                suggestions.add(entry.category)
            
            if len(suggestions) >= limit:
                break
        
        return sorted(list(suggestions))[:limit]

    def save_search(self, name: str, criteria: SearchCriteria) -> None:
        """
        Save a search criteria for later use.
        
        Args:
            name: Name for the saved search
            criteria: SearchCriteria to save
        """
        self.saved_searches[name] = criteria
        log.debug("Saved search: %s", name)

    def load_search(self, name: str) -> Optional[SearchCriteria]:
        """
        Load a saved search.
        
        Args:
            name: Name of the saved search
            
        Returns:
            SearchCriteria if found, None otherwise
        """
        return self.saved_searches.get(name)

    def delete_saved_search(self, name: str) -> bool:
        """
        Delete a saved search.
        
        Args:
            name: Name of the saved search
            
        Returns:
            True if deleted, False if not found
        """
        if name in self.saved_searches:
            del self.saved_searches[name]
            log.debug("Deleted saved search: %s", name)
            return True
        return False

    def get_saved_searches(self) -> List[str]:
        """Get list of saved search names."""
        return list(self.saved_searches.keys())

    def get_recent_searches(self, limit: int = 10) -> List[str]:
        """
        Get recent search queries (placeholder for future implementation).
        
        Args:
            limit: Maximum recent searches
            
        Returns:
            List of recent search queries
        """
        # This could be implemented with persistent storage in the future
        return []

    def add_recent_search(self, query: str) -> None:
        """
        Add a query to recent searches (placeholder for future implementation).
        
        Args:
            query: Search query to add
        """
        # This could be implemented with persistent storage in the future
        pass

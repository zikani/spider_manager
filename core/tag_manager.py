"""
Spider Manager — Tag Manager
Manages download tags with persistence, color customization, and statistics.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from pathlib import Path

from utils.logger import get_logger
from config.settings import get_download_directory

log = get_logger(__name__)


@dataclass
class Tag:
    """Represents a download tag."""
    name: str
    color: str = "#3498db"  # Default blue
    description: str = ""
    created_at: float = 0.0
    usage_count: int = 0

    def __post_init__(self):
        if self.created_at == 0.0:
            import time
            self.created_at = time.time()


class TagManager:
    """
    Manages download tags with SQLite persistence.
    
    Features:
    - Tag creation, editing, deletion
    - Color customization
    - Usage statistics
    - Tag assignment to downloads
    - Tag filtering and search
    - Import/export tags
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize TagManager.
        
        Args:
            db_path: Custom database path. If None, uses default location.
        """
        if db_path is None:
            download_dir = Path(get_download_directory())
            tags_dir = download_dir / ".spider_manager"
            tags_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(tags_dir / "tags.db")
        
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    name TEXT PRIMARY KEY,
                    color TEXT DEFAULT '#3498db',
                    description TEXT DEFAULT '',
                    created_at REAL NOT NULL,
                    usage_count INTEGER DEFAULT 0
                )
            """)
            
            # Create index for search
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tag_name ON tags(name)")
            
            conn.commit()

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def create_tag(self, tag: Tag) -> bool:
        """
        Create a new tag.
        
        Args:
            tag: Tag to create
            
        Returns:
            True if created, False if already exists
        """
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO tags (name, color, description, created_at, usage_count)
                    VALUES (?, ?, ?, ?, ?)
                """, (tag.name, tag.color, tag.description, tag.created_at, tag.usage_count))
                conn.commit()
                log.debug("Created tag: %s", tag.name)
                return True
        except sqlite3.IntegrityError:
            log.warning("Tag already exists: %s", tag.name)
            return False

    def update_tag(self, tag: Tag) -> bool:
        """
        Update an existing tag.
        
        Args:
            tag: Tag to update
            
        Returns:
            True if updated, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                UPDATE tags SET
                    color = ?, description = ?, usage_count = ?
                WHERE name = ?
            """, (tag.color, tag.description, tag.usage_count, tag.name))
            conn.commit()
            updated = cursor.rowcount > 0
            if updated:
                log.debug("Updated tag: %s", tag.name)
            return updated

    def delete_tag(self, name: str) -> bool:
        """
        Delete a tag.
        
        Args:
            name: Tag name to delete
            
        Returns:
            True if deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM tags WHERE name = ?", (name,))
            conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                log.debug("Deleted tag: %s", name)
            return deleted

    def get_tag(self, name: str) -> Optional[Tag]:
        """
        Get a specific tag by name.
        
        Args:
            name: Tag name to retrieve
            
        Returns:
            Tag if found, None otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM tags WHERE name = ?", (name,))
            row = cursor.fetchone()
            if row:
                return self._row_to_tag(row)
        return None

    def get_all_tags(self) -> List[Tag]:
        """
        Get all tags sorted by usage count.
        
        Returns:
            List of Tag objects
        """
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM tags ORDER BY usage_count DESC, name ASC")
            rows = cursor.fetchall()
            return [self._row_to_tag(row) for row in rows]

    def search_tags(self, query: str) -> List[Tag]:
        """
        Search tags by name or description.
        
        Args:
            query: Search query
            
        Returns:
            List of matching Tag objects
        """
        search_pattern = f"%{query}%"
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM tags
                WHERE name LIKE ? OR description LIKE ?
                ORDER BY usage_count DESC
            """, (search_pattern, search_pattern))
            rows = cursor.fetchall()
            return [self._row_to_tag(row) for row in rows]

    def increment_usage(self, name: str) -> bool:
        """
        Increment usage count for a tag.
        
        Args:
            name: Tag name
            
        Returns:
            True if updated, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE tags SET usage_count = usage_count + 1 WHERE name = ?",
                (name,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def decrement_usage(self, name: str) -> bool:
        """
        Decrement usage count for a tag.
        
        Args:
            name: Tag name
            
        Returns:
            True if updated, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE tags SET usage_count = MAX(0, usage_count - 1) WHERE name = ?",
                (name,)
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_popular_tags(self, limit: int = 10) -> List[Tag]:
        """
        Get most popular tags by usage count.
        
        Args:
            limit: Maximum number of tags to return
            
        Returns:
            List of Tag objects
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM tags
                ORDER BY usage_count DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [self._row_to_tag(row) for row in rows]

    def get_recent_tags(self, limit: int = 10) -> List[Tag]:
        """
        Get most recently created tags.
        
        Args:
            limit: Maximum number of tags to return
            
        Returns:
            List of Tag objects
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM tags
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [self._row_to_tag(row) for row in rows]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get overall tag statistics.
        
        Returns:
            Dictionary with statistics
        """
        with self._get_connection() as conn:
            # Total tags
            total = conn.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
            
            # Total usage
            total_usage = conn.execute("SELECT SUM(usage_count) FROM tags").fetchone()[0] or 0
            
            # Most used tag
            most_used = conn.execute("""
                SELECT name, usage_count FROM tags
                ORDER BY usage_count DESC LIMIT 1
            """).fetchone()
            
            return {
                "total_tags": total,
                "total_usage": total_usage,
                "most_used_tag": most_used[0] if most_used else None,
                "most_used_count": most_used[1] if most_used else 0
            }

    def export_tags(self, file_path: str) -> None:
        """
        Export all tags to JSON file.
        
        Args:
            file_path: Output JSON file path
        """
        tags = self.get_all_tags()
        data = [asdict(tag) for tag in tags]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        log.info("Exported %d tags to JSON: %s", len(tags), file_path)

    def import_tags(self, file_path: str, overwrite: bool = False) -> int:
        """
        Import tags from JSON file.
        
        Args:
            file_path: Input JSON file path
            overwrite: Whether to overwrite existing tags
            
        Returns:
            Number of tags imported
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        imported = 0
        for tag_data in data:
            tag = Tag(**tag_data)
            if overwrite:
                self.update_tag(tag)
                imported += 1
            else:
                if self.create_tag(tag):
                    imported += 1
        
        log.info("Imported %d tags from JSON: %s", imported, file_path)
        return imported

    def _row_to_tag(self, row: sqlite3.Row) -> Tag:
        """Convert database row to Tag."""
        return Tag(
            name=row['name'],
            color=row['color'],
            description=row['description'],
            created_at=row['created_at'],
            usage_count=row['usage_count']
        )

    def __del__(self):
        """Cleanup on deletion."""
        self.close()

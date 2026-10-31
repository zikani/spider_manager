"""
Spider Manager — Download History Manager
Manages download history with SQLite persistence, search, filtering, and export capabilities.
"""

from __future__ import annotations

import sqlite3
import json
import csv
import os
import asyncio
import aiosqlite
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

from utils.logger import get_logger
from config.settings import get_download_directory

log = get_logger(__name__)


class HistoryFilter(Enum):
    """Filter options for history queries."""
    ALL = "all"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    TODAY = "today"
    THIS_WEEK = "this_week"
    THIS_MONTH = "this_month"


@dataclass
class HistoryEntry:
    """Represents a single download history entry."""
    id: str
    url: str
    filename: str
    save_path: str
    total_size: int
    downloaded: int
    state: str
    category: str
    download_mode: str
    speed: float
    peak_speed: float
    eta: int
    error: str
    retry_count: int
    created_at: float
    started_at: Optional[float]
    completed_at: Optional[float]
    tags: List[str]
    referrer: str
    headers: Dict[str, str]

    @property
    def progress(self) -> float:
        """Calculate progress percentage."""
        if self.total_size == 0:
            return 0.0
        return round(min(self.downloaded / self.total_size * 100, 100.0), 2)

    @property
    def duration(self) -> float:
        """Calculate download duration in seconds."""
        if self.started_at is None:
            return 0.0
        end = self.completed_at or datetime.now().timestamp()
        return end - self.started_at

    @property
    def is_completed(self) -> bool:
        """Check if download was completed."""
        return self.state == "completed"

    @property
    def is_failed(self) -> bool:
        """Check if download failed."""
        return self.state == "error"

    @property
    def is_cancelled(self) -> bool:
        """Check if download was cancelled."""
        return self.state == "cancelled"

    @property
    def date_str(self) -> str:
        """Get formatted date string."""
        dt = datetime.fromtimestamp(self.created_at)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def size_str(self) -> str:
        """Get human-readable size string."""
        from utils.file_utils import format_size
        return format_size(self.total_size)


class HistoryManager:
    """
    Manages download history with SQLite persistence.
    
    Features:
    - SQLite database for persistent storage
    - Search by filename, URL, tags
    - Filter by state, date range
    - Export to CSV/JSON
    - Tag management
    - Automatic cleanup of old entries
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize HistoryManager.
        
        Args:
            db_path: Custom database path. If None, uses default location.
        """
        if db_path is None:
            download_dir = Path(get_download_directory())
            history_dir = download_dir / ".spider_manager"
            history_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(history_dir / "history.db")
        
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None
        self._init_lock = asyncio.Lock()
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Ensure database is initialized."""
        if not self._initialized:
            async with self._init_lock:
                if not self._initialized:
                    await self._init_db()
                    self._initialized = True

    async def _init_db(self) -> None:
        """Initialize database schema with WAL mode."""
        async with aiosqlite.connect(self.db_path) as conn:
            # Enable WAL mode for better concurrency
            await conn.execute("PRAGMA journal_mode=WAL")
            await conn.execute("PRAGMA synchronous=NORMAL")
            await conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
            await conn.execute("PRAGMA busy_timeout=5000")  # 5 second timeout
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id TEXT PRIMARY KEY,
                    url TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    save_path TEXT NOT NULL,
                    total_size INTEGER DEFAULT 0,
                    downloaded INTEGER DEFAULT 0,
                    state TEXT NOT NULL,
                    category TEXT DEFAULT 'Other',
                    download_mode TEXT DEFAULT 'direct',
                    speed REAL DEFAULT 0.0,
                    peak_speed REAL DEFAULT 0.0,
                    eta INTEGER DEFAULT 0,
                    error TEXT DEFAULT '',
                    retry_count INTEGER DEFAULT 0,
                    created_at REAL NOT NULL,
                    started_at REAL,
                    completed_at REAL,
                    tags TEXT DEFAULT '[]',
                    referrer TEXT DEFAULT '',
                    headers TEXT DEFAULT '{}'
                )
            """)
            
            # Create indexes for common queries
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_state ON history(state)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON history(created_at)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_filename ON history(filename)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON history(category)")
            
            await conn.commit()

    async def close(self) -> None:
        """Close database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def add_entry(self, entry: HistoryEntry) -> None:
        """
        Add a new history entry.
        
        Args:
            entry: HistoryEntry to add
        """
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                INSERT OR REPLACE INTO history (
                    id, url, filename, save_path, total_size, downloaded,
                    state, category, download_mode, speed, peak_speed, eta,
                    error, retry_count, created_at, started_at, completed_at,
                    tags, referrer, headers
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.id, entry.url, entry.filename, entry.save_path,
                entry.total_size, entry.downloaded, entry.state,
                entry.category, entry.download_mode, entry.speed,
                entry.peak_speed, entry.eta, entry.error,
                entry.retry_count, entry.created_at, entry.started_at,
                entry.completed_at, json.dumps(entry.tags),
                entry.referrer, json.dumps(entry.headers)
            ))
            await conn.commit()
            log.debug("Added history entry: %s", entry.filename)

    async def update_entry(self, entry: HistoryEntry) -> None:
        """
        Update an existing history entry.
        
        Args:
            entry: HistoryEntry to update
        """
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                UPDATE history SET
                    url = ?, filename = ?, save_path = ?, total_size = ?,
                    downloaded = ?, state = ?, category = ?, download_mode = ?,
                    speed = ?, peak_speed = ?, eta = ?, error = ?,
                    retry_count = ?, started_at = ?, completed_at = ?,
                    tags = ?, referrer = ?, headers = ?
                WHERE id = ?
            """, (
                entry.url, entry.filename, entry.save_path,
                entry.total_size, entry.downloaded, entry.state,
                entry.category, entry.download_mode, entry.speed,
                entry.peak_speed, entry.eta, entry.error,
                entry.retry_count, entry.started_at, entry.completed_at,
                json.dumps(entry.tags), entry.referrer,
                json.dumps(entry.headers), entry.id
            ))
            await conn.commit()
            log.debug("Updated history entry: %s", entry.filename)

    async def get_entry(self, entry_id: str) -> Optional[HistoryEntry]:
        """
        Get a specific history entry by ID.
        
        Args:
            entry_id: Entry ID to retrieve
            
        Returns:
            HistoryEntry if found, None otherwise
        """
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT * FROM history WHERE id = ?",
                (entry_id,)
            )
            row = await cursor.fetchone()
            if row:
                return self._row_to_entry(row)
        return None

    async def get_all_entries(
        self,
        filter_type: HistoryFilter = HistoryFilter.ALL,
        search_query: str = "",
        category: str = "",
        limit: int = 1000,
        offset: int = 0
    ) -> List[HistoryEntry]:
        """
        Get history entries with optional filtering and search.
        
        Args:
            filter_type: Filter by state or date range
            search_query: Search in filename and URL
            category: Filter by category
            limit: Maximum number of entries to return
            offset: Offset for pagination
            
        Returns:
            List of HistoryEntry objects
        """
        await self._ensure_initialized()
        query = "SELECT * FROM history WHERE 1=1"
        params: List[Any] = []

        # Apply state filter
        if filter_type == HistoryFilter.COMPLETED:
            query += " AND state = 'completed'"
        elif filter_type == HistoryFilter.FAILED:
            query += " AND state = 'error'"
        elif filter_type == HistoryFilter.CANCELLED:
            query += " AND state = 'cancelled'"
        elif filter_type == HistoryFilter.PAUSED:
            query += " AND state = 'paused'"
        elif filter_type == HistoryFilter.TODAY:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            query += " AND created_at >= ?"
            params.append(today_start.timestamp())
        elif filter_type == HistoryFilter.THIS_WEEK:
            week_ago = datetime.now() - timedelta(days=7)
            query += " AND created_at >= ?"
            params.append(week_ago.timestamp())
        elif filter_type == HistoryFilter.THIS_MONTH:
            month_ago = datetime.now() - timedelta(days=30)
            query += " AND created_at >= ?"
            params.append(month_ago.timestamp())

        # Apply search query
        if search_query:
            query += " AND (filename LIKE ? OR url LIKE ?)"
            search_pattern = f"%{search_query}%"
            params.extend([search_pattern, search_pattern])

        # Apply category filter
        if category:
            query += " AND category = ?"
            params.append(category)

        # Order by creation date (newest first)
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
            return [self._row_to_entry(row) for row in rows]

    async def search(self, query: str, limit: int = 100) -> List[HistoryEntry]:
        """
        Full-text search across filename, URL, and tags.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching HistoryEntry objects
        """
        await self._ensure_initialized()
        search_pattern = f"%{query}%"
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT * FROM history
                WHERE filename LIKE ? OR url LIKE ? OR tags LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (search_pattern, search_pattern, search_pattern, limit))
            rows = await cursor.fetchall()
            return [self._row_to_entry(row) for row in rows]

    async def get_categories(self) -> List[str]:
        """Get list of all unique categories."""
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("SELECT DISTINCT category FROM history ORDER BY category")
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get overall statistics with optimized single query.
        
        Returns:
            Dictionary with statistics
        """
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as conn:
            # Single query to get all stats at once
            cursor = await conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN state = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN state = 'error' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN state = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
                    COALESCE(SUM(downloaded), 0) as total_downloaded,
                    COALESCE(SUM(total_size), 0) as total_size
                FROM history
            """)
            row = await cursor.fetchone()
            total, completed, failed, cancelled, total_downloaded, total_size = row
            
            return {
                "total_entries": total,
                "completed": completed,
                "failed": failed,
                "cancelled": cancelled,
                "total_downloaded_bytes": total_downloaded,
                "total_size_bytes": total_size,
                "success_rate": round(completed / total * 100, 2) if total > 0 else 0.0
            }

    async def delete_entry(self, entry_id: str) -> bool:
        """
        Delete a specific history entry.
        
        Args:
            entry_id: Entry ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("DELETE FROM history WHERE id = ?", (entry_id,))
            await conn.commit()
            deleted = cursor.rowcount > 0
            if deleted:
                log.debug("Deleted history entry: %s", entry_id)
            return deleted

    async def clear_all(self) -> int:
        """
        Clear all history entries.
        
        Returns:
            Number of entries deleted
        """
        await self._ensure_initialized()
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("DELETE FROM history")
            await conn.commit()
            count = cursor.rowcount
            log.info("Cleared %d history entries", count)
            return count

    async def clear_old_entries(self, days: int = 30) -> int:
        """
        Clear entries older than specified days.
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of entries deleted
        """
        await self._ensure_initialized()
        cutoff = datetime.now() - timedelta(days=days)
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                "DELETE FROM history WHERE created_at < ?",
                (cutoff.timestamp(),)
            )
            await conn.commit()
            count = cursor.rowcount
            log.info("Cleared %d history entries older than %d days", count, days)
            return count

    def export_to_csv(self, file_path: str, entries: Optional[List[HistoryEntry]] = None) -> None:
        """
        Export history to CSV file.
        
        Args:
            file_path: Output CSV file path
            entries: Entries to export (if None, exports all)
        """
        if entries is None:
            entries = self.get_all_entries()
        
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'ID', 'URL', 'Filename', 'Save Path', 'Total Size',
                'Downloaded', 'State', 'Category', 'Download Mode',
                'Speed', 'Peak Speed', 'ETA', 'Error', 'Retry Count',
                'Created At', 'Started At', 'Completed At', 'Tags', 'Referrer'
            ])
            
            for entry in entries:
                writer.writerow([
                    entry.id, entry.url, entry.filename, entry.save_path,
                    entry.total_size, entry.downloaded, entry.state,
                    entry.category, entry.download_mode, entry.speed,
                    entry.peak_speed, entry.eta, entry.error,
                    entry.retry_count, entry.created_at, entry.started_at,
                    entry.completed_at, json.dumps(entry.tags), entry.referrer
                ])
        
        log.info("Exported %d entries to CSV: %s", len(entries), file_path)

    def export_to_json(self, file_path: str, entries: Optional[List[HistoryEntry]] = None) -> None:
        """
        Export history to JSON file.
        
        Args:
            file_path: Output JSON file path
            entries: Entries to export (if None, exports all)
        """
        if entries is None:
            entries = self.get_all_entries()
        
        data = [asdict(entry) for entry in entries]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        log.info("Exported %d entries to JSON: %s", len(entries), file_path)

    def _row_to_entry(self, row: sqlite3.Row) -> HistoryEntry:
        """Convert database row to HistoryEntry."""
        return HistoryEntry(
            id=row['id'],
            url=row['url'],
            filename=row['filename'],
            save_path=row['save_path'],
            total_size=row['total_size'],
            downloaded=row['downloaded'],
            state=row['state'],
            category=row['category'],
            download_mode=row['download_mode'],
            speed=row['speed'],
            peak_speed=row['peak_speed'],
            eta=row['eta'],
            error=row['error'],
            retry_count=row['retry_count'],
            created_at=row['created_at'],
            started_at=row['started_at'],
            completed_at=row['completed_at'],
            tags=json.loads(row['tags']) if row['tags'] else [],
            referrer=row['referrer'],
            headers=json.loads(row['headers']) if row['headers'] else {}
        )

    def __del__(self):
        """Cleanup on deletion."""
        self.close()

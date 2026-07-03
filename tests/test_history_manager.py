"""
Tests for HistoryManager
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta

from core.history_manager import HistoryManager, HistoryEntry, HistoryFilter


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
        db_path = f.name
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def history_manager(temp_db):
    """Create a HistoryManager instance with temporary database."""
    manager = HistoryManager(db_path=temp_db)
    yield manager
    manager.close()


@pytest.fixture
def sample_entry():
    """Create a sample history entry."""
    return HistoryEntry(
        id="test-id-1",
        url="https://example.com/file.zip",
        filename="file.zip",
        save_path="/Downloads",
        total_size=1024 * 1024,  # 1MB
        downloaded=1024 * 1024,
        state="completed",
        category="Compressed",
        download_mode="direct",
        speed=1024 * 1024,  # 1MB/s
        peak_speed=2 * 1024 * 1024,  # 2MB/s
        eta=0,
        error="",
        retry_count=0,
        created_at=datetime.now().timestamp(),
        started_at=datetime.now().timestamp(),
        completed_at=datetime.now().timestamp(),
        tags=["test", "sample"],
        referrer="https://example.com",
        headers={"User-Agent": "test"}
    )


class TestHistoryManager:
    """Test cases for HistoryManager."""

    def test_add_entry(self, history_manager, sample_entry):
        """Test adding a history entry."""
        history_manager.add_entry(sample_entry)
        retrieved = history_manager.get_entry(sample_entry.id)
        assert retrieved is not None
        assert retrieved.id == sample_entry.id
        assert retrieved.filename == sample_entry.filename

    def test_update_entry(self, history_manager, sample_entry):
        """Test updating a history entry."""
        history_manager.add_entry(sample_entry)
        sample_entry.downloaded = 512 * 1024  # Update to 512KB
        history_manager.update_entry(sample_entry)
        retrieved = history_manager.get_entry(sample_entry.id)
        assert retrieved.downloaded == 512 * 1024

    def test_get_all_entries(self, history_manager, sample_entry):
        """Test getting all entries."""
        history_manager.add_entry(sample_entry)
        entries = history_manager.get_all_entries()
        assert len(entries) == 1
        assert entries[0].id == sample_entry.id

    def test_filter_by_completed(self, history_manager, sample_entry):
        """Test filtering by completed state."""
        history_manager.add_entry(sample_entry)
        entries = history_manager.get_all_entries(filter_type=HistoryFilter.COMPLETED)
        assert len(entries) == 1
        assert entries[0].is_completed

    def test_filter_by_failed(self, history_manager, sample_entry):
        """Test filtering by failed state."""
        sample_entry.state = "error"
        history_manager.add_entry(sample_entry)
        entries = history_manager.get_all_entries(filter_type=HistoryFilter.FAILED)
        assert len(entries) == 1
        assert entries[0].is_failed

    def test_search(self, history_manager, sample_entry):
        """Test search functionality."""
        history_manager.add_entry(sample_entry)
        results = history_manager.search("file.zip")
        assert len(results) == 1
        assert results[0].filename == "file.zip"

    def test_get_categories(self, history_manager, sample_entry):
        """Test getting unique categories."""
        history_manager.add_entry(sample_entry)
        categories = history_manager.get_categories()
        assert "Compressed" in categories

    def test_get_stats(self, history_manager, sample_entry):
        """Test getting statistics."""
        history_manager.add_entry(sample_entry)
        stats = history_manager.get_stats()
        assert stats["total_entries"] == 1
        assert stats["completed"] == 1
        assert stats["success_rate"] == 100.0

    def test_delete_entry(self, history_manager, sample_entry):
        """Test deleting an entry."""
        history_manager.add_entry(sample_entry)
        deleted = history_manager.delete_entry(sample_entry.id)
        assert deleted is True
        retrieved = history_manager.get_entry(sample_entry.id)
        assert retrieved is None

    def test_clear_all(self, history_manager, sample_entry):
        """Test clearing all entries."""
        history_manager.add_entry(sample_entry)
        count = history_manager.clear_all()
        assert count == 1
        entries = history_manager.get_all_entries()
        assert len(entries) == 0

    def test_clear_old_entries(self, history_manager, sample_entry):
        """Test clearing old entries."""
        # Create an old entry
        old_entry = sample_entry
        old_entry.id = "old-id"
        old_entry.created_at = (datetime.now() - timedelta(days=35)).timestamp()
        history_manager.add_entry(old_entry)
        
        # Create a recent entry
        recent_entry = sample_entry
        recent_entry.id = "recent-id"
        recent_entry.created_at = datetime.now().timestamp()
        history_manager.add_entry(recent_entry)
        
        # Clear entries older than 30 days
        count = history_manager.clear_old_entries(30)
        assert count == 1
        
        # Verify only recent entry remains
        entries = history_manager.get_all_entries()
        assert len(entries) == 1
        assert entries[0].id == "recent-id"

    def test_export_to_csv(self, history_manager, sample_entry, temp_db):
        """Test exporting to CSV."""
        history_manager.add_entry(sample_entry)
        csv_path = temp_db.replace('.db', '.csv')
        history_manager.export_to_csv(csv_path)
        assert os.path.exists(csv_path)
        os.unlink(csv_path)

    def test_export_to_json(self, history_manager, sample_entry, temp_db):
        """Test exporting to JSON."""
        history_manager.add_entry(sample_entry)
        json_path = temp_db.replace('.db', '.json')
        history_manager.export_to_json(json_path)
        assert os.path.exists(json_path)
        os.unlink(json_path)


class TestHistoryEntry:
    """Test cases for HistoryEntry."""

    def test_progress_calculation(self):
        """Test progress calculation."""
        entry = HistoryEntry(
            id="test",
            url="https://example.com/file.zip",
            filename="file.zip",
            save_path="/Downloads",
            total_size=1024 * 1024,
            downloaded=512 * 1024,
            state="downloading"
        )
        assert entry.progress == 50.0

    def test_duration_calculation(self):
        """Test duration calculation."""
        now = datetime.now()
        entry = HistoryEntry(
            id="test",
            url="https://example.com/file.zip",
            filename="file.zip",
            save_path="/Downloads",
            total_size=1024 * 1024,
            downloaded=1024 * 1024,
            state="completed",
            started_at=now.timestamp(),
            completed_at=(now + timedelta(seconds=10)).timestamp()
        )
        assert entry.duration == 10.0

    def test_size_str(self):
        """Test size string formatting."""
        entry = HistoryEntry(
            id="test",
            url="https://example.com/file.zip",
            filename="file.zip",
            save_path="/Downloads",
            total_size=1024 * 1024,
            downloaded=0,
            state="queued"
        )
        assert "MB" in entry.size_str

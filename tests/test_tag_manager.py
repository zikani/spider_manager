"""
Tests for TagManager
"""

import pytest
import tempfile
import os

from core.tag_manager import TagManager, Tag


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
        db_path = f.name
    yield db_path
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def tag_manager(temp_db):
    """Create a TagManager instance with temporary database."""
    manager = TagManager(db_path=temp_db)
    yield manager
    manager.close()


@pytest.fixture
def sample_tag():
    """Create a sample tag."""
    return Tag(
        name="test-tag",
        color="#ff0000",
        description="A test tag"
    )


class TestTagManager:
    """Test cases for TagManager."""

    def test_create_tag(self, tag_manager, sample_tag):
        """Test creating a tag."""
        result = tag_manager.create_tag(sample_tag)
        assert result is True
        retrieved = tag_manager.get_tag(sample_tag.name)
        assert retrieved is not None
        assert retrieved.name == sample_tag.name

    def test_create_duplicate_tag(self, tag_manager, sample_tag):
        """Test creating a duplicate tag."""
        tag_manager.create_tag(sample_tag)
        result = tag_manager.create_tag(sample_tag)
        assert result is False

    def test_update_tag(self, tag_manager, sample_tag):
        """Test updating a tag."""
        tag_manager.create_tag(sample_tag)
        sample_tag.color = "#00ff00"
        tag_manager.update_tag(sample_tag)
        retrieved = tag_manager.get_tag(sample_tag.name)
        assert retrieved.color == "#00ff00"

    def test_delete_tag(self, tag_manager, sample_tag):
        """Test deleting a tag."""
        tag_manager.create_tag(sample_tag)
        deleted = tag_manager.delete_tag(sample_tag.name)
        assert deleted is True
        retrieved = tag_manager.get_tag(sample_tag.name)
        assert retrieved is None

    def test_get_all_tags(self, tag_manager, sample_tag):
        """Test getting all tags."""
        tag_manager.create_tag(sample_tag)
        tags = tag_manager.get_all_tags()
        assert len(tags) == 1
        assert tags[0].name == sample_tag.name

    def test_search_tags(self, tag_manager, sample_tag):
        """Test searching tags."""
        tag_manager.create_tag(sample_tag)
        results = tag_manager.search_tags("test")
        assert len(results) == 1
        assert results[0].name == sample_tag.name

    def test_increment_usage(self, tag_manager, sample_tag):
        """Test incrementing tag usage."""
        tag_manager.create_tag(sample_tag)
        tag_manager.increment_usage(sample_tag.name)
        retrieved = tag_manager.get_tag(sample_tag.name)
        assert retrieved.usage_count == 1

    def test_decrement_usage(self, tag_manager, sample_tag):
        """Test decrementing tag usage."""
        tag_manager.create_tag(sample_tag)
        tag_manager.increment_usage(sample_tag.name)
        tag_manager.decrement_usage(sample_tag.name)
        retrieved = tag_manager.get_tag(sample_tag.name)
        assert retrieved.usage_count == 0

    def test_get_popular_tags(self, tag_manager, sample_tag):
        """Test getting popular tags."""
        tag_manager.create_tag(sample_tag)
        tag_manager.increment_usage(sample_tag.name)
        popular = tag_manager.get_popular_tags(limit=10)
        assert len(popular) == 1
        assert popular[0].name == sample_tag.name

    def test_get_statistics(self, tag_manager, sample_tag):
        """Test getting statistics."""
        tag_manager.create_tag(sample_tag)
        stats = tag_manager.get_statistics()
        assert stats["total_tags"] == 1
        assert stats["total_usage"] == 0

    def test_export_tags(self, tag_manager, sample_tag, temp_db):
        """Test exporting tags to JSON."""
        tag_manager.create_tag(sample_tag)
        json_path = temp_db.replace('.db', '.json')
        tag_manager.export_tags(json_path)
        assert os.path.exists(json_path)
        os.unlink(json_path)

    def test_import_tags(self, tag_manager, sample_tag, temp_db):
        """Test importing tags from JSON."""
        tag_manager.create_tag(sample_tag)
        json_path = temp_db.replace('.db', '.json')
        tag_manager.export_tags(json_path)
        
        # Create new manager and import
        new_manager = TagManager(db_path=temp_db + "_new")
        count = new_manager.import_tags(json_path, overwrite=False)
        assert count == 1
        new_manager.close()
        os.unlink(json_path)


class TestTag:
    """Test cases for Tag."""

    def test_tag_creation(self):
        """Test tag creation."""
        tag = Tag(name="test", color="#ff0000")
        assert tag.name == "test"
        assert tag.color == "#ff0000"
        assert tag.usage_count == 0

    def test_tag_defaults(self):
        """Test tag default values."""
        tag = Tag(name="test")
        assert tag.color == "#3498db"  # Default blue
        assert tag.description == ""
        assert tag.usage_count == 0

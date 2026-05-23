"""
File Categorizer - Automatically categorize files by type for organized downloads.
"""
 
import os
from pathlib import Path
from typing import Optional
from utils.logger import get_logger
 
log = get_logger(__name__)
 
 
class FileCategory:
    """File category constants."""
    PROGRAMS = "Programs"
    DOCUMENTS = "Documents"
    COMPRESSED = "Compressed"
    PICTURES = "Pictures"
    VIDEO = "Video"
    AUDIO = "Audio"
    OTHER = "Other"
 
 
class FileCategorizer:
    """Categorizes files based on extension and MIME type."""
 
    CATEGORY_MAP = {
        FileCategory.PROGRAMS: [
            '.exe', '.msi', '.app', '.dmg', '.deb', '.rpm', '.apk', '.ipa',
            '.jar', '.war', '.ear', '.sh', '.bat', '.cmd', '.ps1', '.vbs',
            '.dll', '.so', '.dylib', '.lib', '.a', '.o', '.bin', '.iso',
            '.img', '.vhd', '.vmdk', '.ova', '.ovf', '.qcow2', '.vdi'
        ],
        FileCategory.DOCUMENTS: [
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.odt', '.ods', '.odp', '.rtf', '.txt', '.csv', '.tex',
            '.epub', '.mobi', '.azw3', '.pages', '.numbers', '.key',
            '.md', '.markdown', '.json', '.xml', '.yaml', '.yml', '.ini'
        ],
        FileCategory.COMPRESSED: [
            '.zip', '.rar', '.7z', '.tar', '.gz', '.gzip', '.bz2', '.xz',
            '.lzma', '.cab', '.ace', '.arj', '.lzh', '.z', '.tgz', '.tbz',
            '.txz', '.tlz', '.apk', '.ipa', '.deb', '.rpm', '.dmg', '.pkg'
        ],
        FileCategory.PICTURES: [
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp',
            '.svg', '.ico', '.psd', '.ai', '.eps', '.raw', '.cr2', '.nef',
            '.orf', '.sr2', '.dng', '.heic', '.heif', '.avif', '.jxl'
        ],
        FileCategory.VIDEO: [
            '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v',
            '.3gp', '.3g2', '.mpg', '.mpeg', '.mpe', '.m2v', '.ts', '.mts',
            '.m2ts', '.vob', '.ogv', '.drc', '.rm', '.rmvb', '.asf', '.amv',
            '.mxf', '.roq', '.nsv', '.f4v', '.f4p', '.f4a', '.f4b'
        ],
        FileCategory.AUDIO: [
            '.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.wma', '.opus',
            '.aiff', '.au', '.ra', '.mka', '.ac3', '.dts', '.ape', '.wv',
            '.tta', '.alac', '.amr', '.3ga', '.mid', '.midi', '.gsm'
        ]
    }
 
    @classmethod
    def categorize_by_extension(cls, filename: str) -> str:
        """Categorize file based on its extension."""
        if not filename:
            return FileCategory.OTHER
 
        ext = Path(filename).suffix.lower()
 
        for category, extensions in cls.CATEGORY_MAP.items():
            if ext in extensions:
                return category
 
        return FileCategory.OTHER
 
    @classmethod
    def categorize_by_mime(cls, mime_type: Optional[str]) -> str:
        """Categorize file based on MIME type."""
        if not mime_type:
            return FileCategory.OTHER
 
        mime_lower = mime_type.lower()
 
        if mime_type.startswith('application/'):
            if 'zip' in mime_lower or 'rar' in mime_lower or 'tar' in mime_lower or 'compressed' in mime_lower:
                return FileCategory.COMPRESSED
            if 'pdf' in mime_lower:
                return FileCategory.DOCUMENTS
            if 'executable' in mime_lower or 'x-msdownload' in mime_lower or 'x-msi' in mime_lower:
                return FileCategory.PROGRAMS
            return FileCategory.OTHER
 
        if mime_type.startswith('image/'):
            return FileCategory.PICTURES
 
        if mime_type.startswith('video/'):
            return FileCategory.VIDEO
 
        if mime_type.startswith('audio/'):
            return FileCategory.AUDIO
 
        if mime_type.startswith('text/'):
            return FileCategory.DOCUMENTS
 
        return FileCategory.OTHER
 
    @classmethod
    def categorize(cls, filename: str, mime_type: Optional[str] = None) -> str:
        """Categorize file using both extension and MIME type."""
        if mime_type:
            category = cls.categorize_by_mime(mime_type)
            if category != FileCategory.OTHER:
                return category
 
        return cls.categorize_by_extension(filename)
 
 
class DownloadPathManager:
    """Manages download paths with automatic categorization."""
 
    def __init__(self, base_download_dir: str):
        self.base_dir = Path(base_download_dir)
        self.temp_dir = self.base_dir / "Temp"
        self._ensure_directories()
 
    def _ensure_directories(self):
        """Ensure all category directories exist."""
        categories = [
            FileCategory.PROGRAMS,
            FileCategory.DOCUMENTS,
            FileCategory.COMPRESSED,
            FileCategory.PICTURES,
            FileCategory.VIDEO,
            FileCategory.AUDIO,
            FileCategory.OTHER,
            "Temp"
        ]
 
        for category in categories:
            category_dir = self.base_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)
            log.debug(f"Ensured directory exists: {category_dir}")
 
    def get_category_path(self, category: str) -> Path:
        """Get the full path for a category directory."""
        return self.base_dir / category
 
    def get_temp_path(self) -> Path:
        """Get the temp directory path."""
        return self.temp_dir
 
    def get_save_path(self, filename: str, mime_type: Optional[str] = None, category: Optional[str] = None) -> str:
        """
        Get the appropriate save path for a file.
 
        Args:
            filename: The filename to save
            mime_type: Optional MIME type for better categorization
            category: Optional explicit category override
 
        Returns:
            Full path where the file should be saved
        """
        if category:
            target_dir = self.get_category_path(category)
        else:
            category = FileCategorizer.categorize(filename, mime_type)
            target_dir = self.get_category_path(category)
 
        return str(target_dir / filename)
 
    def get_temp_file_path(self, filename: str) -> str:
        """Get a temp file path for partial downloads."""
        return str(self.temp_dir / f"{filename}.tmp")
 
    def cleanup_temp_files(self, max_age_hours: int = 24):
        """
        Clean up temporary files older than specified hours.
 
        Args:
            max_age_hours: Maximum age in hours for temp files to keep
        """
        import time
 
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
 
        cleaned_count = 0
        try:
            for file_path in self.temp_dir.glob("*.tmp"):
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        file_path.unlink()
                        cleaned_count += 1
                        log.info(f"Cleaned up temp file: {file_path}")
 
            if cleaned_count > 0:
                log.info(f"Cleaned up {cleaned_count} temporary files")
        except Exception as e:
            log.error(f"Error cleaning up temp files: {e}")
 
        return cleaned_count
 
    def move_from_temp(self, temp_path: str, final_path: str) -> bool:
        """
        Move a file from temp directory to final location.
 
        Args:
            temp_path: Current temporary file path
            final_path: Final destination path
 
        Returns:
            True if successful, False otherwise
        """
        try:
            temp_file = Path(temp_path)
            final_file = Path(final_path)
 
            final_file.parent.mkdir(parents=True, exist_ok=True)
 
            temp_file.replace(final_file)
            log.info(f"Moved file from temp to final: {temp_path} -> {final_path}")
            return True
        except Exception as e:
            log.error(f"Error moving file from temp: {e}")
            return False
 
 
def get_categorized_save_path(filename: str, base_dir: Optional[str] = None, mime_type: Optional[str] = None) -> str:
    """
    Convenience function to get categorized save path.
 
    Args:
        filename: The filename to save
        base_dir: Base download directory (uses default if not provided)
        mime_type: Optional MIME type for better categorization
 
    Returns:
        Full path where the file should be saved
    """
    if not base_dir:
        from config.settings import get_download_directory
        base_dir = get_download_directory()
 
    manager = DownloadPathManager(base_dir)
    return manager.get_save_path(filename, mime_type)
 


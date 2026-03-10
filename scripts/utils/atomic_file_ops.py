"""Atomic file operations with integrity verification.

Provides robust file write mechanisms that prevent data loss through:
- Atomic writes (write-to-temp + rename)
- SHA256 checksums for integrity verification
- Automatic backups before overwrite
- Thread-safe operations
"""

import os
import hashlib
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional


def calculate_checksum(content: str) -> str:
    """Calculate SHA256 checksum of string content.
    
    Args:
        content: String content to checksum
        
    Returns:
        Hexadecimal SHA256 checksum
    """
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def calculate_file_checksum(filepath: str) -> str:
    """Calculate SHA256 checksum of file content.
    
    Args:
        filepath: Path to file
        
    Returns:
        Hexadecimal SHA256 checksum
        
    Raises:
        FileNotFoundError: If file does not exist
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    
    sha256_hash = hashlib.sha256()
    with open(filepath, 'rb') as f:
        # Read file in chunks for large files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    
    return sha256_hash.hexdigest()


def verified_backup(filepath: str) -> Optional[str]:
    """Create a timestamped backup with integrity verification.
    
    Args:
        filepath: Path to file to backup
        
    Returns:
        Path to backup file, or None if source file doesn't exist
    """
    if not os.path.exists(filepath):
        return None
    
    # Generate timestamped backup filename
    path_obj = Path(filepath)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{path_obj.stem}_backup_{timestamp}{path_obj.suffix}"
    backup_path = path_obj.parent / backup_name
    
    # Copy file to backup location
    shutil.copy2(filepath, backup_path)
    
    # Verify backup integrity
    original_checksum = calculate_file_checksum(filepath)
    backup_checksum = calculate_file_checksum(str(backup_path))
    
    if original_checksum != backup_checksum:
        os.remove(backup_path)
        raise IOError(f"Backup verification failed for {filepath}")
    
    return str(backup_path)


def atomic_write(filepath: str, content: str, backup: bool = False) -> Tuple[str, str]:
    """Atomically write content to file using write-to-temp + rename pattern.
    
    This prevents partial writes and corruption by:
    1. Writing to a temporary file in the same directory
    2. Using os.replace() for atomic rename (POSIX guarantees atomicity)
    3. Creating backups before overwrite if requested
    
    Args:
        filepath: Destination file path
        content: String content to write
        backup: If True, create backup before overwrite
        
    Returns:
        Tuple of (filepath, checksum)
    """
    filepath = str(filepath)  # Convert Path objects to string
    file_path = Path(filepath)
    
    # Create parent directories if needed
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create backup if file exists and backup requested
    if backup and os.path.exists(filepath):
        verified_backup(filepath)
    
    # Write to temporary file in same directory (required for atomic rename)
    temp_fd, temp_path = tempfile.mkstemp(
        dir=file_path.parent,
        prefix=f".{file_path.name}.",
        suffix=".tmp"
    )
    
    try:
        # Write content to temp file
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())  # Ensure data is written to disk
        
        # Calculate checksum
        checksum = calculate_checksum(content)
        
        # Atomic rename (os.replace is atomic on POSIX systems)
        os.replace(temp_path, filepath)
        
        return filepath, checksum
        
    except Exception as e:
        # Clean up temp file on error
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise IOError(f"Atomic write failed for {filepath}: {e}")


def integrity_check(filepath: str, expected_checksum: Optional[str] = None) -> bool:
    """Verify file integrity against expected checksum.
    
    Args:
        filepath: Path to file to check
        expected_checksum: Optional expected SHA256 checksum
        
    Returns:
        True if file matches expected checksum or no checksum provided,
        False if checksums don't match
    """
    if expected_checksum is None:
        return True
    
    if not os.path.exists(filepath):
        return False
    
    actual_checksum = calculate_file_checksum(filepath)
    return actual_checksum == expected_checksum


def read_with_verification(filepath: str, expected_checksum: Optional[str] = None) -> Tuple[str, str]:
    """Read file content and verify integrity.
    
    Args:
        filepath: Path to file to read
        expected_checksum: Optional expected SHA256 checksum
        
    Returns:
        Tuple of (content, checksum)
        
    Raises:
        IOError: If file integrity check fails
        FileNotFoundError: If file does not exist
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    
    # Read file content
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Calculate checksum
    checksum = calculate_checksum(content)
    
    # Verify against expected checksum if provided
    if expected_checksum is not None and checksum != expected_checksum:
        raise IOError(f"File integrity check failed for {filepath}: "
                     f"expected {expected_checksum}, got {checksum}")
    
    return content, checksum


class AtomicFile:
    """Context manager for atomic file writes.
    
    Usage:
        with AtomicFile('/path/to/file.txt') as f:
            f.write('content')
    """
    
    def __init__(self, filepath: str, backup: bool = False):
        """Initialize atomic file writer.
        
        Args:
            filepath: Destination file path
            backup: If True, create backup before overwrite
        """
        self.filepath = filepath
        self.backup = backup
        self.content = ""
    
    def write(self, content: str) -> None:
        """Buffer content to write.
        
        Args:
            content: String content to write
        """
        self.content = content
    
    def __enter__(self):
        """Enter context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and perform atomic write.
        
        Only writes if no exception occurred in the context.
        """
        if exc_type is None:
            # No exception - perform atomic write
            atomic_write(self.filepath, self.content, backup=self.backup)
        
        # Don't suppress exceptions
        return False

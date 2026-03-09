"""Comprehensive test suite for atomic_file_ops.py

Tests all 7 functions/classes:
- calculate_checksum()
- calculate_file_checksum()
- verified_backup()
- atomic_write()
- integrity_check()
- read_with_verification()
- AtomicFile context manager
"""

import pytest
import os
import time
import hashlib
from pathlib import Path
from threading import Thread
import sys

# Add root directory to path for imports
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from scripts.utils.atomic_file_ops import (
    calculate_checksum,
    calculate_file_checksum,
    verified_backup,
    atomic_write,
    integrity_check,
    read_with_verification,
    AtomicFile
)


# Test 1: Basic atomic write creates file
def test_atomic_write_creates_file(tmp_path):
    """Test that atomic_write creates a new file successfully."""
    test_file = tmp_path / "test.txt"
    content = "Hello, world!"
    
    path, checksum = atomic_write(str(test_file), content)
    
    assert os.path.exists(test_file)
    assert path == str(test_file)
    assert checksum is not None


# Test 2: Atomic write content is correct
def test_atomic_write_content_correct(tmp_path):
    """Test that written content matches input."""
    test_file = tmp_path / "content_test.txt"
    content = "Test content with special chars: ñ, €, 中文"
    
    atomic_write(str(test_file), content)
    
    with open(test_file, 'r', encoding='utf-8') as f:
        written_content = f.read()
    
    assert written_content == content


# Test 3: Atomic write replaces existing file
def test_atomic_write_replaces_existing(tmp_path):
    """Test that atomic_write correctly overwrites existing files."""
    test_file = tmp_path / "replace_test.txt"
    
    # Write initial content
    atomic_write(str(test_file), "Original content")
    
    # Overwrite with new content
    new_content = "Replaced content"
    atomic_write(str(test_file), new_content)
    
    with open(test_file, 'r') as f:
        actual_content = f.read()
    
    assert actual_content == new_content


# Test 4: No partial files remain visible
def test_atomic_write_no_partial_files_visible(tmp_path):
    """Test that temporary files are cleaned up."""
    test_file = tmp_path / "no_partial.txt"
    content = "Test content"
    
    atomic_write(str(test_file), content)
    
    # Check no .tmp files remain
    temp_files = list(tmp_path.glob("*.tmp"))
    assert len(temp_files) == 0
    
    # Check no hidden temp files remain
    hidden_temp_files = list(tmp_path.glob(".*.tmp"))
    assert len(hidden_temp_files) == 0


# Test 5: Checksum matches after write
def test_checksum_matches_after_write(tmp_path):
    """Test that returned checksum matches file content."""
    test_file = tmp_path / "checksum_test.txt"
    content = "Content for checksum verification"
    
    path, checksum = atomic_write(str(test_file), content)
    
    # Calculate expected checksum
    expected_checksum = calculate_checksum(content)
    
    assert checksum == expected_checksum


# Test 6: Checksum fails on tampered file
def test_checksum_fails_on_tampered_file(tmp_path):
    """Test that integrity_check detects file tampering."""
    test_file = tmp_path / "tamper_test.txt"
    content = "Original content"
    
    path, original_checksum = atomic_write(str(test_file), content)
    
    # Tamper with the file
    with open(test_file, 'w') as f:
        f.write("Tampered content")
    
    # Integrity check should fail
    assert not integrity_check(str(test_file), original_checksum)


# Test 7: Backup created on write
def test_backup_created_on_write(tmp_path):
    """Test that backup is created when requested."""
    test_file = tmp_path / "backup_test.txt"
    
    # Create initial file
    atomic_write(str(test_file), "Initial content")
    
    # Overwrite with backup
    atomic_write(str(test_file), "New content", backup=True)
    
    # Check backup file exists
    backup_files = list(tmp_path.glob("backup_test_backup_*.txt"))
    assert len(backup_files) == 1


# Test 8: Backup content matches original
def test_backup_content_matches_original(tmp_path):
    """Test that backup preserves original content."""
    test_file = tmp_path / "backup_content_test.txt"
    original_content = "Original content to backup"
    
    # Create initial file
    atomic_write(str(test_file), original_content)
    
    # Overwrite with backup
    atomic_write(str(test_file), "New content", backup=True)
    
    # Read backup file
    backup_files = list(tmp_path.glob("backup_content_test_backup_*.txt"))
    assert len(backup_files) == 1
    
    with open(backup_files[0], 'r') as f:
        backup_content = f.read()
    
    assert backup_content == original_content


# Test 9: Read with verification success
def test_read_with_verification_success(tmp_path):
    """Test that read_with_verification returns correct content and checksum."""
    test_file = tmp_path / "read_verify_test.txt"
    content = "Content for read verification"
    
    path, original_checksum = atomic_write(str(test_file), content)
    
    # Read with verification
    read_content, read_checksum = read_with_verification(str(test_file))
    
    assert read_content == content
    assert read_checksum == original_checksum


# Test 10: Read with verification fails on corruption
def test_read_with_verification_fails_on_corruption(tmp_path):
    """Test that read_with_verification detects corrupted files."""
    test_file = tmp_path / "corrupt_read_test.txt"
    content = "Original content"
    
    path, original_checksum = atomic_write(str(test_file), content)
    
    # Tamper with file
    with open(test_file, 'w') as f:
        f.write("Corrupted content")
    
    # Should raise IOError
    with pytest.raises(IOError, match="File integrity check failed"):
        read_with_verification(str(test_file), expected_checksum=original_checksum)


# Test 11: Concurrent writes are safe
def test_concurrent_writes_are_safe(tmp_path):
    """Test that concurrent writes don't corrupt files (atomic rename)."""
    test_file = tmp_path / "concurrent_test.txt"
    results = []
    
    def write_content(content):
        try:
            path, checksum = atomic_write(str(test_file), content)
            results.append((content, checksum))
        except Exception as e:
            results.append(e)
    
    # Launch concurrent writes
    threads = []
    for i in range(5):
        content = f"Content {i}"
        thread = Thread(target=write_content, args=(content,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads
    for thread in threads:
        thread.join()
    
    # File should exist and be valid
    assert os.path.exists(test_file)
    
    # Final content should match one of the writes
    with open(test_file, 'r') as f:
        final_content = f.read()
    
    assert final_content in [f"Content {i}" for i in range(5)]


# Test 12: Large file write (1MB)
def test_large_file_write_1mb(tmp_path):
    """Test that atomic_write handles large files correctly."""
    test_file = tmp_path / "large_file_test.txt"
    
    # Create 1MB of content (1024 * 1024 characters)
    large_content = "A" * (1024 * 1024)
    
    path, checksum = atomic_write(str(test_file), large_content)
    
    assert os.path.exists(test_file)
    assert os.path.getsize(test_file) == 1024 * 1024
    
    # Verify content integrity
    assert integrity_check(str(test_file), checksum)


# Test 13: Write to nested directory
def test_write_to_nested_directory(tmp_path):
    """Test that atomic_write creates nested directories automatically."""
    nested_file = tmp_path / "level1" / "level2" / "level3" / "nested.txt"
    content = "Nested content"
    
    path, checksum = atomic_write(str(nested_file), content)
    
    assert os.path.exists(nested_file)
    
    with open(nested_file, 'r') as f:
        actual_content = f.read()
    
    assert actual_content == content


# Test 14: Empty content write
def test_empty_content_write(tmp_path):
    """Test that atomic_write handles empty strings correctly."""
    test_file = tmp_path / "empty_test.txt"
    content = ""
    
    path, checksum = atomic_write(str(test_file), content)
    
    assert os.path.exists(test_file)
    assert os.path.getsize(test_file) == 0
    
    with open(test_file, 'r') as f:
        actual_content = f.read()
    
    assert actual_content == ""


# Test 15: Unicode content handling
def test_unicode_content_handling(tmp_path):
    """Test that atomic_write correctly handles Unicode characters."""
    test_file = tmp_path / "unicode_test.txt"
    content = "English, Español, 中文, العربية, עברית, 日本語, 한국어, Ελληνικά 🚀✨"
    
    path, checksum = atomic_write(str(test_file), content)
    
    assert os.path.exists(test_file)
    
    with open(test_file, 'r', encoding='utf-8') as f:
        actual_content = f.read()
    
    assert actual_content == content


# Test 16: AtomicFile context manager
def test_atomic_file_context_manager(tmp_path):
    """Test that AtomicFile context manager works correctly."""
    test_file = tmp_path / "context_test.txt"
    content = "Content via context manager"
    
    with AtomicFile(str(test_file)) as f:
        f.write(content)
    
    assert os.path.exists(test_file)
    
    with open(test_file, 'r') as f:
        actual_content = f.read()
    
    assert actual_content == content


# Test 17: AtomicFile context manager with backup
def test_atomic_file_context_manager_with_backup(tmp_path):
    """Test that AtomicFile context manager creates backups."""
    test_file = tmp_path / "context_backup_test.txt"
    
    # Create initial file
    atomic_write(str(test_file), "Original content")
    
    # Use context manager with backup
    with AtomicFile(str(test_file), backup=True) as f:
        f.write("New content via context manager")
    
    # Check backup exists
    backup_files = list(tmp_path.glob("context_backup_test_backup_*.txt"))
    assert len(backup_files) == 1


# Test 18: Calculate file checksum for non-existent file
def test_calculate_file_checksum_nonexistent(tmp_path):
    """Test that calculate_file_checksum raises FileNotFoundError."""
    nonexistent_file = tmp_path / "does_not_exist.txt"
    
    with pytest.raises(FileNotFoundError):
        calculate_file_checksum(str(nonexistent_file))


# Test 19: Verified backup returns None for non-existent file
def test_verified_backup_nonexistent_file(tmp_path):
    """Test that verified_backup returns None for non-existent files."""
    nonexistent_file = tmp_path / "does_not_exist.txt"
    
    result = verified_backup(str(nonexistent_file))
    
    assert result is None


# Test 20: Integrity check with no expected checksum
def test_integrity_check_no_expected_checksum(tmp_path):
    """Test that integrity_check returns True when no expected checksum provided."""
    test_file = tmp_path / "no_expected_test.txt"
    
    atomic_write(str(test_file), "Some content")
    
    # Should return True when no expected checksum
    assert integrity_check(str(test_file)) is True


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

"""File Integrity Checker Utility

Provides batch integrity checking and manifest generation for multiple files.
Useful for verifying backups, detecting file corruption, and monitoring
file changes across directories.

Usage:
    from scripts.utils.file_integrity_checker import FileIntegrityChecker

    checker = FileIntegrityChecker()

    # Compute checksum for single file
    checksum = checker.compute_checksum('path/to/file.txt')

    # Verify file integrity
    if checker.verify_checksum('path/to/file.txt', expected_checksum):
        print("File is intact")

    # Create manifest for directory
    manifest = checker.create_manifest('data/')

    # Verify directory against manifest
    failed_files = checker.verify_manifest('data/', manifest)
    if failed_files:
        print(f"Corrupted files: {failed_files}")
"""

import os
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional


class FileIntegrityChecker:
    """
    Utility class for computing and verifying file checksums.

    Supports single-file verification and batch manifest operations
    for entire directories.
    """

    def __init__(self, algorithm: str = 'sha256'):
        """
        Initialize integrity checker.

        Args:
            algorithm: Hash algorithm to use (sha256, md5, sha1, sha512)
        """
        self.algorithm = algorithm
        self._validate_algorithm()

    def _validate_algorithm(self):
        """Validate that the hash algorithm is supported."""
        try:
            hashlib.new(self.algorithm)
        except ValueError:
            raise ValueError(
                f"Unsupported hash algorithm: {self.algorithm}. "
                f"Supported: sha256, sha1, md5, sha512, etc."
            )

    def compute_checksum(self, filepath: str, algorithm: Optional[str] = None) -> str:
        """
        Compute checksum of a file.

        Args:
            filepath: Path to file
            algorithm: Optional override for hash algorithm

        Returns:
            Hexadecimal checksum string

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If file cannot be read

        Example:
            checker = FileIntegrityChecker()
            checksum = checker.compute_checksum('soul.md')
            print(f"SHA-256: {checksum}")
        """
        algo = algorithm or self.algorithm
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        if not filepath.is_file():
            raise IOError(f"Not a file: {filepath}")

        hasher = hashlib.new(algo)

        try:
            with open(filepath, 'rb') as f:
                # Read in chunks for memory efficiency
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
        except IOError as e:
            raise IOError(f"Failed to read {filepath}: {e}") from e

        return hasher.hexdigest()

    def verify_checksum(
        self,
        filepath: str,
        expected_checksum: str,
        algorithm: Optional[str] = None
    ) -> bool:
        """
        Verify file matches expected checksum.

        Args:
            filepath: Path to file
            expected_checksum: Expected checksum value
            algorithm: Optional override for hash algorithm

        Returns:
            True if checksum matches, False otherwise

        Raises:
            FileNotFoundError: If file doesn't exist

        Example:
            if checker.verify_checksum('soul.md', stored_checksum):
                print("File is intact")
            else:
                print("WARNING: File has been modified or corrupted")
        """
        try:
            actual_checksum = self.compute_checksum(filepath, algorithm)
            return actual_checksum.lower() == expected_checksum.lower()
        except (FileNotFoundError, IOError):
            return False

    def create_manifest(
        self,
        directory: str,
        recursive: bool = True,
        exclude_patterns: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Create checksum manifest for all files in directory.

        Args:
            directory: Directory path to scan
            recursive: Include subdirectories (default: True)
            exclude_patterns: List of filename patterns to exclude (e.g., ['*.tmp', '.git'])

        Returns:
            Dictionary mapping relative file paths to checksums
            {"file1.txt": "abc123...", "subdir/file2.txt": "def456..."}

        Raises:
            NotADirectoryError: If path is not a directory

        Example:
            checker = FileIntegrityChecker()
            manifest = checker.create_manifest('data/', recursive=True)
            print(f"Created manifest for {len(manifest)} files")

            # Save manifest
            with open('manifest.json', 'w') as f:
                json.dump(manifest, f, indent=2)
        """
        directory = Path(directory)

        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        if not directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory}")

        exclude_patterns = exclude_patterns or []
        manifest = {}

        # Get file iterator based on recursive flag
        if recursive:
            files = directory.rglob('*')
        else:
            files = directory.glob('*')

        for filepath in files:
            # Skip directories
            if not filepath.is_file():
                continue

            # Skip excluded patterns
            if any(filepath.match(pattern) for pattern in exclude_patterns):
                continue

            # Compute relative path from base directory
            relative_path = filepath.relative_to(directory)

            try:
                checksum = self.compute_checksum(str(filepath))
                manifest[str(relative_path)] = checksum
            except IOError as e:
                # Log error but continue processing other files
                print(f"Warning: Could not process {relative_path}: {e}")
                continue

        return manifest

    def verify_manifest(
        self,
        directory: str,
        manifest: Dict[str, str],
        algorithm: Optional[str] = None
    ) -> List[str]:
        """
        Verify directory contents against manifest.

        Args:
            directory: Directory path to verify
            manifest: Dictionary mapping file paths to expected checksums
            algorithm: Optional override for hash algorithm

        Returns:
            List of files that failed verification (empty list if all pass)
            Includes: corrupted files, missing files, extra files

        Example:
            # Load saved manifest
            with open('manifest.json', 'r') as f:
                manifest = json.load(f)

            # Verify directory
            failed = checker.verify_manifest('data/', manifest)
            if failed:
                print(f"Integrity issues: {failed}")
            else:
                print("All files verified successfully")
        """
        directory = Path(directory)
        failed_files = []

        # Check each file in manifest
        for relative_path, expected_checksum in manifest.items():
            filepath = directory / relative_path

            if not filepath.exists():
                failed_files.append(f"MISSING: {relative_path}")
                continue

            if not self.verify_checksum(str(filepath), expected_checksum, algorithm):
                failed_files.append(f"CORRUPTED: {relative_path}")

        # Check for extra files not in manifest
        if directory.exists():
            actual_files = {
                str(f.relative_to(directory))
                for f in directory.rglob('*')
                if f.is_file()
            }
            manifest_files = set(manifest.keys())
            extra_files = actual_files - manifest_files

            for extra_file in extra_files:
                failed_files.append(f"EXTRA: {extra_file}")

        return failed_files

    def save_manifest(
        self,
        manifest: Dict[str, str],
        output_path: str,
        include_metadata: bool = True
    ) -> None:
        """
        Save manifest to JSON file.

        Args:
            manifest: Manifest dictionary to save
            output_path: Path to output JSON file
            include_metadata: Include metadata (algorithm, timestamp)

        Example:
            manifest = checker.create_manifest('data/')
            checker.save_manifest(manifest, 'data_manifest.json')
        """
        output = {
            "files": manifest
        }

        if include_metadata:
            from datetime import datetime
            output["metadata"] = {
                "algorithm": self.algorithm,
                "created_at": datetime.utcnow().isoformat() + 'Z',
                "file_count": len(manifest)
            }

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)

    def load_manifest(self, manifest_path: str) -> Dict[str, str]:
        """
        Load manifest from JSON file.

        Args:
            manifest_path: Path to manifest JSON file

        Returns:
            Manifest dictionary

        Example:
            manifest = checker.load_manifest('data_manifest.json')
            failed = checker.verify_manifest('data/', manifest)
        """
        with open(manifest_path, 'r') as f:
            data = json.load(f)

        # Handle both old format (direct dict) and new format (with metadata)
        if "files" in data:
            return data["files"]
        else:
            return data


if __name__ == '__main__':
    # Self-test
    import tempfile
    import sys

    print("Testing FileIntegrityChecker...")

    checker = FileIntegrityChecker()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Test 1: Single file checksum
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("Test content")

        checksum = checker.compute_checksum(str(test_file))
        print(f"✓ Computed checksum: {checksum[:16]}...")

        # Test 2: Verify checksum
        if checker.verify_checksum(str(test_file), checksum):
            print("✓ Checksum verification passed")
        else:
            print("✗ Checksum verification failed")
            sys.exit(1)

        # Test 3: Create manifest
        subdir = Path(tmpdir) / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("File 2 content")

        manifest = checker.create_manifest(tmpdir)
        print(f"✓ Created manifest with {len(manifest)} files")

        # Test 4: Verify manifest
        failed = checker.verify_manifest(tmpdir, manifest)
        if not failed:
            print("✓ Manifest verification passed")
        else:
            print(f"✗ Manifest verification failed: {failed}")
            sys.exit(1)

        # Test 5: Detect corruption
        test_file.write_text("Tampered content")
        failed = checker.verify_manifest(tmpdir, manifest)
        if failed:
            print(f"✓ Detected corruption: {failed[0]}")
        else:
            print("✗ Failed to detect corruption")
            sys.exit(1)

    print("\n✓ All tests passed!")

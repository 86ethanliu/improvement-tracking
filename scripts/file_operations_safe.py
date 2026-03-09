"""Safe File Operations Module

Provides defensive file I/O operations with validation, atomic writes,
backup creation, and checksum verification. Integrates with error_resilience
module for robust error handling.

Usage:
    from file_operations_safe import SafeFileReader, SafeFileWriter, SafeJsonHandler
    
    # Safe file reading
    reader = SafeFileReader()
    result = reader.read_file('data.txt')
    if result.success:
        print(result.content)
    
    # Atomic file writing with backup
    writer = SafeFileWriter()
    result = writer.write_file('output.txt', 'Hello World', create_backup=True)
    
    # JSON operations with schema validation
    handler = SafeJsonHandler()
    data = handler.load_json('config.json')
"""

import os
import json
import shutil
import hashlib
import tempfile
from pathlib import Path
from typing import Optional, Any, Dict, List
from dataclasses import dataclass
from datetime import datetime
import logging

# Import from Module 1
from error_resilience import (
    ErrorCategory,
    PreflightValidator,
    RetryStrategy,
    PreflightError,
    TransientError,
    error_tracker
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FileOperationResult:
    """Result of a file operation with status and error details."""
    success: bool
    content: Optional[Any] = None
    error: Optional[str] = None
    error_category: Optional[ErrorCategory] = None
    metadata: Optional[Dict[str, Any]] = None


class SafeFileReader:
    """Safe file reading operations with pre-flight validation.
    
    Validates file existence, readability, and non-empty content before
    attempting to read. Returns typed results with detailed error information.
    
    Attributes:
        retry_strategy: RetryStrategy instance for transient error handling
        validator: PreflightValidator instance for pre-operation checks
    """
    
    def __init__(self, max_retries: int = 3):
        """Initialize safe file reader.
        
        Args:
            max_retries: Maximum retry attempts for transient errors
        """
        self.retry_strategy = RetryStrategy(max_attempts=max_retries)
        self.validator = PreflightValidator()
        logger.info(f"SafeFileReader initialized with {max_retries} max retries")
    
    def read_file(self, path: str, encoding: str = 'utf-8') -> FileOperationResult:
        """Read file with pre-flight validation and error handling.
        
        Args:
            path: File path to read
            encoding: Character encoding (default: utf-8)
        
        Returns:
            FileOperationResult with content or error details
        """
        try:
            # Pre-flight validation
            self.validator.check_file_readable(path)
            
            # Read file
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            
            metadata = {
                'path': path,
                'size_bytes': os.path.getsize(path),
                'encoding': encoding,
                'read_at': datetime.now().isoformat()
            }
            
            logger.info(f"Successfully read file: {path} ({metadata['size_bytes']} bytes)")
            return FileOperationResult(
                success=True,
                content=content,
                metadata=metadata
            )
            
        except PreflightError as e:
            error_msg = f"Pre-flight validation failed: {e}"
            logger.error(error_msg)
            error_tracker.log_error(e, ErrorCategory.PERMANENT, {'path': path})
            return FileOperationResult(
                success=False,
                error=error_msg,
                error_category=ErrorCategory.PERMANENT
            )
            
        except PermissionError as e:
            error_msg = f"Permission denied: {e}"
            logger.error(error_msg)
            error_tracker.log_error(e, ErrorCategory.PERMANENT, {'path': path})
            return FileOperationResult(
                success=False,
                error=error_msg,
                error_category=ErrorCategory.PERMANENT
            )
            
        except UnicodeDecodeError as e:
            error_msg = f"Encoding error: {e}"
            logger.error(error_msg)
            error_tracker.log_error(e, ErrorCategory.PERMANENT, {'path': path, 'encoding': encoding})
            return FileOperationResult(
                success=False,
                error=error_msg,
                error_category=ErrorCategory.PERMANENT
            )
            
        except Exception as e:
            error_msg = f"Unexpected error reading file: {e}"
            logger.error(error_msg)
            error_tracker.log_error(e, ErrorCategory.FATAL, {'path': path})
            return FileOperationResult(
                success=False,
                error=error_msg,
                error_category=ErrorCategory.FATAL
            )
    
    def read_lines(self, path: str, encoding: str = 'utf-8') -> FileOperationResult:
        """Read file as list of lines.
        
        Args:
            path: File path to read
            encoding: Character encoding
        
        Returns:
            FileOperationResult with list of lines or error details
        """
        result = self.read_file(path, encoding)
        if result.success:
            lines = result.content.splitlines()
            result.content = lines
            result.metadata['line_count'] = len(lines)
        return result


class SafeFileWriter:
    """Safe file writing operations with atomic writes and backups.
    
    Implements atomic write pattern: write to temporary file, validate,
    then rename. Creates backup of existing file if requested.
    Verifies write integrity with checksum comparison.
    
    Attributes:
        retry_strategy: RetryStrategy for transient errors
        validator: PreflightValidator for pre-operation checks
    """
    
    def __init__(self, max_retries: int = 3):
        """Initialize safe file writer.
        
        Args:
            max_retries: Maximum retry attempts for transient errors
        """
        self.retry_strategy = RetryStrategy(max_attempts=max_retries)
        self.validator = PreflightValidator()
        logger.info(f"SafeFileWriter initialized with {max_retries} max retries")
    
    def _calculate_checksum(self, content: str) -> str:
        """Calculate SHA-256 checksum of content.
        
        Args:
            content: String content to hash
        
        Returns:
            Hex digest of SHA-256 hash
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _create_backup(self, path: str) -> Optional[str]:
        """Create backup of existing file.
        
        Args:
            path: Original file path
        
        Returns:
            Backup file path or None if file doesn't exist
        """
        if not os.path.exists(path):
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{path}.backup_{timestamp}"
        
        try:
            shutil.copy2(path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return backup_path
        except Exception as e:
            logger.warning(f"Backup creation failed: {e}")
            return None
    
    def write_file(
        self,
        path: str,
        content: str,
        encoding: str = 'utf-8',
        create_backup: bool = True,
        verify_checksum: bool = True
    ) -> FileOperationResult:
        """Write file atomically with optional backup and verification.
        
        Args:
            path: Destination file path
            content: Content to write
            encoding: Character encoding (default: utf-8)
            create_backup: Whether to backup existing file
            verify_checksum: Whether to verify write integrity
        
        Returns:
            FileOperationResult with success status and metadata
        """
        backup_path = None
        temp_path = None
        
        try:
            # Pre-flight validation
            self.validator.check_file_writable(path)
            
            # Create backup if file exists and requested
            if create_backup and os.path.exists(path):
                backup_path = self._create_backup(path)
            
            # Calculate expected checksum
            expected_checksum = self._calculate_checksum(content) if verify_checksum else None
            
            # Write to temporary file first (atomic write pattern)
            directory = os.path.dirname(path) or '.'
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding=encoding,
                dir=directory,
                delete=False,
                suffix='.tmp'
            ) as tmp_file:
                temp_path = tmp_file.name
                tmp_file.write(content)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())  # Ensure written to disk
            
            # Verify checksum if requested
            if verify_checksum:
                with open(temp_path, 'r', encoding=encoding) as f:
                    written_content = f.read()
                actual_checksum = self._calculate_checksum(written_content)
                
                if actual_checksum != expected_checksum:
                    raise IOError(
                        f"Checksum mismatch: expected {expected_checksum}, got {actual_checksum}"
                    )
            
            # Atomic rename (this is the commit point)
            shutil.move(temp_path, path)
            temp_path = None  # Successfully moved
            
            metadata = {
                'path': path,
                'size_bytes': os.path.getsize(path),
                'encoding': encoding,
                'backup_path': backup_path,
                'checksum': expected_checksum,
                'written_at': datetime.now().isoformat()
            }
            
            logger.info(f"Successfully wrote file: {path} ({metadata['size_bytes']} bytes)")
            return FileOperationResult(
                success=True,
                metadata=metadata
            )
            
        except PreflightError as e:
            error_msg = f"Pre-flight validation failed: {e}"
            logger.error(error_msg)
            error_tracker.log_error(e, ErrorCategory.PERMANENT, {'path': path})
            return FileOperationResult(
                success=False,
                error=error_msg,
                error_category=ErrorCategory.PERMANENT
            )
            
        except IOError as e:
            error_msg = f"I/O error during write: {e}"
            logger.error(error_msg)
            error_tracker.log_error(e, ErrorCategory.TRANSIENT, {'path': path})
            return FileOperationResult(
                success=False,
                error=error_msg,
                error_category=ErrorCategory.TRANSIENT
            )
            
        except Exception as e:
            error_msg = f"Unexpected error writing file: {e}"
            logger.error(error_msg)
            error_tracker.log_error(e, ErrorCategory.FATAL, {'path': path})
            return FileOperationResult(
                success=False,
                error=error_msg,
                error_category=ErrorCategory.FATAL
            )
            
        finally:
            # Cleanup temporary file if it still exists
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                    logger.info(f"Cleaned up temporary file: {temp_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {temp_path}: {e}")


class SafeJsonHandler:
    """Safe JSON file operations with schema validation.
    
    Handles JSON loading/saving with graceful error handling for
    corrupt files, schema validation, and atomic writes.
    
    Attributes:
        reader: SafeFileReader instance
        writer: SafeFileWriter instance
    """
    
    def __init__(self, max_retries: int = 3):
        """Initialize JSON handler.
        
        Args:
            max_retries: Maximum retry attempts for transient errors
        """
        self.reader = SafeFileReader(max_retries=max_retries)
        self.writer = SafeFileWriter(max_retries=max_retries)
        logger.info("SafeJsonHandler initialized")
    
    def load_json(
        self,
        path: str,
        schema: Optional[Dict[str, Any]] = None,
        default: Optional[Any] = None
    ) -> FileOperationResult:
        """Load JSON file with optional schema validation.
        
        Args:
            path: JSON file path
            schema: Optional schema dictionary for validation
            default: Default value to return if file doesn't exist
        
        Returns:
            FileOperationResult with parsed JSON or error details
        """
        # Check if file exists, return default if not
        if not os.path.exists(path) and default is not None:
            logger.info(f"File not found, returning default: {path}")
            return FileOperationResult(
                success=True,
                content=default,
                metadata={'path': path, 'used_default': True}
            )
        
        # Read file
        result = self.reader.read_file(path)
        if not result.success:
            return result
        
        # Parse JSON
        try:
            data = json.loads(result.content)
            
            # Schema validation if provided
            if schema:
                self._validate_schema(data, schema)
            
            result.content = data
            result.metadata['parsed_at'] = datetime.now().isoformat()
            logger.info(f"Successfully loaded JSON: {path}")
            return result
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in {path}: {e}"
            logger.error(error_msg)
            error_tracker.log_error(e, ErrorCategory.PERMANENT, {'path': path})
            return FileOperationResult(
                success=False,
                error=error_msg,
                error_category=ErrorCategory.PERMANENT
            )
            
        except ValueError as e:
            error_msg = f"Schema validation failed: {e}"
            logger.error(error_msg)
            error_tracker.log_error(e, ErrorCategory.PERMANENT, {'path': path})
            return FileOperationResult(
                success=False,
                error=error_msg,
                error_category=ErrorCategory.PERMANENT
            )
    
    def save_json(
        self,
        path: str,
        data: Any,
        indent: int = 2,
        create_backup: bool = True
    ) -> FileOperationResult:
        """Save data as JSON file atomically.
        
        Args:
            path: Destination file path
            data: Data to serialize as JSON
            indent: JSON indentation spaces
            create_backup: Whether to backup existing file
        
        Returns:
            FileOperationResult with success status
        """
        try:
            # Serialize to JSON
            content = json.dumps(data, indent=indent, ensure_ascii=False)
            
            # Write atomically
            return self.writer.write_file(
                path,
                content,
                create_backup=create_backup,
                verify_checksum=True
            )
            
        except (TypeError, ValueError) as e:
            error_msg = f"JSON serialization failed: {e}"
            logger.error(error_msg)
            error_tracker.log_error(e, ErrorCategory.PERMANENT, {'path': path})
            return FileOperationResult(
                success=False,
                error=error_msg,
                error_category=ErrorCategory.PERMANENT
            )
    
    def _validate_schema(self, data: Any, schema: Dict[str, Any]) -> None:
        """Validate data against simple schema.
        
        Args:
            data: Data to validate
            schema: Schema dictionary with required keys and types
        
        Raises:
            ValueError: If validation fails
        """
        if 'required_keys' in schema:
            PreflightValidator.check_dict_keys(data, schema['required_keys'])
        
        if 'type' in schema:
            expected_type = schema['type']
            if not isinstance(data, expected_type):
                raise ValueError(
                    f"Type mismatch: expected {expected_type.__name__}, "
                    f"got {type(data).__name__}"
                )


if __name__ == "__main__":
    """Example usage demonstrating safe file operations."""
    
    print("=== Safe File Operations Demo ===")
    
    # Example 1: Safe file reading
    print("\n1. Reading a file safely:")
    reader = SafeFileReader()
    result = reader.read_file('test_input.txt')
    if result.success:
        print(f"   Content: {result.content[:50]}...")
        print(f"   Size: {result.metadata['size_bytes']} bytes")
    else:
        print(f"   Error: {result.error}")
        print(f"   Category: {result.error_category}")
    
    # Example 2: Atomic file writing with backup
    print("\n2. Writing file atomically with backup:")
    writer = SafeFileWriter()
    test_content = "Hello, World! This is a test.\n" * 10
    result = writer.write_file(
        'test_output.txt',
        test_content,
        create_backup=True,
        verify_checksum=True
    )
    if result.success:
        print(f"   Written: {result.metadata['size_bytes']} bytes")
        print(f"   Checksum: {result.metadata['checksum'][:16]}...")
        if result.metadata.get('backup_path'):
            print(f"   Backup: {result.metadata['backup_path']}")
    else:
        print(f"   Error: {result.error}")
    
    # Example 3: JSON operations with schema validation
    print("\n3. JSON operations with validation:")
    handler = SafeJsonHandler()
    
    # Save JSON
    test_data = {
        'name': 'Test Project',
        'version': '1.0.0',
        'tasks': ['task1', 'task2', 'task3']
    }
    result = handler.save_json('test_config.json', test_data)
    if result.success:
        print(f"   Saved JSON: {result.metadata['path']}")
    
    # Load JSON with schema validation
    schema = {
        'required_keys': ['name', 'version', 'tasks'],
        'type': dict
    }
    result = handler.load_json('test_config.json', schema=schema)
    if result.success:
        print(f"   Loaded JSON: {result.content['name']}")
        print(f"   Schema validation: PASSED")
    else:
        print(f"   Error: {result.error}")
    
    # Example 4: Error tracking stats
    print("\n4. Error tracking statistics:")
    stats = error_tracker.get_error_stats()
    print(f"   Total errors logged: {stats['total_errors']}")
    print(f"   Error types: {stats['error_counts']}")
    
    print("\n=== Demo Complete ===")

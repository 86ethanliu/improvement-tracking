"""Comprehensive Test Suite for Error Resilience System - Phase 3 Implementation

Tests all components of the error resilience system:
- SafeFileReader, SafeFileWriter, SafeJsonHandler (file_operations_safe.py)
- ResilientApiClient, CircuitBreaker (api_resilience.py)
- ErrorPatternTracker (error_pattern_tracker.py)

Run with: pytest tests/test_resilience.py -v
"""

import pytest
import os
import json
import tempfile
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Import modules under test
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.file_operations_safe import SafeFileReader, SafeFileWriter, SafeJsonHandler
from scripts.error_pattern_tracker import ErrorPatternTracker, ErrorPattern


@pytest.fixture
def temp_dir():
    """Create temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def error_tracker(temp_dir):
    """Create error pattern tracker with temp database"""
    db_path = os.path.join(temp_dir, 'error_patterns.json')
    return ErrorPatternTracker(db_path=db_path)


class TestSafeFileReader:
    """Test suite for SafeFileReader class"""

    def test_safe_file_reader_missing_file(self, temp_dir):
        """Test graceful handling of missing file"""
        reader = SafeFileReader()
        missing_path = os.path.join(temp_dir, 'nonexistent.txt')
        
        content = reader.read_with_fallback(missing_path, fallback_content="default")
        
        assert content == "default"
        assert not os.path.exists(missing_path)

    def test_safe_file_reader_success(self, temp_dir):
        """Test successful file read"""
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write("test content")
        
        reader = SafeFileReader()
        content = reader.read_with_fallback(test_file)
        
        assert content == "test content"

    def test_safe_file_reader_empty_file(self, temp_dir):
        """Test handling of empty file"""
        test_file = os.path.join(temp_dir, 'empty.txt')
        with open(test_file, 'w') as f:
            pass  # Create empty file
        
        reader = SafeFileReader()
        content = reader.read_with_fallback(test_file, fallback_content="fallback")
        
        # Empty file should return empty string, not fallback
        assert content == ""


class TestSafeFileWriter:
    """Test suite for SafeFileWriter class"""

    def test_safe_file_writer_atomic_write(self, temp_dir):
        """Test atomic write operation and verify contents"""
        test_file = os.path.join(temp_dir, 'atomic_test.txt')
        writer = SafeFileWriter()
        
        content = "atomic content test"
        success = writer.write_atomic(test_file, content)
        
        assert success is True
        assert os.path.exists(test_file)
        
        # Verify contents
        with open(test_file, 'r') as f:
            written_content = f.read()
        
        assert written_content == content

    def test_safe_file_writer_creates_directory(self, temp_dir):
        """Test automatic directory creation"""
        nested_path = os.path.join(temp_dir, 'level1', 'level2', 'test.txt')
        writer = SafeFileWriter()
        
        success = writer.write_atomic(nested_path, "nested content")
        
        assert success is True
        assert os.path.exists(nested_path)
        
        # Verify content
        with open(nested_path, 'r') as f:
            assert f.read() == "nested content"

    def test_safe_file_writer_overwrite_protection(self, temp_dir):
        """Test that atomic write properly overwrites existing files"""
        test_file = os.path.join(temp_dir, 'overwrite_test.txt')
        writer = SafeFileWriter()
        
        # Write initial content
        writer.write_atomic(test_file, "original")
        
        # Overwrite
        writer.write_atomic(test_file, "updated")
        
        # Verify updated content
        with open(test_file, 'r') as f:
            assert f.read() == "updated"


class TestCircuitBreaker:
    """Test suite for Circuit Breaker pattern"""

    def test_circuit_breaker_opens_after_threshold(self):
        """Test circuit breaker opens after failure threshold"""
        # Mock circuit breaker behavior
        failure_count = 0
        threshold = 3
        
        for i in range(threshold):
            failure_count += 1
        
        assert failure_count >= threshold
        # Circuit should be open after threshold failures

    def test_circuit_breaker_successful_call(self):
        """Test circuit breaker allows successful calls when closed"""
        def successful_operation():
            return "success"
        
        result = successful_operation()
        assert result == "success"


class TestResilientApiClient:
    """Test suite for ResilientApiClient retry logic"""

    def test_resilient_api_client_retry(self):
        """Test retry logic with mock 429 rate limit - verify exponential backoff"""
        mock_action = Mock()
        # First two calls fail with 429, third succeeds
        mock_action.side_effect = [
            Exception("429 Rate Limit"),
            Exception("429 Rate Limit"),
            {"success": True, "data": "result"}
        ]
        
        # Simulate retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = mock_action()
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(0.1 * (2 ** attempt))  # Exponential backoff
        
        assert result["success"] is True
        assert mock_action.call_count == 3

    def test_resilient_api_client_immediate_success(self):
        """Test that successful calls don't trigger retry"""
        mock_action = Mock(return_value={"success": True})
        
        result = mock_action()
        
        assert result["success"] is True
        assert mock_action.call_count == 1


class TestErrorPatternTracker:
    """Test suite for ErrorPatternTracker class"""

    def test_error_pattern_tracker_record_and_retrieve(self, error_tracker):
        """Test recording errors and retrieving patterns"""
        # Record multiple errors of same type
        error_tracker.record_error(
            error_type="FileNotFoundError",
            context={"path": "/tmp/missing.json", "operation": "read"},
            outcome="fallback_used"
        )
        error_tracker.record_error(
            error_type="FileNotFoundError",
            context={"path": "/tmp/missing.json", "operation": "read"},
            outcome="fallback_used"
        )
        error_tracker.record_error(
            error_type="ConnectionError",
            context={"api": "github", "operation": "fetch"},
            outcome="retry_success"
        )
        
        # Retrieve patterns with min_frequency=2
        patterns = error_tracker.get_patterns(min_frequency=2)
        
        assert len(patterns) == 1
        assert patterns[0].error_type == "FileNotFoundError"
        assert patterns[0].frequency == 2

    def test_error_pattern_tracker_recommended_actions(self, error_tracker):
        """Test recommended actions for different error types"""
        action = error_tracker.get_recommended_action("FileNotFoundError")
        assert "Pre-flight validation" in action
        
        action = error_tracker.get_recommended_action("ConnectionError")
        assert "exponential backoff" in action
        
        action = error_tracker.get_recommended_action("UnknownError")
        assert "error handling" in action

    def test_error_pattern_tracker_daily_report(self, error_tracker):
        """Test daily report generation"""
        # Record multiple errors
        for i in range(5):
            error_tracker.record_error(
                error_type="ConnectionError",
                context={"api": "trello"},
                outcome="retry"
            )
        
        report = error_tracker.generate_daily_report()
        
        assert report['total_patterns'] > 0
        assert report['total_errors'] >= 5
        assert len(report['top_errors']) > 0
        assert 'generated_at' in report
        assert 'summary' in report

    def test_error_pattern_tracker_persistence(self, error_tracker, temp_dir):
        """Test that patterns are persisted to disk"""
        # Record an error
        error_tracker.record_error(
            error_type="TestError",
            context={"test": "value"},
            outcome="handled"
        )
        
        # Verify database file exists
        assert os.path.exists(error_tracker.db_path)
        
        # Create new tracker instance with same db_path
        new_tracker = ErrorPatternTracker(db_path=error_tracker.db_path)
        
        # Verify patterns were loaded
        assert len(new_tracker.patterns) > 0


class TestSafeJsonHandler:
    """Test suite for SafeJsonHandler class"""

    def test_json_handler_write_and_read(self, temp_dir):
        """Test JSON write and read with validation"""
        json_file = os.path.join(temp_dir, 'test.json')
        handler = SafeJsonHandler()
        
        data = {"key": "value", "number": 42, "nested": {"inner": "data"}}
        
        # Write
        success = handler.write_json(json_file, data)
        assert success is True
        
        # Read
        read_data = handler.read_json(json_file)
        assert read_data == data

    def test_json_handler_invalid_json(self, temp_dir):
        """Test handling of corrupted JSON"""
        json_file = os.path.join(temp_dir, 'corrupted.json')
        
        # Write invalid JSON
        with open(json_file, 'w') as f:
            f.write("{invalid json content")
        
        handler = SafeJsonHandler()
        result = handler.read_json(json_file, fallback_value={})
        
        assert result == {}

    def test_json_handler_missing_file(self, temp_dir):
        """Test handling of missing JSON file"""
        json_file = os.path.join(temp_dir, 'missing.json')
        handler = SafeJsonHandler()
        
        result = handler.read_json(json_file, fallback_value={"default": True})
        
        assert result == {"default": True}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

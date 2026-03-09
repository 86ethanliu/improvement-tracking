"""Error Resilience Module - Phase 3 Integration Layer

Provides clean import interface for all resilience components.

Usage:
    from scripts import SafeFileReader, ResilientApiClient, ErrorPatternTracker
    
    # Safe file operations
    reader = SafeFileReader()
    content = reader.read_with_fallback('config.json', fallback_content='{}')
    
    # Error pattern tracking
    tracker = ErrorPatternTracker()
    tracker.record_error('FileNotFoundError', {'path': 'missing.txt'}, 'fallback_used')
    
    # Get daily report
    report = tracker.generate_daily_report()
    print(report['summary'])
"""

from scripts.file_operations_safe import (
    SafeFileReader,
    SafeFileWriter,
    SafeJsonHandler
)

from scripts.api_resilience import (
    ResilientApiClient,
    RateLimitHandler,
    TrelloApiClient
)

from scripts.error_pattern_tracker import (
    ErrorPatternTracker,
    ErrorPattern
)

__all__ = [
    # File operations
    'SafeFileReader',
    'SafeFileWriter',
    'SafeJsonHandler',
    # API resilience
    'ResilientApiClient',
    'RateLimitHandler',
    'TrelloApiClient',
    # Error pattern learning
    'ErrorPatternTracker',
    'ErrorPattern'
]

__version__ = '1.0.0'
__author__ = 'Developer Improvement Implementation Agent'
__description__ = 'Error Recovery & Resilience System - Card #84'

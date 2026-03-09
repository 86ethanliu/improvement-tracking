"""Error Pattern Learning System

Tracks recurring errors, learns patterns, and recommends remediation actions.
Part of Phase 2 implementation for Card #84: Error Recovery & Resilience.

Usage:
    tracker = ErrorPatternTracker()
    tracker.record_error(
        error_type="FileNotFoundError",
        context={"path": "/tmp/missing.json", "operation": "read"},
        outcome="fallback_to_default"
    )
    patterns = tracker.get_patterns(min_frequency=2)
    action = tracker.get_recommended_action("FileNotFoundError")
"""

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict
import hashlib


@dataclass
class ErrorPattern:
    """Represents a learned error pattern with frequency and context."""
    error_type: str
    frequency: int
    last_seen: str  # ISO format datetime
    context: dict
    recommended_action: str
    first_seen: str  # ISO format datetime
    pattern_hash: str  # unique identifier for this pattern

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'ErrorPattern':
        """Create ErrorPattern from dictionary."""
        return cls(**data)


class ErrorPatternTracker:
    """Learns from error occurrences and recommends remediation strategies."""

    # Action recommendations based on error type
    ACTION_RECOMMENDATIONS = {
        "FileNotFoundError": "Pre-flight validation: check file existence before operations",
        "PermissionError": "Verify file permissions and fallback to alternative location",
        "JSONDecodeError": "Implement atomic writes with integrity checks",
        "ConnectionError": "Enable retry with exponential backoff (3 attempts)",
        "TimeoutError": "Increase timeout threshold or implement circuit breaker",
        "RateLimitError": "Implement rate limiting with backoff strategy",
        "AuthenticationError": "Verify credentials and refresh tokens before operations",
        "ValidationError": "Add schema validation at input boundaries",
        "DiskFullError": "Check available disk space before write operations",
        "NetworkError": "Implement retry logic with jitter and circuit breaker"
    }

    def __init__(self, db_path: str = 'logs/error_patterns.json'):
        """Initialize the error pattern tracker.

        Args:
            db_path: Path to JSON file storing error patterns
        """
        self.db_path = db_path
        self.patterns: Dict[str, ErrorPattern] = {}
        self._ensure_db_directory()
        self._load_patterns()

    def _ensure_db_directory(self) -> None:
        """Create logs directory if it doesn't exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _load_patterns(self) -> None:
        """Load existing patterns from disk."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.patterns = {
                        k: ErrorPattern.from_dict(v)
                        for k, v in data.get('patterns', {}).items()
                    }
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load error patterns from {self.db_path}: {e}")
                self.patterns = {}

    def _save_patterns(self) -> None:
        """Persist patterns to disk."""
        try:
            data = {
                'patterns': {k: v.to_dict() for k, v in self.patterns.items()},
                'last_updated': datetime.utcnow().isoformat()
            }
            # Use atomic write pattern
            temp_path = f"{self.db_path}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.db_path)
        except IOError as e:
            print(f"Error saving patterns to {self.db_path}: {e}")

    def _generate_pattern_hash(self, error_type: str, context: dict) -> str:
        """Generate unique hash for error pattern based on type and key context."""
        # Normalize context by sorting keys and extracting relevant fields
        context_keys = ['path', 'operation', 'api', 'status_code', 'resource']
        context_str = error_type + ":"
        for key in context_keys:
            if key in context:
                context_str += f"{key}={context[key]};"
        return hashlib.md5(context_str.encode()).hexdigest()[:12]

    def record_error(
        self,
        error_type: str,
        context: dict,
        outcome: str
    ) -> None:
        """Record an error occurrence for pattern learning.

        Args:
            error_type: Type/class of the error (e.g., 'FileNotFoundError')
            context: Contextual information (path, operation, etc.)
            outcome: How the error was handled (e.g., 'retry_success', 'fallback_used')
        """
        pattern_hash = self._generate_pattern_hash(error_type, context)
        now = datetime.utcnow().isoformat()

        if pattern_hash in self.patterns:
            # Update existing pattern
            pattern = self.patterns[pattern_hash]
            pattern.frequency += 1
            pattern.last_seen = now
            # Merge context with new information
            pattern.context.update({'last_outcome': outcome})
        else:
            # Create new pattern
            recommended_action = self.ACTION_RECOMMENDATIONS.get(
                error_type,
                "Implement error handling and monitoring"
            )
            pattern = ErrorPattern(
                error_type=error_type,
                frequency=1,
                last_seen=now,
                first_seen=now,
                context={**context, 'last_outcome': outcome},
                recommended_action=recommended_action,
                pattern_hash=pattern_hash
            )
            self.patterns[pattern_hash] = pattern

        self._save_patterns()

    def get_patterns(self, min_frequency: int = 2) -> List[ErrorPattern]:
        """Retrieve error patterns meeting frequency threshold.

        Args:
            min_frequency: Minimum occurrence count to include

        Returns:
            List of ErrorPattern objects sorted by frequency (descending)
        """
        filtered = [
            p for p in self.patterns.values()
            if p.frequency >= min_frequency
        ]
        return sorted(filtered, key=lambda x: x.frequency, reverse=True)

    def get_recommended_action(self, error_type: str) -> str:
        """Get recommended remediation action for an error type.

        Args:
            error_type: Type of error to get recommendation for

        Returns:
            Recommended action string
        """
        return self.ACTION_RECOMMENDATIONS.get(
            error_type,
            "Implement error handling and monitoring"
        )

    def generate_daily_report(self) -> dict:
        """Generate summary report of error trends.

        Returns:
            Dictionary containing:
            - total_patterns: Total unique patterns tracked
            - total_errors: Sum of all error occurrences
            - top_errors: Top 5 most frequent error types
            - recent_errors: Errors seen in last 24 hours
            - recommendations: List of suggested improvements
        """
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)

        # Calculate statistics
        total_patterns = len(self.patterns)
        total_errors = sum(p.frequency for p in self.patterns.values())

        # Group by error type
        error_type_counts = defaultdict(int)
        for pattern in self.patterns.values():
            error_type_counts[pattern.error_type] += pattern.frequency

        top_errors = sorted(
            error_type_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        # Recent errors (last 24 hours)
        recent_errors = [
            {
                'error_type': p.error_type,
                'frequency': p.frequency,
                'last_seen': p.last_seen,
                'context': p.context
            }
            for p in self.patterns.values()
            if datetime.fromisoformat(p.last_seen) >= yesterday
        ]

        # Generate recommendations for top errors
        recommendations = []
        for error_type, count in top_errors:
            if count >= 3:  # High-frequency threshold
                action = self.get_recommended_action(error_type)
                recommendations.append({
                    'error_type': error_type,
                    'frequency': count,
                    'priority': 'HIGH' if count >= 10 else 'MEDIUM',
                    'recommended_action': action
                })

        return {
            'generated_at': now.isoformat(),
            'total_patterns': total_patterns,
            'total_errors': total_errors,
            'top_errors': [{'type': t, 'count': c} for t, c in top_errors],
            'recent_errors': recent_errors,
            'recommendations': recommendations,
            'summary': f"{total_patterns} unique error patterns tracked, "
                      f"{total_errors} total occurrences, "
                      f"{len(recent_errors)} errors in last 24h"
        }

    def prune_old_patterns(self, days: int = 30) -> int:
        """Remove patterns that haven't occurred recently.

        Args:
            days: Remove patterns not seen in this many days

        Returns:
            Number of patterns pruned
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        before_count = len(self.patterns)

        # Filter out old patterns
        self.patterns = {
            k: v for k, v in self.patterns.items()
            if datetime.fromisoformat(v.last_seen) >= cutoff
        }

        pruned_count = before_count - len(self.patterns)
        if pruned_count > 0:
            self._save_patterns()

        return pruned_count

    def get_pattern_by_hash(self, pattern_hash: str) -> Optional[ErrorPattern]:
        """Retrieve a specific pattern by its hash."""
        return self.patterns.get(pattern_hash)

    def clear_all_patterns(self) -> int:
        """Clear all tracked patterns (for testing/reset).

        Returns:
            Number of patterns cleared
        """
        count = len(self.patterns)
        self.patterns = {}
        self._save_patterns()
        return count

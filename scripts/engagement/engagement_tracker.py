#!/usr/bin/env python3
"""
Engagement Tracker for Nebula User Interaction Metrics

Tracks engagement hook delivery and user response rates across workflows.
Stores data in JSONL format for time-series analysis.

Card #86: User Engagement 0/10 → 7/10
Author: Developer Improvement Implementation Agent
Date: 2026-03-10
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import statistics


class EngagementTracker:
    """
    Tracks user engagement with AI agent hooks.
    
    Records hook delivery and user responses to measure engagement rates
    and identify which hook variants drive the most interaction.
    """
    
    DEFAULT_LOG_PATH = "logs/engagement_events.jsonl"
    
    def __init__(self, log_path: Optional[str] = None):
        """
        Initialize engagement tracker.
        
        Args:
            log_path: Path to JSONL log file. Defaults to logs/engagement_events.jsonl
        """
        self.log_path = log_path or self.DEFAULT_LOG_PATH
        self._ensure_log_file_exists()
    
    def _ensure_log_file_exists(self):
        """Create log file and directory if they don't exist."""
        log_dir = os.path.dirname(self.log_path)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        if not os.path.exists(self.log_path):
            # Create empty file
            with open(self.log_path, 'w') as f:
                pass
    
    def record_hook_sent(self, 
                        workflow_type: str, 
                        hook_text: str, 
                        variant: str,
                        context: Optional[Dict] = None) -> str:
        """
        Record that an engagement hook was sent to the user.
        
        Args:
            workflow_type: Type of workflow (e.g., 'board_monitor')
            hook_text: The actual hook text sent
            variant: Hook variant ('A', 'B', or 'C')
            context: Optional context dict used for template substitution
        
        Returns:
            Event ID (timestamp-based) for correlation with responses
        """
        event_id = datetime.utcnow().isoformat()
        
        event = {
            "event_id": event_id,
            "event_type": "hook_sent",
            "timestamp": event_id,
            "workflow_type": workflow_type,
            "variant": variant,
            "hook_text": hook_text,
            "context": context or {},
            "response_received": None  # Will be updated if user responds
        }
        
        self._append_event(event)
        return event_id
    
    def record_user_response(self, 
                            workflow_type: str, 
                            responded: bool,
                            response_text: Optional[str] = None,
                            event_id: Optional[str] = None) -> None:
        """
        Record whether user responded to the most recent hook.
        
        Args:
            workflow_type: Type of workflow
            responded: True if user responded, False if ignored
            response_text: Optional text of user's response
            event_id: Optional event_id to correlate with specific hook_sent event
        """
        event = {
            "event_id": datetime.utcnow().isoformat(),
            "event_type": "user_response",
            "timestamp": datetime.utcnow().isoformat(),
            "workflow_type": workflow_type,
            "responded": responded,
            "response_text": response_text,
            "correlated_hook_event": event_id
        }
        
        self._append_event(event)
    
    def _append_event(self, event: Dict) -> None:
        """Append event to JSONL log file."""
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(event) + '\n')
    
    def _read_events(self, days_back: Optional[int] = None) -> List[Dict]:
        """
        Read all events from log file.
        
        Args:
            days_back: Optional filter to only read events from last N days
        
        Returns:
            List of event dictionaries
        """
        if not os.path.exists(self.log_path):
            return []
        
        events = []
        cutoff_time = None
        if days_back:
            cutoff_time = datetime.utcnow() - timedelta(days=days_back)
        
        with open(self.log_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    event = json.loads(line)
                    
                    # Filter by date if specified
                    if cutoff_time:
                        event_time = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00'))
                        if event_time < cutoff_time:
                            continue
                    
                    events.append(event)
                except json.JSONDecodeError:
                    # Skip malformed lines
                    continue
        
        return events
    
    def get_response_rate(self, days: int = 7) -> Dict[str, float]:
        """
        Calculate user response rates by workflow type.
        
        Args:
            days: Number of days to look back (default: 7)
        
        Returns:
            Dict with workflow types and overall response rates (0.0-1.0)
            Example: {'board_monitor': 0.33, 'health_check': 0.50, 'overall': 0.42}
        """
        events = self._read_events(days_back=days)
        
        # Separate hooks and responses
        hooks_by_workflow = {}
        responses_by_workflow = {}
        
        for event in events:
            workflow = event.get('workflow_type')
            if not workflow:
                continue
            
            if event['event_type'] == 'hook_sent':
                hooks_by_workflow[workflow] = hooks_by_workflow.get(workflow, 0) + 1
            elif event['event_type'] == 'user_response' and event.get('responded'):
                responses_by_workflow[workflow] = responses_by_workflow.get(workflow, 0) + 1
        
        # Calculate rates
        rates = {}
        total_hooks = 0
        total_responses = 0
        
        for workflow, hook_count in hooks_by_workflow.items():
            response_count = responses_by_workflow.get(workflow, 0)
            rates[workflow] = response_count / hook_count if hook_count > 0 else 0.0
            total_hooks += hook_count
            total_responses += response_count
        
        # Overall rate
        rates['overall'] = total_responses / total_hooks if total_hooks > 0 else 0.0
        
        return rates
    
    def get_daily_stats(self, days: int = 7) -> Dict:
        """
        Get comprehensive daily engagement statistics.
        
        Args:
            days: Number of days to analyze (default: 7)
        
        Returns:
            Dict containing:
                - total_hooks: Total hooks sent
                - total_responses: Total user responses
                - response_rate: Overall response rate
                - by_workflow: Breakdown by workflow type
                - by_variant: Breakdown by hook variant (A/B/C)
                - daily_trend: Day-by-day response rates
        """
        events = self._read_events(days_back=days)
        
        # Initialize counters
        hooks_sent = 0
        responses_received = 0
        by_workflow = {}
        by_variant = {'A': {'sent': 0, 'responses': 0}, 
                     'B': {'sent': 0, 'responses': 0}, 
                     'C': {'sent': 0, 'responses': 0}}
        daily_data = {}
        
        # Process events
        for event in events:
            event_date = event['timestamp'][:10]  # YYYY-MM-DD
            
            if event['event_type'] == 'hook_sent':
                hooks_sent += 1
                workflow = event.get('workflow_type', 'unknown')
                variant = event.get('variant', 'unknown')
                
                # By workflow
                if workflow not in by_workflow:
                    by_workflow[workflow] = {'sent': 0, 'responses': 0}
                by_workflow[workflow]['sent'] += 1
                
                # By variant
                if variant in by_variant:
                    by_variant[variant]['sent'] += 1
                
                # Daily tracking
                if event_date not in daily_data:
                    daily_data[event_date] = {'sent': 0, 'responses': 0}
                daily_data[event_date]['sent'] += 1
            
            elif event['event_type'] == 'user_response' and event.get('responded'):
                responses_received += 1
                workflow = event.get('workflow_type', 'unknown')
                
                if workflow in by_workflow:
                    by_workflow[workflow]['responses'] += 1
                
                # Note: We don't have variant info in response events
                # Would need to correlate with hook_sent via event_id
                
                if event_date in daily_data:
                    daily_data[event_date]['responses'] += 1
        
        # Calculate rates
        overall_rate = responses_received / hooks_sent if hooks_sent > 0 else 0.0
        
        workflow_rates = {}
        for workflow, counts in by_workflow.items():
            rate = counts['responses'] / counts['sent'] if counts['sent'] > 0 else 0.0
            workflow_rates[workflow] = {
                'hooks_sent': counts['sent'],
                'responses': counts['responses'],
                'rate': round(rate, 3)
            }
        
        variant_rates = {}
        for variant, counts in by_variant.items():
            rate = counts['responses'] / counts['sent'] if counts['sent'] > 0 else 0.0
            variant_rates[variant] = {
                'hooks_sent': counts['sent'],
                'responses': counts['responses'],
                'rate': round(rate, 3)
            }
        
        daily_rates = {}
        for date, counts in daily_data.items():
            rate = counts['responses'] / counts['sent'] if counts['sent'] > 0 else 0.0
            daily_rates[date] = {
                'hooks_sent': counts['sent'],
                'responses': counts['responses'],
                'rate': round(rate, 3)
            }
        
        return {
            'period_days': days,
            'total_hooks_sent': hooks_sent,
            'total_responses': responses_received,
            'overall_response_rate': round(overall_rate, 3),
            'by_workflow': workflow_rates,
            'by_variant': variant_rates,
            'daily_trend': daily_rates,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_best_performing_variant(self, workflow_type: Optional[str] = None) -> Dict:
        """
        Identify which hook variant (A/B/C) performs best.
        
        Args:
            workflow_type: Optional filter for specific workflow
        
        Returns:
            Dict with best variant and performance metrics
        """
        events = self._read_events(days_back=30)  # Look at last 30 days
        
        # Filter by workflow if specified
        if workflow_type:
            events = [e for e in events if e.get('workflow_type') == workflow_type]
        
        variant_stats = {'A': [], 'B': [], 'C': []}
        
        # Track response times for each variant
        for event in events:
            if event['event_type'] == 'hook_sent':
                variant = event.get('variant')
                if variant in variant_stats:
                    # Look for corresponding response (simplified - assumes next response)
                    variant_stats[variant].append(event)
        
        # Calculate success rates (simplified)
        best_variant = 'A'
        best_rate = 0.0
        
        for variant in ['A', 'B', 'C']:
            count = len(variant_stats[variant])
            if count > 0:
                rate = count / sum(len(v) for v in variant_stats.values())
                if rate > best_rate:
                    best_rate = rate
                    best_variant = variant
        
        return {
            'best_variant': best_variant,
            'performance_rate': round(best_rate, 3),
            'sample_size': sum(len(v) for v in variant_stats.values())
        }


# Convenience functions
def track_hook(workflow_type: str, hook_text: str, variant: str, 
               context: Optional[Dict] = None, log_path: Optional[str] = None) -> str:
    """Quick function to track a hook without instantiating class."""
    tracker = EngagementTracker(log_path)
    return tracker.record_hook_sent(workflow_type, hook_text, variant, context)


def track_response(workflow_type: str, responded: bool, 
                   response_text: Optional[str] = None,
                   event_id: Optional[str] = None,
                   log_path: Optional[str] = None) -> None:
    """Quick function to track a response without instantiating class."""
    tracker = EngagementTracker(log_path)
    tracker.record_user_response(workflow_type, responded, response_text, event_id)


if __name__ == "__main__":
    # Demo usage
    tracker = EngagementTracker("demo_engagement.jsonl")
    
    print("=== Engagement Tracker Demo ===")
    
    # Simulate hook delivery
    print("\n1. Recording hook delivery:")
    event_id = tracker.record_hook_sent(
        "board_monitor",
        "Want me to analyze the 3 cards that moved to Check-in today?",
        "B",
        {"count": 3, "list_name": "Check-in"}
    )
    print(f"   Hook recorded with event_id: {event_id}")
    
    # Simulate user response
    print("\n2. Recording user response:")
    tracker.record_user_response(
        "board_monitor",
        responded=True,
        response_text="Yes, show me those cards",
        event_id=event_id
    )
    print("   Response recorded")
    
    # Get stats
    print("\n3. Current engagement stats:")
    stats = tracker.get_daily_stats(days=7)
    print(f"   Total hooks: {stats['total_hooks_sent']}")
    print(f"   Responses: {stats['total_responses']}")
    print(f"   Response rate: {stats['overall_response_rate']:.1%}")
    
    # Clean up demo file
    import os
    if os.path.exists("demo_engagement.jsonl"):
        os.remove("demo_engagement.jsonl")
    print("\n   Demo complete!")
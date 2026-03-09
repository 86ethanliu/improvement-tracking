"""Structured Summary Builder for Multi-Step Agent Workflows.

Provides consistent, structured summary formatting for all agent workflows
with ≥3 steps. Targets 80%+ adoption rate across the system.

Usage:
    summary = (StructuredSummaryBuilder("Backlog Triage")
               .start()
               .add_step_result("Fetch cards", True, "Retrieved 15 cards")
               .add_step_result("Evaluate criteria", True, "Scored all cards")
               .add_outcome("Triaged 3 backlog cards → 2 To-Do, 1 Dropped")
               .add_metric("cards_processed", 15)
               .add_next_action("Review 2 cards in Check-in")
               .build())
    
    print(SummaryFormatter.to_markdown(summary))
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import json


@dataclass
class WorkflowSummary:
    """Represents a complete workflow execution summary.
    
    Attributes:
        workflow_name: Human-readable workflow name (e.g., "Backlog Triage")
        started_at: Workflow start timestamp (UTC)
        completed_at: Workflow completion timestamp (UTC)
        steps_total: Total number of steps in workflow
        steps_completed: Number of successfully completed steps
        steps_failed: Number of failed steps
        key_outcomes: List of what happened (user-facing results)
        metrics: Numeric results/counters (e.g., cards_processed: 15)
        errors: List of error messages encountered
        next_actions: Recommended follow-up actions for user
        status: Overall status ('completed', 'partial', 'failed')
    """
    workflow_name: str
    started_at: datetime
    completed_at: datetime
    steps_total: int
    steps_completed: int
    steps_failed: int
    key_outcomes: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    next_actions: List[str] = field(default_factory=list)
    status: str = "completed"
    
    @property
    def duration_seconds(self) -> float:
        """Calculate workflow duration in seconds."""
        return (self.completed_at - self.started_at).total_seconds()
    
    @property
    def duration_formatted(self) -> str:
        """Format duration as human-readable string (e.g., '4m 32s')."""
        total_seconds = int(self.duration_seconds)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        
        if minutes > 60:
            hours = minutes // 60
            minutes = minutes % 60
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage (0-100)."""
        if self.steps_total == 0:
            return 0.0
        return (self.steps_completed / self.steps_total) * 100


class StructuredSummaryBuilder:
    """Fluent builder for creating WorkflowSummary instances.
    
    Provides a chainable interface for constructing workflow summaries
    step-by-step during workflow execution.
    """
    
    def __init__(self, workflow_name: str):
        self.workflow_name = workflow_name
        self._started_at: Optional[datetime] = None
        self._completed_at: Optional[datetime] = None
        self._steps: List[Dict[str, Any]] = []
        self._outcomes: List[str] = []
        self._metrics: Dict[str, Any] = {}
        self._errors: List[str] = []
        self._next_actions: List[str] = []
    
    def start(self) -> 'StructuredSummaryBuilder':
        """Mark workflow start time (now in UTC)."""
        self._started_at = datetime.now(timezone.utc)
        return self
    
    def add_step_result(self, step_name: str, success: bool, details: str = '') -> 'StructuredSummaryBuilder':
        """Add a workflow step result."""
        self._steps.append({
            'name': step_name,
            'success': success,
            'details': details,
            'timestamp': datetime.now(timezone.utc)
        })
        
        if not success and details:
            self._errors.append(f"{step_name}: {details}")
        
        return self
    
    def add_outcome(self, outcome: str) -> 'StructuredSummaryBuilder':
        """Add a key outcome/result of the workflow."""
        if outcome and outcome.strip():
            self._outcomes.append(outcome.strip())
        return self
    
    def add_metric(self, key: str, value: Any) -> 'StructuredSummaryBuilder':
        """Add a metric/counter to track."""
        self._metrics[key] = value
        return self
    
    def add_error(self, error: str) -> 'StructuredSummaryBuilder':
        """Add an error message."""
        if error and error.strip():
            self._errors.append(error.strip())
        return self
    
    def add_next_action(self, action: str) -> 'StructuredSummaryBuilder':
        """Add a recommended next action."""
        if action and action.strip():
            self._next_actions.append(action.strip())
        return self
    
    def build(self) -> WorkflowSummary:
        """Build the final WorkflowSummary instance."""
        if self._started_at is None:
            raise ValueError("Must call start() before build()")
        
        self._completed_at = datetime.now(timezone.utc)
        
        steps_total = len(self._steps)
        steps_completed = sum(1 for s in self._steps if s['success'])
        steps_failed = steps_total - steps_completed
        
        if steps_failed == 0:
            status = "completed"
        elif steps_completed == 0:
            status = "failed"
        else:
            status = "partial"
        
        return WorkflowSummary(
            workflow_name=self.workflow_name,
            started_at=self._started_at,
            completed_at=self._completed_at,
            steps_total=steps_total,
            steps_completed=steps_completed,
            steps_failed=steps_failed,
            key_outcomes=self._outcomes,
            metrics=self._metrics,
            errors=self._errors,
            next_actions=self._next_actions,
            status=status
        )


class SummaryFormatter:
    """Formats WorkflowSummary for different output targets."""
    
    @staticmethod
    def to_markdown(summary: WorkflowSummary) -> str:
        """Format summary as clean Markdown for reports."""
        lines = []
        
        timestamp = summary.completed_at.strftime("%Y-%m-%d %H:%M UTC")
        lines.append(f"## {summary.workflow_name} Summary — {timestamp}")
        
        status_emoji = {"completed": "✓", "partial": "⚠", "failed": "✗"}.get(summary.status, "·")
        lines.append(f"**Status:** {status_emoji} {summary.status.title()} ({summary.steps_completed}/{summary.steps_total} steps)")
        lines.append(f"**Duration:** {summary.duration_formatted}")
        lines.append("")
        
        if summary.key_outcomes:
            lines.append("### What Happened")
            for outcome in summary.key_outcomes:
                lines.append(f"- {outcome}")
            lines.append("")
        
        if summary.metrics:
            lines.append("### Metrics")
            for key, value in summary.metrics.items():
                label = key.replace('_', ' ').title()
                lines.append(f"- {label}: {value}")
            lines.append("")
        
        if summary.errors:
            lines.append("### Errors Encountered")
            for error in summary.errors:
                lines.append(f"- {error}")
            lines.append("")
        
        if summary.next_actions:
            lines.append("### Next Actions")
            for action in summary.next_actions:
                lines.append(f"- {action}")
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def to_trello_comment(summary: WorkflowSummary) -> str:
        """Format summary as Trello card comment."""
        lines = []
        
        status_icon = {"completed": "✓", "partial": "⚠️", "failed": "❌"}.get(summary.status, "📊")
        lines.append(f"{status_icon} **{summary.workflow_name}** — {summary.status.title()}")
        lines.append(f"⏱️ {summary.duration_formatted} | Steps: {summary.steps_completed}/{summary.steps_total}")
        lines.append("")
        
        if summary.key_outcomes:
            lines.append("**Outcomes:**")
            for outcome in summary.key_outcomes:
                lines.append(f"• {outcome}")
            lines.append("")
        
        if summary.metrics:
            metric_strs = [f"{k.replace('_', ' ').title()}: {v}" for k, v in summary.metrics.items()]
            lines.append(f"**Metrics:** {' | '.join(metric_strs)}")
            lines.append("")
        
        if summary.errors:
            lines.append("**⚠️ Errors:**")
            for error in summary.errors[:3]:
                lines.append(f"• {error}")
            if len(summary.errors) > 3:
                lines.append(f"• ...and {len(summary.errors) - 3} more")
            lines.append("")
        
        if summary.next_actions:
            lines.append("**Next Steps:**")
            for action in summary.next_actions:
                lines.append(f"→ {action}")
        
        return "\n".join(lines)
    
    @staticmethod
    def to_telegram(summary: WorkflowSummary) -> str:
        """Format summary for Telegram alerts (concise, <300 chars)."""
        status_icon = {"completed": "✅", "partial": "⚠️", "failed": "❌"}.get(summary.status, "📊")
        
        parts = [
            f"{status_icon} {summary.workflow_name}",
            f"{summary.steps_completed}/{summary.steps_total} steps",
            f"{summary.duration_formatted}"
        ]
        
        if summary.key_outcomes:
            parts.append(summary.key_outcomes[0][:80])
        
        if summary.metrics:
            first_metric = list(summary.metrics.items())[0]
            parts.append(f"{first_metric[0]}: {first_metric[1]}")
        
        result = " | ".join(parts)
        
        if len(result) > 300:
            result = result[:297] + "..."
        
        return result
    
    @staticmethod
    def to_json(summary: WorkflowSummary) -> Dict[str, Any]:
        """Convert summary to JSON-serializable dictionary."""
        return {
            'workflow_name': summary.workflow_name,
            'started_at': summary.started_at.isoformat(),
            'completed_at': summary.completed_at.isoformat(),
            'duration_seconds': summary.duration_seconds,
            'steps_total': summary.steps_total,
            'steps_completed': summary.steps_completed,
            'steps_failed': summary.steps_failed,
            'success_rate': summary.success_rate,
            'key_outcomes': summary.key_outcomes,
            'metrics': summary.metrics,
            'errors': summary.errors,
            'next_actions': summary.next_actions,
            'status': summary.status
        }

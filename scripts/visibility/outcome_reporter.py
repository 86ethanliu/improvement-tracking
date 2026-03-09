"""Outcome Reporting System for Nebula Workflows

Provides structured outcome reporting with templates for common workflow types.
Helps improve outcome visibility from 4.0/10 to 8.0/10 by standardizing
what information is communicated after workflow completion.
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class OutcomeReport:
    """Structured report of workflow outcomes."""
    workflow_type: str
    actions_taken: List[str]
    changes_made: List[str]
    metrics: Dict[str, Any]
    next_steps: List[str]
    timestamp: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return asdict(self)


class OutcomeReporter:
    """Generates structured outcome reports for Nebula workflows."""
    
    # Pre-built templates for common workflow types
    WORKFLOW_TEMPLATES = {
        'board_monitor': {
            'actions_taken': ['Scanned Implementation list for actionable cards', 'Evaluated card readiness', 'Filtered by priority and clarity'],
            'metrics_keys': ['cards_scanned', 'cards_recommended', 'high_priority_count'],
            'next_steps': ['Review recommended cards', 'Assign developers to top 3 cards', 'Check due dates for urgent items']
        },
        'morning_backlog': {
            'actions_taken': ['Retrieved all Backlog cards', 'Applied triage criteria', 'Moved approved cards to To-Do'],
            'metrics_keys': ['backlog_count', 'approved_count', 'dropped_count', 'clarification_needed'],
            'next_steps': ['Review newly approved To-Do items', 'Respond to clarification requests', 'Update sprint planning board']
        },
        'expense_backup': {
            'actions_taken': ['Exported Notion expenses database', 'Created timestamped backup', 'Verified file integrity'],
            'metrics_keys': ['expense_count', 'total_amount', 'backup_file_size_kb'],
            'next_steps': ['Verify backup file accessibility', 'Review expense patterns if anomalies detected']
        },
        'health_check': {
            'actions_taken': ['Executed health check monitors', 'Analyzed system metrics', 'Compared against thresholds'],
            'metrics_keys': ['checks_run', 'checks_passed', 'checks_failed', 'critical_issues'],
            'next_steps': ['Address any failed checks', 'Review P0/P1 issues immediately', 'Update monitoring thresholds if needed']
        },
        'developer_sprint': {
            'actions_taken': ['Implemented feature code', 'Wrote automated tests', 'Committed to GitHub repository'],
            'metrics_keys': ['files_created', 'lines_of_code', 'tests_written', 'commit_sha'],
            'next_steps': ['Run test suite locally', 'Create pull request for review', 'Update Trello card with implementation summary']
        }
    }
    
    def __init__(self):
        self.report_log_path = Path('logs/outcome_reports.jsonl')
        self.report_log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def build_report(
        self,
        workflow_type: str,
        raw_results: Dict[str, Any],
        actions_taken: Optional[List[str]] = None,
        changes_made: Optional[List[str]] = None,
        next_steps: Optional[List[str]] = None
    ) -> OutcomeReport:
        """Build structured outcome report from workflow results.
        
        Args:
            workflow_type: Type of workflow (e.g., 'board_monitor', 'expense_backup')
            raw_results: Raw results dictionary containing metrics and outcomes
            actions_taken: Override default actions (optional)
            changes_made: List of system changes (optional)
            next_steps: Override default next steps (optional)
            
        Returns:
            OutcomeReport with all fields populated
        """
        template = self.WORKFLOW_TEMPLATES.get(workflow_type, {})
        
        # Use provided actions or fall back to template
        final_actions = actions_taken or template.get('actions_taken', ['Executed workflow'])
        
        # Extract changes from raw results
        final_changes = changes_made or self._extract_changes(raw_results)
        
        # Extract metrics based on template keys
        metrics_keys = template.get('metrics_keys', [])
        final_metrics = self._extract_metrics(raw_results, metrics_keys)
        
        # Use provided next steps or fall back to template
        final_next_steps = next_steps or template.get('next_steps', ['Review results'])
        
        return OutcomeReport(
            workflow_type=workflow_type,
            actions_taken=final_actions,
            changes_made=final_changes,
            metrics=final_metrics,
            next_steps=final_next_steps,
            timestamp=datetime.utcnow().isoformat() + 'Z'
        )
    
    def _extract_changes(self, raw_results: Dict[str, Any]) -> List[str]:
        """Extract change statements from raw results."""
        changes = []
        
        # Check for common change indicators
        if 'created' in raw_results:
            for item_type, items in raw_results['created'].items():
                if isinstance(items, list):
                    changes.append(f"Created {len(items)} {item_type}")
                else:
                    changes.append(f"Created {item_type}: {items}")
        
        if 'updated' in raw_results:
            for item_type, items in raw_results['updated'].items():
                if isinstance(items, list):
                    changes.append(f"Updated {len(items)} {item_type}")
                else:
                    changes.append(f"Updated {item_type}: {items}")
        
        if 'moved' in raw_results:
            changes.append(f"Moved {raw_results['moved']} items")
        
        if 'deleted' in raw_results:
            changes.append(f"Deleted {raw_results['deleted']} items")
        
        return changes or ['No system changes']
    
    def _extract_metrics(self, raw_results: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
        """Extract metrics from raw results based on template keys."""
        metrics = {}
        
        # Extract known keys
        for key in keys:
            if key in raw_results:
                metrics[key] = raw_results[key]
        
        # Always include duration if present
        if 'duration_seconds' in raw_results:
            metrics['duration_seconds'] = raw_results['duration_seconds']
        
        # Include any numeric metrics not already captured
        for key, value in raw_results.items():
            if isinstance(value, (int, float)) and key not in metrics:
                metrics[key] = value
        
        return metrics
    
    def format_as_markdown(self, report: OutcomeReport) -> str:
        """Format outcome report as human-readable markdown.
        
        Returns:
            Markdown string with clear sections for actions, changes, metrics, and next steps
        """
        lines = [
            f"# Workflow Outcome: {report.workflow_type.replace('_', ' ').title()}",
            f"*Completed at {report.timestamp}*",
            "",
            "## Actions Taken"
        ]
        
        for action in report.actions_taken:
            lines.append(f"- {action}")
        
        lines.extend(["", "## Changes Made"])
        for change in report.changes_made:
            lines.append(f"- {change}")
        
        if report.metrics:
            lines.extend(["", "## Metrics"])
            for key, value in report.metrics.items():
                formatted_key = key.replace('_', ' ').title()
                lines.append(f"- **{formatted_key}**: {value}")
        
        lines.extend(["", "## Next Steps"])
        for i, step in enumerate(report.next_steps, 1):
            lines.append(f"{i}. {step}")
        
        return "\n".join(lines)
    
    def format_as_trello_comment(self, report: OutcomeReport) -> str:
        """Format outcome report as Trello card comment.
        
        Returns:
            Formatted string suitable for Trello comment with emoji and concise structure
        """
        lines = [
            f"**Workflow Complete: {report.workflow_type.replace('_', ' ').title()}**",
            f"_Timestamp: {report.timestamp}_",
            "",
            "**Actions:**"
        ]
        
        for action in report.actions_taken[:3]:  # Limit to top 3 for brevity
            lines.append(f"• {action}")
        
        lines.append("")
        lines.append("**Changes:**")
        for change in report.changes_made[:3]:
            lines.append(f"• {change}")
        
        if report.metrics:
            lines.append("")
            lines.append("**Key Metrics:**")
            # Show top 4 metrics
            for key, value in list(report.metrics.items())[:4]:
                formatted_key = key.replace('_', ' ').title()
                lines.append(f"• {formatted_key}: `{value}`")
        
        lines.append("")
        lines.append("**Next Steps:**")
        for step in report.next_steps[:3]:
            lines.append(f"→ {step}")
        
        return "\n".join(lines)
    
    def save_report(self, report: OutcomeReport, path: Optional[str] = None) -> str:
        """Save outcome report to JSONL log file.
        
        Args:
            report: OutcomeReport to save
            path: Optional custom path (defaults to logs/outcome_reports.jsonl)
            
        Returns:
            Path where report was saved
        """
        target_path = Path(path) if path else self.report_log_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Append as JSONL
        with open(target_path, 'a') as f:
            f.write(json.dumps(report.to_dict()) + '\n')
        
        return str(target_path)
    
    def load_reports(self, path: Optional[str] = None, limit: Optional[int] = None) -> List[OutcomeReport]:
        """Load outcome reports from JSONL log file.
        
        Args:
            path: Optional custom path (defaults to logs/outcome_reports.jsonl)
            limit: Maximum number of reports to load (most recent first)
            
        Returns:
            List of OutcomeReport objects
        """
        target_path = Path(path) if path else self.report_log_path
        
        if not target_path.exists():
            return []
        
        reports = []
        with open(target_path, 'r') as f:
            lines = f.readlines()
            if limit:
                lines = lines[-limit:]  # Get most recent
            
            for line in lines:
                data = json.loads(line)
                reports.append(OutcomeReport(**data))
        
        return reports

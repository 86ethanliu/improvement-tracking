"""Summary Registry for tracking and analyzing workflow summary adoption.

Provides centralized storage and analysis of WorkflowSummary instances
to measure adoption rates and identify trends across agent workflows.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from .structured_summary import WorkflowSummary, SummaryFormatter


class SummaryRegistry:
    """Central registry for storing and analyzing workflow summaries.
    
    Stores summaries in JSONL format (one JSON object per line) for efficient
    append operations and streaming reads.
    
    Attributes:
        registry_path: Path to the JSONL file storing summaries
    """
    
    def __init__(self, registry_path: str = 'logs/workflow_summaries.jsonl'):
        """Initialize registry with storage path.
        
        Args:
            registry_path: Path to JSONL file (default: logs/workflow_summaries.jsonl)
        """
        self.registry_path = Path(registry_path)
        self._ensure_registry_exists()
    
    def _ensure_registry_exists(self) -> None:
        """Create registry file and parent directories if they don't exist."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.registry_path.exists():
            self.registry_path.touch()
    
    def save(self, summary: WorkflowSummary, path: Optional[str] = None) -> None:
        """Save a workflow summary to the registry.
        
        Args:
            summary: WorkflowSummary instance to save
            path: Optional override path (defaults to self.registry_path)
        
        Raises:
            IOError: If unable to write to registry file
        """
        target_path = Path(path) if path else self.registry_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to JSON-serializable dict
        summary_dict = SummaryFormatter.to_json(summary)
        
        # Append to JSONL file
        try:
            with open(target_path, 'a', encoding='utf-8') as f:
                json.dump(summary_dict, f, ensure_ascii=False)
                f.write('\n')
        except IOError as e:
            raise IOError(f"Failed to save summary to {target_path}: {e}")
    
    def load_recent(self, n: int = 10, path: Optional[str] = None) -> List[WorkflowSummary]:
        """Load the n most recent summaries from the registry.
        
        Args:
            n: Number of recent summaries to load (default: 10)
            path: Optional override path (defaults to self.registry_path)
        
        Returns:
            List of WorkflowSummary instances, newest first
        
        Raises:
            IOError: If unable to read from registry file
        """
        target_path = Path(path) if path else self.registry_path
        
        if not target_path.exists():
            return []
        
        summaries = []
        
        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Take last n lines and reverse (newest first)
            for line in reversed(lines[-n:]):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    summary = self._dict_to_summary(data)
                    summaries.append(summary)
                except json.JSONDecodeError:
                    # Skip malformed lines
                    continue
        
        except IOError as e:
            raise IOError(f"Failed to load summaries from {target_path}: {e}")
        
        return summaries
    
    def load_all(self, path: Optional[str] = None) -> List[WorkflowSummary]:
        """Load all summaries from the registry.
        
        Args:
            path: Optional override path (defaults to self.registry_path)
        
        Returns:
            List of all WorkflowSummary instances
        """
        target_path = Path(path) if path else self.registry_path
        
        if not target_path.exists():
            return []
        
        summaries = []
        
        with open(target_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    summary = self._dict_to_summary(data)
                    summaries.append(summary)
                except json.JSONDecodeError:
                    continue
        
        return summaries
    
    def _dict_to_summary(self, data: Dict[str, Any]) -> WorkflowSummary:
        """Convert JSON dict back to WorkflowSummary instance.
        
        Args:
            data: Dictionary from JSON deserialization
        
        Returns:
            Reconstructed WorkflowSummary instance
        """
        return WorkflowSummary(
            workflow_name=data['workflow_name'],
            started_at=datetime.fromisoformat(data['started_at']),
            completed_at=datetime.fromisoformat(data['completed_at']),
            steps_total=data['steps_total'],
            steps_completed=data['steps_completed'],
            steps_failed=data['steps_failed'],
            key_outcomes=data.get('key_outcomes', []),
            metrics=data.get('metrics', {}),
            errors=data.get('errors', []),
            next_actions=data.get('next_actions', []),
            status=data.get('status', 'completed')
        )
    
    def get_adoption_rate(self, 
                          total_workflows: Optional[int] = None,
                          path: Optional[str] = None) -> float:
        """Calculate structured summary adoption rate.
        
        Args:
            total_workflows: Total number of workflows run (if known).
                           If None, uses count of summaries in registry.
            path: Optional override path (defaults to self.registry_path)
        
        Returns:
            Adoption rate as percentage (0-100)
        
        Note:
            If total_workflows is provided, adoption_rate = (summaries / total) * 100
            If not provided, assumes 100% adoption (all workflows in registry)
        """
        summaries = self.load_all(path=path)
        summary_count = len(summaries)
        
        if total_workflows is None:
            # If we don't know total workflows, assume registry is complete
            return 100.0 if summary_count > 0 else 0.0
        
        if total_workflows == 0:
            return 0.0
        
        return (summary_count / total_workflows) * 100
    
    def get_stats_by_workflow(self, 
                              workflow_name: str,
                              path: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics for a specific workflow type.
        
        Args:
            workflow_name: Name of the workflow to analyze
            path: Optional override path (defaults to self.registry_path)
        
        Returns:
            Dictionary with statistics:
            - count: Number of executions
            - avg_duration_seconds: Average execution time
            - avg_success_rate: Average success rate
            - total_steps: Total steps across all executions
            - most_recent: ISO timestamp of most recent execution
        """
        summaries = self.load_all(path=path)
        
        # Filter by workflow name
        matching = [s for s in summaries if s.workflow_name == workflow_name]
        
        if not matching:
            return {
                'count': 0,
                'avg_duration_seconds': 0.0,
                'avg_success_rate': 0.0,
                'total_steps': 0,
                'most_recent': None
            }
        
        total_duration = sum(s.duration_seconds for s in matching)
        total_success_rate = sum(s.success_rate for s in matching)
        total_steps = sum(s.steps_total for s in matching)
        most_recent = max(s.completed_at for s in matching)
        
        return {
            'count': len(matching),
            'avg_duration_seconds': total_duration / len(matching),
            'avg_success_rate': total_success_rate / len(matching),
            'total_steps': total_steps,
            'most_recent': most_recent.isoformat()
        }
    
    def get_all_workflow_names(self, path: Optional[str] = None) -> List[str]:
        """Get list of unique workflow names in registry.
        
        Args:
            path: Optional override path (defaults to self.registry_path)
        
        Returns:
            Sorted list of unique workflow names
        """
        summaries = self.load_all(path=path)
        names = set(s.workflow_name for s in summaries)
        return sorted(names)
    
    def get_summary_report(self, path: Optional[str] = None) -> str:
        """Generate a comprehensive summary report of all workflows.
        
        Args:
            path: Optional override path (defaults to self.registry_path)
        
        Returns:
            Formatted markdown report string
        """
        summaries = self.load_all(path=path)
        
        if not summaries:
            return "## Workflow Summary Report\n\nNo summaries recorded yet."
        
        workflow_names = self.get_all_workflow_names(path=path)
        
        lines = [
            "## Workflow Summary Report",
            f"**Total Summaries:** {len(summaries)}",
            f"**Unique Workflows:** {len(workflow_names)}",
            "",
            "### Workflows by Execution Count"
        ]
        
        # Count executions per workflow
        workflow_counts = {}
        for name in workflow_names:
            stats = self.get_stats_by_workflow(name, path=path)
            workflow_counts[name] = stats
        
        # Sort by count descending
        sorted_workflows = sorted(
            workflow_counts.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )
        
        for name, stats in sorted_workflows:
            lines.append(f"- **{name}**: {stats['count']} executions, "
                        f"avg {stats['avg_duration_seconds']:.1f}s, "
                        f"{stats['avg_success_rate']:.1f}% success")
        
        return "\n".join(lines)

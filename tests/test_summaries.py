"""Pytest test suite for structured summary system.

Tests WorkflowSummary, StructuredSummaryBuilder, SummaryFormatter,
and SummaryRegistry to ensure 80%+ adoption target is achievable.
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.summaries.structured_summary import (
    WorkflowSummary,
    StructuredSummaryBuilder,
    SummaryFormatter
)
from scripts.summaries.summary_registry import SummaryRegistry


class TestStructuredSummaryBuilder:
    """Test suite for StructuredSummaryBuilder fluent interface."""
    
    def test_builder_fluent_interface(self):
        """Test that builder methods can be chained fluently."""
        builder = StructuredSummaryBuilder("Test Workflow")
        
        # Chain multiple method calls
        summary = (builder
                   .start()
                   .add_step_result("Step 1", True, "Success")
                   .add_step_result("Step 2", True, "Also success")
                   .add_step_result("Step 3", True, "Done")
                   .add_outcome("Processed 3 items")
                   .add_metric("items_processed", 3)
                   .add_next_action("Review results")
                   .build())
        
        assert summary.workflow_name == "Test Workflow"
        assert summary.steps_total == 3
        assert summary.steps_completed == 3
        assert summary.steps_failed == 0
        assert summary.status == "completed"
        assert len(summary.key_outcomes) == 1
        assert summary.metrics["items_processed"] == 3
        assert len(summary.next_actions) == 1
    
    def test_build_with_failures(self):
        """Test builder correctly handles mixed success/failure steps."""
        builder = StructuredSummaryBuilder("Mixed Results Workflow")
        
        summary = (builder
                   .start()
                   .add_step_result("Step 1", True)
                   .add_step_result("Step 2", False, "Network timeout")
                   .add_step_result("Step 3", True)
                   .add_step_result("Step 4", False, "API rate limit")
                   .build())
        
        assert summary.steps_total == 4
        assert summary.steps_completed == 2
        assert summary.steps_failed == 2
        assert summary.status == "partial"
        assert summary.success_rate == 50.0
        assert len(summary.errors) == 2
        assert "Network timeout" in summary.errors[0]
        assert "API rate limit" in summary.errors[1]
    
    def test_build_without_start_raises_error(self):
        """Test that build() raises ValueError if start() not called."""
        builder = StructuredSummaryBuilder("No Start Workflow")
        
        with pytest.raises(ValueError, match="Must call start\\(\\) before build\\(\\)"):
            builder.add_step_result("Step 1", True).build()
    
    def test_all_failed_status(self):
        """Test that all failed steps result in 'failed' status."""
        builder = StructuredSummaryBuilder("Failed Workflow")
        
        summary = (builder
                   .start()
                   .add_step_result("Step 1", False, "Error 1")
                   .add_step_result("Step 2", False, "Error 2")
                   .build())
        
        assert summary.status == "failed"
        assert summary.steps_completed == 0
        assert summary.success_rate == 0.0


class TestSummaryFormatter:
    """Test suite for SummaryFormatter output formats."""
    
    @pytest.fixture
    def sample_summary(self):
        """Create a sample WorkflowSummary for testing."""
        start = datetime(2026, 3, 9, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 9, 10, 4, 32, tzinfo=timezone.utc)
        
        return WorkflowSummary(
            workflow_name="Backlog Triage",
            started_at=start,
            completed_at=end,
            steps_total=8,
            steps_completed=8,
            steps_failed=0,
            key_outcomes=[
                "Triaged 3 backlog cards → 2 To-Do, 1 Dropped",
                "Moved 1 card to Check-in",
                "Posted 12 staleness comments"
            ],
            metrics={
                "cards_processed": 15,
                "success_rate": 100
            },
            errors=[],
            next_actions=[
                "Review 2 cards in Check-in",
                "Respond to SM feedback on Card #84"
            ],
            status="completed"
        )
    
    def test_formatter_to_markdown_has_required_sections(self, sample_summary):
        """Test that Markdown output contains all required sections."""
        markdown = SummaryFormatter.to_markdown(sample_summary)
        
        # Check for required sections
        assert "## Backlog Triage Summary" in markdown
        assert "**Status:**" in markdown
        assert "**Duration:**" in markdown
        assert "### What Happened" in markdown
        assert "### Metrics" in markdown
        assert "### Next Actions" in markdown
        
        # Check specific content
        assert "8/8 steps" in markdown
        assert "4m 32s" in markdown
        assert "Triaged 3 backlog cards" in markdown
        assert "Cards Processed: 15" in markdown
        assert "Review 2 cards in Check-in" in markdown
    
    def test_formatter_to_trello_comment(self, sample_summary):
        """Test Trello comment formatting."""
        trello = SummaryFormatter.to_trello_comment(sample_summary)
        
        # Check Trello-specific formatting
        assert "**Backlog Triage**" in trello
        assert "Steps: 8/8" in trello
        assert "**Outcomes:**" in trello
        assert "**Metrics:**" in trello
        assert "**Next Steps:**" in trello
        assert "→" in trello  # Next action arrow
    
    def test_formatter_to_telegram_is_concise(self, sample_summary):
        """Test that Telegram format is under 300 characters."""
        telegram = SummaryFormatter.to_telegram(sample_summary)
        
        assert len(telegram) <= 300, f"Telegram message too long: {len(telegram)} chars"
        assert "Backlog Triage" in telegram
        assert "8/8 steps" in telegram
        assert "4m 32s" in telegram
    
    def test_formatter_to_json_serializable(self, sample_summary):
        """Test JSON formatter produces valid JSON-serializable output."""
        json_dict = SummaryFormatter.to_json(sample_summary)
        
        # Should be serializable
        json_str = json.dumps(json_dict)
        assert len(json_str) > 0
        
        # Check required fields
        assert json_dict["workflow_name"] == "Backlog Triage"
        assert json_dict["steps_total"] == 8
        assert json_dict["steps_completed"] == 8
        assert json_dict["status"] == "completed"
        assert isinstance(json_dict["started_at"], str)  # ISO format
        assert isinstance(json_dict["completed_at"], str)


class TestSummaryRegistry:
    """Test suite for SummaryRegistry persistence and analysis."""
    
    @pytest.fixture
    def temp_registry(self):
        """Create a temporary registry file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl') as f:
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    @pytest.fixture
    def sample_summary(self):
        """Create a sample summary for testing."""
        start = datetime.now(timezone.utc) - timedelta(minutes=5)
        end = datetime.now(timezone.utc)
        
        return WorkflowSummary(
            workflow_name="Test Workflow",
            started_at=start,
            completed_at=end,
            steps_total=5,
            steps_completed=5,
            steps_failed=0,
            key_outcomes=["Completed all tasks"],
            metrics={"items": 10},
            errors=[],
            next_actions=["Continue monitoring"],
            status="completed"
        )
    
    def test_summary_registry_save_and_load(self, temp_registry, sample_summary):
        """Test saving and loading summaries from registry."""
        registry = SummaryRegistry(registry_path=temp_registry)
        
        # Save summary
        registry.save(sample_summary)
        
        # Load and verify
        loaded = registry.load_recent(n=1)
        assert len(loaded) == 1
        assert loaded[0].workflow_name == "Test Workflow"
        assert loaded[0].steps_total == 5
        assert loaded[0].status == "completed"
    
    def test_registry_load_recent_returns_newest_first(self, temp_registry):
        """Test that load_recent returns summaries in reverse chronological order."""
        registry = SummaryRegistry(registry_path=temp_registry)
        
        # Create 3 summaries with different timestamps
        for i in range(3):
            start = datetime.now(timezone.utc) - timedelta(minutes=10-i)
            end = datetime.now(timezone.utc) - timedelta(minutes=9-i)
            summary = WorkflowSummary(
                workflow_name=f"Workflow {i}",
                started_at=start,
                completed_at=end,
                steps_total=1,
                steps_completed=1,
                steps_failed=0,
                status="completed"
            )
            registry.save(summary)
        
        # Load recent 2
        loaded = registry.load_recent(n=2)
        assert len(loaded) == 2
        assert loaded[0].workflow_name == "Workflow 2"  # Most recent
        assert loaded[1].workflow_name == "Workflow 1"
    
    def test_get_adoption_rate(self, temp_registry, sample_summary):
        """Test adoption rate calculation."""
        registry = SummaryRegistry(registry_path=temp_registry)
        
        # Save 8 summaries
        for i in range(8):
            registry.save(sample_summary)
        
        # Test with known total
        adoption_rate = registry.get_adoption_rate(total_workflows=10)
        assert adoption_rate == 80.0  # 8/10 = 80%
        
        # Test without total (assumes 100%)
        adoption_rate_default = registry.get_adoption_rate()
        assert adoption_rate_default == 100.0
    
    def test_get_stats_by_workflow(self, temp_registry):
        """Test workflow-specific statistics."""
        registry = SummaryRegistry(registry_path=temp_registry)
        
        # Create multiple executions of same workflow
        for i in range(3):
            start = datetime.now(timezone.utc) - timedelta(seconds=30)
            end = datetime.now(timezone.utc)
            summary = WorkflowSummary(
                workflow_name="Daily Backup",
                started_at=start,
                completed_at=end,
                steps_total=4,
                steps_completed=4,
                steps_failed=0,
                status="completed"
            )
            registry.save(summary)
        
        stats = registry.get_stats_by_workflow("Daily Backup")
        
        assert stats['count'] == 3
        assert stats['avg_success_rate'] == 100.0
        assert stats['total_steps'] == 12  # 4 steps × 3 executions
        assert stats['most_recent'] is not None


class TestWorkflowSummary:
    """Test suite for WorkflowSummary dataclass properties."""
    
    def test_duration_formatted_seconds(self):
        """Test duration formatting for short durations."""
        start = datetime(2026, 3, 9, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 9, 10, 0, 45, tzinfo=timezone.utc)
        
        summary = WorkflowSummary(
            workflow_name="Quick Task",
            started_at=start,
            completed_at=end,
            steps_total=1,
            steps_completed=1,
            steps_failed=0,
            status="completed"
        )
        
        assert summary.duration_formatted == "45s"
    
    def test_duration_formatted_minutes(self):
        """Test duration formatting with minutes."""
        start = datetime(2026, 3, 9, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 9, 10, 4, 32, tzinfo=timezone.utc)
        
        summary = WorkflowSummary(
            workflow_name="Medium Task",
            started_at=start,
            completed_at=end,
            steps_total=1,
            steps_completed=1,
            steps_failed=0,
            status="completed"
        )
        
        assert summary.duration_formatted == "4m 32s"
    
    def test_duration_formatted_hours(self):
        """Test duration formatting with hours."""
        start = datetime(2026, 3, 9, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 9, 12, 15, 30, tzinfo=timezone.utc)
        
        summary = WorkflowSummary(
            workflow_name="Long Task",
            started_at=start,
            completed_at=end,
            steps_total=1,
            steps_completed=1,
            steps_failed=0,
            status="completed"
        )
        
        assert summary.duration_formatted == "2h 15m 30s"
    
    def test_success_rate_calculation(self):
        """Test success rate percentage calculation."""
        summary = WorkflowSummary(
            workflow_name="Partial Success",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
            steps_total=10,
            steps_completed=7,
            steps_failed=3,
            status="partial"
        )
        
        assert summary.success_rate == 70.0

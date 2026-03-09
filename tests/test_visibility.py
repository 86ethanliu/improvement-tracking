"""Test suite for outcome visibility system (Card #80).

Tests the OutcomeReporter and VisibilityScorer modules to ensure
workflow completion messages meet the 8.0/10 visibility target.
"""

import pytest
import json
import sys
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts' / 'visibility'))

from outcome_reporter import OutcomeReporter, OutcomeReport
from visibility_scorer import VisibilityScorer


class TestOutcomeReporter:
    """Test cases for OutcomeReporter class."""
    
    def test_outcome_reporter_board_monitor(self):
        """Test full report generation for board_monitor workflow."""
        reporter = OutcomeReporter()
        
        raw_results = {
            'cards_scanned': 39,
            'cards_recommended': 5,
            'high_priority_count': 3,
            'duration_seconds': 4.2
        }
        
        report = reporter.build_report('board_monitor', raw_results)
        
        assert report.workflow_type == 'board_monitor'
        assert len(report.actions_taken) >= 1
        assert len(report.next_steps) >= 1
        assert report.metrics['cards_scanned'] == 39
        assert report.metrics['cards_recommended'] == 5
        assert report.metrics['high_priority_count'] == 3
        assert 'timestamp' in report.timestamp
    
    def test_format_as_markdown_contains_required_sections(self):
        """Test that markdown format includes all required sections."""
        reporter = OutcomeReporter()
        
        report = OutcomeReport(
            workflow_type='test_workflow',
            actions_taken=['Action 1', 'Action 2'],
            changes_made=['Change 1', 'Change 2'],
            metrics={'count': 5, 'duration': 2.3},
            next_steps=['Step 1', 'Step 2'],
            timestamp='2026-03-10T00:00:00Z'
        )
        
        markdown = reporter.format_as_markdown(report)
        
        # Check for required sections
        assert '# Workflow Outcome:' in markdown
        assert '## Actions Taken' in markdown
        assert '## Changes Made' in markdown
        assert '## Metrics' in markdown
        assert '## Next Steps' in markdown
        
        # Check content appears
        assert 'Action 1' in markdown
        assert 'Change 1' in markdown
        assert '**Count**: 5' in markdown
        assert 'Step 1' in markdown
    
    def test_format_as_trello_comment_concise(self):
        """Test Trello format is concise and well-structured."""
        reporter = OutcomeReporter()
        
        report = OutcomeReport(
            workflow_type='developer_sprint',
            actions_taken=['Implemented code', 'Wrote tests', 'Committed changes'],
            changes_made=['Created 3 files', 'Added 450 lines'],
            metrics={'files_created': 3, 'tests_written': 8, 'lines_of_code': 450},
            next_steps=['Run tests', 'Create PR', 'Update card'],
            timestamp='2026-03-10T00:00:00Z'
        )
        
        trello_comment = reporter.format_as_trello_comment(report)
        
        # Check structure
        assert '**Workflow Complete:' in trello_comment
        assert '**Actions:**' in trello_comment
        assert '**Changes:**' in trello_comment
        assert '**Key Metrics:**' in trello_comment
        assert '**Next Steps:**' in trello_comment
        
        # Check content
        assert 'Implemented code' in trello_comment
        assert 'Created 3 files' in trello_comment
        assert 'Run tests' in trello_comment
    
    def test_save_and_load_report(self, tmp_path):
        """Test roundtrip save and load of reports to JSONL."""
        reporter = OutcomeReporter()
        test_file = tmp_path / 'test_reports.jsonl'
        
        # Create and save report
        report1 = OutcomeReport(
            workflow_type='test',
            actions_taken=['Action A'],
            changes_made=['Change A'],
            metrics={'count': 10},
            next_steps=['Next A'],
            timestamp='2026-03-10T00:00:00Z'
        )
        
        reporter.save_report(report1, path=str(test_file))
        
        # Save another report
        report2 = OutcomeReport(
            workflow_type='test2',
            actions_taken=['Action B'],
            changes_made=['Change B'],
            metrics={'count': 20},
            next_steps=['Next B'],
            timestamp='2026-03-10T01:00:00Z'
        )
        
        reporter.save_report(report2, path=str(test_file))
        
        # Load reports
        loaded = reporter.load_reports(path=str(test_file))
        
        assert len(loaded) == 2
        assert loaded[0].workflow_type == 'test'
        assert loaded[0].metrics['count'] == 10
        assert loaded[1].workflow_type == 'test2'
        assert loaded[1].metrics['count'] == 20
    
    def test_extract_changes_from_raw_results(self):
        """Test automatic extraction of changes from raw results."""
        reporter = OutcomeReporter()
        
        raw_results = {
            'created': {
                'cards': ['card1', 'card2', 'card3'],
                'files': ['file1']
            },
            'updated': {
                'status': 'complete'
            },
            'moved': 5,
            'deleted': 2
        }
        
        report = reporter.build_report('custom', raw_results)
        
        assert 'Created 3 cards' in report.changes_made
        assert 'Created 1 files' in report.changes_made
        assert 'Updated status: complete' in report.changes_made
        assert 'Moved 5 items' in report.changes_made
        assert 'Deleted 2 items' in report.changes_made


class TestVisibilityScorer:
    """Test cases for VisibilityScorer class."""
    
    def test_visibility_scorer_high_quality_response(self):
        """Test scoring of high-quality response (should score >= 8.0)."""
        scorer = VisibilityScorer()
        
        high_quality_response = """
## Actions Taken
- Scanned Implementation list for 39 cards
- Evaluated card readiness and priority
- Filtered by clarity and impact

## Changes Made
- Created 5 recommendation cards
- Updated 3 high-priority items
- Moved 2 cards to Review list

## Metrics
- Cards scanned: 39
- Cards recommended: 5
- High priority count: 3
- Duration: 4.2 seconds

## Before/After
Backlog visibility improved from 4.0/10 to 8.5/10

## Next Steps
1. Review recommended cards
2. Assign developers to top 3 cards
3. Check due dates for urgent items
"""
        
        score = scorer.score_response(high_quality_response)
        assert score >= 8.0, f"Expected score >= 8.0, got {score}"
        
        breakdown = scorer.get_score_breakdown(high_quality_response)
        assert breakdown['criteria_scores']['has_actions_section'] == 2.0
        assert breakdown['criteria_scores']['has_quantified_metrics'] == 2.0
        assert breakdown['criteria_scores']['has_next_steps'] == 2.0
        assert breakdown['criteria_scores']['has_before_after'] == 2.0
    
    def test_visibility_scorer_poor_response(self):
        """Test scoring of poor-quality response (should score <= 3.0)."""
        scorer = VisibilityScorer()
        
        poor_response = "Task completed successfully."
        
        score = scorer.score_response(poor_response)
        assert score <= 3.0, f"Expected score <= 3.0, got {score}"
        
        breakdown = scorer.get_score_breakdown(poor_response)
        assert breakdown['criteria_scores']['has_actions_section'] == 0.0
        assert breakdown['criteria_scores']['has_quantified_metrics'] == 0.0
        assert breakdown['criteria_scores']['has_next_steps'] == 0.0
    
    def test_scorer_detects_actions_section(self):
        """Test detection of actions section."""
        scorer = VisibilityScorer()
        
        with_actions = "## Actions Taken\n- Created file\n- Updated card"
        without_actions = "Everything is done."
        
        assert scorer._check_actions_section(with_actions) == 2.0
        assert scorer._check_actions_section(without_actions) == 0.0
    
    def test_scorer_detects_quantified_metrics(self):
        """Test detection of quantified metrics."""
        scorer = VisibilityScorer()
        
        with_metrics = "Created 3 files, updated 5 cards, 95% test coverage"
        without_metrics = "Created some files and updated cards"
        
        assert scorer._check_quantified_metrics(with_metrics) == 2.0
        assert scorer._check_quantified_metrics(without_metrics) == 0.0
    
    def test_scorer_detects_next_steps(self):
        """Test detection of next steps section."""
        scorer = VisibilityScorer()
        
        with_next_steps = "## Next Steps\n1. Review changes\n2. Deploy to prod"
        without_next_steps = "Task is complete."
        
        assert scorer._check_next_steps(with_next_steps) == 2.0
        assert scorer._check_next_steps(without_next_steps) == 0.0
    
    def test_scorer_detects_before_after(self):
        """Test detection of before/after comparison."""
        scorer = VisibilityScorer()
        
        with_comparison = "Score improved from 4.0 to 8.0"
        without_comparison = "Score is now good"
        
        assert scorer._check_before_after(with_comparison) == 2.0
        assert scorer._check_before_after(without_comparison) == 0.0
    
    def test_scorer_checks_appropriate_length(self):
        """Test length checking (100-500 words)."""
        scorer = VisibilityScorer()
        
        # Too short (< 100 words)
        short_text = "Task done."
        assert scorer._check_appropriate_length(short_text) == 0.0
        
        # Appropriate length (100-500 words)
        good_text = " ".join(["word"] * 200)
        assert scorer._check_appropriate_length(good_text) == 1.0
        
        # Too long (> 800 words)
        long_text = " ".join(["word"] * 1000)
        assert scorer._check_appropriate_length(long_text) == 0.0
    
    def test_scorer_checks_clear_formatting(self):
        """Test formatting quality check."""
        scorer = VisibilityScorer()
        
        well_formatted = """## Section 1
- Point A
- Point B

## Section 2
- Point C
"""
        poorly_formatted = "Section 1 Point A Point B Section 2 Point C"
        
        assert scorer._check_clear_formatting(well_formatted) == 1.0
        assert scorer._check_clear_formatting(poorly_formatted) == 0.0
    
    def test_get_improvement_suggestions(self):
        """Test generation of improvement suggestions."""
        scorer = VisibilityScorer()
        
        poor_response = "Task completed."
        suggestions = scorer.get_improvement_suggestions(poor_response)
        
        # Should get multiple suggestions
        assert len(suggestions) >= 4
        assert any('Actions Taken' in s for s in suggestions)
        assert any('metrics' in s for s in suggestions)
        assert any('Next Steps' in s for s in suggestions)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

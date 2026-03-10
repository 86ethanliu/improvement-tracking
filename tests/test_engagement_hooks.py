#!/usr/bin/env python3
"""
Unit Tests for Engagement Hooks Module

Validates all engagement patterns work correctly and produce expected output.

Author: Developer Improvement Implementation Agent
Created: 2026-03-10
Card: User Engagement - CRITICAL (Due: 2026-03-10)
"""

import unittest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.templates.engagement_hooks import (
    EngagementHooks,
    completion_question,
    binary_choice,
    confirm,
    feedback_request
)


class TestEngagementHooks(unittest.TestCase):
    """Test suite for EngagementHooks class."""
    
    def setUp(self):
        """Initialize test fixtures."""
        self.hooks = EngagementHooks(enable_randomization=False)
    
    def test_completion_question_basic(self):
        """Test basic completion question formatting."""
        result = self.hooks.add_completion_question(
            "Task completed.",
            "the detailed logs"
        )
        
        self.assertIn("Task completed.", result)
        self.assertIn("Would you like to see the detailed logs?", result)
    
    def test_completion_question_multiline(self):
        """Test completion question preserves multiline messages."""
        result = self.hooks.add_completion_question(
            "Task completed.\nAll tests passed.",
            "code coverage report"
        )
        
        self.assertIn("Task completed.", result)
        self.assertIn("All tests passed.", result)
        self.assertIn("Would you like to see code coverage report?", result)
    
    def test_binary_choice_default_labels(self):
        """Test binary choice with default A/B labels."""
        result = self.hooks.add_binary_choice(
            "Choose next action:",
            "Continue implementation",
            "Wait for review"
        )
        
        self.assertIn("Choose next action:", result)
        self.assertIn("Option A: Continue implementation", result)
        self.assertIn("Option B: Wait for review", result)
        self.assertIn("Which would you prefer? (Reply A or B)", result)
    
    def test_binary_choice_custom_labels(self):
        """Test binary choice with custom labels."""
        result = self.hooks.add_binary_choice(
            "Choose priority:",
            "High priority task",
            "Low priority task",
            labels=("1", "2")
        )
        
        self.assertIn("Option 1: High priority task", result)
        self.assertIn("Option 2: Low priority task", result)
        self.assertIn("Which would you prefer? (Reply 1 or 2)", result)
    
    def test_confirmation_prompt_without_impact(self):
        """Test confirmation prompt without impact note."""
        result = self.hooks.add_confirmation_prompt(
            "delete all temporary files"
        )
        
        self.assertIn("Ready to delete all temporary files.", result)
        self.assertIn("Confirm: Should I proceed?", result)
        self.assertIn("(Reply YES to confirm)", result)
    
    def test_confirmation_prompt_with_impact(self):
        """Test confirmation prompt with impact note."""
        result = self.hooks.add_confirmation_prompt(
            "archive 15 completed cards",
            "This will move them out of the active board"
        )
        
        self.assertIn("Ready to archive 15 completed cards.", result)
        self.assertIn("This will move them out of the active board", result)
        self.assertIn("Confirm: Should I proceed?", result)
    
    def test_multi_choice_three_options(self):
        """Test multi-choice with three options."""
        result = self.hooks.add_multi_choice(
            "Select approach:",
            [
                "Quick fix",
                "Robust solution",
                "Research first"
            ]
        )
        
        self.assertIn("Select approach:", result)
        self.assertIn("1. Quick fix", result)
        self.assertIn("2. Robust solution", result)
        self.assertIn("3. Research first", result)
        self.assertIn("(Reply 1, 2 or 3)", result)
    
    def test_multi_choice_custom_prompt(self):
        """Test multi-choice with custom prompt."""
        result = self.hooks.add_multi_choice(
            "Available actions:",
            ["Action A", "Action B"],
            prompt="What should I do next?"
        )
        
        self.assertIn("What should I do next?", result)
    
    def test_feedback_request_without_focus(self):
        """Test feedback request without specific focus."""
        result = self.hooks.add_feedback_request(
            "Analysis complete."
        )
        
        self.assertIn("Analysis complete.", result)
        self.assertIn("Reply with any questions or feedback.", result)
    
    def test_feedback_request_with_focus(self):
        """Test feedback request with specific focus area."""
        result = self.hooks.add_feedback_request(
            "Self-reflection summary posted.",
            "the identified improvement patterns"
        )
        
        self.assertIn("Self-reflection summary posted.", result)
        self.assertIn("Reply with any questions or feedback on the identified improvement patterns.", result)
    
    def test_progress_check(self):
        """Test progress check formatting."""
        result = self.hooks.add_progress_check(
            "File Integrity Implementation",
            "Created atomic_file_ops.py with 20 tests",
            "add integrity verification module"
        )
        
        self.assertIn("Progress Update: File Integrity Implementation", result)
        self.assertIn("Completed: Created atomic_file_ops.py with 20 tests", result)
        self.assertIn("Should I proceed with add integrity verification module", result)
        self.assertIn("or would you like to review this first?", result)
    
    def test_convenience_function_completion_question(self):
        """Test completion_question convenience function."""
        result = completion_question("Done.", "details")
        self.assertIn("Done.", result)
        self.assertIn("Would you like to see details?", result)
    
    def test_convenience_function_binary_choice(self):
        """Test binary_choice convenience function."""
        result = binary_choice("Choose:", "Option 1", "Option 2")
        self.assertIn("Option A: Option 1", result)
        self.assertIn("Option B: Option 2", result)
    
    def test_convenience_function_confirm(self):
        """Test confirm convenience function."""
        result = confirm("proceed with deployment")
        self.assertIn("Ready to proceed with deployment.", result)
        self.assertIn("Confirm: Should I proceed?", result)
    
    def test_convenience_function_feedback_request(self):
        """Test feedback_request convenience function."""
        result = feedback_request("Task done.", "the approach used")
        self.assertIn("Task done.", result)
        self.assertIn("Reply with any questions or feedback on the approach used.", result)
    
    def test_randomization_disabled(self):
        """Test that randomization is disabled by default."""
        hooks = EngagementHooks(enable_randomization=False)
        result1 = hooks.add_completion_question("Test", "details")
        result2 = hooks.add_completion_question("Test", "details")
        
        # Should be identical when randomization disabled
        self.assertEqual(result1, result2)
    
    def test_empty_inputs_handled(self):
        """Test that empty strings don't break formatting."""
        result = self.hooks.add_completion_question("", "details")
        self.assertIn("Would you like to see details?", result)
    
    def test_special_characters_preserved(self):
        """Test that special characters are preserved in messages."""
        result = self.hooks.add_completion_question(
            "Task #42 complete! ✅",
            "the execution logs & metrics"
        )
        
        self.assertIn("Task #42 complete! ✅", result)
        self.assertIn("the execution logs & metrics", result)


class TestEngagementPatternsIntegration(unittest.TestCase):
    """Integration tests for real-world usage patterns."""
    
    def setUp(self):
        """Initialize test fixtures."""
        self.hooks = EngagementHooks()
    
    def test_workflow_completion_pattern(self):
        """Test typical workflow completion engagement."""
        message = self.hooks.add_completion_question(
            "Card #44 moved to Check-in. All tests passing.",
            "the full test results and code coverage report"
        )
        
        # Should be clear, actionable, and engaging
        self.assertTrue(len(message) > 50)  # Substantial message
        self.assertIn("?", message)  # Has question
        self.assertIn("Card #44", message)  # Preserves context
    
    def test_multi_step_workflow_pattern(self):
        """Test engagement for multi-step workflows."""
        message = self.hooks.add_progress_check(
            "User Engagement Implementation",
            "Created engagement_hooks.py with 6 patterns",
            "write unit tests"
        )
        
        self.assertIn("Progress Update:", message)
        self.assertIn("Completed:", message)
        self.assertIn("Should I proceed", message)
    
    def test_critical_action_pattern(self):
        """Test engagement for critical/destructive actions."""
        message = self.hooks.add_confirmation_prompt(
            "delete all cards in Done list",
            "This will permanently remove 23 cards"
        )
        
        self.assertIn("Ready to", message)
        self.assertIn("permanently remove 23 cards", message)
        self.assertIn("Confirm:", message)
        self.assertIn("YES", message)


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)

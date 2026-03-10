#!/usr/bin/env python3
"""
Engagement Hooks - User Interaction Templates

Provides reusable engagement patterns to improve user interaction rates
from 0/10 to 7/10 by adding strategic prompts to agent responses.

Usage:
    from scripts.templates.engagement_hooks import EngagementHooks
    
    # Add engagement to completion messages
    hooks = EngagementHooks()
    message = hooks.add_completion_question(
        base_message="Task completed successfully.",
        detail_offer="the detailed execution logs"
    )
    
Author: Developer Improvement Implementation Agent
Created: 2026-03-10
Card: User Engagement - CRITICAL (Due: 2026-03-10)
"""

from typing import List, Optional
import random


class EngagementHooks:
    """
    Provides engagement patterns for agent-user interactions.
    
    Implements three core strategies:
    1. Completion questions - Offer specific follow-up details
    2. Binary choices - Present clear A/B options
    3. Confirmation prompts - Request approval before major actions
    """
    
    def __init__(self, enable_randomization: bool = False):
        """
        Initialize engagement hooks.
        
        Args:
            enable_randomization: If True, randomly vary phrasing to test engagement
        """
        self.enable_randomization = enable_randomization
    
    def add_completion_question(self, base_message: str, detail_offer: str) -> str:
        """
        Add engagement question after completion message.
        
        Args:
            base_message: The main completion message
            detail_offer: What additional detail can be provided
            
        Returns:
            Enhanced message with engagement question
            
        Example:
            >>> hooks = EngagementHooks()
            >>> hooks.add_completion_question(
            ...     "Card #44 moved to Check-in.",
            ...     "the full test results and code coverage report"
            ... )
            'Card #44 moved to Check-in.\n\nWould you like to see the full test results and code coverage report?'
        """
        templates = [
            f"{base_message}\n\nWould you like to see {detail_offer}?",
            f"{base_message}\n\nShould I show you {detail_offer}?",
            f"{base_message}\n\nInterested in reviewing {detail_offer}?"
        ]
        
        if self.enable_randomization:
            return random.choice(templates)
        return templates[0]  # Use consistent default
    
    def add_binary_choice(self, 
                          base_message: str, 
                          option_a: str, 
                          option_b: str,
                          labels: tuple = ("A", "B")) -> str:
        """
        Present two clear options requiring user decision.
        
        Args:
            base_message: Context leading to the choice
            option_a: First option description
            option_b: Second option description
            labels: Labels for options (default: ("A", "B"))
            
        Returns:
            Message with binary choice prompt
            
        Example:
            >>> hooks = EngagementHooks()
            >>> hooks.add_binary_choice(
            ...     "Implementation complete. Next steps:",
            ...     "Move to Check-in immediately",
            ...     "Wait for your review first"
            ... )
            'Implementation complete. Next steps:\n\nOption A: Move to Check-in immediately\nOption B: Wait for your review first\n\nWhich would you prefer? (Reply A or B)'
        """
        label_a, label_b = labels
        return (
            f"{base_message}\n\n"
            f"Option {label_a}: {option_a}\n"
            f"Option {label_b}: {option_b}\n\n"
            f"Which would you prefer? (Reply {label_a} or {label_b})"
        )
    
    def add_confirmation_prompt(self, action_description: str, 
                               impact_note: Optional[str] = None) -> str:
        """
        Request confirmation before executing major action.
        
        Args:
            action_description: What action will be taken
            impact_note: Optional note about impact/scope
            
        Returns:
            Confirmation request message
            
        Example:
            >>> hooks = EngagementHooks()
            >>> hooks.add_confirmation_prompt(
            ...     "archive all Done cards older than 2 days",
            ...     "This will affect 12 cards"
            ... )
            'Ready to archive all Done cards older than 2 days.\nThis will affect 12 cards\n\nConfirm: Should I proceed? (Reply YES to confirm)'
        """
        message = f"Ready to {action_description}."
        if impact_note:
            message += f"\n{impact_note}"
        message += "\n\nConfirm: Should I proceed? (Reply YES to confirm)"
        return message
    
    def add_multi_choice(self, 
                        base_message: str, 
                        options: List[str],
                        prompt: str = "Which option would you prefer?") -> str:
        """
        Present multiple options (3+) for user selection.
        
        Args:
            base_message: Context for the choice
            options: List of option descriptions
            prompt: Custom prompt text
            
        Returns:
            Message with numbered options
            
        Example:
            >>> hooks = EngagementHooks()
            >>> hooks.add_multi_choice(
            ...     "Found 3 potential approaches:",
            ...     [
            ...         "Quick fix using existing utility",
            ...         "Robust solution with new module",
            ...         "Research best practices first"
            ...     ]
            ... )
            'Found 3 potential approaches:\n\n1. Quick fix using existing utility\n2. Robust solution with new module\n3. Research best practices first\n\nWhich option would you prefer? (Reply 1, 2, or 3)'
        """
        options_text = "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(options))
        option_numbers = ", ".join(str(i+1) for i in range(len(options)))
        
        return (
            f"{base_message}\n\n"
            f"{options_text}\n\n"
            f"{prompt} (Reply {option_numbers.replace(', ' + option_numbers.split(', ')[-1], ' or ' + option_numbers.split(', ')[-1])})"
        )
    
    def add_feedback_request(self, base_message: str, 
                            feedback_focus: Optional[str] = None) -> str:
        """
        Invite open-ended feedback from user.
        
        Args:
            base_message: The main message
            feedback_focus: Optional specific area to focus feedback on
            
        Returns:
            Message with feedback invitation
            
        Example:
            >>> hooks = EngagementHooks()
            >>> hooks.add_feedback_request(
            ...     "Daily self-reflection analysis complete.",
            ...     "the identified improvement areas"
            ... )
            'Daily self-reflection analysis complete.\n\nReply with any questions or feedback on the identified improvement areas.'
        """
        if feedback_focus:
            return f"{base_message}\n\nReply with any questions or feedback on {feedback_focus}."
        return f"{base_message}\n\nReply with any questions or feedback."
    
    def add_progress_check(self, task_name: str, 
                          progress_summary: str,
                          next_step: str) -> str:
        """
        Report progress and ask about direction.
        
        Args:
            task_name: Name of the task
            progress_summary: What has been completed
            next_step: Proposed next action
            
        Returns:
            Progress update with engagement question
            
        Example:
            >>> hooks = EngagementHooks()
            >>> hooks.add_progress_check(
            ...     "Error Recovery Implementation",
            ...     "Created error_resilience.py with retry logic",
            ...     "implement file_operations_safe.py"
            ... )
            'Progress Update: Error Recovery Implementation\n\nCompleted: Created error_resilience.py with retry logic\n\nShould I proceed with implement file_operations_safe.py, or would you like to review this first?'
        """
        return (
            f"Progress Update: {task_name}\n\n"
            f"Completed: {progress_summary}\n\n"
            f"Should I proceed with {next_step}, or would you like to review this first?"
        )


# Convenience functions for quick usage
def completion_question(message: str, detail: str) -> str:
    """Quick helper for completion questions."""
    return EngagementHooks().add_completion_question(message, detail)


def binary_choice(message: str, option_a: str, option_b: str) -> str:
    """Quick helper for binary choices."""
    return EngagementHooks().add_binary_choice(message, option_a, option_b)


def confirm(action: str, impact: Optional[str] = None) -> str:
    """Quick helper for confirmations."""
    return EngagementHooks().add_confirmation_prompt(action, impact)


def feedback_request(message: str, focus: Optional[str] = None) -> str:
    """Quick helper for feedback requests."""
    return EngagementHooks().add_feedback_request(message, focus)


if __name__ == "__main__":
    # Demo/test usage
    import doctest
    doctest.testmod()
    
    print("Engagement Hooks Examples:\n")
    
    hooks = EngagementHooks()
    
    print("1. Completion Question:")
    print(hooks.add_completion_question(
        "Card #44 moved to Check-in.",
        "the full test results and code coverage report"
    ))
    print()
    
    print("2. Binary Choice:")
    print(hooks.add_binary_choice(
        "Implementation complete. Next steps:",
        "Move to Check-in immediately",
        "Wait for your review first"
    ))
    print()
    
    print("3. Confirmation Prompt:")
    print(hooks.add_confirmation_prompt(
        "archive all Done cards older than 2 days",
        "This will affect 12 cards"
    ))
    print()
    
    print("4. Multi-Choice:")
    print(hooks.add_multi_choice(
        "Found 3 potential approaches:",
        [
            "Quick fix using existing utility",
            "Robust solution with new module",
            "Research best practices first"
        ]
    ))
    print()
    
    print("5. Progress Check:")
    print(hooks.add_progress_check(
        "Error Recovery Implementation",
        "Created error_resilience.py with retry logic",
        "implement file_operations_safe.py"
    ))

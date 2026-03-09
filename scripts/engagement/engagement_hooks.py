#!/usr/bin/env python3
"""
Engagement Hook Generator for Nebula Agent Workflows

Provides conversation-ending hooks that prompt user engagement.
Supports A/B/C testing across 8 workflow types.

Card #86: User Engagement 0/10 → 7/10
Author: Developer Improvement Implementation Agent
Date: 2026-03-10
"""

import random
from typing import Dict, List, Optional
from enum import Enum


class HookVariant(Enum):
    """Hook style variants for A/B/C testing."""
    A = "direct"  # Direct, simple questions
    B = "specific"  # Specific, detailed options
    C = "choice"  # Multiple choice format


class EngagementHookGenerator:
    """
    Generates contextual engagement hooks for Nebula workflows.
    
    Each workflow type has 3 variants (A/B/C) to test different
    engagement styles and measure user response rates.
    """
    
    # Template structure: {workflow_type: {variant: [templates]}}
    HOOK_TEMPLATES = {
        "board_monitor": {
            "A": [
                "Need anything else?",
                "Want me to check anything specific?",
                "Should I dive deeper into any of these cards?"
            ],
            "B": [
                "Want me to analyze the {count} cards that moved to {list_name} today?",
                "Should I pull the full details for card #{card_id} ({card_name})?",
                "Need me to check the comment history on the {label} labeled cards?"
            ],
            "C": [
                "What's next? (A) Analyze stuck cards, (B) Review recent comments, (C) Nothing for now",
                "Focus on: (1) Cards moved today, (2) Overdue items, (3) High-priority backlog",
                "Drill into (A) the 3 Check-in cards or (B) the 2 rejected items?"
            ]
        },
        
        "morning_backlog": {
            "A": [
                "Want to review the summary?",
                "Should I prioritize any specific cards?",
                "Need me to do anything else?"
            ],
            "B": [
                "Should I create GitHub issues for the {count} high-priority cards?",
                "Want me to notify the team about the {count} urgent items in Telegram?",
                "Need me to estimate effort for the top {count} backlog cards?"
            ],
            "C": [
                "Next action? (A) Triage new cards, (B) Update priorities, (C) Done for now",
                "What's most urgent? (1) Blocked items, (2) Due-this-week cards, (3) Technical debt",
                "Focus on: (A) P0 critical issues or (B) quick-win improvements?"
            ]
        },
        
        "expense_backup": {
            "A": [
                "Everything look correct?",
                "Need any changes?",
                "Want to see the details?"
            ],
            "B": [
                "Should I break down the ${total} total by category?",
                "Want me to compare this month's ${amount} vs last month?",
                "Need me to flag any expenses over ${threshold}?"
            ],
            "C": [
                "Review options: (A) Show category breakdown, (B) Monthly comparison, (C) All good",
                "What interests you? (1) Spending trends, (2) Budget alerts, (3) Nothing else",
                "Drill into (A) the {count} large expenses or (B) recurring patterns?"
            ]
        },
        
        "health_check": {
            "A": [
                "Want the full diagnostic report?",
                "Should I investigate further?",
                "Need me to fix anything?"
            ],
            "B": [
                "Should I debug the {count} failed health checks?",
                "Want me to restart the {service_name} trigger?",
                "Need me to analyze the error logs for {component}?"
            ],
            "C": [
                "Action needed? (A) Auto-fix errors, (B) Full diagnostic, (C) Monitor only",
                "Priority? (1) Critical failures, (2) Performance issues, (3) Warnings only",
                "Fix (A) the {count} trigger issues or (B) investigate API timeouts?"
            ]
        },
        
        "code_review": {
            "A": [
                "Should I review anything else?",
                "Want more details?",
                "Need me to check related PRs?"
            ],
            "B": [
                "Should I analyze the test coverage for this PR?",
                "Want me to check if this conflicts with PR #{pr_number}?",
                "Need me to review the {count} changed files in detail?"
            ],
            "C": [
                "Next step? (A) Approve PR, (B) Request changes, (C) Check dependencies",
                "Focus on: (1) Test coverage, (2) Performance impact, (3) Security concerns",
                "Review (A) the code quality or (B) the integration tests?"
            ]
        },
        
        "task_completion": {
            "A": [
                "All done?",
                "Anything else to wrap up?",
                "Ready to close this task?"
            ],
            "B": [
                "Should I document the {count} changes in the task summary?",
                "Want me to notify stakeholders about task #{task_id} completion?",
                "Need me to verify all {count} acceptance criteria are met?"
            ],
            "C": [
                "Close task? (A) Yes, all done, (B) Add follow-up items, (C) Need more work",
                "Document: (1) Implementation notes, (2) Testing results, (3) Nothing needed",
                "Finalize (A) with status report or (B) create follow-up tasks?"
            ]
        },
        
        "error_report": {
            "A": [
                "Should I investigate this?",
                "Want me to try fixing it?",
                "Need the full stack trace?"
            ],
            "B": [
                "Should I check the logs for similar errors in the past {hours} hours?",
                "Want me to create a GitHub issue for this {error_type} error?",
                "Need me to restart the {component} service?"
            ],
            "C": [
                "Response? (A) Auto-fix, (B) Create ticket, (C) Monitor for now",
                "Priority? (1) Immediate fix, (2) Debug first, (3) Can wait",
                "Handle as (A) critical incident or (B) track for later?"
            ]
        },
        
        "daily_summary": {
            "A": [
                "Want more details?",
                "Should I break down any section?",
                "Need tomorrow's plan?"
            ],
            "B": [
                "Should I expand on the {count} completed tasks?",
                "Want me to prepare tomorrow's priority list?",
                "Need me to analyze today's {metric} performance?"
            ],
            "C": [
                "Deep dive? (A) Today's wins, (B) Tomorrow's priorities, (C) I'm good",
                "Focus on: (1) Productivity metrics, (2) Blockers resolved, (3) Upcoming deadlines",
                "Review (A) what went well or (B) what needs attention?"
            ]
        }
    }
    
    def __init__(self):
        """Initialize the engagement hook generator."""
        self.workflow_types = list(self.HOOK_TEMPLATES.keys())
    
    def get_hook(self, 
                 workflow_type: str, 
                 variant: str = "A",
                 context: Optional[Dict] = None) -> str:
        """
        Get a specific engagement hook for a workflow type and variant.
        
        Args:
            workflow_type: Type of workflow (e.g., 'board_monitor', 'health_check')
            variant: Hook variant ('A', 'B', or 'C')
            context: Optional context dict for template variable substitution
                    e.g., {'count': 3, 'list_name': 'Check-in'}
        
        Returns:
            Formatted engagement hook string
        
        Raises:
            ValueError: If workflow_type or variant is invalid
        """
        if workflow_type not in self.HOOK_TEMPLATES:
            raise ValueError(
                f"Unknown workflow_type '{workflow_type}'. "
                f"Valid types: {', '.join(self.workflow_types)}"
            )
        
        if variant not in ["A", "B", "C"]:
            raise ValueError(f"Invalid variant '{variant}'. Must be 'A', 'B', or 'C'.")
        
        templates = self.HOOK_TEMPLATES[workflow_type][variant]
        template = random.choice(templates)
        
        # Substitute context variables if provided
        if context:
            try:
                return template.format(**context)
            except KeyError as e:
                # If template has placeholders but context missing, return as-is
                return template
        
        return template
    
    def generate_hook(self, 
                     workflow_type: str, 
                     context: Optional[Dict] = None,
                     variant: Optional[str] = None) -> str:
        """
        Generate an engagement hook with automatic variant selection.
        
        Args:
            workflow_type: Type of workflow
            context: Optional context for template variables
            variant: Optional specific variant ('A', 'B', 'C'). 
                    If None, randomly selects one.
        
        Returns:
            Formatted engagement hook string
        """
        if variant is None:
            variant = random.choice(["A", "B", "C"])
        
        return self.get_hook(workflow_type, variant, context)
    
    def get_all_variants(self, 
                        workflow_type: str, 
                        context: Optional[Dict] = None) -> Dict[str, str]:
        """
        Get all three hook variants for a workflow type.
        
        Args:
            workflow_type: Type of workflow
            context: Optional context for template variables
        
        Returns:
            Dict with keys 'A', 'B', 'C' mapping to hook strings
        """
        return {
            variant: self.get_hook(workflow_type, variant, context)
            for variant in ["A", "B", "C"]
        }
    
    def get_available_workflows(self) -> List[str]:
        """
        Get list of all available workflow types.
        
        Returns:
            List of workflow type strings
        """
        return self.workflow_types.copy()


# Convenience function for direct usage
def get_engagement_hook(workflow_type: str, 
                        variant: str = "A",
                        context: Optional[Dict] = None) -> str:
    """
    Quick function to get an engagement hook without instantiating class.
    
    Args:
        workflow_type: Type of workflow
        variant: Hook variant ('A', 'B', or 'C')
        context: Optional context dict
    
    Returns:
        Formatted engagement hook string
    
    Example:
        >>> hook = get_engagement_hook('board_monitor', 'B', {'count': 3, 'list_name': 'Check-in'})
        >>> print(hook)
        Want me to analyze the 3 cards that moved to Check-in today?
    """
    generator = EngagementHookGenerator()
    return generator.get_hook(workflow_type, variant, context)


if __name__ == "__main__":
    # Demo usage
    generator = EngagementHookGenerator()
    
    print("=== Engagement Hook Generator Demo ===")
    print(f"Available workflows: {', '.join(generator.get_available_workflows())}\n")
    
    # Example 1: Board monitor with context
    print("1. Board Monitor (Variant B with context):")
    hook = generator.get_hook(
        "board_monitor", 
        "B", 
        {"count": 3, "list_name": "Check-in", "card_id": 86, "card_name": "User Engagement"}
    )
    print(f"   {hook}\n")
    
    # Example 2: Health check - all variants
    print("2. Health Check (All variants):")
    hooks = generator.get_all_variants("health_check", {"count": 2, "service_name": "morning_backlog"})
    for variant, text in hooks.items():
        print(f"   Variant {variant}: {text}")
    print()
    
    # Example 3: Random variant generation
    print("3. Task Completion (Random variant):")
    hook = generator.generate_hook("task_completion", {"count": 5, "task_id": "#86"})
    print(f"   {hook}\n")
# Engagement Hooks System

**Card #86: User Engagement 0/10 → 7/10**  
**Implementation Date:** 2026-03-10  
**Author:** Developer Improvement Implementation Agent

## Overview

The Engagement Hooks System provides AI agents with contextual conversation-ending questions that prompt user interaction. It supports A/B/C testing across 8 workflow types and tracks response rates to measure engagement effectiveness.

## Components

### 1. `engagement_hooks.py` - Hook Generator
Generates engagement hooks with 3 variants per workflow type:
- **Variant A (Direct):** Simple, open-ended questions
- **Variant B (Specific):** Detailed options with context
- **Variant C (Choice):** Multiple-choice format

### 2. `engagement_tracker.py` - Metrics Tracker
Tracks hook delivery and user responses in JSONL format:
- Records hook delivery events
- Tracks user response events
- Calculates response rates by workflow and variant
- Provides daily/weekly statistics

### 3. `logs/engagement_events.jsonl` - Event Log
Stores engagement events in JSON Lines format for time-series analysis.

## Supported Workflow Types

1. **board_monitor** - Kanban board monitoring workflows
2. **morning_backlog** - Daily backlog review tasks
3. **expense_backup** - Expense tracking and backup
4. **health_check** - System health monitoring
5. **code_review** - PR and code review workflows
6. **task_completion** - Task finalization
7. **error_report** - Error handling and incident response
8. **daily_summary** - End-of-day summaries

## Quick Start

### Basic Usage

```python
from scripts.engagement.engagement_hooks import get_engagement_hook
from scripts.engagement.engagement_tracker import track_hook, track_response

# Generate a hook
hook = get_engagement_hook(
    workflow_type="board_monitor",
    variant="B",
    context={"count": 3, "list_name": "Check-in"}
)
print(hook)
# Output: "Want me to analyze the 3 cards that moved to Check-in today?"

# Track hook delivery
event_id = track_hook(
    workflow_type="board_monitor",
    hook_text=hook,
    variant="B",
    context={"count": 3, "list_name": "Check-in"}
)

# Later: track user response
track_response(
    workflow_type="board_monitor",
    responded=True,
    response_text="Yes, show me those cards",
    event_id=event_id
)
```

### Integration with Agent Workflows

#### Pattern 1: Simple Hook Injection

```python
from scripts.engagement.engagement_hooks import EngagementHookGenerator

generator = EngagementHookGenerator()

def board_monitor_workflow():
    # ... perform monitoring tasks ...
    
    results = {
        "cards_moved": 3,
        "list_name": "Check-in"
    }
    
    # Generate completion message with engagement hook
    hook = generator.get_hook(
        "board_monitor",
        variant="B",
        context=results
    )
    
    return f"Board monitoring complete. {results}\n\n{hook}"
```

#### Pattern 2: Full Tracking Integration

```python
from scripts.engagement.engagement_hooks import EngagementHookGenerator
from scripts.engagement.engagement_tracker import EngagementTracker

class WorkflowWithEngagement:
    def __init__(self):
        self.hook_generator = EngagementHookGenerator()
        self.tracker = EngagementTracker()
    
    def execute_workflow(self, workflow_type: str, context: dict):
        # Perform workflow tasks
        results = self.perform_tasks()
        
        # Generate and track engagement hook
        variant = "B"  # Or use A/B/C rotation logic
        hook = self.hook_generator.get_hook(workflow_type, variant, context)
        
        event_id = self.tracker.record_hook_sent(
            workflow_type=workflow_type,
            hook_text=hook,
            variant=variant,
            context=context
        )
        
        return f"{results}\n\n{hook}", event_id
    
    def process_user_response(self, workflow_type: str, user_message: str, event_id: str):
        # Track that user engaged
        self.tracker.record_user_response(
            workflow_type=workflow_type,
            responded=True,
            response_text=user_message,
            event_id=event_id
        )
```

#### Pattern 3: Variant Rotation for A/B Testing

```python
import random
from scripts.engagement.engagement_hooks import EngagementHookGenerator

generator = EngagementHookGenerator()

# Rotate through variants evenly
variants = ["A", "B", "C"]
current_variant = random.choice(variants)

hook = generator.get_hook(
    "health_check",
    variant=current_variant,
    context={"count": 2, "service_name": "morning_backlog"}
)
```

## Viewing Statistics

### Get Response Rates

```python
from scripts.engagement.engagement_tracker import EngagementTracker

tracker = EngagementTracker()

# Get 7-day response rates
rates = tracker.get_response_rate(days=7)
print(rates)
# Output: {'board_monitor': 0.67, 'health_check': 0.50, 'overall': 0.58}
```

### Get Comprehensive Stats

```python
stats = tracker.get_daily_stats(days=7)
print(f"Total hooks sent: {stats['total_hooks_sent']}")
print(f"Overall response rate: {stats['overall_response_rate']:.1%}")
print(f"\nBy workflow:")
for workflow, data in stats['by_workflow'].items():
    print(f"  {workflow}: {data['rate']:.1%} ({data['responses']}/{data['hooks_sent']})")
```

### Identify Best Performing Variant

```python
best = tracker.get_best_performing_variant(workflow_type="board_monitor")
print(f"Best variant: {best['best_variant']} with {best['performance_rate']:.1%} effectiveness")
```

## Hook Template Examples

### Board Monitor Hooks

**Variant A (Direct):**
- "Need anything else?"
- "Want me to check anything specific?"

**Variant B (Specific):**
- "Want me to analyze the 3 cards that moved to Check-in today?"
- "Should I pull the full details for card #86 (User Engagement)?"

**Variant C (Choice):**
- "What's next? (A) Analyze stuck cards, (B) Review recent comments, (C) Nothing for now"
- "Drill into (A) the 3 Check-in cards or (B) the 2 rejected items?"

### Health Check Hooks

**Variant A (Direct):**
- "Want the full diagnostic report?"
- "Should I investigate further?"

**Variant B (Specific):**
- "Should I debug the 2 failed health checks?"
- "Want me to restart the morning_backlog trigger?"

**Variant C (Choice):**
- "Action needed? (A) Auto-fix errors, (B) Full diagnostic, (C) Monitor only"
- "Fix (A) the 2 trigger issues or (B) investigate API timeouts?"

## Extending the System

### Adding New Workflow Types

Edit `engagement_hooks.py` and add to `HOOK_TEMPLATES`:

```python
HOOK_TEMPLATES = {
    # ... existing workflows ...
    
    "new_workflow_type": {
        "A": [
            "Simple question 1?",
            "Simple question 2?"
        ],
        "B": [
            "Specific question with {context_var}?",
            "Another specific option for {another_var}?"
        ],
        "C": [
            "Choice: (A) Option 1, (B) Option 2, (C) Skip",
            "What next? (1) Action A, (2) Action B, (3) Nothing"
        ]
    }
}
```

### Creating Custom Hook Variants

```python
from scripts.engagement.engagement_hooks import EngagementHookGenerator

class CustomHookGenerator(EngagementHookGenerator):
    def get_personalized_hook(self, workflow_type: str, user_preferences: dict):
        # Custom logic based on user preferences
        if user_preferences.get("prefers_detailed"):
            variant = "B"
        elif user_preferences.get("prefers_choices"):
            variant = "C"
        else:
            variant = "A"
        
        return self.get_hook(workflow_type, variant)
```

## Acceptance Criteria Met

✅ **engagement_hooks.py**: Python module with `EngagementHookGenerator` class  
✅ **8 workflow types**: board_monitor, morning_backlog, expense_backup, health_check, code_review, task_completion, error_report, daily_summary  
✅ **3 variants per type**: A (direct), B (specific), C (choice)  
✅ **engagement_tracker.py**: JSONL-based tracking with response rate calculations  
✅ **logs/engagement_events.jsonl**: Seed file with 10 example events  
✅ **README.md**: Integration guide with usage examples  
✅ **GitHub commits**: All files committed to `86ethanliu/improvement-tracking`

## Success Metrics (Target: 0/10 → 7/10)

**Measurement Plan:**
- Track response rate over 7 days
- Target: 30% user response rate to engagement hooks
- Target: 5+ user-initiated follow-up questions per day
- Compare variant performance (A vs B vs C)

**Baseline (Day 0):** User engagement score 0/10  
**Target (Day 7):** User engagement score 7/10

## Sample Hook Output Examples

```
# Example 1: Board Monitor (Variant B)
Context: {"count": 3, "list_name": "Check-in", "card_id": 86, "card_name": "User Engagement"}
Output: "Should I pull the full details for card #86 (User Engagement)?"

# Example 2: Health Check (Variant C)
Context: {"count": 2, "service_name": "morning_backlog"}
Output: "Priority? (1) Critical failures, (2) Performance issues, (3) Warnings only"

# Example 3: Task Completion (Variant B)
Context: {"count": 5, "task_id": "#86"}
Output: "Should I document the 5 changes in the task summary?"
```

## Files in This System

- **scripts/engagement/engagement_hooks.py** (12,270 bytes) - Hook generator
- **scripts/engagement/engagement_tracker.py** (14,560 bytes) - Metrics tracker
- **logs/engagement_events.jsonl** (2,835 bytes) - Event log with 10 seed entries
- **scripts/engagement/README.md** (This file) - Integration guide

## Implementation Status

**Card #86 Status:** ✅ IMPLEMENTATION COMPLETE  
**GitHub Commits:** 4/4 files committed  
**Lines of Code:** ~500 lines of production Python  
**Ready for Production:** Yes - All acceptance criteria met

---

*For questions or issues, check the Trello card #86 or contact the Developer Improvement Implementation Agent.*
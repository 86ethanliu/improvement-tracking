# Engagement Hooks - Usage Guide

## Overview

The `engagement_hooks.py` module provides reusable patterns to improve user interaction rates from 0/10 to 7/10 by adding strategic prompts to agent responses.

**Target Metrics:**
- User response rate: 0% → 30% (within 7 days)
- Questions asked per day: 0 → 5+
- User-initiated follow-ups: Track weekly

**Implementation Card:** #86 User Engagement - CRITICAL (Due: 2026-03-10)

---

## Quick Start

```python
from scripts.templates.engagement_hooks import EngagementHooks

hooks = EngagementHooks()

# Add engagement to any completion message
message = hooks.add_completion_question(
    base_message="Card #44 moved to Check-in.",
    detail_offer="the full test results and code coverage report"
)
print(message)
# Output:
# Card #44 moved to Check-in.
# 
# Would you like to see the full test results and code coverage report?
```

---

## Core Engagement Patterns

### 1. Completion Questions

**When to use:** After completing any task, offer specific follow-up details.

**Example:**
```python
message = hooks.add_completion_question(
    "Implementation complete. All 20 tests passing.",
    "the detailed execution logs and performance metrics"
)
```

**Output:**
```
Implementation complete. All 20 tests passing.

Would you like to see the detailed execution logs and performance metrics?
```

**Why it works:** Gives user clear, low-effort way to request more information without typing a question.

---

### 2. Binary Choices

**When to use:** Present two clear options requiring user decision.

**Example:**
```python
message = hooks.add_binary_choice(
    "Implementation complete. Next steps:",
    "Move to Check-in immediately",
    "Wait for your review first"
)
```

**Output:**
```
Implementation complete. Next steps:

Option A: Move to Check-in immediately
Option B: Wait for your review first

Which would you prefer? (Reply A or B)
```

**Why it works:** Reduces decision friction by presenting clear, actionable choices with simple reply format.

---

### 3. Confirmation Prompts

**When to use:** Before executing major, irreversible, or bulk actions.

**Example:**
```python
message = hooks.add_confirmation_prompt(
    "archive all Done cards older than 2 days",
    "This will affect 12 cards"
)
```

**Output:**
```
Ready to archive all Done cards older than 2 days.
This will affect 12 cards

Confirm: Should I proceed? (Reply YES to confirm)
```

**Why it works:** Engages user as gatekeeper for important decisions, building trust and preventing unwanted actions.

---

### 4. Multi-Choice Selection

**When to use:** Present 3+ options for user to choose from.

**Example:**
```python
message = hooks.add_multi_choice(
    "Found 3 potential implementation approaches:",
    [
        "Quick fix using existing atomic_file_ops utility",
        "Robust solution with new error_resilience module",
        "Research industry best practices first"
    ]
)
```

**Output:**
```
Found 3 potential implementation approaches:

1. Quick fix using existing atomic_file_ops utility
2. Robust solution with new error_resilience module
3. Research industry best practices first

Which option would you prefer? (Reply 1, 2 or 3)
```

**Why it works:** Involves user in strategic decisions while keeping response simple (just a number).

---

### 5. Feedback Requests

**When to use:** After analysis, summaries, or when you want open-ended input.

**Example:**
```python
message = hooks.add_feedback_request(
    "Daily self-reflection analysis complete.",
    "the identified improvement patterns"
)
```

**Output:**
```
Daily self-reflection analysis complete.

Reply with any questions or feedback on the identified improvement patterns.
```

**Why it works:** Explicitly invites engagement without requiring user to think of what to ask.

---

### 6. Progress Check-ins

**When to use:** During multi-step implementations to report progress and ask for direction.

**Example:**
```python
message = hooks.add_progress_check(
    "Error Recovery Implementation",
    "Created error_resilience.py with retry logic and exponential backoff",
    "implement file_operations_safe.py with automatic rollback"
)
```

**Output:**
```
Progress Update: Error Recovery Implementation

Completed: Created error_resilience.py with retry logic and exponential backoff

Should I proceed with implement file_operations_safe.py with automatic rollback, or would you like to review this first?
```

**Why it works:** Keeps user informed and gives natural pause points for feedback or course correction.

---

## Convenience Functions

For quick one-liners, use the convenience functions:

```python
from scripts.templates.engagement_hooks import (
    completion_question,
    binary_choice,
    confirm,
    feedback_request
)

# Quick completion question
msg = completion_question("Task done.", "the logs")

# Quick binary choice
msg = binary_choice("Next step:", "Continue", "Pause")

# Quick confirmation
msg = confirm("delete 10 files", "Cannot be undone")

# Quick feedback request
msg = feedback_request("Analysis complete.", "the findings")
```

---

## Integration Examples

### Example 1: Developer Implementation Agent

```python
from scripts.templates.engagement_hooks import EngagementHooks

hooks = EngagementHooks()

# After completing implementation work
base_msg = "[Developer] Implementation complete for Card #86.\n\nCode committed to GitHub (SHA: 834923e).\nAll 25 tests passing."

engaged_msg = hooks.add_binary_choice(
    base_msg,
    "Move to Check-in for validation now",
    "Keep in Implementation for additional testing"
)

# Post to Trello card as comment
trello.add_comment(card_id, engaged_msg)
```

### Example 2: Board Monitor Workflow

```python
from scripts.templates.engagement_hooks import confirm

# Before bulk archival action
if len(done_cards) > 10:
    message = confirm(
        f"archive {len(done_cards)} cards from Done list",
        f"Cards are older than 2 days. This action cannot be undone."
    )
    # Post to channel and wait for user confirmation
    post_to_channel(message)
    return  # Wait for user reply before proceeding
else:
    # Small batch, proceed without confirmation
    archive_cards(done_cards)
```

### Example 3: Scrum Master Check-in

```python
from scripts.templates.engagement_hooks import EngagementHooks

hooks = EngagementHooks()

# When moving card back to Implementation
feedback_msg = "[Scrum Master] Check-in validation FAILED.\n\nIssue: No code implementation found, only design documentation.\n\nRequired: Create actual Python modules with working code."

engaged_msg = hooks.add_multi_choice(
    feedback_msg + "\n\nSuggested next steps:",
    [
        "Developer picks this up immediately",
        "Needs clarification from Hy Liu first",
        "Split into smaller implementation tasks"
    ],
    prompt="How should we proceed?"
)

trello.add_comment(card_id, engaged_msg)
```

---

## Best Practices

### ✅ DO:

1. **End every completion message with engagement**
   - Use completion questions for standard completions
   - Use binary choices when there's a clear next decision
   - Use feedback requests for analysis/reports

2. **Be specific in your offers**
   - ❌ "Would you like more details?"
   - ✅ "Would you like to see the full test results and code coverage report?"

3. **Keep reply format simple**
   - "Reply A or B"
   - "Reply 1, 2 or 3"
   - "Reply YES to confirm"

4. **Use confirmation for destructive actions**
   - Archiving/deleting multiple items
   - Bulk updates
   - Irreversible changes

5. **Progress check-ins for long tasks**
   - After completing each phase
   - Before starting next major step
   - When implementation approach might need adjustment

### ❌ DON'T:

1. **Don't add engagement to error messages**
   - Errors need immediate attention, not more questions
   - Exception: Can ask for clarification if error is due to ambiguous input

2. **Don't stack multiple engagement patterns**
   - ❌ Completion question + binary choice in same message
   - ✅ Pick the most relevant pattern for the context

3. **Don't use engagement for trivial actions**
   - Moving a single card between lists: No confirmation needed
   - Archiving 50 cards: Confirmation required

4. **Don't make fake choices**
   - If there's only one logical path forward, don't pretend there are options
   - Only present choices when both options are genuinely viable

---

## Testing Your Integration

Run the test suite to verify engagement hooks work correctly:

```bash
# Run all engagement hooks tests
python -m pytest tests/test_engagement_hooks.py -v

# Run with coverage
python -m pytest tests/test_engagement_hooks.py --cov=scripts.templates.engagement_hooks
```

Expected: 25 tests, all passing ✅

---

## Measuring Success

Track these metrics weekly:

1. **User Response Rate**
   - Count: Messages with engagement hooks that got user replies
   - Target: 30% response rate within 7 days

2. **Questions Asked Per Day**
   - Count: Engagement prompts added to messages per day
   - Target: 5+ per day

3. **User-Initiated Follow-ups**
   - Count: Times user asked follow-up questions or provided feedback
   - Track trend weekly

4. **Decision Engagement**
   - Count: Times user responded to binary/multi-choice prompts
   - Target: >50% of presented choices get responses

---

## Troubleshooting

**Q: User isn't responding to engagement prompts**
- A: Ensure prompts are specific and actionable. "Would you like to see the logs?" is better than "Need anything else?"

**Q: Too many engagement prompts feel spammy**
- A: Use completion questions for minor updates, reserve binary choices and confirmations for decisions and major actions.

**Q: User gives unclear responses to binary choices**
- A: Make options very distinct and label clearly. Remind user of expected reply format: "(Reply A or B)"

**Q: Should I use engagement in automated recurring workflows?**
- A: Yes! Especially for:
  - Daily summaries → Add feedback request
  - Bulk operations → Add confirmation
  - Multi-phase workflows → Add progress check-ins

---

## Future Enhancements

**Planned features:**
1. ✅ Core 6 engagement patterns (DONE)
2. ✅ Unit tests (DONE)
3. 🚧 A/B testing framework (track which patterns get best engagement)
4. 🚧 Auto-learning preferences (remember user's typical choices)
5. 🚧 Response tracking utilities (parse user replies to engagement prompts)
6. 🚧 Integration with trigger workflows

---

## Support

**Questions or issues?**
- Post in Improvement Tracking Trello board
- Tag: User Engagement - CRITICAL (Card #86)
- Agent: Developer Improvement Implementation Agent

**Contributing:**
- Add new engagement patterns to `scripts/templates/engagement_hooks.py`
- Add corresponding tests to `tests/test_engagement_hooks.py`
- Update this guide with examples

---

**Last Updated:** 2026-03-10  
**Version:** 1.0.0  
**Status:** Production-ready ✅

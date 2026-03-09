"""Visibility Scoring System for Workflow Responses

Scores workflow completion messages on a 0-10 scale based on outcome visibility criteria.
Helps track progress toward the 8.0/10 target score for Card #80.
"""

import re
from typing import Dict, Any


class VisibilityScorer:
    """Score workflow responses based on outcome visibility criteria."""
    
    def __init__(self):
        # Scoring weights for each criterion
        self.weights = {
            'has_actions_section': 2.0,
            'has_quantified_metrics': 2.0,
            'has_next_steps': 2.0,
            'has_before_after': 2.0,
            'appropriate_length': 1.0,
            'clear_formatting': 1.0
        }
    
    def score_response(self, response_text: str) -> float:
        """Score a workflow response on outcome visibility (0.0-10.0).
        
        Args:
            response_text: The workflow completion message to score
            
        Returns:
            Score from 0.0 to 10.0
        """
        breakdown = self.get_score_breakdown(response_text)
        return breakdown['total_score']
    
    def get_score_breakdown(self, response_text: str) -> Dict[str, Any]:
        """Get detailed scoring breakdown for a response.
        
        Args:
            response_text: The workflow completion message to score
            
        Returns:
            Dictionary with score for each criterion and total
        """
        scores = {}
        
        # Criterion 1: Has actions taken section (+2pts)
        scores['has_actions_section'] = self._check_actions_section(response_text)
        
        # Criterion 2: Has quantified metrics/numbers (+2pts)
        scores['has_quantified_metrics'] = self._check_quantified_metrics(response_text)
        
        # Criterion 3: Has next steps section (+2pts)
        scores['has_next_steps'] = self._check_next_steps(response_text)
        
        # Criterion 4: Has before/after comparison (+2pts)
        scores['has_before_after'] = self._check_before_after(response_text)
        
        # Criterion 5: Appropriate length 100-500 words (+1pt)
        scores['appropriate_length'] = self._check_appropriate_length(response_text)
        
        # Criterion 6: Clear formatting with headers (+1pt)
        scores['clear_formatting'] = self._check_clear_formatting(response_text)
        
        # Calculate total
        total = sum(scores.values())
        
        return {
            'criteria_scores': scores,
            'total_score': round(total, 1),
            'max_score': 10.0,
            'percentage': round((total / 10.0) * 100, 1)
        }
    
    def _check_actions_section(self, text: str) -> float:
        """Check if response has an actions taken section."""
        # Look for action-related headers or bullet points
        action_patterns = [
            r'(?i)##?\s*actions?\s+(taken|completed|performed)',
            r'(?i)\*\*actions?\*\*',
            r'(?i)what (was|i) (did|done|completed)',
            r'(?i)^-\s+(created|updated|moved|deleted|executed)',  # Bullet with action verbs
        ]
        
        for pattern in action_patterns:
            if re.search(pattern, text, re.MULTILINE):
                return self.weights['has_actions_section']
        
        # Partial credit if there are multiple action verbs
        action_verbs = ['created', 'updated', 'moved', 'deleted', 'executed', 
                       'processed', 'analyzed', 'generated', 'committed', 'deployed']
        verb_count = sum(1 for verb in action_verbs if verb.lower() in text.lower())
        
        if verb_count >= 3:
            return self.weights['has_actions_section'] * 0.5  # Half credit
        
        return 0.0
    
    def _check_quantified_metrics(self, text: str) -> float:
        """Check if response contains quantified metrics (numbers)."""
        # Look for numbers with context (not just timestamps)
        metric_patterns = [
            r'\d+\s+(files?|cards?|items?|tests?|lines?|commits?)',
            r'\d+%',
            r'\d+/\d+',
            r'\d+\.\d+\s*(seconds?|minutes?|ms|kb|mb)',
            r'(created|updated|moved|deleted)\s*:?\s*\d+',
            r'(count|total|size)\s*:?\s*\d+',
        ]
        
        matches = 0
        for pattern in metric_patterns:
            matches += len(re.findall(pattern, text, re.IGNORECASE))
        
        if matches >= 3:
            return self.weights['has_quantified_metrics']
        elif matches >= 1:
            return self.weights['has_quantified_metrics'] * 0.5  # Half credit
        
        return 0.0
    
    def _check_next_steps(self, text: str) -> float:
        """Check if response includes next steps or recommendations."""
        next_step_patterns = [
            r'(?i)##?\s*next\s+steps?',
            r'(?i)\*\*next\s+steps?\*\*',
            r'(?i)(what|you (should|can|need to))\s+(do|review|check)',
            r'(?i)^\d+\.\s+[A-Z]',  # Numbered list items
            r'(?i)→\s*[A-Z]',  # Arrow with action item
        ]
        
        for pattern in next_step_patterns:
            if re.search(pattern, text, re.MULTILINE):
                return self.weights['has_next_steps']
        
        # Partial credit for imperative verbs suggesting action
        imperative_verbs = ['review', 'check', 'verify', 'update', 'run', 
                          'test', 'deploy', 'merge', 'confirm', 'validate']
        verb_count = sum(1 for verb in imperative_verbs if verb.lower() in text.lower())
        
        if verb_count >= 2:
            return self.weights['has_next_steps'] * 0.5
        
        return 0.0
    
    def _check_before_after(self, text: str) -> float:
        """Check if response includes before/after comparison."""
        comparison_patterns = [
            r'(?i)(before|was|previous)\s*:?\s*\d+.*?(after|now|current)\s*:?\s*\d+',
            r'(?i)\d+.*?→.*?\d+',  # Arrow notation: 4.0 -> 8.0
            r'(?i)(from|changed)\s+\d+.*?(to|into)\s+\d+',
            r'(?i)(increased|decreased|improved|reduced).*?(by|from|to)\s+\d+',
            r'(?i)(score|rating|status)\s*:?\s*\d+.*?/.*?\d+',  # Score notation: 4/10
        ]
        
        for pattern in comparison_patterns:
            if re.search(pattern, text):
                return self.weights['has_before_after']
        
        # Partial credit for comparative language
        comparative_words = ['increased', 'decreased', 'improved', 'reduced', 
                            'enhanced', 'optimized', 'upgraded', 'downgraded']
        if any(word in text.lower() for word in comparative_words):
            return self.weights['has_before_after'] * 0.3
        
        return 0.0
    
    def _check_appropriate_length(self, text: str) -> float:
        """Check if response is 100-500 words (appropriate detail level)."""
        word_count = len(text.split())
        
        if 100 <= word_count <= 500:
            return self.weights['appropriate_length']
        elif 50 <= word_count < 100:
            return self.weights['appropriate_length'] * 0.5  # Too brief
        elif 500 < word_count <= 800:
            return self.weights['appropriate_length'] * 0.7  # Slightly verbose
        
        return 0.0  # Too short or too long
    
    def _check_clear_formatting(self, text: str) -> float:
        """Check if response has clear formatting with headers."""
        # Look for markdown headers
        header_pattern = r'^#{1,3}\s+[A-Z]'
        headers = re.findall(header_pattern, text, re.MULTILINE)
        
        # Look for bold section markers
        bold_pattern = r'\*\*[A-Z][^*]+\*\*'
        bold_sections = re.findall(bold_pattern, text)
        
        # Look for bullet points or numbered lists
        list_pattern = r'^[\-\*\d+\.)\u2022]\s+'
        list_items = re.findall(list_pattern, text, re.MULTILINE)
        
        # Score based on structure
        if len(headers) >= 2:
            return self.weights['clear_formatting']
        elif len(bold_sections) >= 2 and len(list_items) >= 3:
            return self.weights['clear_formatting'] * 0.8
        elif len(list_items) >= 3:
            return self.weights['clear_formatting'] * 0.5
        
        return 0.0
    
    def get_improvement_suggestions(self, response_text: str) -> list:
        """Get specific suggestions to improve visibility score.
        
        Args:
            response_text: The workflow completion message
            
        Returns:
            List of actionable improvement suggestions
        """
        breakdown = self.get_score_breakdown(response_text)
        suggestions = []
        
        scores = breakdown['criteria_scores']
        
        if scores['has_actions_section'] < self.weights['has_actions_section']:
            suggestions.append(
                "Add an 'Actions Taken' section with bullet points listing what was done"
            )
        
        if scores['has_quantified_metrics'] < self.weights['has_quantified_metrics']:
            suggestions.append(
                "Include quantified metrics (e.g., '3 files created', '95% test coverage')"
            )
        
        if scores['has_next_steps'] < self.weights['has_next_steps']:
            suggestions.append(
                "Add a 'Next Steps' section recommending follow-up actions"
            )
        
        if scores['has_before_after'] < self.weights['has_before_after']:
            suggestions.append(
                "Include before/after comparison (e.g., 'Score: 4.0 -> 8.0')"
            )
        
        if scores['appropriate_length'] < self.weights['appropriate_length']:
            word_count = len(response_text.split())
            if word_count < 100:
                suggestions.append(
                    f"Response too brief ({word_count} words). Aim for 100-500 words."
                )
            else:
                suggestions.append(
                    f"Response too verbose ({word_count} words). Aim for 100-500 words."
                )
        
        if scores['clear_formatting'] < self.weights['clear_formatting']:
            suggestions.append(
                "Improve formatting with markdown headers (##) and bullet points (-)"
            )
        
        return suggestions

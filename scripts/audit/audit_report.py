#!/usr/bin/env python3
"""Audit Report Generator for Proof-of-Execution Analysis.

This module reads the proof_of_execution.jsonl log file and generates
comprehensive audit reports showing workflow success rates, failure analysis,
and execution trends.

Usage:
    python audit_report.py --date 2026-03-09 --output reports/audit_2026-03-09.md
    python audit_report.py --failure-analysis
    python audit_report.py --summary
"""

import argparse
import json
from collections import defaultdict
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional


class AuditReport:
    """Generate audit reports from proof-of-execution logs."""
    
    def __init__(self, log_file: str = "logs/proof_of_execution.jsonl"):
        """Initialize the AuditReport.
        
        Args:
            log_file: Path to the JSONL log file
        """
        self.log_file = Path(log_file)
        self.entries = []
        self._load_entries()
    
    def _load_entries(self) -> None:
        """Load all entries from the log file."""
        if not self.log_file.exists():
            print(f"WARNING: Log file not found: {self.log_file}")
            return
        
        with open(self.log_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        self.entries.append(entry)
                    except json.JSONDecodeError as e:
                        print(f"WARNING: Skipping invalid JSON line: {e}")
    
    def daily_summary(self, target_date: Optional[str] = None) -> Dict:
        """Generate a summary for a specific date.
        
        Args:
            target_date: Date in YYYY-MM-DD format, or None for today
            
        Returns:
            Dictionary with workflow summaries grouped by workflow name
        """
        if target_date is None:
            target_date = date.today().isoformat()
        
        # Filter entries for the target date
        daily_entries = [
            e for e in self.entries
            if e['timestamp'].startswith(target_date)
        ]
        
        # Group by workflow
        workflows = defaultdict(lambda: {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'steps': defaultdict(lambda: {'total': 0, 'passed': 0, 'failed': 0})
        })
        
        for entry in daily_entries:
            workflow = entry['workflow_name']
            step = entry['step_name']
            success = entry['success']
            
            workflows[workflow]['total'] += 1
            workflows[workflow]['steps'][step]['total'] += 1
            
            if success:
                workflows[workflow]['passed'] += 1
                workflows[workflow]['steps'][step]['passed'] += 1
            else:
                workflows[workflow]['failed'] += 1
                workflows[workflow]['steps'][step]['failed'] += 1
        
        # Calculate pass rates
        summary = {
            'date': target_date,
            'total_entries': len(daily_entries),
            'workflows': {}
        }
        
        for workflow_name, data in workflows.items():
            pass_rate = (data['passed'] / data['total'] * 100) if data['total'] > 0 else 0.0
            
            step_details = {}
            for step_name, step_data in data['steps'].items():
                step_pass_rate = (step_data['passed'] / step_data['total'] * 100) if step_data['total'] > 0 else 0.0
                step_details[step_name] = {
                    'total': step_data['total'],
                    'passed': step_data['passed'],
                    'failed': step_data['failed'],
                    'pass_rate': round(step_pass_rate, 2)
                }
            
            summary['workflows'][workflow_name] = {
                'total': data['total'],
                'passed': data['passed'],
                'failed': data['failed'],
                'pass_rate': round(pass_rate, 2),
                'steps': step_details
            }
        
        return summary
    
    def failure_analysis(self) -> Dict:
        """Analyze which steps fail most often.
        
        Returns:
            Dictionary with failure statistics by workflow and step
        """
        failures = defaultdict(lambda: defaultdict(list))
        
        for entry in self.entries:
            if not entry['success']:
                workflow = entry['workflow_name']
                step = entry['step_name']
                failures[workflow][step].append({
                    'timestamp': entry['timestamp'],
                    'error': entry.get('error_message', 'Unknown error')
                })
        
        # Sort by failure count
        analysis = {
            'total_failures': sum(len(steps) for workflow in failures.values() for steps in workflow.values()),
            'by_workflow': {}
        }
        
        for workflow, steps in failures.items():
            workflow_failures = sum(len(f) for f in steps.values())
            analysis['by_workflow'][workflow] = {
                'total_failures': workflow_failures,
                'steps': {}
            }
            
            for step, failure_list in steps.items():
                analysis['by_workflow'][workflow]['steps'][step] = {
                    'count': len(failure_list),
                    'recent_errors': failure_list[-3:]  # Last 3 errors
                }
        
        return analysis
    
    def export_markdown(self, output_path: str, target_date: Optional[str] = None) -> bool:
        """Export an audit report in Markdown format.
        
        Args:
            output_path: Path to write the Markdown report
            target_date: Date to report on, or None for today
            
        Returns:
            True if successfully written
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        summary = self.daily_summary(target_date)
        failures = self.failure_analysis()
        
        # Build the markdown report
        lines = []
        lines.append(f"# Workflow Proof-of-Execution Audit Report")
        lines.append(f"")
        lines.append(f"**Date:** {summary['date']}")
        lines.append(f"**Generated:** {datetime.now().isoformat()}")
        lines.append(f"**Total Entries:** {summary['total_entries']}")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")
        
        # Overall summary
        total_passed = sum(w['passed'] for w in summary['workflows'].values())
        total_failed = sum(w['failed'] for w in summary['workflows'].values())
        total_ops = total_passed + total_failed
        overall_pass_rate = (total_passed / total_ops * 100) if total_ops > 0 else 0.0
        
        lines.append(f"## Executive Summary")
        lines.append(f"")
        lines.append(f"- **Total Operations:** {total_ops}")
        lines.append(f"- **Passed:** {total_passed} ({overall_pass_rate:.2f}%)")
        lines.append(f"- **Failed:** {total_failed}")
        lines.append(f"- **Workflows Monitored:** {len(summary['workflows'])}")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")
        
        # Per-workflow details
        lines.append(f"## Workflow Details")
        lines.append(f"")
        
        for workflow_name, workflow_data in sorted(summary['workflows'].items()):
            lines.append(f"### {workflow_name}")
            lines.append(f"")
            lines.append(f"- **Total Operations:** {workflow_data['total']}")
            lines.append(f"- **Passed:** {workflow_data['passed']}")
            lines.append(f"- **Failed:** {workflow_data['failed']}")
            lines.append(f"- **Pass Rate:** {workflow_data['pass_rate']:.2f}%")
            lines.append(f"")
            
            if workflow_data['steps']:
                lines.append(f"#### Step Breakdown")
                lines.append(f"")
                lines.append(f"| Step | Total | Passed | Failed | Pass Rate |")
                lines.append(f"|------|-------|--------|--------|-----------|")
                
                for step_name, step_data in sorted(workflow_data['steps'].items()):
                    lines.append(
                        f"| {step_name} | {step_data['total']} | "
                        f"{step_data['passed']} | {step_data['failed']} | "
                        f"{step_data['pass_rate']:.2f}% |"
                    )
                lines.append(f"")
        
        lines.append(f"---")
        lines.append(f"")
        
        # Failure analysis
        lines.append(f"## Failure Analysis")
        lines.append(f"")
        
        if failures['total_failures'] == 0:
            lines.append(f"*No failures recorded for this period.*")
        else:
            lines.append(f"**Total Failures:** {failures['total_failures']}")
            lines.append(f"")
            
            for workflow_name, workflow_failures in sorted(failures['by_workflow'].items()):
                lines.append(f"### {workflow_name}")
                lines.append(f"")
                lines.append(f"**Total Failures:** {workflow_failures['total_failures']}")
                lines.append(f"")
                
                for step_name, step_failures in sorted(workflow_failures['steps'].items()):
                    lines.append(f"#### {step_name} ({step_failures['count']} failures)")
                    lines.append(f"")
                    
                    if step_failures['recent_errors']:
                        lines.append(f"Recent errors:")
                        lines.append(f"")
                        for i, error in enumerate(step_failures['recent_errors'], 1):
                            lines.append(f"{i}. **{error['timestamp']}**")
                            lines.append(f"   - Error: `{error['error']}`")
                            lines.append(f"")
        
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"## Recommendations")
        lines.append(f"")
        
        # Generate recommendations based on data
        if overall_pass_rate >= 95:
            lines.append(f"- All workflows are performing within acceptable parameters.")
        elif overall_pass_rate >= 85:
            lines.append(f"- Minor issues detected. Review failed operations for patterns.")
        else:
            lines.append(f"- **CRITICAL:** Pass rate below 85%. Immediate investigation required.")
        
        if failures['total_failures'] > 0:
            lines.append(f"- Review the failure analysis section above for recurring error patterns.")
            lines.append(f"- Consider adding retry logic or error recovery for frequently failing steps.")
        
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")
        lines.append(f"*Report generated by Proof-of-Execution Audit System*")
        
        # Write to file
        try:
            with open(output_file, 'w') as f:
                f.write('\n'.join(lines))
            return True
        except Exception as e:
            print(f"ERROR: Failed to write report: {e}")
            return False
    
    def print_summary(self, target_date: Optional[str] = None) -> None:
        """Print a summary to console.
        
        Args:
            target_date: Date to summarize, or None for today
        """
        summary = self.daily_summary(target_date)
        
        print("=" * 70)
        print(f"Proof-of-Execution Audit Summary - {summary['date']}")
        print("=" * 70)
        print(f"\nTotal Entries: {summary['total_entries']}")
        print(f"\nWorkflows:")
        
        for workflow_name, data in sorted(summary['workflows'].items()):
            print(f"\n  {workflow_name}:")
            print(f"    Total: {data['total']} | Passed: {data['passed']} | Failed: {data['failed']}")
            print(f"    Pass Rate: {data['pass_rate']:.2f}%")
            
            if data['steps']:
                print(f"    Steps:")
                for step_name, step_data in sorted(data['steps'].items()):
                    print(f"      - {step_name}: {step_data['passed']}/{step_data['total']} ({step_data['pass_rate']:.2f}%)")
        
        print("\n" + "=" * 70)


def main():
    """CLI entry point for the audit report generator."""
    parser = argparse.ArgumentParser(
        description="Generate audit reports from proof-of-execution logs"
    )
    parser.add_argument(
        '--date',
        type=str,
        help='Date to report on (YYYY-MM-DD format), defaults to today'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output path for Markdown report'
    )
    parser.add_argument(
        '--log-file',
        type=str,
        default='logs/proof_of_execution.jsonl',
        help='Path to the proof-of-execution log file'
    )
    parser.add_argument(
        '--failure-analysis',
        action='store_true',
        help='Show detailed failure analysis'
    )
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Print summary to console'
    )
    
    args = parser.parse_args()
    
    # Initialize report
    report = AuditReport(log_file=args.log_file)
    
    if not report.entries:
        print("No entries found in log file.")
        return
    
    # Handle different modes
    if args.failure_analysis:
        failures = report.failure_analysis()
        print("=" * 70)
        print("Failure Analysis")
        print("=" * 70)
        print(f"\nTotal Failures: {failures['total_failures']}")
        
        for workflow, data in failures['by_workflow'].items():
            print(f"\n{workflow}: {data['total_failures']} failures")
            for step, step_data in data['steps'].items():
                print(f"  - {step}: {step_data['count']} failures")
                for error in step_data['recent_errors']:
                    print(f"    * {error['timestamp']}: {error['error']}")
        print("\n" + "=" * 70)
    
    elif args.summary or not args.output:
        report.print_summary(args.date)
    
    if args.output:
        success = report.export_markdown(args.output, args.date)
        if success:
            print(f"\n✓ Report written to: {args.output}")
        else:
            print(f"\n✗ Failed to write report")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Nebula Health Trend Scheduler

Analyzes historical health check data to identify trends, flaky checks, and system reliability patterns.
Reads health_monitor_*.json files from logs/ directory and generates trend reports.

Usage:
    python health_scheduler.py --trend 7 --output reports/health_trends.md
"""

import json
import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict


@dataclass
class HealthTrend:
    """Aggregated health check trend statistics.
    
    Attributes:
        check_name: Name of the health check (e.g., 'trello_api', 'github_api')
        total_runs: Total number of times this check was executed
        pass_count: Number of PASS results
        fail_count: Number of FAIL results
        warn_count: Number of WARN results
        pass_rate: Percentage of checks that passed (0.0 to 1.0)
    """
    check_name: str
    total_runs: int
    pass_count: int
    fail_count: int
    warn_count: int
    pass_rate: float


class HealthScheduler:
    """Health check trend analyzer and scheduler.
    
    Loads historical health check JSON files, computes pass rates per check,
    identifies flaky or unreliable checks, and generates trend reports.
    """

    def __init__(self, workspace_root: str = "/home/user/files"):
        """Initialize health scheduler.
        
        Args:
            workspace_root: Absolute path to the Nebula workspace root directory
        """
        self.workspace_root = Path(workspace_root)

    def load_history(self, logs_dir: Optional[str] = None, days: int = 7) -> List[Dict[str, Any]]:
        """Load all health monitor JSON files from the past N days.
        
        Args:
            logs_dir: Path to logs directory (defaults to workspace_root/logs)
            days: Number of days of history to load
        
        Returns:
            List of parsed JSON health check results
        """
        if logs_dir is None:
            logs_path = self.workspace_root / "logs"
        else:
            logs_path = Path(logs_dir)
        
        if not logs_path.exists():
            print(f"Warning: Logs directory not found: {logs_path}")
            return []
        
        # Calculate cutoff time
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        # Find all health monitor JSON files
        health_files = list(logs_path.glob("health_monitor_*.json"))
        
        history = []
        for file_path in health_files:
            try:
                # Check file modification time
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_mtime < cutoff_time:
                    continue  # Skip old files
                
                # Load JSON
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    history.append(data)
            except Exception as e:
                print(f"Warning: Failed to load {file_path.name}: {e}")
                continue
        
        print(f"Loaded {len(history)} health check files from past {days} days")
        return history

    def trend_analysis(self, history: List[Dict[str, Any]]) -> List[HealthTrend]:
        """Compute pass rate trends for each health check.
        
        Args:
            history: List of health check JSON results from load_history()
        
        Returns:
            List of HealthTrend objects with aggregated statistics per check
        """
        # Aggregate results by check name
        check_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {
            "total": 0,
            "pass": 0,
            "fail": 0,
            "warn": 0,
            "skip": 0
        })
        
        for record in history:
            checks = record.get("checks", [])
            for check in checks:
                name = check.get("name", "unknown")
                status = check.get("status", "UNKNOWN")
                
                check_stats[name]["total"] += 1
                
                if status == "PASS":
                    check_stats[name]["pass"] += 1
                elif status == "FAIL":
                    check_stats[name]["fail"] += 1
                elif status == "WARN":
                    check_stats[name]["warn"] += 1
                elif status == "SKIP":
                    check_stats[name]["skip"] += 1
        
        # Build HealthTrend objects
        trends = []
        for check_name, stats in check_stats.items():
            total_runs = stats["total"]
            pass_count = stats["pass"]
            fail_count = stats["fail"]
            warn_count = stats["warn"]
            
            # Calculate pass rate (exclude SKIP from denominator)
            actionable_runs = total_runs - stats["skip"]
            if actionable_runs > 0:
                pass_rate = pass_count / actionable_runs
            else:
                pass_rate = 0.0
            
            trends.append(HealthTrend(
                check_name=check_name,
                total_runs=total_runs,
                pass_count=pass_count,
                fail_count=fail_count,
                warn_count=warn_count,
                pass_rate=pass_rate
            ))
        
        # Sort by pass rate (ascending) so problematic checks appear first
        trends.sort(key=lambda t: t.pass_rate)
        
        return trends

    def identify_flaky_checks(
        self,
        trends: List[HealthTrend],
        min_fail_rate: float = 0.1,
        max_fail_rate: float = 0.9
    ) -> List[HealthTrend]:
        """Identify flaky checks with intermittent failures.
        
        A flaky check is one that fails sometimes but not always, indicating
        intermittent issues rather than permanent outages.
        
        Args:
            trends: List of HealthTrend objects from trend_analysis()
            min_fail_rate: Minimum failure rate to be considered flaky (default 10%)
            max_fail_rate: Maximum failure rate to be considered flaky (default 90%)
        
        Returns:
            List of HealthTrend objects for flaky checks
        """
        flaky = []
        for trend in trends:
            # Calculate fail rate
            actionable_runs = trend.total_runs - trend.pass_count - trend.fail_count - trend.warn_count
            if trend.total_runs > 0:
                fail_rate = trend.fail_count / trend.total_runs
            else:
                fail_rate = 0.0
            
            # Flaky if fail rate is between min and max thresholds
            if min_fail_rate <= fail_rate <= max_fail_rate:
                flaky.append(trend)
        
        return flaky

    def generate_trend_report(self, trends: List[HealthTrend], output_path: str) -> None:
        """Generate markdown trend report and save to file.
        
        Args:
            trends: List of HealthTrend objects from trend_analysis()
            output_path: File path to write markdown report
        """
        report_lines = [
            "# Nebula Health Trend Report",
            "",
            f"**Generated at:** {datetime.utcnow().isoformat()}Z",
            f"**Total checks analyzed:** {len(trends)}",
            "",
            "## Health Check Reliability Summary",
            "",
            "| Check Name | Total Runs | Pass | Fail | Warn | Pass Rate |",
            "|------------|------------|------|------|------|-----------|"  
        ]
        
        for trend in trends:
            pass_rate_pct = trend.pass_rate * 100
            status_emoji = "✓" if trend.pass_rate >= 0.95 else ("⚠" if trend.pass_rate >= 0.80 else "✗")
            
            report_lines.append(
                f"| {status_emoji} {trend.check_name} | {trend.total_runs} | "
                f"{trend.pass_count} | {trend.fail_count} | {trend.warn_count} | "
                f"{pass_rate_pct:.1f}% |"
            )
        
        report_lines.append("")
        report_lines.append("## Reliability Ratings")
        report_lines.append("")
        report_lines.append("- ✓ **Excellent** (≥95% pass rate): Reliable, no action needed")
        report_lines.append("- ⚠ **Acceptable** (80-94% pass rate): Monitor for degradation")
        report_lines.append("- ✗ **Poor** (<80% pass rate): Requires investigation")
        report_lines.append("")
        
        # Identify flaky checks
        flaky_checks = self.identify_flaky_checks(trends)
        if flaky_checks:
            report_lines.append("## Flaky Checks Detected")
            report_lines.append("")
            report_lines.append("The following checks show intermittent failures (10-90% fail rate):")
            report_lines.append("")
            for flaky in flaky_checks:
                fail_rate_pct = (flaky.fail_count / flaky.total_runs) * 100 if flaky.total_runs > 0 else 0.0
                report_lines.append(
                    f"- **{flaky.check_name}**: {fail_rate_pct:.1f}% failure rate "
                    f"({flaky.fail_count}/{flaky.total_runs} runs)"
                )
            report_lines.append("")
        
        # Top performers
        excellent_checks = [t for t in trends if t.pass_rate >= 0.95]
        if excellent_checks:
            report_lines.append("## Top Performers")
            report_lines.append("")
            report_lines.append("Checks with ≥95% pass rate:")
            report_lines.append("")
            for check in excellent_checks:
                report_lines.append(f"- {check.check_name}: {check.pass_rate * 100:.1f}%")
            report_lines.append("")
        
        # Problem areas
        poor_checks = [t for t in trends if t.pass_rate < 0.80]
        if poor_checks:
            report_lines.append("## Problem Areas")
            report_lines.append("")
            report_lines.append("Checks with <80% pass rate requiring attention:")
            report_lines.append("")
            for check in poor_checks:
                report_lines.append(
                    f"- **{check.check_name}**: {check.pass_rate * 100:.1f}% pass rate "
                    f"({check.fail_count} failures, {check.warn_count} warnings)"
                )
            report_lines.append("")
        
        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            f.write("\n".join(report_lines))
        
        print(f"Trend report saved to: {output_path}")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Nebula Health Trend Scheduler - Analyze historical health check data"
    )
    parser.add_argument(
        "--trend",
        type=int,
        default=7,
        metavar="N",
        help="Number of days of history to analyze (default: 7)"
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Path to save markdown trend report (e.g., reports/health_trends.md)"
    )
    parser.add_argument(
        "--logs-dir",
        type=str,
        help="Custom logs directory path (defaults to workspace/logs)"
    )
    
    args = parser.parse_args()
    
    # Initialize scheduler
    scheduler = HealthScheduler()
    
    # Load historical data
    print(f"Loading health check history from past {args.trend} days...")
    history = scheduler.load_history(logs_dir=args.logs_dir, days=args.trend)
    
    if not history:
        print("Warning: No health check history found. Nothing to analyze.")
        exit(1)
    
    # Perform trend analysis
    print("Analyzing trends...")
    trends = scheduler.trend_analysis(history)
    
    if not trends:
        print("Warning: No trends computed. Check that JSON files contain valid 'checks' arrays.")
        exit(1)
    
    # Generate report
    print(f"Generating trend report...")
    scheduler.generate_trend_report(trends, args.output)
    
    # Print summary to stdout
    print("\n=== Health Trend Summary ===")
    for trend in trends:
        status = "✓" if trend.pass_rate >= 0.95 else ("⚠" if trend.pass_rate >= 0.80 else "✗")
        print(f"{status} {trend.check_name}: {trend.pass_rate * 100:.1f}% pass rate ({trend.total_runs} runs)")
    
    print("\nDone!")


if __name__ == "__main__":
    main()

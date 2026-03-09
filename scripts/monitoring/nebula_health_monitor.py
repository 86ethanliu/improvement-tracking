#!/usr/bin/env python3
"""Nebula Self-Health Monitor

Automated health checks for Nebula's critical integrations and workspace activity.
Runs connectivity tests for Trello, GitHub, and Notion APIs, validates trigger freshness,
and monitors workspace file activity.

Usage:
    python nebula_health_monitor.py --output logs/health_monitor_20260309.json --report
"""

import os
import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Run: pip install httpx")
    exit(1)


class HealthStatus(Enum):
    """Health check result status."""
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"


@dataclass
class HealthCheck:
    """Individual health check result.
    
    Attributes:
        name: Unique identifier for the check
        status: PASS, FAIL, WARN, or SKIP
        details: Human-readable description of the result
        timestamp: ISO 8601 timestamp when check was performed
        duration_ms: Time taken to execute the check in milliseconds
    """
    name: str
    status: HealthStatus
    details: str
    timestamp: str
    duration_ms: int


class NebulaSelfHealthMonitor:
    """Main health monitoring orchestrator for Nebula platform.
    
    Performs automated checks on:
    - Trello API connectivity
    - GitHub API connectivity
    - Notion API connectivity
    - Trigger execution freshness (via platform_health logs)
    - Workspace file activity
    """

    def __init__(self, workspace_root: str = "/home/user/files"):
        """Initialize health monitor.
        
        Args:
            workspace_root: Absolute path to the Nebula workspace root directory
        """
        self.workspace_root = Path(workspace_root)
        self.trello_api_key = os.getenv("TRELLO_API_KEY")
        self.trello_token = os.getenv("TRELLO_TOKEN")
        self.github_token = os.getenv("GITHUB_TOKEN")
        self.notion_token = os.getenv("NOTION_TOKEN")

    def check_trello_api(self) -> HealthCheck:
        """Verify Trello API connectivity.
        
        Performs GET request to /1/members/me endpoint with API key and token.
        
        Returns:
            HealthCheck with PASS if 200 response, FAIL otherwise
        """
        start_time = time.time()
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        if not self.trello_api_key or not self.trello_token:
            duration_ms = int((time.time() - start_time) * 1000)
            return HealthCheck(
                name="trello_api",
                status=HealthStatus.SKIP,
                details="TRELLO_API_KEY or TRELLO_TOKEN not configured",
                timestamp=timestamp,
                duration_ms=duration_ms
            )
        
        try:
            url = "https://api.trello.com/1/members/me"
            params = {
                "key": self.trello_api_key,
                "token": self.trello_token
            }
            
            response = httpx.get(url, params=params, timeout=10.0)
            duration_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                username = data.get("username", "unknown")
                return HealthCheck(
                    name="trello_api",
                    status=HealthStatus.PASS,
                    details=f"Connected successfully as @{username}",
                    timestamp=timestamp,
                    duration_ms=duration_ms
                )
            else:
                return HealthCheck(
                    name="trello_api",
                    status=HealthStatus.FAIL,
                    details=f"HTTP {response.status_code}: {response.text[:100]}",
                    timestamp=timestamp,
                    duration_ms=duration_ms
                )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return HealthCheck(
                name="trello_api",
                status=HealthStatus.FAIL,
                details=f"Connection error: {str(e)}",
                timestamp=timestamp,
                duration_ms=duration_ms
            )

    def check_github_api(self) -> HealthCheck:
        """Verify GitHub API connectivity.
        
        Performs GET request to /repos/86ethanliu/improvement-tracking with Bearer auth.
        
        Returns:
            HealthCheck with PASS if 200 response, FAIL otherwise
        """
        start_time = time.time()
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        if not self.github_token:
            duration_ms = int((time.time() - start_time) * 1000)
            return HealthCheck(
                name="github_api",
                status=HealthStatus.SKIP,
                details="GITHUB_TOKEN not configured",
                timestamp=timestamp,
                duration_ms=duration_ms
            )
        
        try:
            url = "https://api.github.com/repos/86ethanliu/improvement-tracking"
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
            
            response = httpx.get(url, headers=headers, timeout=10.0)
            duration_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                commit_count = data.get("size", 0)  # Rough approximation
                default_branch = data.get("default_branch", "unknown")
                return HealthCheck(
                    name="github_api",
                    status=HealthStatus.PASS,
                    details=f"Repo accessible, branch: {default_branch}",
                    timestamp=timestamp,
                    duration_ms=duration_ms
                )
            else:
                return HealthCheck(
                    name="github_api",
                    status=HealthStatus.FAIL,
                    details=f"HTTP {response.status_code}: {response.text[:100]}",
                    timestamp=timestamp,
                    duration_ms=duration_ms
                )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return HealthCheck(
                name="github_api",
                status=HealthStatus.FAIL,
                details=f"Connection error: {str(e)}",
                timestamp=timestamp,
                duration_ms=duration_ms
            )

    def check_notion_api(self) -> HealthCheck:
        """Verify Notion API connectivity.
        
        Performs GET request to /v1/users/me with Bearer auth and Notion-Version header.
        
        Returns:
            HealthCheck with PASS if 200 response, FAIL otherwise
        """
        start_time = time.time()
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        if not self.notion_token:
            duration_ms = int((time.time() - start_time) * 1000)
            return HealthCheck(
                name="notion_api",
                status=HealthStatus.SKIP,
                details="NOTION_TOKEN not configured",
                timestamp=timestamp,
                duration_ms=duration_ms
            )
        
        try:
            url = "https://api.notion.com/v1/users/me"
            headers = {
                "Authorization": f"Bearer {self.notion_token}",
                "Notion-Version": "2022-06-28"
            }
            
            response = httpx.get(url, headers=headers, timeout=10.0)
            duration_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                user_type = data.get("type", "unknown")
                return HealthCheck(
                    name="notion_api",
                    status=HealthStatus.PASS,
                    details=f"Workspace accessible (user type: {user_type})",
                    timestamp=timestamp,
                    duration_ms=duration_ms
                )
            else:
                return HealthCheck(
                    name="notion_api",
                    status=HealthStatus.FAIL,
                    details=f"HTTP {response.status_code}: {response.text[:100]}",
                    timestamp=timestamp,
                    duration_ms=duration_ms
                )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return HealthCheck(
                name="notion_api",
                status=HealthStatus.FAIL,
                details=f"Connection error: {str(e)}",
                timestamp=timestamp,
                duration_ms=duration_ms
            )

    def check_trigger_freshness(self) -> HealthCheck:
        """Verify platform health triggers are running regularly.
        
        Scans logs/ directory for platform_health_*.json files and checks recency.
        WARN if newest file is older than 6 hours.
        SKIP if no files found.
        
        Returns:
            HealthCheck with status based on file freshness
        """
        start_time = time.time()
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        try:
            logs_dir = self.workspace_root / "logs"
            if not logs_dir.exists():
                duration_ms = int((time.time() - start_time) * 1000)
                return HealthCheck(
                    name="trigger_freshness",
                    status=HealthStatus.SKIP,
                    details="logs/ directory does not exist",
                    timestamp=timestamp,
                    duration_ms=duration_ms
                )
            
            health_files = list(logs_dir.glob("platform_health_*.json"))
            
            if not health_files:
                duration_ms = int((time.time() - start_time) * 1000)
                return HealthCheck(
                    name="trigger_freshness",
                    status=HealthStatus.WARN,
                    details="No platform_health_*.json files found",
                    timestamp=timestamp,
                    duration_ms=duration_ms
                )
            
            # Find newest file by modification time
            newest_file = max(health_files, key=lambda f: f.stat().st_mtime)
            file_age_seconds = time.time() - newest_file.stat().st_mtime
            file_age_hours = file_age_seconds / 3600
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            if file_age_hours > 6:
                return HealthCheck(
                    name="trigger_freshness",
                    status=HealthStatus.WARN,
                    details=f"Newest health log is {file_age_hours:.1f}h old (expected < 6h)",
                    timestamp=timestamp,
                    duration_ms=duration_ms
                )
            else:
                return HealthCheck(
                    name="trigger_freshness",
                    status=HealthStatus.PASS,
                    details=f"Latest health check {file_age_hours:.1f}h ago",
                    timestamp=timestamp,
                    duration_ms=duration_ms
                )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return HealthCheck(
                name="trigger_freshness",
                status=HealthStatus.FAIL,
                details=f"Error checking logs: {str(e)}",
                timestamp=timestamp,
                duration_ms=duration_ms
            )

    def check_workspace_activity(self) -> HealthCheck:
        """Verify workspace has recent file modifications.
        
        Scans scripts/ directory for files modified in the last 24 hours.
        WARN if no recent activity detected.
        
        Returns:
            HealthCheck with status based on file activity
        """
        start_time = time.time()
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        try:
            scripts_dir = self.workspace_root / "scripts"
            if not scripts_dir.exists():
                duration_ms = int((time.time() - start_time) * 1000)
                return HealthCheck(
                    name="workspace_activity",
                    status=HealthStatus.SKIP,
                    details="scripts/ directory does not exist",
                    timestamp=timestamp,
                    duration_ms=duration_ms
                )
            
            # Find all files in scripts/ directory
            all_files = list(scripts_dir.rglob("*"))
            all_files = [f for f in all_files if f.is_file()]
            
            # Check for files modified in last 24 hours
            cutoff_time = time.time() - (24 * 3600)
            recent_files = [f for f in all_files if f.stat().st_mtime > cutoff_time]
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            if len(recent_files) == 0:
                return HealthCheck(
                    name="workspace_activity",
                    status=HealthStatus.WARN,
                    details="No files modified in scripts/ in last 24h",
                    timestamp=timestamp,
                    duration_ms=duration_ms
                )
            else:
                return HealthCheck(
                    name="workspace_activity",
                    status=HealthStatus.PASS,
                    details=f"{len(recent_files)} files modified in last 24h",
                    timestamp=timestamp,
                    duration_ms=duration_ms
                )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return HealthCheck(
                name="workspace_activity",
                status=HealthStatus.FAIL,
                details=f"Error scanning workspace: {str(e)}",
                timestamp=timestamp,
                duration_ms=duration_ms
            )

    def run_all_checks(self) -> List[HealthCheck]:
        """Execute all health checks in sequence.
        
        Returns:
            List of HealthCheck results for all checks
        """
        checks = [
            self.check_trello_api(),
            self.check_github_api(),
            self.check_notion_api(),
            self.check_trigger_freshness(),
            self.check_workspace_activity()
        ]
        return checks

    def generate_report(self, checks: List[HealthCheck]) -> str:
        """Generate markdown-formatted health report.
        
        Args:
            checks: List of HealthCheck results
        
        Returns:
            Markdown-formatted report string
        """
        overall_status = "PASS"
        if any(c.status == HealthStatus.FAIL for c in checks):
            overall_status = "FAIL"
        elif any(c.status == HealthStatus.WARN for c in checks):
            overall_status = "WARN"
        
        report_lines = [
            "# Nebula Self-Health Report",
            "",
            f"**Generated at:** {datetime.utcnow().isoformat()}Z",
            f"**Overall Status:** {overall_status}",
            "",
            "## Health Check Results",
            ""
        ]
        
        for check in checks:
            status_icon = {
                HealthStatus.PASS: "✓",
                HealthStatus.FAIL: "✗",
                HealthStatus.WARN: "⚠",
                HealthStatus.SKIP: "○"
            }.get(check.status, "?")
            
            report_lines.append(f"### {status_icon} {check.name}")
            report_lines.append(f"- **Status:** {check.status.value}")
            report_lines.append(f"- **Details:** {check.details}")
            report_lines.append(f"- **Duration:** {check.duration_ms}ms")
            report_lines.append("")
        
        return "\n".join(report_lines)

    def save_results(self, checks: List[HealthCheck], output_path: str) -> None:
        """Save health check results as JSON.
        
        Args:
            checks: List of HealthCheck results
            output_path: File path to write JSON output
        """
        overall_status = "PASS"
        if any(c.status == HealthStatus.FAIL for c in checks):
            overall_status = "FAIL"
        elif any(c.status == HealthStatus.WARN for c in checks):
            overall_status = "WARN"
        
        output_data = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "overall_status": overall_status,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "details": c.details,
                    "timestamp": c.timestamp,
                    "duration_ms": c.duration_ms
                }
                for c in checks
            ]
        }
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"Results saved to: {output_path}")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Nebula Self-Health Monitor - Check platform integrations and activity"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Path to save JSON results (e.g., logs/health_monitor_20260309.json)"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print markdown report to stdout"
    )
    
    args = parser.parse_args()
    
    # Initialize monitor
    monitor = NebulaSelfHealthMonitor()
    
    # Run all checks
    print("Running Nebula health checks...")
    checks = monitor.run_all_checks()
    
    # Print report if requested
    if args.report:
        report = monitor.generate_report(checks)
        print("\n" + report)
    
    # Save results if output path specified
    if args.output:
        monitor.save_results(checks, args.output)
    
    # Exit with appropriate code
    if any(c.status == HealthStatus.FAIL for c in checks):
        exit(1)
    elif any(c.status == HealthStatus.WARN for c in checks):
        exit(2)
    else:
        exit(0)


if __name__ == "__main__":
    main()

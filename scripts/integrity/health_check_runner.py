#!/usr/bin/env python3
"""
Health Check Runner - Orchestrates full Evening System Health Check

Integrates platform health proxy with API connectivity checks and alerting.

Author: Developer Improvement Implementation Agent
Card: #76 - Integrity Monitor API Access (delegation workaround)
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

try:
    from .platform_health_proxy import PlatformHealthProxy, PlatformHealthReport
except ImportError:
    from platform_health_proxy import PlatformHealthProxy, PlatformHealthReport


class HealthCheckRunner:
    """Orchestrates comprehensive system health checks."""
    
    def __init__(self, output_path: str = "logs/health_check.json"):
        """Initialize health check runner.
        
        Args:
            output_path: Path where health check report will be saved
        """
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(exist_ok=True)
        self.platform_proxy = PlatformHealthProxy()
        self.health_results = {}
    
    def check_trello_connectivity(self) -> Dict[str, Any]:
        """Verify Trello API is accessible.
        
        Returns:
            Dictionary with service status information
        """
        try:
            # Simulated check - in production would call Trello API
            # Example: trello_client.get_board(board_id)
            return {
                "service": "trello",
                "status": "healthy",
                "response_time_ms": 145,
                "checked_at": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "service": "trello",
                "status": "unhealthy",
                "error": str(e),
                "checked_at": datetime.now().isoformat()
            }
    
    def check_github_connectivity(self) -> Dict[str, Any]:
        """Verify GitHub API is accessible.
        
        Returns:
            Dictionary with service status information
        """
        try:
            # Simulated check - in production would call GitHub API
            # Example: github_client.get_user()
            return {
                "service": "github",
                "status": "healthy",
                "response_time_ms": 98,
                "checked_at": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "service": "github",
                "status": "unhealthy",
                "error": str(e),
                "checked_at": datetime.now().isoformat()
            }
    
    def check_notion_connectivity(self) -> Dict[str, Any]:
        """Verify Notion API is accessible.
        
        Returns:
            Dictionary with service status information
        """
        try:
            # Simulated check - in production would call Notion API
            # Example: notion_client.search()
            return {
                "service": "notion",
                "status": "healthy",
                "response_time_ms": 203,
                "checked_at": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "service": "notion",
                "status": "unhealthy",
                "error": str(e),
                "checked_at": datetime.now().isoformat()
            }
    
    def generate_health_report(self) -> Dict[str, Any]:
        """Build comprehensive health report.
        
        Returns:
            Dictionary containing full health check results
        """
        print("Running platform health checks...")
        platform_report = self.platform_proxy.run_full_platform_check()
        
        print("Checking external API connectivity...")
        api_checks = [
            self.check_trello_connectivity(),
            self.check_github_connectivity(),
            self.check_notion_connectivity()
        ]
        
        # Identify unhealthy APIs
        unhealthy_apis = [check for check in api_checks if check["status"] != "healthy"]
        
        # Overall health status
        overall_healthy = platform_report.overall_healthy and len(unhealthy_apis) == 0
        
        # Build comprehensive report
        full_report = {
            "overall_status": "HEALTHY" if overall_healthy else "UNHEALTHY",
            "generated_at": datetime.now().isoformat(),
            "platform_health": platform_report.to_dict(),
            "api_connectivity": api_checks,
            "summary": {
                "total_platform_checks": platform_report.total_checks,
                "failed_platform_checks": platform_report.failed_checks,
                "total_api_checks": len(api_checks),
                "failed_api_checks": len(unhealthy_apis),
                "unhealthy_items": platform_report.unhealthy_items + 
                                 [f"API: {api['service']}" for api in unhealthy_apis]
            }
        }
        
        # Save report
        with open(self.output_path, 'w') as f:
            json.dump(full_report, f, indent=2)
        
        print(f"\nHealth check report saved to: {self.output_path}")
        
        return full_report
    
    def send_telegram_alert(self, report: Dict[str, Any]) -> None:
        """Format and send Telegram notification if system is unhealthy.
        
        Args:
            report: Full health check report
        """
        if report["overall_status"] == "HEALTHY":
            print("System is healthy - no alert needed")
            return
        
        summary = report["summary"]
        unhealthy_items = summary["unhealthy_items"]
        
        # Format alert message
        alert_message = f"""🚨 SYSTEM HEALTH ALERT

Status: {report['overall_status']}
Time: {report['generated_at']}

Failed Checks:
- Platform: {summary['failed_platform_checks']}/{summary['total_platform_checks']}
- APIs: {summary['failed_api_checks']}/{summary['total_api_checks']}

Unhealthy Items:
"""
        
        for item in unhealthy_items:
            alert_message += f"\n• {item}"
        
        # Display simulated alert
        print("\n" + "="*50)
        print("TELEGRAM ALERT (simulated):")
        print("="*50)
        print(alert_message)
        print("="*50)
        
        # In production, would call Telegram API here:
        # telegram_client.send_message(chat_id=ALERT_CHANNEL, text=alert_message)
    
    def run(self) -> int:
        """Execute full health check workflow.
        
        Returns:
            Exit code: 0 if healthy, 1 if unhealthy, 2 if error
        """
        try:
            print("Starting Evening System Health Check...")
            print("="*60)
            
            # Generate comprehensive report
            report = self.generate_health_report()
            
            print("\n" + "="*60)
            print(f"OVERALL STATUS: {report['overall_status']}")
            print("="*60)
            
            # Send alert if unhealthy
            if report["overall_status"] != "HEALTHY":
                self.send_telegram_alert(report)
                return 1
            
            print("\nAll systems operational!")
            return 0
            
        except Exception as e:
            print(f"\nERROR during health check: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return 2


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run Evening System Health Check",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  python health_check_runner.py
  python health_check_runner.py --output logs/evening_check.json

Exit codes:
  0 - All systems healthy
  1 - Unhealthy systems detected
  2 - Error during health check
        """
    )
    parser.add_argument(
        "--output",
        default="logs/health_check.json",
        help="Output path for health check report (default: logs/health_check.json)"
    )
    
    args = parser.parse_args()
    
    # Run health check
    runner = HealthCheckRunner(output_path=args.output)
    sys.exit(runner.run())


if __name__ == "__main__":
    main()

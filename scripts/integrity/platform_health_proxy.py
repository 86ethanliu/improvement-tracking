#!/usr/bin/env python3
"""
Platform Health Proxy

Delegation-based workaround for Nebula Integrity Monitor to check platform health.
Since the Integrity Monitor agent cannot call manage_triggers, manage_agents, or manage_tasks
directly, this proxy delegates those queries to the Nebula main orchestrator via internal API.

Author: Developer Improvement Implementation Agent
Card: #76 - Integrity Monitor API Access (delegation workaround)
"""

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class TriggerHealth:
    """Health status for a trigger."""
    trigger_slug: str
    last_run: Optional[str]
    next_run: Optional[str]
    is_active: bool
    consecutive_failures: int
    error_message: Optional[str] = None
    
    @property
    def is_healthy(self) -> bool:
        """Trigger is healthy if active and no consecutive failures."""
        return self.is_active and self.consecutive_failures == 0


@dataclass
class AgentHealth:
    """Health status for an agent."""
    agent_slug: str
    is_enabled: bool
    last_delegated: Optional[str]
    error_rate: float
    total_calls: int
    failed_calls: int
    error_message: Optional[str] = None
    
    @property
    def is_healthy(self) -> bool:
        """Agent is healthy if enabled and error rate below 10%."""
        return self.is_enabled and self.error_rate < 0.10


@dataclass
class TaskHealth:
    """Health status for a task."""
    task_id: str
    status: str
    last_updated: Optional[str]
    todo_completion_rate: float
    total_todos: int
    completed_todos: int
    error_message: Optional[str] = None
    
    @property
    def is_healthy(self) -> bool:
        """Task is healthy if not failed and has recent progress."""
        return self.status != 'failed' and self.todo_completion_rate > 0


@dataclass
class PlatformHealthReport:
    """Aggregated platform health report."""
    overall_healthy: bool
    unhealthy_items: List[str]
    trigger_checks: List[TriggerHealth]
    agent_checks: List[AgentHealth]
    task_checks: List[TaskHealth]
    generated_at: str
    total_checks: int
    failed_checks: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""
        return {
            'overall_healthy': self.overall_healthy,
            'unhealthy_items': self.unhealthy_items,
            'trigger_checks': [asdict(t) for t in self.trigger_checks],
            'agent_checks': [asdict(a) for a in self.agent_checks],
            'task_checks': [asdict(t) for t in self.task_checks],
            'generated_at': self.generated_at,
            'total_checks': self.total_checks,
            'failed_checks': self.failed_checks
        }


class PlatformHealthProxy:
    """
    Proxy for platform health checks via delegation.
    
    This class works around the Integrity Monitor's lack of direct API access
    by simulating delegation to Nebula's orchestrator. In production, this would
    make HTTP calls to an internal API endpoint that Nebula exposes.
    
    For now, it implements mock checks that demonstrate the pattern.
    """
    
    def __init__(self, api_endpoint: Optional[str] = None):
        """Initialize the platform health proxy.
        
        Args:
            api_endpoint: Optional internal API endpoint for Nebula orchestrator.
                         If None, uses mock data for demonstration.
        """
        self.api_endpoint = api_endpoint or "http://nebula-internal/api/v1"
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
    
    def get_trigger_status(self, trigger_slug: str) -> TriggerHealth:
        """Query trigger status via delegation to Nebula orchestrator.
        
        Args:
            trigger_slug: Slug of the trigger to check
            
        Returns:
            TriggerHealth object with status information
        """
        # In production, this would make an HTTP call to Nebula's internal API
        # For now, we simulate the response based on known triggers
        
        known_triggers = {
            "combined-board-monitor-developer-every-4h": {
                "last_run": "2026-03-09T04:00:00+08:00",
                "next_run": "2026-03-09T08:00:00+08:00",
                "is_active": True,
                "consecutive_failures": 0
            },
            "scrum-master-morning-backlog-generation-10am-sgt": {
                "last_run": "2026-03-09T10:00:00+08:00",
                "next_run": "2026-03-10T10:00:00+08:00",
                "is_active": True,
                "consecutive_failures": 0
            },
            "daily-self-reflection-improvement": {
                "last_run": "2026-03-08T22:00:00+08:00",
                "next_run": "2026-03-09T22:00:00+08:00",
                "is_active": True,
                "consecutive_failures": 0
            },
            "daily-expense-backup-prompt": {
                "last_run": "2026-03-08T21:00:00+08:00",
                "next_run": "2026-03-09T21:00:00+08:00",
                "is_active": True,
                "consecutive_failures": 0
            }
        }
        
        data = known_triggers.get(trigger_slug, {
            "last_run": None,
            "next_run": None,
            "is_active": False,
            "consecutive_failures": 0,
            "error_message": f"Trigger {trigger_slug} not found"
        })
        
        return TriggerHealth(
            trigger_slug=trigger_slug,
            last_run=data.get("last_run"),
            next_run=data.get("next_run"),
            is_active=data.get("is_active", False),
            consecutive_failures=data.get("consecutive_failures", 0),
            error_message=data.get("error_message")
        )
    
    def get_agent_status(self, agent_slug: str) -> AgentHealth:
        """Query agent status via delegation to Nebula orchestrator.
        
        Args:
            agent_slug: Slug of the agent to check
            
        Returns:
            AgentHealth object with status information
        """
        # In production, this would make an HTTP call to Nebula's internal API
        # For now, we simulate the response based on known agents
        
        known_agents = {
            "nebula-backlog-triage-manager": {
                "is_enabled": True,
                "last_delegated": "2026-03-09T07:00:00+08:00",
                "total_calls": 156,
                "failed_calls": 2,
                "error_rate": 0.013
            },
            "trello-board-manager": {
                "is_enabled": True,
                "last_delegated": "2026-03-09T06:30:00+08:00",
                "total_calls": 203,
                "failed_calls": 0,
                "error_rate": 0.0
            },
            "developer-improvement-implementation-agent": {
                "is_enabled": True,
                "last_delegated": "2026-03-09T08:00:00+08:00",
                "total_calls": 89,
                "failed_calls": 1,
                "error_rate": 0.011
            }
        }
        
        data = known_agents.get(agent_slug, {
            "is_enabled": False,
            "last_delegated": None,
            "total_calls": 0,
            "failed_calls": 0,
            "error_rate": 0.0,
            "error_message": f"Agent {agent_slug} not found"
        })
        
        return AgentHealth(
            agent_slug=agent_slug,
            is_enabled=data.get("is_enabled", False),
            last_delegated=data.get("last_delegated"),
            error_rate=data.get("error_rate", 0.0),
            total_calls=data.get("total_calls", 0),
            failed_calls=data.get("failed_calls", 0),
            error_message=data.get("error_message")
        )
    
    def get_task_status(self, task_id: str) -> TaskHealth:
        """Query task status via delegation to Nebula orchestrator.
        
        Args:
            task_id: ID of the task to check
            
        Returns:
            TaskHealth object with status information
        """
        # In production, this would make an HTTP call to Nebula's internal API
        # For now, we simulate the response
        
        # Simulate a running task with partial completion
        return TaskHealth(
            task_id=task_id,
            status="in_progress",
            last_updated="2026-03-09T08:20:00+08:00",
            total_todos=5,
            completed_todos=1,
            todo_completion_rate=0.20
        )
    
    def run_full_platform_check(self) -> PlatformHealthReport:
        """Run comprehensive platform health check.
        
        Checks all critical triggers, agents, and active tasks.
        
        Returns:
            PlatformHealthReport with aggregated results
        """
        # Check critical triggers
        trigger_slugs = [
            "combined-board-monitor-developer-every-4h",
            "scrum-master-morning-backlog-generation-10am-sgt",
            "daily-self-reflection-improvement",
            "daily-expense-backup-prompt"
        ]
        
        trigger_checks = [self.get_trigger_status(slug) for slug in trigger_slugs]
        
        # Check critical agents
        agent_slugs = [
            "nebula-backlog-triage-manager",
            "trello-board-manager",
            "developer-improvement-implementation-agent"
        ]
        
        agent_checks = [self.get_agent_status(slug) for slug in agent_slugs]
        
        # Check active tasks (simulated)
        task_checks = [
            self.get_task_status("tsk_069ae12f4257758a8000324ae1382d35")
        ]
        
        # Aggregate unhealthy items
        unhealthy_items = []
        
        for trigger in trigger_checks:
            if not trigger.is_healthy:
                unhealthy_items.append(f"Trigger: {trigger.trigger_slug} - {trigger.error_message or 'Not active or has failures'}")
        
        for agent in agent_checks:
            if not agent.is_healthy:
                unhealthy_items.append(f"Agent: {agent.agent_slug} - {agent.error_message or f'Error rate: {agent.error_rate:.1%}'}")
        
        for task in task_checks:
            if not task.is_healthy:
                unhealthy_items.append(f"Task: {task.task_id} - {task.error_message or task.status}")
        
        # Calculate totals
        total_checks = len(trigger_checks) + len(agent_checks) + len(task_checks)
        failed_checks = len(unhealthy_items)
        overall_healthy = failed_checks == 0
        
        # Create report
        report = PlatformHealthReport(
            overall_healthy=overall_healthy,
            unhealthy_items=unhealthy_items,
            trigger_checks=trigger_checks,
            agent_checks=agent_checks,
            task_checks=task_checks,
            generated_at=datetime.now().isoformat(),
            total_checks=total_checks,
            failed_checks=failed_checks
        )
        
        # Save report to disk
        self._save_report(report)
        
        return report
    
    def _save_report(self, report: PlatformHealthReport) -> None:
        """Save platform health report to disk.
        
        Args:
            report: PlatformHealthReport to save
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.logs_dir / f"platform_health_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)
        
        print(f"Platform health report saved to: {filename}")


if __name__ == "__main__":
    # Demo usage
    print("Running platform health check...")
    proxy = PlatformHealthProxy()
    report = proxy.run_full_platform_check()
    
    print(f"\nPlatform Health Status: {'HEALTHY' if report.overall_healthy else 'UNHEALTHY'}")
    print(f"Total checks: {report.total_checks}")
    print(f"Failed checks: {report.failed_checks}")
    
    if report.unhealthy_items:
        print("\nUnhealthy items:")
        for item in report.unhealthy_items:
            print(f"  - {item}")
    else:
        print("\nAll systems operational!")

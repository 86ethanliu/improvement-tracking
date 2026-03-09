#!/usr/bin/env python3
"""Proof-of-Execution Logger for Workflow Auditing.

This module provides a thread-safe logging system for recording verifiable proof
artifacts from automation workflows. Each workflow step can emit a ProofEntry that
is appended to a JSONL file for later audit and analysis.

Inspired by SOUL.md principle: show proof through execution, not words.
"""

import json
import os
import threading
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
import fcntl


class ArtifactType(Enum):
    """Types of proof artifacts that can be logged."""
    TRELLO_CARD_MOVED = "trello_card_moved"
    TRELLO_COMMENT_POSTED = "trello_comment_posted"
    FILE_WRITTEN = "file_written"
    TELEGRAM_SENT = "telegram_sent"
    API_CALL_SUCCESS = "api_call_success"
    NOTION_ENTRY_CREATED = "notion_entry_created"


@dataclass
class ProofEntry:
    """A single proof-of-execution entry.
    
    Attributes:
        workflow_name: Name of the workflow generating the proof
        step_name: Specific step within the workflow
        timestamp: ISO 8601 timestamp of the event
        artifact_type: Type of artifact being logged
        artifact_value: The actual proof value (card ID, file path, etc.)
        success: Whether the operation succeeded
        error_message: Optional error details if success=False
    """
    workflow_name: str
    step_name: str
    timestamp: str
    artifact_type: str
    artifact_value: str
    success: bool
    error_message: Optional[str] = None


class ProofLogger:
    """Thread-safe logger for workflow proof-of-execution artifacts.
    
    This class ensures that multiple workflows can safely log proof entries
    concurrently without file corruption. Uses file locking for safety.
    """
    
    def __init__(self, log_file: str = "logs/proof_of_execution.jsonl"):
        """Initialize the ProofLogger.
        
        Args:
            log_file: Path to the JSONL log file
        """
        self.log_file = Path(log_file)
        self._lock = threading.Lock()
        self._session_entries = []
        
        # Ensure the logs directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create the log file if it doesn't exist
        if not self.log_file.exists():
            self.log_file.touch()
    
    def log_proof(self, entry: ProofEntry) -> bool:
        """Log a proof entry to the JSONL file.
        
        Args:
            entry: ProofEntry to log
            
        Returns:
            True if successfully logged, False otherwise
        """
        with self._lock:
            try:
                # Store in session for summary
                self._session_entries.append(entry)
                
                # Convert entry to JSON line
                entry_dict = asdict(entry)
                json_line = json.dumps(entry_dict) + "\n"
                
                # Write with file locking
                with open(self.log_file, 'a') as f:
                    # Acquire exclusive lock
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        f.write(json_line)
                        f.flush()
                        os.fsync(f.fileno())
                    finally:
                        # Release lock
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                
                return True
                
            except Exception as e:
                print(f"ERROR: Failed to log proof entry: {e}")
                return False
    
    def log_trello_move(self, card_id: str, from_list: str, to_list: str, 
                       card_name: str, success: bool = True, 
                       error_message: Optional[str] = None) -> bool:
        """Convenience method to log a Trello card move.
        
        Args:
            card_id: Trello card ID
            from_list: Source list name
            to_list: Destination list name
            card_name: Name of the card
            success: Whether the move succeeded
            error_message: Optional error details
            
        Returns:
            True if successfully logged
        """
        entry = ProofEntry(
            workflow_name="trello_operations",
            step_name="move_card",
            timestamp=datetime.now().isoformat(),
            artifact_type=ArtifactType.TRELLO_CARD_MOVED.value,
            artifact_value=json.dumps({
                "card_id": card_id,
                "card_name": card_name,
                "from_list": from_list,
                "to_list": to_list
            }),
            success=success,
            error_message=error_message
        )
        return self.log_proof(entry)
    
    def log_trello_comment(self, card_id: str, card_name: str, 
                          comment_preview: str, success: bool = True,
                          error_message: Optional[str] = None) -> bool:
        """Convenience method to log a Trello comment post.
        
        Args:
            card_id: Trello card ID
            card_name: Name of the card
            comment_preview: First 100 chars of the comment
            success: Whether the comment was posted
            error_message: Optional error details
            
        Returns:
            True if successfully logged
        """
        entry = ProofEntry(
            workflow_name="trello_operations",
            step_name="post_comment",
            timestamp=datetime.now().isoformat(),
            artifact_type=ArtifactType.TRELLO_COMMENT_POSTED.value,
            artifact_value=json.dumps({
                "card_id": card_id,
                "card_name": card_name,
                "comment_preview": comment_preview[:100]
            }),
            success=success,
            error_message=error_message
        )
        return self.log_proof(entry)
    
    def log_file_write(self, path: str, size_bytes: int, 
                      workflow_name: str = "file_operations",
                      success: bool = True,
                      error_message: Optional[str] = None) -> bool:
        """Convenience method to log a file write operation.
        
        Args:
            path: File path that was written
            size_bytes: Size of the file in bytes
            workflow_name: Name of the workflow writing the file
            success: Whether the write succeeded
            error_message: Optional error details
            
        Returns:
            True if successfully logged
        """
        entry = ProofEntry(
            workflow_name=workflow_name,
            step_name="write_file",
            timestamp=datetime.now().isoformat(),
            artifact_type=ArtifactType.FILE_WRITTEN.value,
            artifact_value=json.dumps({
                "path": path,
                "size_bytes": size_bytes
            }),
            success=success,
            error_message=error_message
        )
        return self.log_proof(entry)
    
    def log_telegram_sent(self, message_preview: str, chat_id: str,
                         workflow_name: str = "telegram_notifications",
                         success: bool = True,
                         error_message: Optional[str] = None) -> bool:
        """Convenience method to log a Telegram message send.
        
        Args:
            message_preview: First 100 chars of the message
            chat_id: Telegram chat ID
            workflow_name: Name of the workflow sending the message
            success: Whether the send succeeded
            error_message: Optional error details
            
        Returns:
            True if successfully logged
        """
        entry = ProofEntry(
            workflow_name=workflow_name,
            step_name="send_telegram",
            timestamp=datetime.now().isoformat(),
            artifact_type=ArtifactType.TELEGRAM_SENT.value,
            artifact_value=json.dumps({
                "message_preview": message_preview[:100],
                "chat_id": chat_id
            }),
            success=success,
            error_message=error_message
        )
        return self.log_proof(entry)
    
    def log_notion_entry(self, entry_id: str, entry_title: str,
                        workflow_name: str = "notion_operations",
                        success: bool = True,
                        error_message: Optional[str] = None) -> bool:
        """Convenience method to log a Notion entry creation.
        
        Args:
            entry_id: Notion entry ID
            entry_title: Title of the entry
            workflow_name: Name of the workflow creating the entry
            success: Whether the creation succeeded
            error_message: Optional error details
            
        Returns:
            True if successfully logged
        """
        entry = ProofEntry(
            workflow_name=workflow_name,
            step_name="create_notion_entry",
            timestamp=datetime.now().isoformat(),
            artifact_type=ArtifactType.NOTION_ENTRY_CREATED.value,
            artifact_value=json.dumps({
                "entry_id": entry_id,
                "entry_title": entry_title
            }),
            success=success,
            error_message=error_message
        )
        return self.log_proof(entry)
    
    def get_session_summary(self) -> dict:
        """Get a summary of proof entries logged in the current session.
        
        Returns:
            Dictionary with pass_rate, failures, total_steps, and failure_details
        """
        if not self._session_entries:
            return {
                "total_steps": 0,
                "passed": 0,
                "failed": 0,
                "pass_rate": 0.0,
                "failures": []
            }
        
        total = len(self._session_entries)
        passed = sum(1 for e in self._session_entries if e.success)
        failed = total - passed
        pass_rate = (passed / total * 100) if total > 0 else 0.0
        
        failures = [
            {
                "workflow": e.workflow_name,
                "step": e.step_name,
                "timestamp": e.timestamp,
                "error": e.error_message
            }
            for e in self._session_entries if not e.success
        ]
        
        return {
            "total_steps": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(pass_rate, 2),
            "failures": failures
        }


if __name__ == "__main__":
    """Example usage demonstrating the ProofLogger."""
    print("=" * 70)
    print("Proof-of-Execution Logger - Example Usage")
    print("=" * 70)
    
    # Initialize logger
    logger = ProofLogger()
    print(f"\nInitialized logger with file: {logger.log_file}")
    
    # Example 1: Log a successful Trello card move
    print("\n[1] Logging successful Trello card move...")
    success = logger.log_trello_move(
        card_id="699d06cfa300138d8238cd9b",
        from_list="Implementation",
        to_list="Check-in",
        card_name="Card #52 - Workflow Proof-of-Execution Audit"
    )
    print(f"    Result: {'✓ Logged' if success else '✗ Failed'}")
    
    # Example 2: Log a Trello comment
    print("\n[2] Logging Trello comment...")
    success = logger.log_trello_comment(
        card_id="699d06cfa300138d8238cd9b",
        card_name="Card #52 - Workflow Proof-of-Execution Audit",
        comment_preview="[Developer] Implementation complete. All acceptance criteria met."
    )
    print(f"    Result: {'✓ Logged' if success else '✗ Failed'}")
    
    # Example 3: Log a file write
    print("\n[3] Logging file write operation...")
    success = logger.log_file_write(
        path="scripts/audit/proof_logger.py",
        size_bytes=12450,
        workflow_name="card_52_implementation"
    )
    print(f"    Result: {'✓ Logged' if success else '✗ Failed'}")
    
    # Example 4: Log a Telegram notification
    print("\n[4] Logging Telegram notification...")
    success = logger.log_telegram_sent(
        message_preview="Card #52 moved to Check-in. Proof-of-execution audit system complete.",
        chat_id="thrd_06989867443c7cac80009fc40577ff59",
        workflow_name="board_monitor"
    )
    print(f"    Result: {'✓ Logged' if success else '✗ Failed'}")
    
    # Example 5: Log a failed operation
    print("\n[5] Logging failed operation...")
    entry = ProofEntry(
        workflow_name="morning_backlog_generation",
        step_name="fetch_cards",
        timestamp=datetime.now().isoformat(),
        artifact_type=ArtifactType.API_CALL_SUCCESS.value,
        artifact_value="trello_api_list_cards",
        success=False,
        error_message="API rate limit exceeded (429)"
    )
    success = logger.log_proof(entry)
    print(f"    Result: {'✓ Logged' if success else '✗ Failed'}")
    
    # Get session summary
    print("\n" + "=" * 70)
    print("Session Summary")
    print("=" * 70)
    summary = logger.get_session_summary()
    print(f"\nTotal steps: {summary['total_steps']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Pass rate: {summary['pass_rate']}%")
    
    if summary['failures']:
        print("\nFailures:")
        for i, failure in enumerate(summary['failures'], 1):
            print(f"  {i}. {failure['workflow']} -> {failure['step']}")
            print(f"     Error: {failure['error']}")
    
    print(f"\n✓ All proof entries written to: {logger.log_file}")
    print("\nTo view the log file:")
    print(f"  cat {logger.log_file}")
    print("\nTo generate an audit report:")
    print("  python scripts/audit/audit_report.py --date 2026-03-09")
    print("\n" + "=" * 70)

"""
Smart message tracking and deduplication system for FLO-2D GUI.

This module implements intelligent message management to eliminate redundant
messages while providing clear progress updates for technical users.
"""

import time
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum


class OperationState(Enum):
    """States for tracked operations."""
    STARTING = "starting"
    IN_PROGRESS = "in_progress" 
    COMPLETING = "completing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TrackedOperation:
    """Container for tracking operation state and progress."""
    operation_id: str
    operation_type: str
    start_time: float
    state: OperationState = OperationState.STARTING
    progress: float = 0.0
    current_detail: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    message_id: Optional[str] = None
    last_update: float = field(default_factory=time.time)
    
    def update_progress(self, progress: float, detail: str = ""):
        """Update operation progress and detail."""
        self.progress = max(0.0, min(1.0, progress))
        if detail:
            self.current_detail = detail
        self.last_update = time.time()
        if self.progress >= 1.0:
            self.state = OperationState.COMPLETING
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time since operation start."""
        return time.time() - self.start_time
    
    def get_estimated_remaining(self) -> Optional[float]:
        """Estimate remaining time based on current progress."""
        if self.progress <= 0:
            return None
        elapsed = self.get_elapsed_time()
        estimated_total = elapsed / self.progress
        return max(0, estimated_total - elapsed)


class SmartMessageTracker:
    """
    Intelligent message tracking system that prevents message duplication
    and provides consolidated progress updates.
    """
    
    def __init__(self, message_callback: Optional[Callable] = None):
        """
        Initialize the message tracker.
        
        Args:
            message_callback: Function to call for GUI message updates
        """
        self.message_callback = message_callback
        self.active_operations: Dict[str, TrackedOperation] = {}
        self.completed_operations: Dict[str, TrackedOperation] = {}
        self.message_history: Dict[str, float] = {}  # message -> last_sent_time
        self.duplicate_threshold = 2.0  # seconds to prevent duplicate messages
        
    def start_operation(self, operation_id: str, operation_type: str, initial_message: str, category: str = 'processing') -> str:
        """
        Start tracking a new operation.
        
        Args:
            operation_id: Unique identifier for the operation
            operation_type: Type of operation (file_extraction, spatial_processing, etc.)
            initial_message: Initial status message
            category: Message category for styling
            
        Returns:
            Message ID for GUI reference
        """
        operation = TrackedOperation(
            operation_id=operation_id,
            operation_type=operation_type,
            start_time=time.time(),
            current_detail=initial_message
        )
        
        self.active_operations[operation_id] = operation
        
        # Send initial message to GUI
        message_id = self._send_message(initial_message, category)
        operation.message_id = message_id
        
        return message_id
    
    def update_operation(self, operation_id: str, progress: float, detail: str = "", 
                        show_progress: bool = True) -> bool:
        """
        Update an existing operation's progress.
        
        Args:
            operation_id: ID of operation to update
            progress: Progress value (0.0 to 1.0)
            detail: Additional detail text
            show_progress: Whether to show progress percentage
            
        Returns:
            True if update was sent to GUI, False otherwise
        """
        if operation_id not in self.active_operations:
            return False
        
        operation = self.active_operations[operation_id]
        operation.update_progress(progress, detail)
        
        # Construct progress message
        if show_progress and progress > 0:
            progress_text = f"{progress*100:.0f}% - {detail}" if detail else f"{progress*100:.0f}% complete"
        else:
            progress_text = detail
        
        # Check if we should send update (throttle frequent updates)
        if self._should_send_update(operation):
            self._update_message(operation.message_id, progress_text, 'processing')
            return True
        
        return False
    
    def complete_operation(self, operation_id: str, final_message: str, category: str = 'validation') -> Optional[str]:
        """
        Mark an operation as completed with final result message.
        
        Args:
            operation_id: ID of operation to complete
            final_message: Final status/result message
            category: Message category for final message
            
        Returns:
            Message ID for final message, or None if operation not found
        """
        if operation_id not in self.active_operations:
            return None
        
        operation = self.active_operations[operation_id]
        operation.state = OperationState.COMPLETED
        operation.progress = 1.0
        operation.current_detail = final_message
        
        # Replace the progress message with final result
        message_id = self._replace_message(operation.message_id, final_message, category)
        
        # Move to completed operations
        self.completed_operations[operation_id] = operation
        del self.active_operations[operation_id]
        
        return message_id
    
    def fail_operation(self, operation_id: str, error_message: str) -> Optional[str]:
        """
        Mark an operation as failed with error message.
        
        Args:
            operation_id: ID of operation that failed
            error_message: Error description
            
        Returns:
            Message ID for error message
        """
        if operation_id not in self.active_operations:
            return None
        
        operation = self.active_operations[operation_id]
        operation.state = OperationState.FAILED
        operation.current_detail = error_message
        
        # Replace with error message
        message_id = self._replace_message(operation.message_id, error_message, 'error')
        
        # Move to completed operations
        self.completed_operations[operation_id] = operation
        del self.active_operations[operation_id]
        
        return message_id
    
    def is_operation_active(self, operation_id: str) -> bool:
        """Check if an operation is currently active."""
        return operation_id in self.active_operations
    
    def get_operation_status(self, operation_id: str) -> Optional[TrackedOperation]:
        """Get current status of an operation."""
        return self.active_operations.get(operation_id) or self.completed_operations.get(operation_id)
    
    def get_active_operations(self) -> Dict[str, TrackedOperation]:
        """Get all currently active operations."""
        return self.active_operations.copy()
    
    def send_standalone_message(self, message: str, category: str = 'info') -> str:
        """
        Send a standalone message that isn't part of a tracked operation.
        
        Args:
            message: Message text
            category: Message category
            
        Returns:
            Message ID
        """
        # Check for recent duplicates
        if self._is_duplicate_message(message):
            return ""
        
        message_id = self._send_message(message, category)
        self.message_history[message] = time.time()
        return message_id
    
    def _should_send_update(self, operation: TrackedOperation) -> bool:
        """Determine if an operation update should be sent to GUI."""
        # Always send first update
        if operation.state == OperationState.STARTING:
            operation.state = OperationState.IN_PROGRESS
            return True
        
        # Throttle updates - don't send more than once per second
        time_since_update = time.time() - operation.last_update
        if time_since_update < 1.0:
            return False
        
        # Send significant progress milestones
        progress_milestones = [0.25, 0.5, 0.75, 0.9, 1.0]
        for milestone in progress_milestones:
            if abs(operation.progress - milestone) < 0.05:
                return True
        
        return False
    
    def _is_duplicate_message(self, message: str) -> bool:
        """Check if message was sent recently."""
        if message in self.message_history:
            time_since_last = time.time() - self.message_history[message]
            return time_since_last < self.duplicate_threshold
        return False
    
    def _send_message(self, message: str, category: str) -> str:
        """Send message to GUI callback."""
        message_id = f"msg_{int(time.time() * 1000)}"  # Timestamp-based ID
        
        if self.message_callback:
            self.message_callback(message, category, message_id)
        
        return message_id
    
    def _update_message(self, message_id: str, message: str, category: str) -> None:
        """Update existing message in GUI."""
        if self.message_callback and hasattr(self.message_callback, 'update_message'):
            self.message_callback.update_message(message_id, message, category)
        else:
            # Fallback to new message if update not supported
            self._send_message(message, category)
    
    def _replace_message(self, message_id: str, message: str, category: str) -> str:
        """Replace existing message with new content."""
        if self.message_callback and hasattr(self.message_callback, 'replace_message'):
            return self.message_callback.replace_message(message_id, message, category)
        else:
            # Fallback to new message
            return self._send_message(message, category)
    
    def cleanup_old_operations(self, max_age_hours: float = 24) -> int:
        """
        Clean up old completed operations to prevent memory buildup.
        
        Args:
            max_age_hours: Maximum age of completed operations to keep
            
        Returns:
            Number of operations cleaned up
        """
        cutoff_time = time.time() - (max_age_hours * 3600)
        to_remove = []
        
        for op_id, operation in self.completed_operations.items():
            if operation.start_time < cutoff_time:
                to_remove.append(op_id)
        
        for op_id in to_remove:
            del self.completed_operations[op_id]
        
        return len(to_remove)
    
    def get_processing_summary(self) -> Dict[str, Any]:
        """Get summary of current processing state."""
        active_count = len(self.active_operations)
        completed_count = len(self.completed_operations)
        failed_count = sum(1 for op in self.completed_operations.values() 
                          if op.state == OperationState.FAILED)
        
        total_processing_time = sum(op.get_elapsed_time() 
                                  for op in self.completed_operations.values())
        
        return {
            'active_operations': active_count,
            'completed_operations': completed_count,
            'failed_operations': failed_count,
            'total_processing_time': total_processing_time,
            'operations_by_type': self._group_operations_by_type()
        }
    
    def _group_operations_by_type(self) -> Dict[str, int]:
        """Group operations by type for summary."""
        type_counts = {}
        
        all_operations = list(self.active_operations.values()) + list(self.completed_operations.values())
        
        for operation in all_operations:
            op_type = operation.operation_type
            type_counts[op_type] = type_counts.get(op_type, 0) + 1
        
        return type_counts
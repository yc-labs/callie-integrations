"""
Models for sync execution results and status tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class SyncStatus(str, Enum):
    """Status of a sync execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SyncItemStatus(BaseModel):
    """Status of a single item sync."""
    sku: str
    status: str  # success, failed, skipped
    message: Optional[str] = None


class SyncExecutionStatus(BaseModel):
    """Status of sync execution."""
    total_items: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    items: List[SyncItemStatus] = Field(default_factory=list)


class SyncExecution(BaseModel):
    """Represents a sync execution instance."""
    id: str
    config_id: str
    status: SyncStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_items: int = 0
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    results: List[Dict[str, Any]] = Field(default_factory=list)
    error_message: Optional[str] = None
    triggered_by: Optional[str] = None
    execution_time_seconds: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the execution."""
        return {
            "id": self.id,
            "config_id": self.config_id,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_items": self.total_items,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "execution_time_seconds": self.execution_time_seconds
        } 
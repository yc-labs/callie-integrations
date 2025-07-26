"""
Models for sync execution results and tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class SyncItemStatus(str, Enum):
    """Status of individual sync items."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    MATCH = "match"
    DIFF = "diff"
    NOT_FOUND = "not_found"


class SyncExecutionStatus(str, Enum):
    """Status of overall sync execution."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SyncResult(BaseModel):
    """Result of syncing a single item."""
    sku: str = Field(..., description="SKU that was synced")
    status: SyncItemStatus = Field(..., description="Status of this item sync")
    source_value: Any = Field(None, description="Value from source system")
    target_value: Any = Field(None, description="Value in target system")
    new_value: Any = Field(None, description="New value set in target")
    message: Optional[str] = Field(None, description="Additional details or error message")


class SyncExecution(BaseModel):
    """
    Record of a sync execution.
    This is stored in Firestore under sync_executions collection.
    """
    # Identity
    id: str = Field(..., description="Unique execution ID")
    config_id: str = Field(..., description="ID of the sync config that was executed")
    
    # Execution Details
    status: SyncExecutionStatus = Field(..., description="Current execution status")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None, description="When execution completed")
    
    # Results
    total_items: int = Field(0, description="Total items processed")
    success_count: int = Field(0, description="Number of successful syncs")
    failed_count: int = Field(0, description="Number of failed syncs")
    skipped_count: int = Field(0, description="Number of skipped items")
    
    # Detailed Results
    results: List[SyncResult] = Field(default_factory=list, description="Individual item results")
    
    # Error Information
    error_message: Optional[str] = Field(None, description="Error message if execution failed")
    
    # Metadata
    triggered_by: str = Field("system", description="What triggered this sync (scheduler, manual, api)")
    execution_time_seconds: Optional[float] = Field(None, description="Total execution time")
    
    def to_firestore(self) -> Dict[str, Any]:
        """Convert to Firestore document format."""
        data = self.model_dump()
        # Convert datetime objects to ISO strings
        if data.get("started_at"):
            data["started_at"] = data["started_at"].isoformat()
        if data.get("completed_at"):
            data["completed_at"] = data["completed_at"].isoformat()
        return data
    
    @classmethod
    def from_firestore(cls, doc_id: str, data: Dict[str, Any]) -> "SyncExecution":
        """Create instance from Firestore document."""
        # Convert ISO strings back to datetime
        if data.get("started_at") and isinstance(data["started_at"], str):
            data["started_at"] = datetime.fromisoformat(data["started_at"].replace("Z", "+00:00"))
        if data.get("completed_at") and isinstance(data["completed_at"], str):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"].replace("Z", "+00:00"))
        
        data["id"] = doc_id
        return cls(**data)
    
    def mark_completed(self, success_count: int, failed_count: int, skipped_count: int) -> None:
        """Mark execution as completed with final counts."""
        self.status = SyncExecutionStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.success_count = success_count
        self.failed_count = failed_count
        self.skipped_count = skipped_count
        self.total_items = success_count + failed_count + skipped_count
        
        if self.started_at and self.completed_at:
            self.execution_time_seconds = (self.completed_at - self.started_at).total_seconds()
    
    def mark_failed(self, error_message: str) -> None:
        """Mark execution as failed."""
        self.status = SyncExecutionStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        
        if self.started_at and self.completed_at:
            self.execution_time_seconds = (self.completed_at - self.started_at).total_seconds()
    
    def add_result(self, result: SyncResult) -> None:
        """Add a sync result to this execution."""
        self.results.append(result)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of this execution."""
        return {
            "id": self.id,
            "config_id": self.config_id,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_items": self.total_items,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "execution_time_seconds": self.execution_time_seconds,
            "triggered_by": self.triggered_by
        } 
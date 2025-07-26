"""
Configuration models for sync operations.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field


class SyncStatus(str, Enum):
    """Status of a sync configuration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class ServiceConnection(BaseModel):
    """Configuration for connecting to a service."""
    service_type: str = Field(..., description="Type of service (shipstation, infiplex, feedonomics)")
    credentials: Dict[str, str] = Field(..., description="Service authentication credentials")
    base_url: str = Field(..., description="Base URL for the service API")
    warehouse_id: Optional[int] = Field(None, description="Default warehouse ID for operations")
    
    class Config:
        extra = "allow"  # Allow additional service-specific config


class FieldMapping(BaseModel):
    """Maps a field from source to target service."""
    source_field: str = Field(..., description="Field name in source service")
    target_field: str = Field(..., description="Field name in target service") 
    transform: Optional[str] = Field(None, description="Optional transform to apply")
    required: bool = Field(True, description="Whether this mapping is required")


class SyncConfig(BaseModel):
    """
    Configuration for a sync operation between two services.
    This is stored in Firestore.
    """
    # Identity
    id: str = Field(..., description="Unique identifier for this config")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(None, description="Optional description")
    
    # Service Configuration
    source: ServiceConnection = Field(..., description="Source service configuration")
    target: ServiceConnection = Field(..., description="Target service configuration")
    
    # Field Mappings
    field_mappings: List[FieldMapping] = Field(..., description="How to map fields between services")
    
    # Scheduling
    schedule: Optional[str] = Field(None, description="Cron expression for scheduling")
    
    # Status and Metadata
    status: SyncStatus = Field(SyncStatus.ACTIVE, description="Current status")
    active: bool = Field(True, description="Whether this config is active")
    
    # Sync Options
    sync_options: Dict[str, Any] = Field(default_factory=dict, description="Additional sync options")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_sync_at: Optional[datetime] = Field(None, description="When sync was last executed")
    
    # Owner/Team
    created_by: Optional[str] = Field(None, description="User who created this config")
    team: Optional[str] = Field(None, description="Team that owns this config")
    
    def to_firestore(self) -> Dict[str, Any]:
        """Convert to Firestore document format."""
        data = self.model_dump()
        # Convert datetime objects to Firestore timestamps
        if data.get("created_at"):
            data["created_at"] = data["created_at"].isoformat()
        if data.get("updated_at"):
            data["updated_at"] = data["updated_at"].isoformat()
        if data.get("last_sync_at"):
            data["last_sync_at"] = data["last_sync_at"].isoformat()
        return data
    
    @classmethod
    def from_firestore(cls, doc_id: str, data: Dict[str, Any]) -> "SyncConfig":
        """Create instance from Firestore document."""
        # Convert ISO strings back to datetime
        if data.get("created_at") and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        if data.get("updated_at") and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
        if data.get("last_sync_at") and isinstance(data["last_sync_at"], str):
            data["last_sync_at"] = datetime.fromisoformat(data["last_sync_at"].replace("Z", "+00:00"))
        
        data["id"] = doc_id
        return cls(**data)
    
    def get_source_connector_config(self) -> Dict[str, Any]:
        """Get configuration for source connector."""
        return {
            "credentials": self.source.credentials,
            "base_url": self.source.base_url,
            **{k: v for k, v in self.source.model_dump().items() 
               if k not in ["service_type", "credentials", "base_url"]}
        }
    
    def get_target_connector_config(self) -> Dict[str, Any]:
        """Get configuration for target connector."""
        return {
            "credentials": self.target.credentials,
            "base_url": self.target.base_url,
            **{k: v for k, v in self.target.model_dump().items() 
               if k not in ["service_type", "credentials", "base_url"]}
        } 
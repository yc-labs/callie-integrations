"""
Stage-based configuration models for fully configurable sync workflows.

This allows users to configure entire sync workflows by chaining together
connector methods and passing data between stages.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field
from dataclasses import dataclass, field


class StageType(str, Enum):
    """Available stage types that can be configured."""
    # Connector method calls
    CONNECTOR_METHOD = "connector_method"
    
    # Data processing stages
    TRANSFORM = "transform"
    FILTER = "filter"
    MAP_FIELDS = "map_fields"
    
    # Flow control
    CONDITION = "condition"
    LOOP = "loop"
    
    # Utility stages
    LOG = "log"
    SET_VARIABLE = "set_variable"


class StageErrorStrategy(str, Enum):
    """How to handle errors in a stage."""
    FAIL = "fail"      # Stop execution and fail
    SKIP = "skip"      # Skip this stage and continue
    CONTINUE = "continue"  # Log error but continue
    RETRY = "retry"    # Retry the stage


class StageConfig(BaseModel):
    """Configuration for a single stage in the workflow."""
    
    # Identity
    id: str = Field(..., description="Unique stage identifier")
    name: Optional[str] = Field(None, description="Human-readable stage name")
    description: Optional[str] = Field(None, description="Stage description")
    
    # Stage execution
    type: StageType = Field(..., description="Type of stage")
    enabled: bool = Field(True, description="Whether this stage is enabled")
    
    # For connector_method stages
    connector: Optional[str] = Field(None, description="Connector name (source/target)")
    method: Optional[str] = Field(None, description="Method name to call on connector")
    
    # Credentials
    credentials_key: Optional[str] = Field(None, description="Key for stage-specific credentials from credentials_config")
    
    # Parameters and data
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Stage parameters")
    input_variables: List[str] = Field(default_factory=list, description="Variables to use as input")
    output_variable: Optional[str] = Field(None, description="Variable name to store output")
    
    # Flow control
    depends_on: List[str] = Field(default_factory=list, description="Stage IDs this depends on")
    condition: Optional[str] = Field(None, description="Condition to check before execution")
    
    # Error handling
    error_strategy: StageErrorStrategy = Field(StageErrorStrategy.FAIL, description="How to handle errors")
    retry_count: int = Field(0, description="Number of retries for retry strategy")
    retry_delay: int = Field(5, description="Delay between retries in seconds")


class StageResult(BaseModel):
    """Result of executing a single stage."""
    
    stage_id: str = Field(..., description="Stage that was executed")
    status: str = Field(..., description="success, failed, skipped")
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)
    execution_time_seconds: Optional[float] = Field(None)
    
    # Results
    output_data: Any = Field(None, description="Data output from this stage")
    items_processed: int = Field(0, description="Number of items processed")
    
    # Errors
    error_message: Optional[str] = Field(None)
    retry_count: int = Field(0, description="Number of retries attempted")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowConfig(BaseModel):
    """Complete workflow configuration using stages."""
    
    # Identity
    id: str = Field(..., description="Unique workflow identifier")
    name: str = Field(..., description="Human-readable workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    version: str = Field("1.0", description="Workflow version")
    
    # Connectors
    source: Dict[str, Any] = Field(..., description="Source connector configuration")
    target: Dict[str, Any] = Field(..., description="Target connector configuration")
    
    # Credentials configuration for per-stage credentials
    credentials_config: Optional[Dict[str, Dict[str, Any]]] = Field(None, description="Named credential configurations for stages")
    
    # Workflow stages
    stages: List[StageConfig] = Field(..., description="Ordered list of stages")
    
    # Global settings
    variables: Dict[str, Any] = Field(default_factory=dict, description="Global workflow variables")
    timeout_seconds: int = Field(3600, description="Overall workflow timeout")
    
    # Scheduling
    schedule: Optional[str] = Field(None, description="Cron expression for scheduling")
    active: bool = Field(True, description="Whether workflow is active")
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = Field(None)


class WorkflowExecution(BaseModel):
    """Record of a workflow execution."""
    
    id: str = Field(..., description="Unique execution identifier")
    workflow_id: str = Field(..., description="Workflow that was executed")
    
    # Execution timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = Field(None)
    execution_time_seconds: Optional[float] = Field(None)
    
    # Status
    status: str = Field("running", description="running, completed, failed, cancelled")
    
    # Results
    stage_results: List[StageResult] = Field(default_factory=list)
    total_stages: int = Field(0)
    completed_stages: int = Field(0)
    failed_stages: int = Field(0)
    skipped_stages: int = Field(0)
    
    # Final output
    final_variables: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = Field(None)
    
    # Trigger info
    triggered_by: str = Field("manual")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowUpdate(BaseModel):
    """Updatable fields for a workflow."""
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    source: Optional[Dict[str, Any]] = None
    target: Optional[Dict[str, Any]] = None
    credentials_config: Optional[Dict[str, Dict[str, Any]]] = None
    stages: Optional[List[StageConfig]] = None
    variables: Optional[Dict[str, Any]] = None
    timeout_seconds: Optional[int] = None
    schedule: Optional[str] = None
    active: Optional[bool] = None
    created_by: Optional[str] = None 


@dataclass
class IntegrationConfig:
    """Configuration for an integration with default credentials."""
    id: str
    name: str
    service_type: str  # e.g., "shipstation", "infiplex"
    description: Optional[str] = None
    default_credentials: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def model_dump(self) -> Dict[str, Any]:
        """Convert to dictionary for Firestore storage."""
        return {
            "id": self.id,
            "name": self.name,
            "service_type": self.service_type,
            "description": self.description,
            "default_credentials": self.default_credentials,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        } 
"""
Main FastAPI application for Callie Integrations.
"""

import logging
import os
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..models.config import SyncConfig, ServiceConnection, FieldMapping
from ..models.sync import SyncExecution, SyncStatus
from ..models.stages import WorkflowConfig, WorkflowExecution
from ..services.firestore import FirestoreService
from ..services.scheduler import SchedulerService
from ..engine.sync import SyncEngine
from ..engine.workflow_engine import WorkflowEngine
from ..connectors import CONNECTOR_REGISTRY
from ..version import __version__

logger = logging.getLogger(__name__)

# Global services (initialized in lifespan)
firestore_service: Optional[FirestoreService] = None
scheduler_service: Optional[SchedulerService] = None
sync_engine: Optional[SyncEngine] = None
workflow_engine: Optional[WorkflowEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global firestore_service, scheduler_service, sync_engine, workflow_engine
    
    # Initialize services
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    region = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
    
    try:
        # Initialize Firestore service
        try:
            firestore_service = FirestoreService(project_id=project_id)
            logger.info("Firestore service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore service: {e}")
            firestore_service = None
        
        # Initialize Scheduler service
        try:
            scheduler_service = SchedulerService(project_id=project_id, region=region)
            logger.info("Scheduler service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Scheduler service: {e}")
            scheduler_service = None
        
        # Initialize Sync Engine
        sync_engine = SyncEngine()
        logger.info("Sync engine initialized successfully")
        
        # Initialize Workflow Engine
        workflow_engine = WorkflowEngine()
        logger.info("Workflow engine initialized successfully")
        
        logger.info("Application startup complete")
        
    except Exception as e:
        logger.error(f"Failed to initialize application services: {e}")
        # Don't raise - let the app start but services will be None
    
    yield
    
    # Cleanup on shutdown
    logger.info("Application shutdown")


app = FastAPI(
    title="Callie Integration API",
    description="API for managing data synchronization between business systems",
    version=__version__,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency injection
def get_firestore_service() -> FirestoreService:
    if firestore_service is None:
        raise HTTPException(status_code=500, detail="Firestore service not initialized")
    return firestore_service

def get_scheduler_service() -> SchedulerService:
    if scheduler_service is None:
        raise HTTPException(status_code=500, detail="Scheduler service not initialized")
    return scheduler_service

def get_sync_engine() -> SyncEngine:
    if sync_engine is None:
        raise HTTPException(status_code=500, detail="Sync engine not initialized")
    return sync_engine

def get_workflow_engine() -> WorkflowEngine:
    if workflow_engine is None:
        raise HTTPException(status_code=500, detail="Workflow engine not initialized")
    return workflow_engine


# Request/Response models
class CreateConfigRequest(BaseModel):
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(None, description="Optional description")
    source: ServiceConnection = Field(..., description="Source service configuration")
    target: ServiceConnection = Field(..., description="Target service configuration")
    field_mappings: List[FieldMapping] = Field(..., description="Field mappings")
    schedule: Optional[str] = Field(None, description="Cron expression for scheduling")
    sync_options: Dict[str, Any] = Field(default_factory=dict, description="Sync options")
    active: bool = Field(True, description="Whether config is active")


class UpdateConfigRequest(BaseModel):
    name: Optional[str] = Field(None, description="Human-readable name")
    description: Optional[str] = Field(None, description="Optional description")
    source: Optional[ServiceConnection] = Field(None, description="Source service configuration")
    target: Optional[ServiceConnection] = Field(None, description="Target service configuration")
    field_mappings: Optional[List[FieldMapping]] = Field(None, description="Field mappings")
    schedule: Optional[str] = Field(None, description="Cron expression for scheduling")
    sync_options: Optional[Dict[str, Any]] = Field(None, description="Sync options")
    active: Optional[bool] = Field(None, description="Whether config is active")


class SyncTriggerRequest(BaseModel):
    triggered_by: str = Field(..., description="Who/what triggered this sync")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "services": {
            "firestore": firestore_service is not None,
            "scheduler": scheduler_service is not None,
            "sync_engine": sync_engine is not None
        }
    }


# Configuration management endpoints
@app.post("/api/v1/configs", response_model=SyncConfig)
async def create_config(
    request: CreateConfigRequest,
    fs: FirestoreService = Depends(get_firestore_service)
):
    """Create a new sync configuration."""
    try:
        config = SyncConfig(
            name=request.name,
            description=request.description,
            source=request.source,
            target=request.target,
            field_mappings=request.field_mappings,
            schedule=request.schedule,
            sync_options=request.sync_options,
            active=request.active
        )
        
        created_config = fs.create_config(config)
        return created_config
        
    except Exception as e:
        logger.error(f"Failed to create config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/configs", response_model=List[SyncConfig])
async def list_configs(
    fs: FirestoreService = Depends(get_firestore_service)
):
    """List all sync configurations."""
    try:
        configs = fs.list_configs()
        return configs
    except Exception as e:
        logger.error(f"Failed to list configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/configs/{config_id}", response_model=SyncConfig)
async def get_config(
    config_id: str,
    fs: FirestoreService = Depends(get_firestore_service)
):
    """Get a specific sync configuration."""
    try:
        config = fs.get_config(config_id)
        if config is None:
            raise HTTPException(status_code=404, detail="Configuration not found")
        return config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get config {config_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/v1/configs/{config_id}", response_model=SyncConfig)
async def update_config(
    config_id: str,
    request: UpdateConfigRequest,
    fs: FirestoreService = Depends(get_firestore_service)
):
    """Update an existing sync configuration."""
    try:
        # Get existing config
        existing_config = fs.get_config(config_id)
        if existing_config is None:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        # Update only provided fields
        update_data = {}
        if request.name is not None:
            update_data["name"] = request.name
        if request.description is not None:
            update_data["description"] = request.description
        if request.source is not None:
            update_data["source"] = request.source
        if request.target is not None:
            update_data["target"] = request.target
        if request.field_mappings is not None:
            update_data["field_mappings"] = request.field_mappings
        if request.schedule is not None:
            update_data["schedule"] = request.schedule
        if request.sync_options is not None:
            update_data["sync_options"] = request.sync_options
        if request.active is not None:
            update_data["active"] = request.active
        
        updated_config = fs.update_config(config_id, update_data)
        return updated_config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update config {config_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/configs/{config_id}")
async def delete_config(
    config_id: str,
    fs: FirestoreService = Depends(get_firestore_service)
):
    """Delete a sync configuration."""
    try:
        success = fs.delete_config(config_id)
        if not success:
            raise HTTPException(status_code=404, detail="Configuration not found")
        return {"message": "Configuration deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete config {config_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Sync execution endpoints
@app.post("/api/v1/configs/{config_id}/sync", response_model=SyncExecution)
async def execute_sync(
    config_id: str,
    request: SyncTriggerRequest,
    background_tasks: BackgroundTasks,
    fs: FirestoreService = Depends(get_firestore_service),
    engine: SyncEngine = Depends(get_sync_engine)
):
    """Execute a sync operation."""
    try:
        # Get config
        config = fs.get_config(config_id)
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        if not config.active:
            raise HTTPException(status_code=400, detail="Configuration is not active")
        
        # Execute sync in background
        def run_sync():
            try:
                execution = engine.execute_sync(config, triggered_by=request.triggered_by)
                
                # Save execution result
                fs.create_execution(execution)
                
            except Exception as e:
                logger.error(f"Background sync failed: {e}")
        
        background_tasks.add_task(run_sync)
        
        # Return immediately with a placeholder execution
        from ..models.sync import SyncExecution
        import time
        
        execution = SyncExecution(
            id=f"sync_{config_id}_{int(time.time())}",
            config_id=config_id,
            status=SyncStatus.RUNNING,
            triggered_by=request.triggered_by,
            started_at=datetime.utcnow()
        )
        
        return execution
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute sync for config {config_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/configs/{config_id}/executions", response_model=List[SyncExecution])
async def list_executions(
    config_id: str,
    limit: int = 50,
    fs: FirestoreService = Depends(get_firestore_service)
):
    """List sync executions for a configuration."""
    try:
        executions = fs.list_executions(config_id, limit=limit)
        return executions
    except Exception as e:
        logger.error(f"Failed to list executions for config {config_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/executions/{execution_id}", response_model=SyncExecution)
async def get_execution(
    execution_id: str,
    fs: FirestoreService = Depends(get_firestore_service)
):
    """Get a specific sync execution."""
    try:
        execution = fs.get_execution(execution_id)
        if execution is None:
            raise HTTPException(status_code=404, detail="Execution not found")
        return execution
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution {execution_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Connector information endpoints
@app.get("/api/v1/connectors")
async def list_connectors():
    """List available connectors."""
    return {
        "connectors": list(CONNECTOR_REGISTRY.keys()),
        "details": {
            name: {
                "class": connector_class.__name__,
                "module": connector_class.__module__
            }
            for name, connector_class in CONNECTOR_REGISTRY.items()
        }
    }


# Schedule management endpoints
@app.post("/api/v1/configs/{config_id}/schedule")
async def create_schedule(
    config_id: str,
    scheduler: SchedulerService = Depends(get_scheduler_service),
    fs: FirestoreService = Depends(get_firestore_service)
):
    """Create a Cloud Scheduler job for a sync configuration."""
    try:
        config = fs.get_config(config_id)
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        if not config.schedule:
            raise HTTPException(status_code=400, detail="Configuration does not have a schedule")
        
        job_name = f"sync-{config_id}"
        target_url = f"https://your-api-url/api/v1/configs/{config_id}/sync"
        
        result = scheduler.create_job(
            job_name=job_name,
            schedule=config.schedule,
            target_url=target_url,
            payload={"triggered_by": "scheduler"}
        )
        
        return {"message": "Schedule created successfully", "job_name": job_name}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create schedule for config {config_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# WORKFLOW ENDPOINTS (NEW CONFIGURABLE SYSTEM)
# =============================================================================

@app.post("/api/v1/workflows", response_model=WorkflowConfig)
async def create_workflow(
    workflow: WorkflowConfig,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """Create a new configurable workflow."""
    try:
        return firestore.create_workflow(workflow)
    except Exception as e:
        logger.error(f"Failed to create workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/workflows", response_model=List[WorkflowConfig])
async def list_workflows(
    active_only: bool = True,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """List all workflows."""
    try:
        return firestore.list_workflows(active_only=active_only)
    except Exception as e:
        logger.error(f"Failed to list workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/workflows/{workflow_id}", response_model=WorkflowConfig)
async def get_workflow(
    workflow_id: str,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """Get a specific workflow by ID."""
    try:
        workflow = firestore.get_workflow(workflow_id)
        if workflow is None:
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
        return workflow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/v1/workflows/{workflow_id}", response_model=WorkflowConfig)
async def update_workflow(
    workflow_id: str,
    updates: Dict[str, Any],
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """Update a workflow configuration."""
    try:
        workflow = firestore.update_workflow(workflow_id, updates)
        if workflow is None:
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
        return workflow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/workflows/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """Delete a workflow configuration."""
    try:
        success = firestore.delete_workflow(workflow_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
        return {"message": f"Workflow {workflow_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/workflows/{workflow_id}/execute", response_model=WorkflowExecution)
async def execute_workflow(
    workflow_id: str,
    background_tasks: BackgroundTasks,
    firestore: FirestoreService = Depends(get_firestore_service),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine)
):
    """Execute a configurable workflow."""
    try:
        # Get workflow configuration
        workflow = firestore.get_workflow(workflow_id)
        if workflow is None:
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
        
        if not workflow.active:
            raise HTTPException(status_code=400, detail=f"Workflow {workflow_id} is not active")
        
        # Execute workflow
        execution = workflow_engine.execute_workflow(workflow, triggered_by="manual")
        
        # Store execution result
        firestore.create_workflow_execution(execution)
        
        return execution
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/workflows/{workflow_id}/executions", response_model=List[WorkflowExecution])
async def list_workflow_executions(
    workflow_id: str,
    limit: int = 100,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """List executions for a specific workflow."""
    try:
        return firestore.list_workflow_executions(workflow_id=workflow_id, limit=limit)
    except Exception as e:
        logger.error(f"Failed to list executions for workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/workflow-executions/{execution_id}", response_model=WorkflowExecution)
async def get_workflow_execution(
    execution_id: str,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """Get a specific workflow execution by ID."""
    try:
        execution = firestore.get_workflow_execution(execution_id)
        if execution is None:
            raise HTTPException(status_code=404, detail=f"Workflow execution {execution_id} not found")
        return execution
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get workflow execution {execution_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/workflow-executions", response_model=List[WorkflowExecution])
async def list_all_workflow_executions(
    limit: int = 100,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """List all workflow executions across all workflows."""
    try:
        return firestore.list_workflow_executions(limit=limit)
    except Exception as e:
        logger.error(f"Failed to list all workflow executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 
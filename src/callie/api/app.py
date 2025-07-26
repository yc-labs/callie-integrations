"""
Main FastAPI application for Callie Integrations.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ..models.config import SyncConfig, ServiceConnection, FieldMapping, SyncStatus
from ..models.sync import SyncExecution
from ..services.firestore import FirestoreService
from ..services.scheduler import SchedulerService
from ..engine.sync import SyncEngine
from ..connectors import CONNECTOR_REGISTRY

logger = logging.getLogger(__name__)

# Global services (initialized in lifespan)
firestore_service: Optional[FirestoreService] = None
scheduler_service: Optional[SchedulerService] = None
sync_engine: Optional[SyncEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global firestore_service, scheduler_service, sync_engine
    
    # Initialize services
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    region = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
    
    try:
        # Initialize Firestore service
        try:
            firestore_service = FirestoreService(project_id=project_id)
            logger.info("Firestore service initialized successfully")
        except ImportError as e:
            logger.warning(f"Firestore service not available: {e}")
            firestore_service = None
        
        # Initialize Scheduler service  
        try:
            scheduler_service = SchedulerService(project_id=project_id, region=region)
            logger.info("Scheduler service initialized successfully")
        except ImportError as e:
            logger.warning(f"Scheduler service not available: {e}")
            scheduler_service = None
        
        # Initialize sync engine
        sync_engine = SyncEngine()
        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    yield
    
    # Cleanup (if needed)
    logger.info("Application shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="Callie Integrations",
        description="Enterprise data synchronization platform for Calibrate Network",
        version="1.0.0",
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
    
    return app


app = create_app()

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


class SyncRequest(BaseModel):
    triggered_by: str = Field("api", description="What triggered this sync")


class ScheduleRequest(BaseModel):
    schedule: str = Field(..., description="Cron expression")
    description: Optional[str] = Field(None, description="Schedule description")


# API Routes

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Callie Integrations",
        "version": "1.0.0",
        "status": "healthy",
        "supported_connectors": list(CONNECTOR_REGISTRY.keys())
    }

@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "services": {
            "firestore": firestore_service is not None,
            "scheduler": scheduler_service is not None,
            "sync_engine": sync_engine is not None
        }
    }

# Configuration Management Endpoints

@app.get("/api/v1/configs", response_model=List[SyncConfig])
async def list_configs(
    limit: int = 100,
    active_only: bool = False,
    fs: FirestoreService = Depends(get_firestore_service)
):
    """List all sync configurations."""
    try:
        configs = fs.list_configs(limit=limit, active_only=active_only)
        return configs
    except Exception as e:
        logger.error(f"Failed to list configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/configs", response_model=SyncConfig)
async def create_config(
    request: CreateConfigRequest,
    fs: FirestoreService = Depends(get_firestore_service),
    engine: SyncEngine = Depends(get_sync_engine)
):
    """Create a new sync configuration."""
    try:
        # Generate config ID from name
        config_id = request.name.lower().replace(" ", "-").replace("_", "-")
        config_id = "".join(c for c in config_id if c.isalnum() or c == "-")
        
        # Create config object
        config = SyncConfig(
            id=config_id,
            name=request.name,
            description=request.description,
            source=request.source,
            target=request.target,
            field_mappings=request.field_mappings,
            schedule=request.schedule,
            sync_options=request.sync_options,
            active=request.active
        )
        
        # Validate configuration
        validation = engine.validate_config(config)
        if not validation["valid"]:
            raise HTTPException(
                status_code=400, 
                detail={"message": "Configuration validation failed", "errors": validation["errors"]}
            )
        
        # Save to Firestore
        created_config = fs.create_config(config)
        
        return created_config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/configs/{config_id}", response_model=SyncConfig)
async def get_config(
    config_id: str,
    fs: FirestoreService = Depends(get_firestore_service)
):
    """Get a specific sync configuration."""
    try:
        config = fs.get_config(config_id)
        if not config:
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
    fs: FirestoreService = Depends(get_firestore_service),
    engine: SyncEngine = Depends(get_sync_engine)
):
    """Update an existing sync configuration."""
    try:
        # Get existing config
        config = fs.get_config(config_id)
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        # Update fields
        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(config, field, value)
        
        # Validate configuration
        validation = engine.validate_config(config)
        if not validation["valid"]:
            raise HTTPException(
                status_code=400,
                detail={"message": "Configuration validation failed", "errors": validation["errors"]}
            )
        
        # Save to Firestore
        updated_config = fs.update_config(config)
        
        return updated_config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update config {config_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/configs/{config_id}")
async def delete_config(
    config_id: str,
    fs: FirestoreService = Depends(get_firestore_service),
    scheduler: SchedulerService = Depends(get_scheduler_service)
):
    """Delete a sync configuration."""
    try:
        # Delete scheduler job if exists
        try:
            scheduler.delete_schedule(config_id)
        except Exception as e:
            logger.warning(f"Failed to delete schedule for {config_id}: {e}")
        
        # Delete config
        if not fs.delete_config(config_id):
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        return {"message": "Configuration deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete config {config_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Sync Execution Endpoints

@app.post("/api/v1/configs/{config_id}/sync", response_model=SyncExecution)
async def trigger_sync(
    config_id: str,
    request: SyncRequest = SyncRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    fs: FirestoreService = Depends(get_firestore_service),
    engine: SyncEngine = Depends(get_sync_engine)
):
    """Trigger a sync operation for a configuration."""
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
                
                # Save execution to Firestore
                fs.create_execution(execution)
                
                # Update config last sync time
                if execution.completed_at:
                    fs.update_config_last_sync(config_id, execution.completed_at)
                
            except Exception as e:
                logger.error(f"Background sync failed for {config_id}: {e}")
        
        background_tasks.add_task(run_sync)
        
        # Return immediate response
        return SyncExecution(
            id="pending",
            config_id=config_id,
            status="running",
            triggered_by=request.triggered_by
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to trigger sync for {config_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/configs/{config_id}/status")
async def get_sync_status(
    config_id: str,
    fs: FirestoreService = Depends(get_firestore_service)
):
    """Get sync status and statistics for a configuration."""
    try:
        # Get config
        config = fs.get_config(config_id)
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        # Get recent executions
        executions = fs.list_executions(config_id=config_id, limit=10)
        
        # Get statistics
        stats = fs.get_config_stats(config_id)
        
        return {
            "config_id": config_id,
            "config_name": config.name,
            "active": config.active,
            "last_sync_at": config.last_sync_at,
            "recent_executions": [exec.get_summary() for exec in executions],
            "statistics": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get status for {config_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/configs/{config_id}/executions", response_model=List[SyncExecution])
async def list_executions(
    config_id: str,
    limit: int = 50,
    fs: FirestoreService = Depends(get_firestore_service)
):
    """List sync executions for a configuration."""
    try:
        executions = fs.list_executions(config_id=config_id, limit=limit)
        return executions
    except Exception as e:
        logger.error(f"Failed to list executions for {config_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/executions/{execution_id}", response_model=SyncExecution)
async def get_execution(
    execution_id: str,
    fs: FirestoreService = Depends(get_firestore_service)
):
    """Get a specific sync execution."""
    try:
        execution = fs.get_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        return execution
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get execution {execution_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Schedule Management Endpoints

@app.post("/api/v1/configs/{config_id}/schedule")
async def create_schedule(
    config_id: str,
    request: ScheduleRequest,
    fs: FirestoreService = Depends(get_firestore_service),
    scheduler: SchedulerService = Depends(get_scheduler_service)
):
    """Create or update a schedule for a configuration."""
    try:
        # Get config
        config = fs.get_config(config_id)
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        # Get service URL from environment
        service_url = os.getenv("SERVICE_URL", "https://callie-sync-service.com")
        
        # Create scheduler job
        schedule_info = scheduler.create_schedule(
            config_id=config_id,
            schedule=request.schedule,
            service_url=service_url,
            description=request.description
        )
        
        # Update config with schedule
        config.schedule = request.schedule
        fs.update_config(config)
        
        return schedule_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create schedule for {config_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/configs/{config_id}/schedule")
async def get_schedule(
    config_id: str,
    scheduler: SchedulerService = Depends(get_scheduler_service)
):
    """Get schedule information for a configuration."""
    try:
        schedule_info = scheduler.get_schedule(config_id)
        if not schedule_info:
            raise HTTPException(status_code=404, detail="Schedule not found")
        return schedule_info
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get schedule for {config_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/v1/configs/{config_id}/schedule")
async def delete_schedule(
    config_id: str,
    fs: FirestoreService = Depends(get_firestore_service),
    scheduler: SchedulerService = Depends(get_scheduler_service)
):
    """Delete a schedule for a configuration."""
    try:
        # Delete scheduler job
        if not scheduler.delete_schedule(config_id):
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        # Update config to remove schedule
        config = fs.get_config(config_id)
        if config:
            config.schedule = None
            fs.update_config(config)
        
        return {"message": "Schedule deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete schedule for {config_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Connector Information Endpoints

@app.get("/api/v1/connectors")
async def list_connectors():
    """List all available connectors."""
    connectors = {}
    for service_type, connector_class in CONNECTOR_REGISTRY.items():
        # Create a temporary instance to get schema info
        try:
            temp_connector = connector_class(credentials={"dummy": "dummy"}, base_url="dummy")
            connectors[service_type] = {
                "service_type": service_type,
                "capabilities": temp_connector.get_capabilities().model_dump(),
                "inventory_schema": temp_connector.get_inventory_schema().model_dump()
            }
        except Exception:
            # If connector requires specific credentials, just show basic info
            connectors[service_type] = {
                "service_type": service_type,
                "capabilities": {},
                "inventory_schema": {}
            }
    
    return connectors


@app.get("/api/v1/connectors/{service_type}")
async def get_connector_info(service_type: str):
    """Get detailed information about a specific connector."""
    if service_type not in CONNECTOR_REGISTRY:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    connector_class = CONNECTOR_REGISTRY[service_type]
    
    # Create a temporary instance to get schema info
    try:
        temp_connector = connector_class(credentials={"dummy": "dummy"}, base_url="dummy")
        return {
            "service_type": service_type,
            "capabilities": temp_connector.get_capabilities().model_dump(),
            "inventory_schema": temp_connector.get_inventory_schema().model_dump(),
            "products_schema": temp_connector.get_products_schema().model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get connector info: {e}")


def main():
    """Main entry point for the API server."""
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main() 
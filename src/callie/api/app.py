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
    """Request to trigger a sync operation."""
    triggered_by: str = Field("api", description="What triggered this sync")
    sync_mode: str = Field("async", description="Sync mode: 'async' (background) or 'sync' (wait for completion)")


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
        
        # Check sync mode
        logger.info(f"Received sync request with mode: '{request.sync_mode}' for config {config_id}")
        
        if request.sync_mode == "sync":
            # Execute synchronously and return detailed results
            logger.info(f"Starting synchronous sync for config {config_id}")
            execution = engine.execute_sync(config, triggered_by=request.triggered_by)
            
            # Save execution to Firestore
            fs.create_execution(execution)
            
            # Update config last sync time
            if execution.completed_at:
                fs.update_config_last_sync(config_id, execution.completed_at)
            
            logger.info(f"Sync completed for {config_id}: {execution.total_items} items, "
                       f"{execution.success_count} success, {execution.failed_count} failed, "
                       f"{execution.skipped_count} skipped")
            
            return execution
        
        else:
            # Execute sync in background (existing behavior)
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
    """Get detailed sync status and statistics for a configuration."""
    try:
        # Get config
        config = fs.get_config(config_id)
        if not config:
            raise HTTPException(status_code=404, detail="Configuration not found")
        
        # Get recent executions
        executions = fs.list_executions(config_id=config_id, limit=10)
        
        # Get statistics
        stats = fs.get_config_stats(config_id)
        
        # Calculate additional metrics
        total_executions = len(executions)
        successful_executions = len([e for e in executions if e.status == "completed" and e.failed_count == 0])
        failed_executions = len([e for e in executions if e.status == "failed" or e.failed_count > 0])
        
        # Get latest execution details
        latest_execution = executions[0] if executions else None
        
        # Calculate success rate
        success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0
        
        # Get average execution time
        completed_executions = [e for e in executions if e.execution_time_seconds is not None]
        avg_execution_time = (
            sum(e.execution_time_seconds for e in completed_executions) / len(completed_executions)
            if completed_executions else None
        )
        
        return {
            "config": {
                "id": config_id,
                "name": config.name,
                "description": config.description,
                "active": config.active,
                "last_sync_at": config.last_sync_at.isoformat() if config.last_sync_at else None,
                "source_service": config.source.service_type,
                "target_service": config.target.service_type
            },
            "latest_execution": {
                "id": latest_execution.id if latest_execution else None,
                "status": latest_execution.status if latest_execution else None,
                "started_at": latest_execution.started_at.isoformat() if latest_execution and latest_execution.started_at else None,
                "completed_at": latest_execution.completed_at.isoformat() if latest_execution and latest_execution.completed_at else None,
                "execution_time_seconds": latest_execution.execution_time_seconds if latest_execution else None,
                "total_items": latest_execution.total_items if latest_execution else 0,
                "success_count": latest_execution.success_count if latest_execution else 0,
                "failed_count": latest_execution.failed_count if latest_execution else 0,
                "skipped_count": latest_execution.skipped_count if latest_execution else 0,
                "triggered_by": latest_execution.triggered_by if latest_execution else None,
                "error_message": latest_execution.error_message if latest_execution else None
            },
            "performance_metrics": {
                "total_executions": total_executions,
                "successful_executions": successful_executions,
                "failed_executions": failed_executions,
                "success_rate_percent": round(success_rate, 2),
                "average_execution_time_seconds": round(avg_execution_time, 2) if avg_execution_time else None,
                "total_items_synced": stats.get("total_items_synced", 0),
                "total_successful_items": stats.get("total_successful_items", 0),
                "total_failed_items": stats.get("total_failed_items", 0)
            },
            "recent_executions": [
                {
                    "id": exec.id,
                    "status": exec.status,
                    "started_at": exec.started_at.isoformat() if exec.started_at else None,
                    "completed_at": exec.completed_at.isoformat() if exec.completed_at else None,
                    "total_items": exec.total_items,
                    "success_count": exec.success_count,
                    "failed_count": exec.failed_count,
                    "skipped_count": exec.skipped_count,
                    "execution_time_seconds": exec.execution_time_seconds,
                    "triggered_by": exec.triggered_by
                }
                for exec in executions
            ],
            "health_status": {
                "overall": "healthy" if success_rate >= 80 and (not latest_execution or latest_execution.status in ["completed"]) else "degraded" if success_rate >= 50 else "unhealthy",
                "last_success": executions[0].completed_at.isoformat() if executions and executions[0].status == "completed" else None,
                "consecutive_failures": len([e for e in executions if e.status == "failed"]) if executions and executions[0].status == "failed" else 0
            }
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


@app.get("/api/v1/configs/{config_id}/executions/{execution_id}")
async def get_execution_details(
    config_id: str,
    execution_id: str,
    fs: FirestoreService = Depends(get_firestore_service)
):
    """Get detailed information about a specific sync execution."""
    try:
        # Get the execution
        execution = fs.get_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        
        if execution.config_id != config_id:
            raise HTTPException(status_code=404, detail="Execution not found for this configuration")
        
        # Group results by status for summary
        results_by_status = {}
        for result in execution.results:
            status = result.status
            if status not in results_by_status:
                results_by_status[status] = []
            results_by_status[status].append({
                "sku": result.sku,
                "source_value": result.source_value,
                "target_value": result.target_value,
                "message": result.message,
                "processed_at": result.processed_at.isoformat() if result.processed_at else None
            })
        
        # Calculate detailed metrics
        execution_details = {
            "execution": {
                "id": execution.id,
                "config_id": execution.config_id,
                "status": execution.status,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "execution_time_seconds": execution.execution_time_seconds,
                "triggered_by": execution.triggered_by,
                "error_message": execution.error_message
            },
            "summary": {
                "total_items": execution.total_items,
                "success_count": execution.success_count,
                "failed_count": execution.failed_count,
                "skipped_count": execution.skipped_count,
                "success_rate_percent": round((execution.success_count / execution.total_items * 100) if execution.total_items > 0 else 0, 2)
            },
            "results_by_status": results_by_status,
            "performance": {
                "items_per_second": round(execution.total_items / execution.execution_time_seconds, 2) if execution.execution_time_seconds and execution.execution_time_seconds > 0 else None,
                "average_time_per_item_ms": round((execution.execution_time_seconds * 1000) / execution.total_items, 2) if execution.total_items > 0 and execution.execution_time_seconds else None
            }
        }
        
        return execution_details
        
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


class TestFieldsRequest(BaseModel):
    credentials: Dict[str, str]
    base_url: str
    limit: int = 5

@app.post("/api/v1/connectors/{service_type}/test-fields")
async def test_connector_fields(
    service_type: str,
    request: TestFieldsRequest
):
    """
    Test a connector and return sample data with available fields.
    This helps with field mapping configuration.
    """
    try:
        if service_type not in CONNECTOR_REGISTRY:
            raise HTTPException(status_code=400, detail=f"Unknown service type: {service_type}")
        
        # Create connector instance
        connector_class = CONNECTOR_REGISTRY[service_type]
        connector = connector_class(
            credentials=request.credentials,
            base_url=request.base_url
        )
        
        # Test connection first
        if not connector.test_connection():
            raise HTTPException(status_code=400, detail=f"Cannot connect to {service_type} API")
        
        # Get sample inventory data to show available fields
        sample_data = connector.read_inventory(limit=request.limit)
        
        # Extract unique field names from sample data
        available_fields = set()
        for item in sample_data:
            available_fields.update(item.keys())
        
        # Get sample values for each field
        field_examples = {}
        if sample_data:
            first_item = sample_data[0]
            for field in available_fields:
                field_examples[field] = first_item.get(field)
        
        return {
            "service_type": service_type,
            "connection_status": "success",
            "available_fields": sorted(list(available_fields)),
            "field_examples": field_examples,
            "sample_count": len(sample_data),
            "sample_data": sample_data[:2] if sample_data else []  # Show first 2 items
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test {service_type} fields: {e}")
        raise HTTPException(status_code=500, detail=f"Error testing connector: {str(e)}")


def main():
    """Main entry point for the API server."""
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main() 
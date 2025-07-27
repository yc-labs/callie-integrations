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

from ..models.stages import WorkflowConfig, WorkflowExecution, WorkflowUpdate
from ..services.firestore import FirestoreService
from ..services.scheduler import SchedulerService
from ..services.secrets import SecretManagerService
from ..engine.workflow_engine import WorkflowEngine
from ..connectors import CONNECTOR_REGISTRY
from ..version import __version__
from ..exceptions import CallieException, ConfigurationError

logger = logging.getLogger(__name__)

# Global services (initialized in lifespan)
firestore_service: Optional[FirestoreService] = None
scheduler_service: Optional[SchedulerService] = None
secret_service: Optional[SecretManagerService] = None
workflow_engine: Optional[WorkflowEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global firestore_service, scheduler_service, secret_service, workflow_engine
    
    # Initialize services
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    region = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
    
    try:
        # Initialize Secret Manager service
        try:
            secret_service = SecretManagerService(project_id=project_id)
            logger.info("Secret Manager service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Secret Manager service: {e}")
            secret_service = None
        
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

# Get allowed origins from environment variable
allowed_origins_str = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins = [origin.strip() for origin in allowed_origins_str.split(",") if origin.strip()]

if not allowed_origins:
    # Default to allowing all for local dev if not set
    allowed_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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

def get_secret_service() -> Optional[SecretManagerService]:
    """Get Secret Manager service if available, otherwise return None."""
    return secret_service

def get_workflow_engine() -> WorkflowEngine:
    if workflow_engine is None:
        raise HTTPException(status_code=500, detail="Workflow engine not initialized")
    return workflow_engine


def inject_credentials_into_workflow(workflow: WorkflowConfig, credentials: Dict[str, str]) -> WorkflowConfig:
    """Inject real API credentials into workflow configuration."""
    import json
    
    # Convert workflow to JSON string
    workflow_json = workflow.model_dump_json()
    
    # Replace ${VAR_NAME} patterns with actual credential values
    for var_name, var_value in credentials.items():
        placeholder = f"${{{var_name}}}"
        workflow_json = workflow_json.replace(placeholder, var_value)
    
    # Convert back to WorkflowConfig
    workflow_dict = json.loads(workflow_json)
    return WorkflowConfig(**workflow_dict)


# Request/Response models - These can be removed if they are no longer needed


# Health check endpoint
@app.get("/health")
async def health_check():
    """Check the health of the application and its services."""
    return {
        "status": "healthy",
        "services": {
            "firestore": firestore_service is not None,
            "scheduler": scheduler_service is not None,
            "secret_manager": secret_service is not None,
            "workflow_engine": workflow_engine is not None,
        }
    }


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


# Schedule management endpoints are now tied to workflows
@app.post("/api/v1/workflows/{workflow_id}/schedule")
async def create_schedule_for_workflow(
    workflow_id: str,
    scheduler: SchedulerService = Depends(get_scheduler_service),
    fs: FirestoreService = Depends(get_firestore_service)
):
    """Create a Cloud Scheduler job for a workflow."""
    try:
        workflow = fs.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        if not workflow.schedule:
            raise HTTPException(status_code=400, detail="Workflow does not have a schedule")

        job_name = f"workflow-{workflow_id}"
        
        # Get base URL from environment variable, with a default for local dev
        base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        target_url = f"{base_url}/api/v1/workflows/{workflow_id}/execute"

        result = scheduler.create_job(
            job_name=job_name,
            schedule=workflow.schedule,
            target_url=target_url,
            payload={"triggered_by": "scheduler"}
        )

        return {"message": "Schedule created successfully", "job_name": job_name}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create schedule for workflow {workflow_id}: {e}")
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
    except CallieException as e:
        logger.error(f"Failed to create workflow: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"An unexpected error occurred during workflow creation: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@app.get("/api/v1/workflows", response_model=List[WorkflowConfig])
async def list_workflows(
    active_only: bool = True,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """List all workflows."""
    try:
        return firestore.list_workflows(active_only=active_only)
    except CallieException as e:
        logger.error(f"Failed to list workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing workflows: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@app.get("/api/v1/workflows/{workflow_id}", response_model=WorkflowConfig)
async def get_workflow(
    workflow_id: str,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """Get a specific workflow by ID."""
    try:
        workflow = firestore.get_workflow(workflow_id)
        if workflow is None:
            raise ConfigurationError(f"Workflow {workflow_id} not found")
        return workflow
    except ConfigurationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CallieException as e:
        logger.error(f"Failed to get workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@app.put("/api/v1/workflows/{workflow_id}", response_model=WorkflowConfig)
async def update_workflow(
    workflow_id: str,
    updates: WorkflowUpdate,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """Update a workflow configuration."""
    try:
        update_data = updates.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="No update data provided. At least one field must be specified."
            )

        workflow = firestore.update_workflow(workflow_id, update_data)
        if workflow is None:
            raise ConfigurationError(f"Workflow {workflow_id} not found")
        return workflow
    except ConfigurationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CallieException as e:
        logger.error(f"Failed to update workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"An unexpected error occurred while updating workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@app.delete("/api/v1/workflows/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """Delete a workflow configuration."""
    try:
        success = firestore.delete_workflow(workflow_id)
        if not success:
            raise ConfigurationError(f"Workflow {workflow_id} not found")
        return {"message": f"Workflow {workflow_id} deleted successfully"}
    except ConfigurationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CallieException as e:
        logger.error(f"Failed to delete workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"An unexpected error occurred while deleting workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@app.post("/api/v1/workflows/{workflow_id}/execute-sync")
async def execute_workflow_sync(
    workflow_id: str,
    firestore: FirestoreService = Depends(get_firestore_service),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
    secret_service: Optional[SecretManagerService] = Depends(get_secret_service)
):
    """Execute a workflow synchronously for testing."""
    try:
        # Get workflow configuration
        workflow = firestore.get_workflow(workflow_id)
        if workflow is None:
            raise ConfigurationError(f"Workflow {workflow_id} not found")
        
        if not workflow.active:
            raise ConfigurationError(f"Workflow {workflow_id} is not active")
        
        # Get API credentials from Secret Manager or environment variables
        credentials = {}
        if secret_service:
            try:
                credentials = secret_service.get_api_credentials()
                logger.info(f"Retrieved credentials from Secret Manager: {list(credentials.keys())}")
            except Exception as e:
                logger.error(f"Failed to get credentials from Secret Manager: {e}")
        
        # Fall back to environment variables if no secret service or secret retrieval failed
        if not credentials:
            logger.info("Using environment variables for credentials")
            credentials = {
                "SHIPSTATION_API_KEY": os.getenv("SHIPSTATION_API_KEY", ""),
                "SHIPSTATION_BASE_URL": os.getenv("SHIPSTATION_BASE_URL", "https://api.shipstation.com"),
                "INFIPLEX_API_KEY": os.getenv("INFIPLEX_API_KEY", ""),
                "INFIPLEX_BASE_URL": os.getenv("INFIPLEX_BASE_URL", ""),
                "API_BASE_URL": os.getenv("API_BASE_URL", "http://localhost:8000"),
            }
        
        # Inject credentials into workflow
        workflow_with_credentials = inject_credentials_into_workflow(workflow, credentials)
        logger.info(f"Injected credentials into workflow")
        
        # Execute workflow synchronously
        execution = workflow_engine.execute_workflow(workflow_with_credentials, triggered_by="manual-sync")
        
        return execution
        
    except ConfigurationError as e:
        logger.error(f"Configuration error executing workflow {workflow_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except CallieException as e:
        logger.error(f"Failed to execute workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"An unexpected error occurred during workflow execution {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@app.post("/api/v1/workflows/{workflow_id}/execute", status_code=202)
async def execute_workflow(
    workflow_id: str,
    background_tasks: BackgroundTasks,
    firestore: FirestoreService = Depends(get_firestore_service),
    workflow_engine: WorkflowEngine = Depends(get_workflow_engine),
    secret_service: Optional[SecretManagerService] = Depends(get_secret_service)
):
    """
    Execute a configurable workflow in the background.
    Returns a task ID that can be used to monitor the execution.
    """
    try:
        # Get workflow configuration
        workflow = firestore.get_workflow(workflow_id)
        if workflow is None:
            raise ConfigurationError(f"Workflow {workflow_id} not found")
        
        if not workflow.active:
            raise ConfigurationError(f"Workflow {workflow_id} is not active")
        
        # Define the background task
        def run_workflow():
            try:
                # Get API credentials from Secret Manager or environment variables
                credentials = {}
                if secret_service:
                    try:
                        credentials = secret_service.get_api_credentials()
                    except Exception as e:
                        logger.error(f"Failed to get credentials from Secret Manager: {e}")
                
                # Fall back to environment variables if no secret service or secret retrieval failed
                if not credentials:
                    credentials = {
                        "SHIPSTATION_API_KEY": os.getenv("SHIPSTATION_API_KEY", ""),
                        "SHIPSTATION_BASE_URL": os.getenv("SHIPSTATION_BASE_URL", "https://api.shipstation.com"),
                        "INFIPLEX_API_KEY": os.getenv("INFIPLEX_API_KEY", ""),
                        "INFIPLEX_BASE_URL": os.getenv("INFIPLEX_BASE_URL", ""),
                        "API_BASE_URL": os.getenv("API_BASE_URL", "http://localhost:8000"),
                    }
                
                # Inject credentials into workflow
                workflow_with_credentials = inject_credentials_into_workflow(workflow, credentials)
                
                execution = workflow_engine.execute_workflow(workflow_with_credentials, triggered_by="manual")
                firestore.create_workflow_execution(execution)
            except Exception as e:
                logger.error(f"Background workflow execution for {workflow_id} failed: {e}")

        # Add task to background
        background_tasks.add_task(run_workflow)
        
        # For now, we'll just return a simple task ID.
        # In a real system, this would be a proper task queue ID.
        task_id = f"task_{workflow_id}_{int(datetime.utcnow().timestamp())}"
        
        return {"task_id": task_id, "status": "accepted"}
        
    except ConfigurationError as e:
        logger.error(f"Configuration error executing workflow {workflow_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except CallieException as e:
        logger.error(f"Failed to execute workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"An unexpected error occurred during workflow execution {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@app.get("/api/v1/workflows/{workflow_id}/executions", response_model=List[WorkflowExecution])
async def list_workflow_executions(
    workflow_id: str,
    limit: int = 100,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """List executions for a specific workflow."""
    try:
        return firestore.list_workflow_executions(workflow_id=workflow_id, limit=limit)
    except CallieException as e:
        logger.error(f"Failed to list executions for workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing executions for workflow {workflow_id}: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@app.get("/api/v1/workflow-executions/{execution_id}", response_model=WorkflowExecution)
async def get_workflow_execution(
    execution_id: str,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """Get a specific workflow execution by ID."""
    try:
        execution = firestore.get_workflow_execution(execution_id)
        if execution is None:
            raise ConfigurationError(f"Workflow execution {execution_id} not found")
        return execution
    except ConfigurationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except CallieException as e:
        logger.error(f"Failed to get workflow execution {execution_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting workflow execution {execution_id}: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@app.get("/api/v1/workflow-executions", response_model=List[WorkflowExecution])
async def list_all_workflow_executions(
    limit: int = 100,
    firestore: FirestoreService = Depends(get_firestore_service)
):
    """List all workflow executions across all workflows."""
    try:
        return firestore.list_workflow_executions(limit=limit)
    except CallieException as e:
        logger.error(f"Failed to list all workflow executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing all workflow executions: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 
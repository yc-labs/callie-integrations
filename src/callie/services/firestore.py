"""
Firestore service for managing sync configurations and execution history.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from google.cloud import firestore
from google.auth import default

from ..models.stages import WorkflowConfig, WorkflowExecution

logger = logging.getLogger(__name__)


class FirestoreService:
    """
    Service for managing sync configurations and execution history in Firestore.
    """
    
    def __init__(self, project_id: Optional[str] = None):
        """
        Initialize Firestore service.
        
        Args:
            project_id: Google Cloud project ID. If None, uses default from environment.
        """
        try:
            if project_id:
                self.db = firestore.Client(project=project_id)
            else:
                # Use application default credentials
                credentials, project = default()
                self.db = firestore.Client(project=project, credentials=credentials)
            
            # New workflow collections
            self.workflows_collection = "workflows"
            self.workflow_executions_collection = "workflow_executions"
            
            logger.info(f"Firestore service initialized for project: {self.db.project}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firestore: {e}")
            raise
    
    # Workflow Management (New Configurable System)
    
    def create_workflow(self, workflow: WorkflowConfig) -> WorkflowConfig:
        """Create a new workflow configuration."""
        try:
            # Convert to dict for Firestore
            workflow_data = workflow.model_dump()
            workflow_data['created_at'] = datetime.utcnow()
            workflow_data['updated_at'] = datetime.utcnow()
            
            # Store in Firestore
            doc_ref = self.db.collection(self.workflows_collection).document(workflow.id)
            doc_ref.set(workflow_data)
            
            logger.info(f"Created workflow: {workflow.id}")
            return workflow
            
        except Exception as e:
            logger.error(f"Failed to create workflow {workflow.id}: {e}")
            raise
    
    def get_workflow(self, workflow_id: str) -> Optional[WorkflowConfig]:
        """Get a workflow configuration by ID."""
        try:
            doc_ref = self.db.collection(self.workflows_collection).document(workflow_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                return WorkflowConfig(**data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get workflow {workflow_id}: {e}")
            raise
    
    def list_workflows(self, active_only: bool = True) -> List[WorkflowConfig]:
        """List all workflow configurations."""
        try:
            query = self.db.collection(self.workflows_collection)
            
            if active_only:
                query = query.where("active", "==", True)
            
            docs = query.order_by("created_at", direction=firestore.Query.DESCENDING).stream()
            
            workflows = []
            for doc in docs:
                data = doc.to_dict()
                workflows.append(WorkflowConfig(**data))
            
            logger.info(f"Listed {len(workflows)} workflows")
            return workflows
            
        except Exception as e:
            logger.error(f"Failed to list workflows: {e}")
            raise
    
    def update_workflow(self, workflow_id: str, updates: Dict[str, Any]) -> Optional[WorkflowConfig]:
        """Update a workflow configuration."""
        try:
            doc_ref = self.db.collection(self.workflows_collection).document(workflow_id)
            
            # Add updated timestamp
            updates['updated_at'] = datetime.utcnow()
            
            # Update document
            doc_ref.update(updates)
            
            # Return updated workflow
            return self.get_workflow(workflow_id)
            
        except Exception as e:
            logger.error(f"Failed to update workflow {workflow_id}: {e}")
            raise
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow configuration."""
        try:
            doc_ref = self.db.collection(self.workflows_collection).document(workflow_id)
            doc_ref.delete()
            
            logger.info(f"Deleted workflow: {workflow_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete workflow {workflow_id}: {e}")
            raise
    
    def create_workflow_execution(self, execution: WorkflowExecution) -> WorkflowExecution:
        """Create a new workflow execution record."""
        try:
            # Convert to dict for Firestore
            execution_data = execution.model_dump()
            
            # Store in Firestore
            doc_ref = self.db.collection(self.workflow_executions_collection).document(execution.id)
            doc_ref.set(execution_data)
            
            logger.info(f"Created workflow execution: {execution.id}")
            return execution
            
        except Exception as e:
            logger.error(f"Failed to create workflow execution {execution.id}: {e}")
            raise
    
    def get_workflow_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get a workflow execution by ID."""
        try:
            doc_ref = self.db.collection(self.workflow_executions_collection).document(execution_id)
            doc = doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                return WorkflowExecution(**data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get workflow execution {execution_id}: {e}")
            raise
    
    def list_workflow_executions(self, workflow_id: Optional[str] = None, limit: int = 100) -> List[WorkflowExecution]:
        """List workflow executions, optionally filtered by workflow ID."""
        try:
            query = self.db.collection(self.workflow_executions_collection)
            
            if workflow_id:
                query = query.where("workflow_id", "==", workflow_id)
            
            query = query.order_by("started_at", direction=firestore.Query.DESCENDING).limit(limit)
            docs = query.stream()
            
            executions = []
            for doc in docs:
                data = doc.to_dict()
                executions.append(WorkflowExecution(**data))
            
            logger.info(f"Listed {len(executions)} workflow executions")
            return executions
            
        except Exception as e:
            logger.error(f"Failed to list workflow executions: {e}")
            raise
    
    def update_workflow_execution(self, execution_id: str, updates: Dict[str, Any]) -> Optional[WorkflowExecution]:
        """Update a workflow execution."""
        try:
            doc_ref = self.db.collection(self.workflow_executions_collection).document(execution_id)
            doc_ref.update(updates)
            
            return self.get_workflow_execution(execution_id)
            
        except Exception as e:
            logger.error(f"Failed to update workflow execution {execution_id}: {e}")
            raise 
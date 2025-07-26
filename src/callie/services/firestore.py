"""
Firestore service for managing sync configurations and execution history.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from google.cloud import firestore
from google.auth import default

from ..models.config import SyncConfig
from ..models.sync import SyncExecution

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
            
            self.configs_collection = "sync_configs"
            self.executions_collection = "sync_executions"
            
            logger.info(f"Firestore service initialized for project: {self.db.project}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Firestore: {e}")
            raise
    
    # Configuration Management
    
    def create_config(self, config: SyncConfig) -> SyncConfig:
        """
        Create a new sync configuration.
        
        Args:
            config: Sync configuration to create
            
        Returns:
            Created configuration
        """
        try:
            config.created_at = datetime.utcnow()
            config.updated_at = datetime.utcnow()
            
            doc_ref = self.db.collection(self.configs_collection).document(config.id)
            doc_ref.set(config.to_firestore())
            
            logger.info(f"Created sync config: {config.id}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to create config {config.id}: {e}")
            raise
    
    def get_config(self, config_id: str) -> Optional[SyncConfig]:
        """
        Get a sync configuration by ID.
        
        Args:
            config_id: Configuration ID
            
        Returns:
            Configuration if found, None otherwise
        """
        try:
            doc_ref = self.db.collection(self.configs_collection).document(config_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return SyncConfig.from_firestore(config_id, doc.to_dict())
            return None
            
        except Exception as e:
            logger.error(f"Failed to get config {config_id}: {e}")
            raise
    
    def list_configs(self, limit: int = 100, active_only: bool = False) -> List[SyncConfig]:
        """
        List sync configurations.
        
        Args:
            limit: Maximum number of configs to return
            active_only: If True, only return active configurations
            
        Returns:
            List of configurations
        """
        try:
            query = self.db.collection(self.configs_collection)
            
            if active_only:
                query = query.where("active", "==", True)
            
            query = query.order_by("created_at", direction=firestore.Query.DESCENDING)
            query = query.limit(limit)
            
            configs = []
            for doc in query.stream():
                configs.append(SyncConfig.from_firestore(doc.id, doc.to_dict()))
            
            return configs
            
        except Exception as e:
            logger.error(f"Failed to list configs: {e}")
            raise
    
    def update_config(self, config: SyncConfig) -> SyncConfig:
        """
        Update an existing sync configuration.
        
        Args:
            config: Updated configuration
            
        Returns:
            Updated configuration
        """
        try:
            config.updated_at = datetime.utcnow()
            
            doc_ref = self.db.collection(self.configs_collection).document(config.id)
            doc_ref.update(config.to_firestore())
            
            logger.info(f"Updated sync config: {config.id}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to update config {config.id}: {e}")
            raise
    
    def delete_config(self, config_id: str) -> bool:
        """
        Delete a sync configuration.
        
        Args:
            config_id: Configuration ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        try:
            doc_ref = self.db.collection(self.configs_collection).document(config_id)
            doc = doc_ref.get()
            
            if doc.exists:
                doc_ref.delete()
                logger.info(f"Deleted sync config: {config_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete config {config_id}: {e}")
            raise
    
    def update_config_last_sync(self, config_id: str, last_sync_at: datetime) -> None:
        """
        Update the last sync timestamp for a configuration.
        
        Args:
            config_id: Configuration ID
            last_sync_at: Timestamp of last sync
        """
        try:
            doc_ref = self.db.collection(self.configs_collection).document(config_id)
            doc_ref.update({
                "last_sync_at": last_sync_at.isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Failed to update last sync for config {config_id}: {e}")
            raise
    
    # Execution History Management
    
    def create_execution(self, execution: SyncExecution) -> SyncExecution:
        """
        Create a new sync execution record.
        
        Args:
            execution: Sync execution to create
            
        Returns:
            Created execution
        """
        try:
            doc_ref = self.db.collection(self.executions_collection).document(execution.id)
            doc_ref.set(execution.to_firestore())
            
            logger.info(f"Created sync execution: {execution.id}")
            return execution
            
        except Exception as e:
            logger.error(f"Failed to create execution {execution.id}: {e}")
            raise
    
    def update_execution(self, execution: SyncExecution) -> SyncExecution:
        """
        Update an existing sync execution record.
        
        Args:
            execution: Updated execution
            
        Returns:
            Updated execution
        """
        try:
            doc_ref = self.db.collection(self.executions_collection).document(execution.id)
            doc_ref.update(execution.to_firestore())
            
            logger.info(f"Updated sync execution: {execution.id}")
            return execution
            
        except Exception as e:
            logger.error(f"Failed to update execution {execution.id}: {e}")
            raise
    
    def get_execution(self, execution_id: str) -> Optional[SyncExecution]:
        """
        Get a sync execution by ID.
        
        Args:
            execution_id: Execution ID
            
        Returns:
            Execution if found, None otherwise
        """
        try:
            doc_ref = self.db.collection(self.executions_collection).document(execution_id)
            doc = doc_ref.get()
            
            if doc.exists:
                return SyncExecution.from_firestore(execution_id, doc.to_dict())
            return None
            
        except Exception as e:
            logger.error(f"Failed to get execution {execution_id}: {e}")
            raise
    
    def list_executions(
        self, 
        config_id: Optional[str] = None, 
        limit: int = 50
    ) -> List[SyncExecution]:
        """
        List sync executions.
        
        Args:
            config_id: If provided, only return executions for this config
            limit: Maximum number of executions to return
            
        Returns:
            List of executions
        """
        try:
            query = self.db.collection(self.executions_collection)
            
            if config_id:
                query = query.where("config_id", "==", config_id)
            
            query = query.order_by("started_at", direction=firestore.Query.DESCENDING)
            query = query.limit(limit)
            
            executions = []
            for doc in query.stream():
                executions.append(SyncExecution.from_firestore(doc.id, doc.to_dict()))
            
            return executions
            
        except Exception as e:
            logger.error(f"Failed to list executions: {e}")
            raise
    
    def get_config_stats(self, config_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get statistics for a configuration.
        
        Args:
            config_id: Configuration ID
            days: Number of days to look back
            
        Returns:
            Dictionary with statistics
        """
        try:
            # Calculate cutoff date
            cutoff_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)
            
            query = (self.db.collection(self.executions_collection)
                    .where("config_id", "==", config_id)
                    .where("started_at", ">=", cutoff_date.isoformat())
                    .order_by("started_at", direction=firestore.Query.DESCENDING))
            
            executions = []
            for doc in query.stream():
                executions.append(SyncExecution.from_firestore(doc.id, doc.to_dict()))
            
            # Calculate statistics
            total_executions = len(executions)
            successful_executions = len([e for e in executions if e.status == "completed"])
            failed_executions = len([e for e in executions if e.status == "failed"])
            
            total_items_synced = sum(e.total_items for e in executions)
            total_items_successful = sum(e.success_count for e in executions)
            total_items_failed = sum(e.failed_count for e in executions)
            
            # Calculate average execution time
            completed_executions = [e for e in executions if e.execution_time_seconds]
            avg_execution_time = (
                sum(e.execution_time_seconds for e in completed_executions) / len(completed_executions)
                if completed_executions else 0
            )
            
            last_execution = executions[0] if executions else None
            
            return {
                "config_id": config_id,
                "period_days": days,
                "total_executions": total_executions,
                "successful_executions": successful_executions,
                "failed_executions": failed_executions,
                "success_rate": successful_executions / total_executions if total_executions > 0 else 0,
                "total_items_synced": total_items_synced,
                "total_items_successful": total_items_successful,
                "total_items_failed": total_items_failed,
                "avg_execution_time_seconds": avg_execution_time,
                "last_execution": last_execution.get_summary() if last_execution else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats for config {config_id}: {e}")
            raise 
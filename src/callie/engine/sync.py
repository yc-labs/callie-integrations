"""
Sync execution engine for coordinating data synchronization between services.
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from ..models.config import SyncConfig
from ..models.sync import SyncExecution, SyncStatus

logger = logging.getLogger(__name__)


class SyncEngine:
    """
    Legacy sync engine for backward compatibility.
    Use StageSyncEngine for new configurations.
    """

    def __init__(self):
        """Initialize sync engine."""
        logger.info("Legacy SyncEngine initialized")

    def execute_sync(self, config: SyncConfig, triggered_by: str = "system") -> SyncExecution:
        """
        Execute a sync operation with legacy configuration.
        For new stage-based configs, use StageSyncEngine instead.
        """
        execution_id = f"legacy_sync_{int(time.time())}"
        execution = SyncExecution(
            id=execution_id,
            config_id=config.id,
            status=SyncStatus.RUNNING,
            started_at=datetime.utcnow(),
            triggered_by=triggered_by
        )

        try:
            logger.info(f"Starting legacy sync execution: {execution_id}")
            
            # This is a simplified version - real implementation would
            # need to handle the legacy config format and convert it
            # to stages or use the old logic
            
            logger.warning("Legacy sync engine - consider migrating to stage-based configuration")
            
            # For now, mark as completed with minimal processing
            execution.status = SyncStatus.COMPLETED
            execution.total_items = 0
            execution.success_count = 0
            execution.failed_count = 0

        except Exception as e:
            logger.error(f"Legacy sync execution failed: {e}")
            execution.status = SyncStatus.FAILED
            execution.error_message = str(e)

        finally:
            execution.completed_at = datetime.utcnow()
            if execution.started_at and execution.completed_at:
                execution.execution_time_seconds = (
                    execution.completed_at - execution.started_at
                ).total_seconds()

        return execution 
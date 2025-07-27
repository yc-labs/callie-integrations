"""
Main sync engine that orchestrates data synchronization between services.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

from ..connectors import get_connector, CONNECTOR_REGISTRY
from ..models.config import SyncConfig
from ..models.sync import SyncExecution, SyncResult, SyncItemStatus, SyncExecutionStatus
from .transforms import FieldTransformer

logger = logging.getLogger(__name__)


class SyncEngine:
    """
    Main engine for executing sync operations between services.
    """
    
    def __init__(self):
        """Initialize the sync engine."""
        self.transformer = FieldTransformer()
    
    def execute_sync(self, config: SyncConfig, triggered_by: str = "api") -> SyncExecution:
        """
        Execute a sync operation based on the provided configuration.
        
        Args:
            config: Sync configuration
            triggered_by: What triggered this sync (api, scheduler, manual)
            
        Returns:
            SyncExecution with results
        """
        # Create execution record
        execution = SyncExecution(
            id=str(uuid.uuid4()),
            config_id=config.id,
            status=SyncExecutionStatus.RUNNING,
            triggered_by=triggered_by
        )
        
        try:
            logger.info(f"Starting sync execution {execution.id} for config {config.id}")
            
            # Initialize connectors
            source_connector = self._create_connector(
                config.source.service_type,
                config.get_source_connector_config()
            )
            target_connector = self._create_connector(
                config.target.service_type,
                config.get_target_connector_config()
            )
            
            # Test connections
            if not source_connector.test_connection():
                raise Exception(f"Failed to connect to source service: {config.source.service_type}")
            if not target_connector.test_connection():
                raise Exception(f"Failed to connect to target service: {config.target.service_type}")
            
            # Read data from source
            logger.info(f"Reading data from {config.source.service_type}")

            # Get target SKUs to filter source data
            logger.info(f"Reading target SKUs from {config.target.service_type} for targeted sync")
            try:
                target_inventory = target_connector.read_inventory()
                target_skus = [item.get("sku") for item in target_inventory if item.get("sku")]
                logger.info(f"Found {len(target_skus)} SKUs in target system")
            except Exception as e:
                logger.error(f"Could not read target SKUs: {e}. Proceeding with unfiltered source read.")
                target_skus = []

            source_read_options = config.sync_options.copy()
            if target_skus:
                source_read_options["sku_list"] = target_skus

            source_data = source_connector.read_inventory(**source_read_options)
            logger.info(f"Retrieved {len(source_data)} items from source")
            
            # Transform data using field mappings
            logger.info("Transforming data using field mappings")
            field_mappings = [mapping.model_dump() for mapping in config.field_mappings]
            transformed_data = self.transformer.map_item_list(source_data, field_mappings)
            
            # Execute sync (read target data for comparison)
            sync_results = self._execute_inventory_sync(
                source_data, transformed_data, target_connector, config
            )
            
            # Update execution with results
            execution.results = sync_results
            success_count = len([r for r in sync_results if r.status == SyncItemStatus.SUCCESS])
            failed_count = len([r for r in sync_results if r.status == SyncItemStatus.FAILED])
            skipped_count = len([r for r in sync_results if r.status in [SyncItemStatus.SKIPPED, SyncItemStatus.MATCH]])
            
            execution.mark_completed(success_count, failed_count, skipped_count)
            
            logger.info(f"Sync execution {execution.id} completed: {success_count} success, {failed_count} failed, {skipped_count} skipped")
            
        except Exception as e:
            logger.error(f"Sync execution {execution.id} failed: {e}")
            execution.mark_failed(str(e))
        
        return execution
    
    def _create_connector(self, service_type: str, config: Dict[str, Any]):
        """Create a connector instance."""
        if service_type not in CONNECTOR_REGISTRY:
            raise ValueError(f"Unknown service type: {service_type}")
        
        connector_class = CONNECTOR_REGISTRY[service_type]
        return connector_class(**config)
    
    def _execute_inventory_sync(
        self, 
        source_data: List[Dict[str, Any]], 
        transformed_data: List[Dict[str, Any]], 
        target_connector,
        config: SyncConfig
    ) -> List[SyncResult]:
        """
        Execute inventory synchronization.
        
        Args:
            source_data: Original data from source
            transformed_data: Transformed data ready for target
            target_connector: Target connector instance
            config: Sync configuration
            
        Returns:
            List of sync results
        """
        results = []
        items_to_write = []
        
        # Read existing target data for comparison
        try:
            # We already read this in execute_sync, but we can't easily pass it down
            # so we re-read. This could be optimized.
            target_data = target_connector.read_inventory()
            target_by_sku = {item.get("sku"): item for item in target_data if item.get("sku")}
        except Exception as e:
            logger.warning(f"Could not read target data for comparison: {e}")
            target_by_sku = {}
        
        # Process each item
        for i, (source_item, transformed_item) in enumerate(zip(source_data, transformed_data)):
            sku = source_item.get("sku")
            if not sku:
                results.append(SyncResult(
                    sku="UNKNOWN",
                    status=SyncItemStatus.FAILED,
                    message="SKU not found in source data"
                ))
                continue
            
            # Check current target value
            target_item = target_by_sku.get(sku)
            current_target_value = None
            if target_item:
                # Find the target field name for comparison
                quantity_field = self._get_target_quantity_field(config)
                current_target_value = target_item.get(quantity_field)
            
            # Get new value that would be set
            new_value = transformed_item.get("quantity_to_set")
            source_value = source_item.get("available")  # Assuming we sync available quantity
            
            # Determine if sync is needed
            if current_target_value is not None:
                try:
                    current_val = int(current_target_value) if current_target_value != "" else 0
                    new_val = int(new_value) if new_value is not None else 0
                    
                    if current_val == new_val:
                        results.append(SyncResult(
                            sku=sku,
                            status=SyncItemStatus.MATCH,
                            source_value=source_value,
                            target_value=current_val,
                            new_value=new_val,
                            message="Values already match"
                        ))
                        continue
                except (ValueError, TypeError):
                    pass  # Fall through to sync
            
            # Add to items that need syncing
            items_to_write.append(transformed_item)
            
            results.append(SyncResult(
                sku=sku,
                status=SyncItemStatus.SUCCESS,  # Will be updated after write
                source_value=source_value,
                target_value=current_target_value,
                new_value=new_value
            ))
        
        # Write items that need updating
        if items_to_write:
            try:
                logger.info(f"Writing {len(items_to_write)} items to target")
                write_result = target_connector.write_inventory(items_to_write)
                
                # Update results based on write success
                success_count = write_result.get("success", 0)
                failed_count = write_result.get("failed", 0)
                
                # Mark results as success or failed based on bulk result
                # For simplicity, assume success if we got a success count
                written_count = 0
                for result in results:
                    if result.status == SyncItemStatus.SUCCESS:
                        if written_count < success_count:
                            result.status = SyncItemStatus.SUCCESS
                            result.message = "Successfully updated"
                        else:
                            result.status = SyncItemStatus.FAILED
                            result.message = "Write operation failed"
                        written_count += 1
                        
            except Exception as e:
                logger.error(f"Failed to write inventory: {e}")
                # Mark all pending writes as failed
                for result in results:
                    if result.status == SyncItemStatus.SUCCESS:
                        result.status = SyncItemStatus.FAILED
                        result.message = f"Write failed: {e}"
        
        return results
    
    def _get_target_quantity_field(self, config: SyncConfig) -> str:
        """Get the field name used for quantity in target system."""
        # Look for quantity mapping in field mappings
        for mapping in config.field_mappings:
            if mapping.source_field in ["available", "quantity", "on_hand"]:
                if mapping.target_field in ["quantity", "quantity_to_set"]:
                    return "quantity"  # Return the read field name
        return "quantity"  # Default
    
    def validate_config(self, config: SyncConfig) -> Dict[str, Any]:
        """
        Validate a sync configuration.
        
        Args:
            config: Configuration to validate
            
        Returns:
            Validation result with status and messages
        """
        errors = []
        warnings = []
        
        try:
            # Check if service types are supported
            if config.source.service_type not in CONNECTOR_REGISTRY:
                errors.append(f"Unsupported source service: {config.source.service_type}")
            if config.target.service_type not in CONNECTOR_REGISTRY:
                errors.append(f"Unsupported target service: {config.target.service_type}")
            
            # Test connector creation and connections
            if not errors:
                try:
                    source_connector = self._create_connector(
                        config.source.service_type,
                        config.get_source_connector_config()
                    )
                    if not source_connector.test_connection():
                        errors.append(f"Cannot connect to source service: {config.source.service_type}")
                except Exception as e:
                    errors.append(f"Source connector error: {e}")
                
                try:
                    target_connector = self._create_connector(
                        config.target.service_type,
                        config.get_target_connector_config()
                    )
                    if not target_connector.test_connection():
                        errors.append(f"Cannot connect to target service: {config.target.service_type}")
                except Exception as e:
                    errors.append(f"Target connector error: {e}")
            
            # Validate field mappings
            if not config.field_mappings:
                errors.append("At least one field mapping is required")
            
            for mapping in config.field_mappings:
                if not mapping.source_field or not mapping.target_field:
                    errors.append(f"Invalid field mapping: {mapping}")
            
            # Validate schedule format if provided
            if config.schedule:
                # Basic cron validation (can be enhanced)
                parts = config.schedule.split()
                if len(parts) != 5:
                    errors.append("Schedule must be a valid cron expression (5 parts)")
            
        except Exception as e:
            errors.append(f"Validation error: {e}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        } 
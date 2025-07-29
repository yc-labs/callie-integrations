"""
Workflow execution engine for configurable stage-based workflows.

This engine can execute any workflow defined by stages, calling connector methods
dynamically and passing data between stages based on configuration.
"""

import logging
import time
import inspect
from datetime import datetime
from typing import Dict, List, Any, Optional, Type, Union
import os
import asyncio

from ..models.stages import (
    WorkflowConfig, WorkflowExecution, StageConfig, StageResult,
    StageType, StageErrorStrategy
)
from ..connectors.base import BaseConnector
from ..connectors.shipstation import ShipStationConnector
from ..connectors.infiplex import InfiPlexConnector
from ..services.secrets import SecretManagerService

logger = logging.getLogger(__name__)


class WorkflowExecutionContext:
    """Context that maintains state during workflow execution."""

    def __init__(self, workflow: WorkflowConfig):
        self.workflow = workflow
        self.variables: Dict[str, Any] = workflow.variables.copy()
        self.stage_results: List[StageResult] = []
        self.connectors: Dict[str, BaseConnector] = {}
        self.execution: Optional[WorkflowExecution] = None

    def set_variable(self, name: str, value: Any):
        """Set a variable in the context."""
        self.variables[name] = value
        logger.debug(f"Set variable {name} = {type(value).__name__}")

    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get a variable from the context."""
        return self.variables.get(name, default)

    def get_connector(self, name: str) -> BaseConnector:
        """Get a connector instance."""
        if name not in self.connectors:
            raise ValueError(f"Connector '{name}' not found. Available: {list(self.connectors.keys())}")
        return self.connectors[name]


class WorkflowEngine:
    """Executes configurable stage-based workflows."""

    def __init__(self, secret_service: Optional[SecretManagerService] = None):
        self.connector_classes = {
            "shipstation": ShipStationConnector,
            "infiplex": InfiPlexConnector
        }
        self.integration_configs: Dict[str, Dict[str, Any]] = {}
        if secret_service:
            self.secret_service = secret_service
        else:
            # Fallback for older initialization paths, though app.py now provides it
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            if project_id:
                self.secret_service = SecretManagerService(project_id=project_id)
            else:
                logger.warning("WorkflowEngine initialized without a SecretManagerService and no GOOGLE_CLOUD_PROJECT set.")
                self.secret_service = None

    def load_integration_configs(self):
        """Load integration configurations from Secret Manager using known secret names."""
        if not self.secret_service:
            logger.warning("SecretManagerService not available, skipping integration config loading.")
            return

        logger.info("Loading integration configurations from Secret Manager...")
        try:
            # Load ShipStation credentials
            shipstation_api_key = self.secret_service.get_secret("shipstation-api-key")
            shipstation_base_url = self.secret_service.get_secret("shipstation-base-url")
            self.integration_configs["shipstation"] = {
                "api_key": shipstation_api_key,
                "base_url": shipstation_base_url
            }
            logger.info(f"Loaded ShipStation integration config: api_key={'*' * len(shipstation_api_key) if shipstation_api_key else 'None'}, base_url={shipstation_base_url}")

            # Load InfiPlex credentials (default warehouse 17)
            infiplex_api_key = self.secret_service.get_secret("infiplex-api-key")
            infiplex_base_url = self.secret_service.get_secret("infiplex-base-url")
            self.integration_configs["infiplex"] = {
                "api_key": infiplex_api_key,
                "base_url": infiplex_base_url
            }
            logger.info(f"Loaded InfiPlex integration config: api_key={'*' * len(infiplex_api_key) if infiplex_api_key else 'None'}, base_url={infiplex_base_url}")

            logger.info(f"Successfully loaded {len(self.integration_configs)} integration configurations.")
        except Exception as e:
            logger.error(f"Failed to load integration configurations: {e}")
            # Don't raise - let the workflow continue and individual stages can handle missing credentials

    def execute_workflow(self, workflow: WorkflowConfig, triggered_by: str = "manual", initial_variables: Optional[Dict[str, Any]] = None) -> WorkflowExecution:
        """Execute a complete workflow."""
        # Load integration configs before execution
        self.load_integration_configs()
        
        execution_id = f"workflow_{workflow.id}_{int(time.time())}"
        execution = WorkflowExecution(
            id=execution_id,
            workflow_id=workflow.id,
            triggered_by=triggered_by,
            total_stages=len([s for s in workflow.stages if s.enabled])
        )

        logger.info(f"Starting workflow execution: {execution_id}")

        try:
            context = WorkflowExecutionContext(workflow)
            if initial_variables:
                context.variables.update(initial_variables)
            
            # Initialize connectors
            self._initialize_connectors(workflow, context)

            # Execute stages in order
            for stage in workflow.stages:
                if not stage.enabled:
                    logger.info(f"Skipping disabled stage: {stage.id}")
                    continue

                # Check dependencies
                if not self._check_dependencies(stage, context):
                    logger.warning(f"Dependencies not met for stage: {stage.id}")
                    continue

                # Execute stage
                stage_result = self._execute_stage(stage, context)
                execution.stage_results.append(stage_result)
                context.stage_results.append(stage_result)

                # Update execution counts
                if stage_result.status == "success":
                    execution.completed_stages += 1
                elif stage_result.status == "failed":
                    execution.failed_stages += 1
                    if stage.error_strategy == StageErrorStrategy.FAIL:
                        execution.status = "failed"
                        execution.error_message = stage_result.error_message
                        break
                elif stage_result.status == "skipped":
                    execution.skipped_stages += 1

            # Mark as completed if we didn't fail
            if execution.status == "running":
                execution.status = "completed"

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            execution.status = "failed"
            execution.error_message = str(e)

        finally:
            execution.completed_at = datetime.utcnow()
            if execution.started_at:
                execution.execution_time_seconds = (
                    execution.completed_at - execution.started_at
                ).total_seconds()

            # Store execution in context for potential access
            context.execution = execution

        logger.info(f"Workflow execution completed: {execution_id} - Status: {execution.status}")
        return execution

    def _execute_stage(self, stage: StageConfig, context: WorkflowExecutionContext) -> StageResult:
        """Execute a single stage."""
        logger.info(f"Executing stage: {stage.id} ({stage.type})")

        try:
            result = StageResult(stage_id=stage.id, status="running")
            logger.info(f"Created StageResult for {stage.id}: {result}")
        except Exception as e:
            logger.error(f"Failed to create StageResult for {stage.id}: {e}")
            raise

        try:
            # Check condition if specified
            if stage.condition and not self._evaluate_condition(stage.condition, context):
                result.status = "skipped"
                result.completed_at = datetime.utcnow()
                return result

            # Execute based on stage type
            if stage.type == StageType.CONNECTOR_METHOD:
                output_data = self._execute_connector_method(stage, context)
            elif stage.type == StageType.TRANSFORM:
                output_data = self._execute_transform(stage, context)
            elif stage.type == StageType.FILTER:
                output_data = self._execute_filter(stage, context)
            elif stage.type == StageType.MAP_FIELDS:
                output_data = self._execute_map_fields(stage, context)
            elif stage.type == StageType.SET_VARIABLE:
                output_data = self._execute_set_variable(stage, context)
            elif stage.type == StageType.LOG:
                output_data = self._execute_log(stage, context)
            else:
                raise ValueError(f"Unknown stage type: {stage.type}")

            # Store output in variable if specified
            if stage.output_variable and output_data is not None:
                context.set_variable(stage.output_variable, output_data)

            result.output_data = output_data
            result.status = "success"

            if isinstance(output_data, list):
                result.items_processed = len(output_data)
            elif isinstance(output_data, dict) and "items" in output_data:
                result.items_processed = len(output_data["items"])

        except Exception as e:
            logger.error(f"Stage {stage.id} failed: {e}")
            result.status = "failed"
            result.error_message = str(e)

            # Handle retries
            if stage.error_strategy == StageErrorStrategy.RETRY and result.retry_count < stage.retry_count:
                logger.info(f"Retrying stage {stage.id} (attempt {result.retry_count + 1})")
                time.sleep(stage.retry_delay)
                result.retry_count += 1
                return self._execute_stage(stage, context)  # Recursive retry

        finally:
            result.completed_at = datetime.utcnow()
            if result.started_at:
                result.execution_time_seconds = (
                    result.completed_at - result.started_at
                ).total_seconds()

        logger.info(f"Returning StageResult for {stage.id}: {result}")
        return result

    def _initialize_connectors(self, workflow: WorkflowConfig, context: WorkflowExecutionContext):
        """Initialize basic connector instances without credentials."""
        # Initialize source connector (basic instance)
        source_config = workflow.source
        source_type = source_config.get("service_type")
        if source_type in self.connector_classes:
            connector_class = self.connector_classes[source_type]
            # Create basic connector without credentials - credentials handled per-stage
            context.connectors["source"] = connector_class()

        # Initialize target connector (basic instance)
        target_config = workflow.target
        target_type = target_config.get("service_type")
        if target_type in self.connector_classes:
            connector_class = self.connector_classes[target_type]
            # Create basic connector without credentials - credentials handled per-stage
            context.connectors["target"] = connector_class()

        logger.info(f"Initialized basic connectors: {list(context.connectors.keys())}")

    def _check_dependencies(self, stage: StageConfig, context: WorkflowExecutionContext) -> bool:
        """Check if stage dependencies are met."""
        if not stage.depends_on:
            return True

        completed_stages = {r.stage_id for r in context.stage_results if r.status == "success"}
        return all(dep_id in completed_stages for dep_id in stage.depends_on)

    def _get_stage_connector(self, stage: StageConfig, context: WorkflowExecutionContext) -> BaseConnector:
        """Get connector for a specific stage."""
        connector_name = stage.connector
        
        # SIMPLIFIED: Always use the basic connector
        # Credentials are handled in _execute_connector_method via credentials_key
        return context.get_connector(connector_name)

    def _execute_connector_method(self, stage: StageConfig, context: WorkflowExecutionContext) -> Any:
        """Execute a connector method dynamically."""
        if not stage.connector or not stage.method:
            raise ValueError(f"Stage {stage.id}: connector and method are required for connector_method type")

        # Get the appropriate connector (default or stage-specific)
        connector = self._get_stage_connector(stage, context)
        method_name = stage.method

        if not hasattr(connector, method_name):
            raise ValueError(f"Connector {stage.connector} does not have method {method_name}")

        method = getattr(connector, method_name)

        # Prepare method arguments
        method_args = {}
        sig = inspect.signature(method)

        # Add parameters from stage config
        method_args.update(stage.parameters)

        # Add input variables
        for var_name in stage.input_variables:
            if var_name in context.variables:
                method_args[var_name] = context.variables[var_name]

        # New simplified credential system using integration configs
        connector_type = None
        if stage.connector == "source":
            connector_type = "shipstation"
        elif stage.connector == "target":
            connector_type = "infiplex"
        
        if connector_type:
            try:
                credentials = self.integration_configs.get(connector_type)
                logger.info(f"Looking up credentials for {connector_type}: {credentials is not None}")
                
                # Add credentials to method args if the method expects them
                if credentials and "api_key" in sig.parameters and "api_key" in credentials:
                    method_args["api_key"] = credentials["api_key"]
                    logger.info(f"Added API key for {connector_type} connector")
                else:
                    logger.warning(f"No API key available for {connector_type} connector. Credentials: {credentials is not None}, sig has api_key: {'api_key' in sig.parameters}")
                
                if credentials and "base_url" in sig.parameters and "base_url" in credentials:
                    method_args["base_url"] = credentials["base_url"]
                    logger.info(f"Added base URL for {connector_type} connector")
                else:
                    logger.warning(f"No base URL available for {connector_type} connector. Credentials: {credentials is not None}, sig has base_url: {'base_url' in sig.parameters}")
                    
            except Exception as e:
                logger.error(f"Failed to get credentials for {connector_type}: {e}")
                # Continue execution - let the connector handle missing credentials

        # Filter arguments to only include those the method accepts
        
        # Check if method accepts **kwargs (VAR_KEYWORD)
        accepts_kwargs = any(
            param.kind == inspect.Parameter.VAR_KEYWORD 
            for param in sig.parameters.values()
        )
        
        if accepts_kwargs:
            # If method accepts **kwargs, pass all arguments through
            filtered_args = {k: v for k, v in method_args.items() if k != 'self'}
        else:
            # Otherwise, filter to only include named parameters
            filtered_args = {
                k: v for k, v in method_args.items()
                if k in sig.parameters
            }

        logger.info(f"Calling {stage.connector}.{method_name} with args: {list(filtered_args.keys())}")
        logger.info(f"Full arguments: {filtered_args}")

        # Call the method
        return method(**filtered_args)

    def _execute_transform(self, stage: StageConfig, context: WorkflowExecutionContext) -> Any:
        """Execute a data transformation."""
        # Get input data
        input_data = None
        if stage.input_variables:
            input_data = context.get_variable(stage.input_variables[0])

        transform_type = stage.parameters.get("transform_type", "identity")

        if transform_type == "identity":
            return input_data
        elif transform_type == "extract_field":
            field = stage.parameters.get("field")
            if isinstance(input_data, list):
                return [item.get(field) for item in input_data if isinstance(item, dict)]
            elif isinstance(input_data, dict):
                return input_data.get(field)
        elif transform_type == "filter_field":
            field = stage.parameters.get("field")
            value = stage.parameters.get("value")
            if isinstance(input_data, list):
                return [item for item in input_data if item.get(field) == value]
        elif transform_type == "add_field":
            field = stage.parameters.get("field")
            value = stage.parameters.get("value")
            if isinstance(input_data, list):
                result = []
                for item in input_data:
                    if isinstance(item, dict):
                        new_item = item.copy()
                        new_item[field] = value
                        result.append(new_item)
                    else:
                        result.append(item)
                return result
            elif isinstance(input_data, dict):
                result = input_data.copy()
                result[field] = value
                return result
        elif transform_type == "slice":
            start = stage.parameters.get("start", 0)
            end = stage.parameters.get("end", 5)
            if isinstance(input_data, list):
                return input_data[start:end]

        return input_data

    def _execute_filter(self, stage: StageConfig, context: WorkflowExecutionContext) -> Any:
        """Execute a filter operation."""
        input_data = None
        if stage.input_variables:
            input_data = context.get_variable(stage.input_variables[0])

        if not isinstance(input_data, list):
            return input_data

        filter_field = stage.parameters.get("field")
        value_from_variable = stage.parameters.get("value_from_variable")

        if filter_field and value_from_variable:
            filter_values = context.get_variable(value_from_variable)
            if isinstance(filter_values, list):
                filter_set = set(filter_values)
                return [item for item in input_data if item.get(filter_field) in filter_set]

        # Fallback to original simple filter
        filter_value = stage.parameters.get("value")
        if filter_field and filter_value is not None:
            return [item for item in input_data if item.get(filter_field) == filter_value]

        return input_data

    def _execute_map_fields(self, stage: StageConfig, context: WorkflowExecutionContext) -> Any:
        """Execute field mapping."""
        input_data = None
        if stage.input_variables:
            input_data = context.get_variable(stage.input_variables[0])

        field_mappings = stage.parameters.get("mappings", {})

        if isinstance(input_data, list):
            return [
                {field_mappings.get(k, k): v for k, v in item.items()}
                for item in input_data if isinstance(item, dict)
            ]
        elif isinstance(input_data, dict):
            return {field_mappings.get(k, k): v for k, v in input_data.items()}

        return input_data

    def _execute_set_variable(self, stage: StageConfig, context: WorkflowExecutionContext) -> Any:
        """Set a variable to a specific value."""
        var_name = stage.parameters.get("variable_name")
        var_value = stage.parameters.get("value")

        if var_name:
            context.set_variable(var_name, var_value)

        return var_value

    def _execute_log(self, stage: StageConfig, context: WorkflowExecutionContext) -> Any:
        """Log a message."""
        message = stage.parameters.get("message", "")
        log_level = stage.parameters.get("level", "info").lower()

        # Replace variables in message
        for var_name, var_value in context.variables.items():
            placeholder = f"{{{var_name}}}"
            if placeholder in message:
                message = message.replace(placeholder, str(var_value))
            
            len_placeholder = f"{{len({var_name})}}"
            if len_placeholder in message:
                if isinstance(var_value, list):
                    message = message.replace(len_placeholder, str(len(var_value)))
                else:
                    message = message.replace(len_placeholder, "N/A")

        if log_level == "debug":
            logger.debug(message)
        elif log_level == "info":
            logger.info(message)
        elif log_level == "warning":
            logger.warning(message)
        elif log_level == "error":
            logger.error(message)

        return message

    def _evaluate_condition(self, condition: str, context: WorkflowExecutionContext) -> bool:
        """Evaluate a simple condition."""
        # For now, just check if a variable exists and is truthy
        if condition.startswith("exists:"):
            var_name = condition[7:]
            return var_name in context.variables and context.variables[var_name]

        # More condition types can be added here
        return True 
#!/bin/bash
set -e

# Get service URL
if [ -z "$SERVICE_URL" ]; then
    SERVICE_URL="https://callie-api-4mrdokvqlq-uc.a.run.app"
fi

echo "🔧 Creating sample ShipStation → InfiPlex workflow configuration..."
echo "🌐 Service URL: $SERVICE_URL"

# Create the workflow configuration directly (no file dependency)
WORKFLOW_JSON='{
  "id": "shipstation-to-infiplex-configurable",
  "name": "ShipStation to InfiPlex Inventory Sync (Fully Configurable)",
  "description": "Configurable workflow that gets InfiPlex SKUs, queries ShipStation for each, handles zero inventory, and bulk updates InfiPlex",
  "version": "1.0",
  "source": {
    "service_type": "shipstation",
    "credentials": {
      "api_key": "${SHIPSTATION_API_KEY}"
    },
    "base_url": "https://api.shipstation.com"
  },
  "target": {
    "service_type": "infiplex", 
    "credentials": {
      "api_key": "${INFIPLEX_API_KEY}"
    },
    "base_url": "${INFIPLEX_BASE_URL}",
    "warehouse_id": 17
  },
  "variables": {
    "warehouse_id": 17,
    "sync_description": "Configurable ShipStation to InfiPlex sync"
  },
  "stages": [
    {
      "id": "log_start",
      "name": "Log Sync Start",
      "type": "log",
      "parameters": {
        "message": "Starting {sync_description} for warehouse {warehouse_id}",
        "level": "info"
      }
    },
    {
      "id": "get_infiplex_skus",
      "name": "Get InfiPlex SKUs",
      "description": "Get all SKUs from InfiPlex to determine what to sync",
      "type": "connector_method",
      "connector": "target",
      "method": "read_inventory",
      "parameters": {},
      "output_variable": "infiplex_inventory",
      "error_strategy": "fail"
    },
    {
      "id": "extract_sku_list",
      "name": "Extract SKU List",
      "description": "Extract just the SKUs from InfiPlex inventory data",
      "type": "transform",
      "input_variables": ["infiplex_inventory"],
      "parameters": {
        "transform_type": "extract_field",
        "field": "sku"
      },
      "output_variable": "target_skus",
      "depends_on": ["get_infiplex_skus"]
    },
    {
      "id": "log_sku_count",
      "name": "Log SKU Count",
      "type": "log",
      "parameters": {
        "message": "Found {target_skus} SKUs in InfiPlex to sync",
        "level": "info"
      },
      "depends_on": ["extract_sku_list"]
    },
    {
      "id": "get_shipstation_inventory",
      "name": "Get ShipStation Inventory for SKUs",
      "description": "Query ShipStation for inventory data for each InfiPlex SKU",
      "type": "connector_method", 
      "connector": "source",
      "method": "read_inventory",
      "parameters": {},
      "input_variables": ["target_skus"],
      "output_variable": "shipstation_inventory",
      "depends_on": ["extract_sku_list"],
      "error_strategy": "fail"
    },
    {
      "id": "log_retrieved_count",
      "name": "Log Retrieved Count",
      "type": "log",
      "parameters": {
        "message": "Retrieved {shipstation_inventory} items from ShipStation",
        "level": "info"
      },
      "depends_on": ["get_shipstation_inventory"]
    },
    {
      "id": "map_inventory_fields",
      "name": "Map Inventory Fields",
      "description": "Map ShipStation fields to InfiPlex format",
      "type": "map_fields",
      "input_variables": ["shipstation_inventory"],
      "parameters": {
        "mappings": {
          "sku": "sku",
          "available": "quantity_to_set"
        }
      },
      "output_variable": "mapped_inventory",
      "depends_on": ["get_shipstation_inventory"]
    },
    {
      "id": "add_warehouse_id",
      "name": "Add Warehouse ID",
      "description": "Add warehouse_id to each inventory item",
      "type": "transform",
      "input_variables": ["mapped_inventory"],
      "parameters": {
        "transform_type": "add_field",
        "field": "warehouse_id",
        "value": 17
      },
      "output_variable": "final_inventory",
      "depends_on": ["map_inventory_fields"]
    },
    {
      "id": "log_final_count",
      "name": "Log Final Count",
      "type": "log",
      "parameters": {
        "message": "Prepared {final_inventory} items for bulk update to InfiPlex",
        "level": "info"
      },
      "depends_on": ["add_warehouse_id"]
    },
    {
      "id": "bulk_update_infiplex",
      "name": "Bulk Update InfiPlex",
      "description": "Send bulk inventory update to InfiPlex",
      "type": "connector_method",
      "connector": "target", 
      "method": "_bulk_update_inventory",
      "input_variables": ["final_inventory"],
      "parameters": {},
      "output_variable": "update_result",
      "depends_on": ["add_warehouse_id"],
      "error_strategy": "fail",
      "retry_count": 3,
      "retry_delay": 10
    },
    {
      "id": "log_completion",
      "name": "Log Completion",
      "type": "log",
      "parameters": {
        "message": "Successfully completed {sync_description}. Result: {update_result}",
        "level": "info"
      },
      "depends_on": ["bulk_update_infiplex"]
    }
  ],
  "schedule": "0 */6 * * *",
  "active": true,
  "timeout_seconds": 1800
}'

echo "📤 Sending workflow configuration to API..."
RESPONSE=$(curl -s -X POST "$SERVICE_URL/api/v1/workflows" \
  -H "Content-Type: application/json" \
  -d "$WORKFLOW_JSON")

if echo "$RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
    WORKFLOW_ID=$(echo "$RESPONSE" | jq -r '.id')
    echo "✅ Workflow created successfully!"
    echo "🆔 Workflow ID: $WORKFLOW_ID"
    
    # Create schedule
    echo "⏰ Creating schedule..."
    SCHEDULE_RESPONSE=$(curl -s -X POST "$SERVICE_URL/api/v1/workflows/$WORKFLOW_ID/schedule" \
      -H "Content-Type: application/json")
    
    if echo "$SCHEDULE_RESPONSE" | jq -e '.job_name' > /dev/null 2>&1; then
        echo "✅ Schedule created successfully!"
        echo "⏰ Job name: $(echo "$SCHEDULE_RESPONSE" | jq -r '.job_name')"
    else
        echo "⚠️  Schedule creation failed: $SCHEDULE_RESPONSE"
    fi
    
    # Test sync
    echo "🧪 Testing workflow execution..."
    TEST_RESPONSE=$(curl -s -X POST "$SERVICE_URL/api/v1/workflows/$WORKFLOW_ID/execute-sync" \
      -H "Content-Type: application/json")
    
    echo "✅ Test workflow execution completed!"
    echo "📋 Response: $(echo "$TEST_RESPONSE" | jq '.')"
    
    echo ""
    echo "🎉 Sample workflow configuration is ready!"
    echo "📋 Workflow Details:"
    echo "   • Workflow ID: $WORKFLOW_ID"
    echo "   • Schedule: Every 6 hours (0 */6 * * *)"
    echo "   • Source: ShipStation (available inventory)"
    echo "   • Target: InfiPlex Warehouse 17"
    echo ""
    echo "🔗 Useful endpoints:"
    echo "   • Workflow: $SERVICE_URL/api/v1/workflows/$WORKFLOW_ID"
    echo "   • Executions: $SERVICE_URL/api/v1/workflows/$WORKFLOW_ID/executions"
    echo "   • Execute: $SERVICE_URL/api/v1/workflows/$WORKFLOW_ID/execute"
    echo "   • API Docs: $SERVICE_URL/docs"
    
else
    echo "❌ Workflow creation failed!"
    echo "📋 Response: $RESPONSE"
    exit 1
fi 
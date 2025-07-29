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
  "name": "ShipStation to InfiPlex Multi-Warehouse Inventory Sync",
  "description": "Configurable workflow that syncs inventory from ShipStation to multiple InfiPlex warehouses (17 and 18)",
  "version": "1.1",
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
  "credentials_config": {
    "infiplex_warehouse_17": {
      "secret_name": "infiplex-api-key",
      "warehouse_id": 17
    },
    "infiplex_warehouse_18": {
      "secret_name": "infiplex-warehouse-18-api-key",
      "warehouse_id": 18
    }
  },
  "variables": {
    "sync_description": "Multi-warehouse ShipStation to InfiPlex sync"
  },
  "stages": [
    {
      "id": "log_start",
      "name": "Log Sync Start",
      "type": "log",
      "parameters": {
        "message": "Starting {sync_description} for warehouses 17 and 18",
        "level": "info"
      }
    },
    {
      "id": "get_infiplex_skus_wh17",
      "name": "Get InfiPlex SKUs (Warehouse 17)",
      "description": "Get SKUs from InfiPlex warehouse 17 to determine what to sync",
      "type": "connector_method",
      "connector": "target",
      "method": "read_inventory",
      "credentials_key": "infiplex_warehouse_17",
      "parameters": {
        "warehouse_id": 17
      },
      "output_variable": "infiplex_inventory_wh17",
      "error_strategy": "fail"
    },
    {
      "id": "extract_sku_list",
      "name": "Extract SKU List",
      "description": "Extract just the SKUs from InfiPlex inventory data",
      "type": "transform",
      "input_variables": ["infiplex_inventory_wh17"],
      "parameters": {
        "transform_type": "extract_field",
        "field": "sku"
      },
      "output_variable": "target_skus",
      "depends_on": ["get_infiplex_skus_wh17"]
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
      "id": "add_warehouse_id_wh17",
      "name": "Add Warehouse ID (Warehouse 17)",
      "description": "Add warehouse_id 17 to each inventory item",
      "type": "transform",
      "input_variables": ["mapped_inventory"],
      "parameters": {
        "transform_type": "add_field",
        "field": "warehouse_id",
        "value": 17
      },
      "output_variable": "items_wh17",
      "depends_on": ["map_inventory_fields"]
    },
    {
      "id": "add_warehouse_id_wh18",
      "name": "Add Warehouse ID (Warehouse 18)",
      "description": "Add warehouse_id 18 to each inventory item",
      "type": "transform",
      "input_variables": ["mapped_inventory"],
      "parameters": {
        "transform_type": "add_field",
        "field": "warehouse_id",
        "value": 18
      },
      "output_variable": "items_wh18",
      "depends_on": ["map_inventory_fields"]
    },
    {
      "id": "bulk_update_infiplex_wh17",
      "name": "Bulk Update InfiPlex (Warehouse 17)",
      "description": "Send bulk inventory update to InfiPlex warehouse 17",
      "type": "connector_method",
      "connector": "target", 
      "method": "_write_inventory",
      "credentials_key": "infiplex_warehouse_17",
      "input_variables": ["items_wh17"],
      "parameters": {},
      "output_variable": "update_result_wh17",
      "depends_on": ["add_warehouse_id_wh17"],
      "error_strategy": "fail",
      "retry_count": 3,
      "retry_delay": 10
    },
    {
      "id": "bulk_update_infiplex_wh18",
      "name": "Bulk Update InfiPlex (Warehouse 18)",
      "description": "Send bulk inventory update to InfiPlex warehouse 18",
      "type": "connector_method",
      "connector": "target",
      "method": "_write_inventory",
      "credentials_key": "infiplex_warehouse_18",
      "input_variables": ["items_wh18"],
      "parameters": {},
      "output_variable": "update_result_wh18",
      "depends_on": ["add_warehouse_id_wh18"],
      "error_strategy": "fail",
      "retry_count": 3,
      "retry_delay": 10
    },
    {
      "id": "log_completion",
      "name": "Log Completion",
      "type": "log",
      "parameters": {
        "message": "Successfully completed {sync_description}. WH17 Result: {update_result_wh17}, WH18 Result: {update_result_wh18}",
        "level": "info"
      },
      "depends_on": ["bulk_update_infiplex_wh17", "bulk_update_infiplex_wh18"]
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
    echo "   • Target: InfiPlex Warehouses 17 and 18"
    echo "   • Multi-warehouse sync with separate credentials"
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
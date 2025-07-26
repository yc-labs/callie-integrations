#!/bin/bash
set -e

# Get service URL
if [ -z "$SERVICE_URL" ]; then
    SERVICE_URL="https://callie-api-4mrdokvqlq-uc.a.run.app"
fi

echo "🔧 Creating sample ShipStation → InfiPlex sync configuration..."
echo "🌐 Service URL: $SERVICE_URL"

# Create the configuration
CONFIG_JSON='{
  "name": "ShipStation to InfiPlex Inventory Sync",
  "description": "Syncs available inventory from ShipStation to InfiPlex warehouse 17",
  "source": {
    "service_type": "shipstation",
    "credentials": {
      "api_key": "'"$SHIPSTATION_API_KEY"'"
    },
    "base_url": "https://api.shipstation.com",
    "warehouse_id": null
  },
  "target": {
    "service_type": "infiplex",
    "credentials": {
      "api_key": "'"$INFIPLEX_API_KEY"'"
    },
    "base_url": "https://calibratenetwork.infiplex.com",
    "warehouse_id": 17
  },
  "field_mappings": [
    {
      "source_field": "available",
      "target_field": "quantity_to_set",
      "transform": null,
      "required": true
    },
    {
      "source_field": "sku",
      "target_field": "sku",
      "transform": null,
      "required": true
    }
  ],
  "schedule": "*/5 * * * *",
  "sync_options": {
    "limit": null,
    "warehouse_id": 17
  },
  "active": true
}'

echo "📤 Sending configuration to API..."
RESPONSE=$(curl -s -X POST "$SERVICE_URL/api/v1/configs" \
  -H "Content-Type: application/json" \
  -d "$CONFIG_JSON")

if echo "$RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
    CONFIG_ID=$(echo "$RESPONSE" | jq -r '.id')
    echo "✅ Configuration created successfully!"
    echo "🆔 Config ID: $CONFIG_ID"
    
    # Create schedule
    echo "⏰ Creating schedule..."
    SCHEDULE_JSON='{
      "schedule": "*/5 * * * *",
      "description": "Run inventory sync every 5 minutes"
    }'
    
    SCHEDULE_RESPONSE=$(curl -s -X POST "$SERVICE_URL/api/v1/configs/$CONFIG_ID/schedule" \
      -H "Content-Type: application/json" \
      -d "$SCHEDULE_JSON")
    
    if echo "$SCHEDULE_RESPONSE" | jq -e '.job_name' > /dev/null 2>&1; then
        echo "✅ Schedule created successfully!"
        echo "⏰ Job name: $(echo "$SCHEDULE_RESPONSE" | jq -r '.job_name')"
    else
        echo "⚠️  Schedule creation failed: $SCHEDULE_RESPONSE"
    fi
    
    # Test sync
    echo "🧪 Testing sync..."
    TEST_RESPONSE=$(curl -s -X POST "$SERVICE_URL/api/v1/configs/$CONFIG_ID/sync" \
      -H "Content-Type: application/json" \
      -d '{"triggered_by": "manual_test"}')
    
    echo "✅ Test sync triggered!"
    echo "📋 Response: $TEST_RESPONSE"
    
    echo ""
    echo "🎉 Sample configuration is ready!"
    echo "📋 Configuration Details:"
    echo "   • Config ID: $CONFIG_ID"
    echo "   • Schedule: Every 5 minutes"
    echo "   • Source: ShipStation (available inventory)"
    echo "   • Target: InfiPlex Warehouse 17"
    echo ""
    echo "🔗 Useful endpoints:"
    echo "   • Status: $SERVICE_URL/api/v1/configs/$CONFIG_ID/status"
    echo "   • Executions: $SERVICE_URL/api/v1/configs/$CONFIG_ID/executions"
    echo "   • API Docs: $SERVICE_URL/docs"
    
else
    echo "❌ Configuration creation failed!"
    echo "📋 Response: $RESPONSE"
    exit 1
fi 
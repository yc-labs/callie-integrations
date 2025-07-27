#!/bin/bash
set -e

# Get service URL
if [ -z "$SERVICE_URL" ]; then
    SERVICE_URL="https://callie-api-4mrdokvqlq-uc.a.run.app"
fi

echo "🔧 Creating sample ShipStation → InfiPlex workflow configuration..."
echo "🌐 Service URL: $SERVICE_URL"

# Use the existing workflow configuration and inject credentials
WORKFLOW_JSON=$(cat workflows/shipstation-to-infiplex-configurable.json | jq --arg shipstation_key "$SHIPSTATION_API_KEY" --arg infiplex_key "$INFIPLEX_API_KEY" --arg infiplex_url "$INFIPLEX_BASE_URL" '
  .source.credentials.api_key = $shipstation_key |
  .target.credentials.api_key = $infiplex_key |
  .target.base_url = $infiplex_url
')

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
#!/bin/bash

set -e

# Configuration
PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project)}
REGION=${REGION:-us-central1}
JOB_NAME=${JOB_NAME:-inventory-sync-job}
SCHEDULER_JOB_NAME=${SCHEDULER_JOB_NAME:-inventory-sync-scheduler}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}📊 Checking deployment status${NC}"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo

# Check Cloud Run job
echo -e "${YELLOW}🏃 Cloud Run Job Status:${NC}"
if gcloud run jobs describe $JOB_NAME --region=$REGION --project=$PROJECT_ID >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Cloud Run job exists${NC}"
    
    # Get job details
    JOB_STATUS=$(gcloud run jobs describe $JOB_NAME --region=$REGION --project=$PROJECT_ID --format="value(status.conditions[0].type)")
    echo "  Status: $JOB_STATUS"
    
    # Get last execution
    LAST_EXECUTION=$(gcloud run jobs executions list --job=$JOB_NAME --region=$REGION --project=$PROJECT_ID --limit=1 --format="value(metadata.name)" 2>/dev/null | head -1)
    if [ ! -z "$LAST_EXECUTION" ]; then
        echo "  Last execution: $LAST_EXECUTION"
        EXEC_STATUS=$(gcloud run jobs executions describe $LAST_EXECUTION --region=$REGION --project=$PROJECT_ID --format="value(status.conditions[0].type)" 2>/dev/null)
        echo "  Execution status: $EXEC_STATUS"
    else
        echo -e "${YELLOW}  ⚠️ No executions found${NC}"
    fi
else
    echo -e "${RED}❌ Cloud Run job not found${NC}"
fi

echo

# Check Cloud Scheduler
echo -e "${YELLOW}⏰ Cloud Scheduler Status:${NC}"
if gcloud scheduler jobs describe $SCHEDULER_JOB_NAME --location=$REGION --project=$PROJECT_ID >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Scheduler job exists${NC}"
    
    SCHEDULER_STATUS=$(gcloud scheduler jobs describe $SCHEDULER_JOB_NAME --location=$REGION --project=$PROJECT_ID --format="value(state)")
    echo "  Status: $SCHEDULER_STATUS"
    
    SCHEDULE=$(gcloud scheduler jobs describe $SCHEDULER_JOB_NAME --location=$REGION --project=$PROJECT_ID --format="value(schedule)")
    echo "  Schedule: $SCHEDULE"
    
    NEXT_RUN=$(gcloud scheduler jobs describe $SCHEDULER_JOB_NAME --location=$REGION --project=$PROJECT_ID --format="value(scheduleTime)" 2>/dev/null || echo "Unknown")
    echo "  Next run: $NEXT_RUN"
else
    echo -e "${RED}❌ Scheduler job not found${NC}"
fi

echo

# Check secrets
echo -e "${YELLOW}🔐 Secret Manager Status:${NC}"
SECRETS=("shipstation-api-key" "shipstation-base-url" "infiplex-api-key" "infiplex-base-url")
for secret in "${SECRETS[@]}"; do
    if gcloud secrets describe $secret --project=$PROJECT_ID >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Secret: $secret${NC}"
    else
        echo -e "${RED}❌ Secret missing: $secret${NC}"
    fi
done

echo

# Show recent logs
echo -e "${YELLOW}📝 Recent logs (last 10 entries):${NC}"
gcloud logs read --project=$PROJECT_ID \
    --filter='resource.type="cloud_run_job" AND resource.labels.job_name="'$JOB_NAME'"' \
    --limit=10 \
    --format="value(timestamp,severity,textPayload)" 2>/dev/null || echo "No logs found"

echo
echo -e "${GREEN}🔗 Useful commands:${NC}"
echo "  Manual trigger:  gcloud run jobs execute $JOB_NAME --region=$REGION --project=$PROJECT_ID"
echo "  View logs:       gcloud logs read --project=$PROJECT_ID --filter='resource.type=\"cloud_run_job\"'"
echo "  Local validation: ./scripts/validate-sync.sh" 
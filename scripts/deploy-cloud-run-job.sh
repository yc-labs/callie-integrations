#!/bin/bash

set -e

# Configuration
PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project)}
REGION=${REGION:-us-central1}
REPOSITORY=${REPOSITORY:-inventory-sync}
IMAGE_NAME=${IMAGE_NAME:-shipstation-infiplex-sync}
TAG=${TAG:-latest}
JOB_NAME=${JOB_NAME:-inventory-sync-job}
WAREHOUSE_ID=${WAREHOUSE_ID:-17}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}☁️ Deploying Cloud Run job${NC}"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Job Name: $JOB_NAME"
echo "Warehouse ID: $WAREHOUSE_ID"
echo

# Enable required APIs
echo -e "${YELLOW}🔧 Enabling required APIs...${NC}"
gcloud services enable run.googleapis.com --project=$PROJECT_ID
gcloud services enable cloudscheduler.googleapis.com --project=$PROJECT_ID

# Image URL
FULL_IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${TAG}"

# Create service account for Cloud Run job
echo -e "${YELLOW}👤 Creating service account...${NC}"
SERVICE_ACCOUNT="inventory-sync-sa"
if ! gcloud iam service-accounts describe ${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com --project=$PROJECT_ID >/dev/null 2>&1; then
    gcloud iam service-accounts create $SERVICE_ACCOUNT \
        --description="Service account for inventory sync job" \
        --display-name="Inventory Sync Service Account" \
        --project=$PROJECT_ID
else
    echo "Service account already exists ✅"
fi

# Grant Secret Manager access to service account
echo -e "${YELLOW}🔐 Granting Secret Manager access...${NC}"
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Check if job exists and delete it
if gcloud run jobs describe $JOB_NAME --region=$REGION --project=$PROJECT_ID >/dev/null 2>&1; then
    echo "Deleting existing job..."
    gcloud run jobs delete $JOB_NAME --region=$REGION --project=$PROJECT_ID --quiet
fi

# Deploy Cloud Run job
echo -e "${YELLOW}🚀 Deploying Cloud Run job...${NC}"
gcloud run jobs create $JOB_NAME \
    --image=$FULL_IMAGE_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --service-account=${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com \
    --set-secrets="SHIPSTATION_API_KEY=shipstation-api-key:latest" \
    --set-secrets="SHIPSTATION_BASE_URL=shipstation-base-url:latest" \
    --set-secrets="INFIPLEX_API_KEY=infiplex-api-key:latest" \
    --set-secrets="INFIPLEX_BASE_URL=infiplex-base-url:latest" \
    --cpu=1 \
    --memory=512Mi \
    --max-retries=3 \
    --args="bulk-sync,--all-skus,--warehouse-id,$WAREHOUSE_ID"

echo -e "${GREEN}✅ Cloud Run job deployed successfully!${NC}"

# Create Cloud Scheduler job for every 5 minutes
echo -e "${YELLOW}⏰ Creating Cloud Scheduler job (every 5 minutes)...${NC}"
SCHEDULER_JOB_NAME="inventory-sync-scheduler"

# Delete existing scheduler job if it exists
if gcloud scheduler jobs describe $SCHEDULER_JOB_NAME --location=$REGION --project=$PROJECT_ID >/dev/null 2>&1; then
    echo "Deleting existing scheduler job..."
    gcloud scheduler jobs delete $SCHEDULER_JOB_NAME \
        --location=$REGION \
        --project=$PROJECT_ID \
        --quiet
fi

# Create new scheduler job
gcloud scheduler jobs create http $SCHEDULER_JOB_NAME \
    --location=$REGION \
    --schedule="*/5 * * * *" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
    --http-method=POST \
    --oauth-service-account-email="${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --project=$PROJECT_ID

echo -e "${GREEN}✅ Cloud Scheduler job created successfully!${NC}"
echo
echo -e "${GREEN}📋 Deployment Summary:${NC}"
echo "  🏃 Cloud Run Job: $JOB_NAME"
echo "  ⏰ Scheduler: $SCHEDULER_JOB_NAME (every 5 minutes)"
echo "  🖼️  Image: $FULL_IMAGE_NAME"
echo "  👤 Service Account: ${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com"
echo "  🏭 Warehouse ID: $WAREHOUSE_ID"
echo
echo -e "${GREEN}🔗 Useful commands:${NC}"
echo "  View job logs: gcloud logs read --project=$PROJECT_ID --filter='resource.type=\"cloud_run_job\" AND resource.labels.job_name=\"$JOB_NAME\"'"
echo "  Trigger job manually: gcloud run jobs execute $JOB_NAME --region=$REGION --project=$PROJECT_ID"
echo "  View scheduler: gcloud scheduler jobs describe $SCHEDULER_JOB_NAME --location=$REGION --project=$PROJECT_ID" 
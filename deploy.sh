#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 ShipStation-InfiPlex Inventory Sync Deployment${NC}"
echo "=================================================="
echo

# Check prerequisites
echo -e "${YELLOW}🔍 Checking prerequisites...${NC}"

if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI not found. Please install Google Cloud SDK.${NC}"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker.${NC}"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found. Please create it with your API keys.${NC}"
    exit 1
fi

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ No active Google Cloud project. Run: gcloud config set project YOUR_PROJECT_ID${NC}"
    exit 1
fi

echo -e "${GREEN}✅ All prerequisites met!${NC}"
echo "Project ID: $PROJECT_ID"
echo

# Make scripts executable
echo -e "${YELLOW}🔧 Making scripts executable...${NC}"
chmod +x scripts/*.sh

# Step 1: Set up secrets
echo -e "${BLUE}📋 Step 1: Setting up secrets in Secret Manager${NC}"
./scripts/setup-secrets.sh

echo

# Step 2: Build and push Docker image
echo -e "${BLUE}📋 Step 2: Building and pushing Docker image${NC}"
./scripts/build-and-push.sh

echo

# Step 3: Deploy Cloud Run job
echo -e "${BLUE}📋 Step 3: Deploying Cloud Run job and scheduler${NC}"
./scripts/deploy-cloud-run-job.sh

echo

# Step 4: Test the deployment
echo -e "${BLUE}📋 Step 4: Testing deployment${NC}"
echo -e "${YELLOW}🧪 Running a test execution...${NC}"

REGION=${REGION:-us-central1}
JOB_NAME=${JOB_NAME:-inventory-sync-job}

gcloud run jobs execute $JOB_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --wait

echo
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo
echo -e "${GREEN}📋 What was deployed:${NC}"
echo "  🔐 Secrets in Secret Manager (API keys and URLs)"
echo "  🐳 Docker image in Artifact Registry"
echo "  🏃 Cloud Run job (inventory-sync-job)"
echo "  ⏰ Cloud Scheduler (runs every 5 minutes)"
echo
echo -e "${GREEN}🔗 Useful commands:${NC}"
echo "  Manual sync:     ./scripts/manual-sync.sh"
echo "  Validate sync:   ./scripts/validate-sync.sh"
echo "  View logs:       gcloud logs read --project=$PROJECT_ID --filter='resource.type=\"cloud_run_job\"'"
echo "  Trigger job:     gcloud run jobs execute $JOB_NAME --region=$REGION --project=$PROJECT_ID"
echo
echo -e "${GREEN}📊 Your inventory will now sync automatically every 5 minutes!${NC}" 
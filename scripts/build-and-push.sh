#!/bin/bash

set -e

# Configuration
PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project)}
REGION=${REGION:-us-central1}
REPOSITORY=${REPOSITORY:-inventory-sync}
IMAGE_NAME=${IMAGE_NAME:-shipstation-infiplex-sync}
TAG=${TAG:-latest}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Building and pushing inventory sync Docker image${NC}"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Repository: $REPOSITORY"
echo "Image: $IMAGE_NAME:$TAG"
echo

# Create Artifact Registry repository if it doesn't exist
echo -e "${YELLOW}📦 Checking Artifact Registry repository...${NC}"
if ! gcloud artifacts repositories describe $REPOSITORY \
    --location=$REGION \
    --project=$PROJECT_ID >/dev/null 2>&1; then
    echo "Creating Artifact Registry repository..."
    gcloud artifacts repositories create $REPOSITORY \
        --repository-format=docker \
        --location=$REGION \
        --description="Inventory sync Docker images" \
        --project=$PROJECT_ID
else
    echo "Repository already exists ✅"
fi

# Configure Docker to use Artifact Registry
echo -e "${YELLOW}🔧 Configuring Docker authentication...${NC}"
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

# Build image
echo -e "${YELLOW}🔨 Building Docker image...${NC}"
FULL_IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${TAG}"
docker build -t $FULL_IMAGE_NAME .

# Push image
echo -e "${YELLOW}📤 Pushing image to Artifact Registry...${NC}"
docker push $FULL_IMAGE_NAME

echo -e "${GREEN}✅ Successfully built and pushed image:${NC}"
echo "$FULL_IMAGE_NAME"
echo
echo -e "${GREEN}🔗 Image URL for Cloud Run:${NC}"
echo "$FULL_IMAGE_NAME" 
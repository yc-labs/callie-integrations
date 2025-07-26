#!/bin/bash

set -e

# Configuration
PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project)}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔐 Setting up secrets in Google Secret Manager${NC}"
echo "Project ID: $PROJECT_ID"
echo

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${RED}❌ .env file not found. Please create it first.${NC}"
    exit 1
fi

# Source the .env file to get the values
source .env

# Enable Secret Manager API
echo -e "${YELLOW}🔧 Enabling Secret Manager API...${NC}"
gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID

# Create or update SHIPSTATION_API_KEY secret
echo -e "${YELLOW}🔑 Creating/updating SHIPSTATION_API_KEY secret...${NC}"
if gcloud secrets describe shipstation-api-key --project=$PROJECT_ID >/dev/null 2>&1; then
    echo "Secret exists, creating new version..."
    echo -n "$SHIPSTATION_API_KEY" | gcloud secrets versions add shipstation-api-key \
        --data-file=- \
        --project=$PROJECT_ID
else
    echo "Creating new secret..."
    echo -n "$SHIPSTATION_API_KEY" | gcloud secrets create shipstation-api-key \
        --data-file=- \
        --project=$PROJECT_ID
fi

# Create or update SHIPSTATION_BASE_URL secret
echo -e "${YELLOW}🔗 Creating/updating SHIPSTATION_BASE_URL secret...${NC}"
if gcloud secrets describe shipstation-base-url --project=$PROJECT_ID >/dev/null 2>&1; then
    echo "Secret exists, creating new version..."
    echo -n "$SHIPSTATION_BASE_URL" | gcloud secrets versions add shipstation-base-url \
        --data-file=- \
        --project=$PROJECT_ID
else
    echo "Creating new secret..."
    echo -n "$SHIPSTATION_BASE_URL" | gcloud secrets create shipstation-base-url \
        --data-file=- \
        --project=$PROJECT_ID
fi

# Create or update INFIPLEX_API_KEY secret
echo -e "${YELLOW}🔑 Creating/updating INFIPLEX_API_KEY secret...${NC}"
if gcloud secrets describe infiplex-api-key --project=$PROJECT_ID >/dev/null 2>&1; then
    echo "Secret exists, creating new version..."
    echo -n "$INFIPLEX_API_KEY" | gcloud secrets versions add infiplex-api-key \
        --data-file=- \
        --project=$PROJECT_ID
else
    echo "Creating new secret..."
    echo -n "$INFIPLEX_API_KEY" | gcloud secrets create infiplex-api-key \
        --data-file=- \
        --project=$PROJECT_ID
fi

# Create or update INFIPLEX_BASE_URL secret
echo -e "${YELLOW}🔗 Creating/updating INFIPLEX_BASE_URL secret...${NC}"
if gcloud secrets describe infiplex-base-url --project=$PROJECT_ID >/dev/null 2>&1; then
    echo "Secret exists, creating new version..."
    echo -n "$INFIPLEX_BASE_URL" | gcloud secrets versions add infiplex-base-url \
        --data-file=- \
        --project=$PROJECT_ID
else
    echo "Creating new secret..."
    echo -n "$INFIPLEX_BASE_URL" | gcloud secrets create infiplex-base-url \
        --data-file=- \
        --project=$PROJECT_ID
fi

echo -e "${GREEN}✅ All secrets created successfully!${NC}"
echo
echo -e "${GREEN}📝 Created secrets:${NC}"
echo "  - shipstation-api-key"
echo "  - shipstation-base-url"
echo "  - infiplex-api-key"
echo "  - infiplex-base-url" 
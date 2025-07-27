#!/bin/bash
set -e

# Configuration
PROJECT_ID="yc-partners"
REGION="us-central1"
REPOSITORY="callie-integrations"
SERVICE_NAME="callie-api"

# Get version from version.py
VERSION=$(python3 -c "from src.callie.version import get_docker_tag; print(get_docker_tag())")
COMMIT_SHA=$(git rev-parse --short HEAD)

echo "🏗️  Building Callie API Docker image..."
echo "📦 Version: $VERSION"
echo "🔑 Commit: $COMMIT_SHA"

# Set up Artifact Registry repository URL
REPOSITORY_URL="$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY"

# Check if Artifact Registry repository exists, create if not
echo "🔍 Checking Artifact Registry repository..."
if ! gcloud artifacts repositories describe $REPOSITORY --location=$REGION --project=$PROJECT_ID &>/dev/null; then
    echo "📦 Creating Artifact Registry repository: $REPOSITORY"
    gcloud artifacts repositories create $REPOSITORY \
        --repository-format=docker \
        --location=$REGION \
        --project=$PROJECT_ID \
        --description="Callie Integrations Docker images"
fi

# Configure Docker to use gcloud as credential helper
echo "🔐 Configuring Docker authentication..."
gcloud auth configure-docker $REPOSITORY_URL --quiet

# Build and tag image
IMAGE_NAME="$REPOSITORY_URL/$SERVICE_NAME"
echo "🏗️  Building Docker image: $IMAGE_NAME:$VERSION"

gcloud builds submit \
    --config=cloudbuild.api.yaml \
    --substitutions=_IMAGE_NAME="$IMAGE_NAME",_VERSION="$VERSION",_COMMIT_SHA="$COMMIT_SHA" \
    --project=$PROJECT_ID \
    --region=$REGION

echo "✅ Successfully built and pushed: $IMAGE_NAME:$VERSION"
echo "🏷️  Also tagged as: $IMAGE_NAME:latest"
echo ""
echo "📋 Image details:"
echo "   Repository: $REPOSITORY_URL"
echo "   Image: $SERVICE_NAME"
echo "   Version: $VERSION"
echo "   Commit: $COMMIT_SHA" 
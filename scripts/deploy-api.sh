#!/bin/bash
set -e

# Configuration
PROJECT_ID="yc-partners"
REGION="us-central1"
SERVICE_NAME="callie-api"
REPOSITORY="callie-integrations"

# Get version
VERSION=$(python -c "from src.callie.version import get_docker_tag; print(get_docker_tag())")
IMAGE_URL="$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$SERVICE_NAME:$VERSION"

echo "🚀 Deploying Callie API to Cloud Run..."
echo "📦 Image: $IMAGE_URL"
echo "📍 Region: $REGION"

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable run.googleapis.com --project=$PROJECT_ID
gcloud services enable cloudbuild.googleapis.com --project=$PROJECT_ID
gcloud services enable firestore.googleapis.com --project=$PROJECT_ID
gcloud services enable cloudscheduler.googleapis.com --project=$PROJECT_ID

# Create service account if it doesn't exist
SERVICE_ACCOUNT="callie-api-sa@$PROJECT_ID.iam.gserviceaccount.com"
echo "👤 Setting up service account: $SERVICE_ACCOUNT"

if ! gcloud iam service-accounts describe $SERVICE_ACCOUNT --project=$PROJECT_ID &>/dev/null; then
    echo "📝 Creating service account..."
    gcloud iam service-accounts create callie-api-sa \
        --display-name="Callie API Service Account" \
        --description="Service account for Callie API" \
        --project=$PROJECT_ID
fi

# Grant necessary permissions
echo "🔐 Granting permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/datastore.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/cloudscheduler.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/secretmanager.secretAccessor"

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image=$IMAGE_URL \
    --platform=managed \
    --region=$REGION \
    --project=$PROJECT_ID \
    --service-account=$SERVICE_ACCOUNT \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GOOGLE_CLOUD_REGION=$REGION" \
    --set-secrets="SHIPSTATION_API_KEY=shipstation-api-key:latest,SHIPSTATION_BASE_URL=shipstation-base-url:latest,INFIPLEX_API_KEY=infiplex-api-key:latest,INFIPLEX_BASE_URL=infiplex-base-url:latest" \
    --allow-unauthenticated \
    --memory=512Mi \
    --cpu=1 \
    --concurrency=80 \
    --max-instances=10 \
    --timeout=300

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --project=$PROJECT_ID --format="value(status.url)")

echo "✅ Deployment successful!"
echo "🌐 Service URL: $SERVICE_URL"
echo "📊 Health check: $SERVICE_URL/health"
echo "📖 API docs: $SERVICE_URL/docs"

# Test the deployment
echo "🧪 Testing deployment..."
if curl -f -s "$SERVICE_URL/health" > /dev/null; then
    echo "✅ Health check passed!"
else
    echo "❌ Health check failed!"
    exit 1
fi

# Update environment variable for scheduler
echo "🔧 Setting SERVICE_URL environment variable..."
if ! gcloud secrets describe service-url --project=$PROJECT_ID &>/dev/null; then
    echo "$SERVICE_URL" | gcloud secrets create service-url --data-file=- --project=$PROJECT_ID
else
    echo "$SERVICE_URL" | gcloud secrets versions add service-url --data-file=- --project=$PROJECT_ID
fi

echo ""
echo "🎉 Callie API is now deployed and ready!"
echo "📋 Summary:"
echo "   Service: $SERVICE_NAME"
echo "   URL: $SERVICE_URL"
echo "   Region: $REGION"
echo "   Version: $VERSION"
echo ""
echo "🔗 Next steps:"
echo "   • Visit $SERVICE_URL/docs for API documentation"
echo "   • Create sync configurations via the API"
echo "   • Set up schedules using the /schedule endpoints" 
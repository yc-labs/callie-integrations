.PHONY: help install run-local test-local build-api push-api deploy-api create-workflow trigger-sync

# ====================================================================================
# HELP
# ====================================================================================

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  install          Install dependencies using Poetry"
	@echo "  run-local        Run the API locally using Docker Compose"
	@echo "  test-local       Test the API locally"
	@echo "  build-api        Build the API Docker image using Cloud Build"
	@echo "  push-api         Push the API Docker image to the Artifact Registry"
	@echo "  deploy-api       Deploy the API to Cloud Run"

# ====================================================================================
# DEVELOPMENT
# ====================================================================================

install:
	poetry install

run-local:
	docker-compose up --build

test-local:
	@echo "🧪 Testing local API health..."
	@curl -f -s http://localhost:8000/health
	@echo "\n✅ API is healthy."
	@echo "\n🚀 Triggering the final multi-warehouse sync workflow..."
	@curl -X POST http://localhost:8000/api/v1/workflows/shipstation-to-infiplex-multi-warehouse-fixed/execute-sync | jq
	@echo "\n✅ Workflow triggered."

# ====================================================================================
# DEPLOYMENT
# ====================================================================================

build-api:
	@echo "🏗️ Building API image with Cloud Build..."
	gcloud builds submit --config cloudbuild.api.yaml .

deploy-api: build-api
	@echo "🚀 Deploying API to Cloud Run..."
	@bash scripts/deploy-api.sh

# ====================================================================================
# WORKFLOW MANAGEMENT
# ====================================================================================

create-workflow:
	@echo "📝 Creating/updating the final multi-warehouse workflow in Firestore..."
	docker-compose exec callie-api python /app/scripts/create_multi_warehouse_sync_workflow.py

trigger-sync:
	@SERVICE_URL=$$(gcloud run services describe callie-api --region us-central1 --format="value(status.url)") && \
	echo "🚀 Triggering sync on Cloud Run: $$SERVICE_URL" && \
	curl -X POST $$SERVICE_URL/api/v1/workflows/shipstation-to-infiplex-multi-warehouse-fixed/execute-sync | jq 
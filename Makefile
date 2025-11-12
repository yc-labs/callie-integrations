.PHONY: help install run-local test-local build-api push-api deploy-api

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
	docker-compose up

test-local:
	@echo "Testing workflow creation..."
	@curl -X POST -H "Content-Type: application/json" -d @workflows/shipstation-to-infiplex-configurable.json http://localhost:8000/api/v1/workflows
	@echo "\n\nTesting workflow execution..."
	@curl -X POST http://localhost:8000/api/v1/workflows/shipstation-to-infiplex-configurable/execute

# ====================================================================================
# DEPLOYMENT
# ====================================================================================

build-api:
	gcloud builds submit --config cloudbuild.api.yaml .

push-api:
	@echo "This step is handled by the cloudbuild.api.yaml file."

deploy-api:
	gcloud run deploy callie-api \
		--image us-central1-docker.pkg.dev/$(gcloud config get-value project)/callie-api/callie-api:latest \
		--platform managed \
		--region us-central1 \
		--allow-unauthenticated 
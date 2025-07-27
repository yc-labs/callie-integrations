"""
Secret Manager service for retrieving API credentials and configuration.
"""

import logging
import os
from typing import Dict, Optional
from google.cloud import secretmanager

logger = logging.getLogger(__name__)


class SecretManagerService:
    """Service for retrieving secrets from Google Secret Manager."""
    
    def __init__(self, project_id: Optional[str] = None):
        """Initialize Secret Manager service."""
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable must be set")
        
        self.client = secretmanager.SecretManagerServiceClient()
        self._cache: Dict[str, str] = {}
    
    def get_secret(self, secret_name: str, version: str = "latest") -> str:
        """Retrieve a secret value from Secret Manager."""
        cache_key = f"{secret_name}:{version}"
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            secret_path = f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"
            response = self.client.access_secret_version(request={"name": secret_path})
            secret_value = response.payload.data.decode("UTF-8")
            
            # Cache the value
            self._cache[cache_key] = secret_value
            logger.info(f"Retrieved secret: {secret_name}")
            return secret_value
            
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {e}")
            raise
    
    def get_api_credentials(self) -> Dict[str, str]:
        """Get all API credentials needed for the application."""
        try:
            return {
                "SHIPSTATION_API_KEY": self.get_secret("shipstation-api-key"),
                "SHIPSTATION_BASE_URL": self.get_secret("shipstation-base-url"),
                "INFIPLEX_API_KEY": self.get_secret("infiplex-api-key"),
                "INFIPLEX_BASE_URL": self.get_secret("infiplex-base-url"),
                "API_BASE_URL": self.get_secret("service-url"),
            }
        except Exception as e:
            logger.warning(f"Failed to retrieve some API credentials: {e}")
            # Fall back to environment variables if secrets are not available
            return {
                "SHIPSTATION_API_KEY": os.getenv("SHIPSTATION_API_KEY", ""),
                "SHIPSTATION_BASE_URL": os.getenv("SHIPSTATION_BASE_URL", "https://api.shipstation.com"),
                "INFIPLEX_API_KEY": os.getenv("INFIPLEX_API_KEY", ""),
                "INFIPLEX_BASE_URL": os.getenv("INFIPLEX_BASE_URL", ""),
                "API_BASE_URL": os.getenv("API_BASE_URL", "http://localhost:8000"),
            } 
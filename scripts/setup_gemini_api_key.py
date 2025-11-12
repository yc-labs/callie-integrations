"""
Helper script to store Gemini API key in Google Secret Manager.
"""
import os
import sys
from google.cloud import secretmanager

def store_api_key(api_key: str, secret_name: str = "GEMINI_API_KEY"):
    """Store the Gemini API key in Google Secret Manager."""
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "yc-partners")
    
    # Create the Secret Manager client
    client = secretmanager.SecretManagerServiceClient()
    
    # Build the parent name
    parent = f"projects/{project_id}"
    
    # Create the secret
    try:
        secret = client.create_secret(
            request={
                "parent": parent,
                "secret_id": secret_name,
                "secret": {"replication": {"automatic": {}}},
            }
        )
        print(f"Created secret: {secret.name}")
    except Exception as e:
        if "already exists" in str(e):
            print(f"Secret {secret_name} already exists, will add new version")
            secret_path = f"{parent}/secrets/{secret_name}"
        else:
            raise e
    else:
        secret_path = secret.name
    
    # Add the secret version
    version = client.add_secret_version(
        request={
            "parent": secret_path,
            "payload": {"data": api_key.encode("UTF-8")},
        }
    )
    
    print(f"Added secret version: {version.name}")
    print(f"✅ API key stored successfully in Secret Manager as '{secret_name}'")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python setup_gemini_api_key.py YOUR_GEMINI_API_KEY")
        sys.exit(1)
    
    api_key = sys.argv[1]
    store_api_key(api_key)
"""
Creates the final, corrected ShipStation to InfiPlex inventory sync workflow.
This version correctly uses the credentials_key field to reference secrets
and ensures products are created in InfiPlex before inventory is updated.
"""
import os
import sys
from google.cloud import firestore

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.callie.models.stages import WorkflowConfig, StageConfig, StageType

def create_final_inventory_sync_workflow():
    """
    Creates and saves the final ShipStation to InfiPlex inventory sync workflow.
    """
    workflow_id = "shipstation-to-infiplex-inventory-sync-v4"
    
    stages = [
        StageConfig(
            id="read_shipstation_inventory",
            name="Read Inventory from ShipStation",
            type=StageType.CONNECTOR_METHOD,
            connector="source",
            method="read_inventory",
            parameters={},
            output_variable="shipstation_inventory",
            credentials_key="shipstation_creds"
        ),
        StageConfig(
            id="write_infiplex_inventory_wh17",
            name="Write Inventory to InfiPlex Warehouse 17",
            type=StageType.CONNECTOR_METHOD,
            connector="target",
            method="write_inventory",
            input_variables=["shipstation_inventory"],
            parameters={"warehouse_id": 17},
            credentials_key="infiplex_creds"
        ),
        StageConfig(
            id="write_infiplex_inventory_wh18",
            name="Write Inventory to InfiPlex Warehouse 18",
            type=StageType.CONNECTOR_METHOD,
            connector="target",
            method="write_inventory",
            input_variables=["shipstation_inventory"],
            parameters={"warehouse_id": 18},
            credentials_key="infiplex_creds"
        ),
    ]
    
    workflow_config = WorkflowConfig(
        id=workflow_id,
        name="ShipStation to InfiPlex Inventory Sync (v4)",
        description="Reads inventory from ShipStation and writes it to InfiPlex warehouses 17 and 18, creating products if they do not exist.",
        version="4.0",
        source={"service_type": "shipstation"},
        target={"service_type": "infiplex"},
        credentials_config={
            "shipstation_creds": {
                "api_key_secret": "shipstation-api-key",
                "base_url_secret": "shipstation-base-url"
            },
            "infiplex_creds": {
                "api_key_secret": "infiplex-api-key",
                "base_url_secret": "infiplex-base-url"
            }
        },
        stages=stages,
        schedule="*/15 * * * *",  # Every 15 minutes
        active=True
    )

    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "yc-partners")
        db = firestore.Client(project=project_id)
        
        doc_ref = db.collection("workflows").document(workflow_id)
        doc_ref.set(workflow_config.model_dump())
        
        print(f"✅ Successfully created/updated workflow: {workflow_id}")

    except Exception as e:
        print(f"❌ Error saving workflow to Firestore: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_final_inventory_sync_workflow()
#!/usr/bin/env python3

import os
import sys
sys.path.append('/app/src')

from callie.services.firestore import FirestoreService
from callie.models.stages import WorkflowConfig, StageConfig

def main():
    """Create corrected multi-warehouse ShipStation to InfiPlex workflow with product creation."""
    
    # Get project ID from environment
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "yc-partners")
    
    # Initialize Firestore service  
    fs = FirestoreService(project_id)
    
    # Create corrected workflow configuration
    workflow_config = WorkflowConfig(
        id="shipstation-to-infiplex-multi-warehouse-fixed",
        name="Fixed Multi-Warehouse ShipStation to InfiPlex Sync with Product Creation",
        description="Corrected workflow that syncs ALL ShipStation inventory to multiple InfiPlex warehouses (17 and 18) and creates missing products",
        version="2.1",
        # FIX: Remove base_url and credentials from source config to avoid conflict
        source={
            "service_type": "shipstation"
        },
        target={
            "service_type": "infiplex", 
            "warehouse_id": 17
        },
        credentials_config={
            "shipstation_creds": {
                "api_key_secret": "shipstation-api-key",
                "base_url_secret": "shipstation-base-url"
            },
            "infiplex_warehouse_17": {
                "warehouse_id": 17,
                "api_key_secret": "infiplex-api-key",
                "base_url_secret": "infiplex-base-url"
            },
            "infiplex_warehouse_18": {
                "warehouse_id": 18,
                "api_key_secret": "infiplex-warehouse-18-api-key", 
                "base_url_secret": "infiplex-base-url"
            }
        },
        stages=[
            # 1. Start logging
            StageConfig(
                id="log-start",
                name="Log Multi-Warehouse Sync Start",
                type="log",
                parameters={
                    "message": "Starting corrected multi-warehouse sync with product creation for warehouses 17 & 18",
                    "level": "info"
                }
            ),
            
            # 2. Read ALL ShipStation inventory
            StageConfig(
                id="read-shipstation-inventory",
                name="Read ShipStation Inventory",
                description="Get all inventory from ShipStation",
                type="connector_method",
                connector="source",
                method="_read_inventory",
                credentials_key="shipstation_creds",
                output_variable="shipstation_inventory"
            ),
            
            # 3. Log ShipStation count
            StageConfig(
                id="log-shipstation-count",
                name="Log ShipStation Count",
                type="log", 
                parameters={
                    "message": "Found {len(shipstation_inventory)} items in ShipStation",
                    "level": "info"
                },
                depends_on=["read-shipstation-inventory"]
            ),
            
            # 4. Read existing InfiPlex inventory (warehouse 17 for reference)
            StageConfig(
                id="read-infiplex-inventory-wh17",
                name="Read InfiPlex Inventory (Warehouse 17)", 
                description="Get existing inventory from InfiPlex warehouse 17",
                type="connector_method",
                connector="target",
                method="_read_inventory",
                credentials_key="infiplex_warehouse_17", 
                parameters={"warehouse_id": 17},
                output_variable="infiplex_inventory_wh17"
            ),
            
            # 5. Extract existing SKUs
            StageConfig(
                id="extract-existing-skus",
                name="Extract Existing InfiPlex SKUs",
                type="transform",
                parameters={
                    "field": "sku", 
                    "transform_type": "extract_field"
                },
                input_variables=["infiplex_inventory_wh17"],
                output_variable="existing_infiplex_skus",
                depends_on=["read-infiplex-inventory-wh17"]
            ),
            
            # 6. Find NEW products to create by filtering out existing ones
            StageConfig(
                id="find-new-products",
                name="Find New Products to Create",
                type="filter",
                parameters={
                    "filter_type": "exclude", # Exclude items that are in the second list
                    "field": "sku",           # Field to match on in the first list (shipstation_inventory)
                    "values_variable": "existing_infiplex_skus" # Variable containing the list of values to exclude
                },
                input_variables=["shipstation_inventory", "existing_infiplex_skus"],
                output_variable="new_products_to_create", 
                depends_on=["read-shipstation-inventory", "extract-existing-skus"]
            ),
            
            # 7. Log new products
            StageConfig(
                id="log-new-products",
                name="Log New Products to Create",
                type="log",
                parameters={
                    "message": "Found {len(new_products_to_create)} NEW products to create in InfiPlex",
                    "level": "info"
                },
                depends_on=["find-new-products"]
            ),
            
            # 8. Create missing products
            StageConfig(
                id="create-missing-products",
                name="Create Missing Products in InfiPlex",
                description="Create new products that don't exist in InfiPlex",
                type="connector_method",
                connector="target", 
                method="_create_products",
                credentials_key="infiplex_warehouse_17",
                input_variables=["new_products_to_create"],
                output_variable="product_creation_results",
                depends_on=["find-new-products"],
                error_strategy="continue"
            ),
            
            # 9. Map inventory fields
            StageConfig(
                id="map-inventory-fields",
                name="Map Inventory Fields",
                type="map_fields",
                parameters={
                    "mappings": {
                        "sku": "sku",
                        "available": "quantity_to_set"
                    }
                },
                input_variables=["shipstation_inventory"],
                output_variable="mapped_inventory",
                depends_on=["create-missing-products"]
            ),
            
            # 10. Prepare for warehouse 17
            StageConfig(
                id="add-warehouse-17-id",
                name="Add Warehouse 17 ID",
                type="transform",
                parameters={
                    "field": "warehouse_id",
                    "value": 17,
                    "transform_type": "add_field"
                },
                input_variables=["mapped_inventory"],
                output_variable="inventory_wh17",
                depends_on=["map-inventory-fields"]
            ),
            
            # 11. Prepare for warehouse 18
            StageConfig(
                id="add-warehouse-18-id", 
                name="Add Warehouse 18 ID",
                type="transform",
                parameters={
                    "field": "warehouse_id",
                    "value": 18,
                    "transform_type": "add_field"
                },
                input_variables=["mapped_inventory"],
                output_variable="inventory_wh18",
                depends_on=["map-inventory-fields"]
            ),
            
            # 12. Update warehouse 17
            StageConfig(
                id="write-inventory-wh17",
                name="Write Inventory to Warehouse 17",
                description="Update inventory in InfiPlex warehouse 17",
                type="connector_method",
                connector="target",
                method="_write_inventory", 
                credentials_key="infiplex_warehouse_17",
                input_variables=["inventory_wh17"],
                output_variable="result_wh17",
                depends_on=["add-warehouse-17-id"]
            ),
            
            # 13. Update warehouse 18
            StageConfig(
                id="write-inventory-wh18",
                name="Write Inventory to Warehouse 18",
                description="Update inventory in InfiPlex warehouse 18", 
                type="connector_method",
                connector="target",
                method="_write_inventory",
                credentials_key="infiplex_warehouse_18",
                input_variables=["inventory_wh18"],
                output_variable="result_wh18",
                depends_on=["add-warehouse-18-id"]
            ),
            
            # 14. Final summary
            StageConfig(
                id="log-completion",
                name="Log Multi-Warehouse Sync Completion",
                type="log",
                parameters={
                    "message": "Multi-warehouse sync completed! Products created: {product_creation_results}, WH17: {result_wh17}, WH18: {result_wh18}",
                    "level": "info"
                },
                depends_on=["write-inventory-wh17", "write-inventory-wh18"]
            )
        ],
        variables={
            "sync_type": "multi_warehouse_with_product_creation",
            "target_warehouses": [17, 18]
        },
        timeout_seconds=3600,  # 1 hour
        schedule="0 */6 * * *",  # Every 6 hours
        active=True
    )
    
    # Create workflow in Firestore
    result = fs.create_workflow(workflow_config, merge=True)
    print(f"Corrected multi-warehouse workflow created: {result}")
    print(f"Workflow ID: {workflow_config.id}")
    print(f"")
    print(f"✅ FIXES APPLIED:")
    print(f"  • Removed base_url from source config (fixes connector conflict)")
    print(f"  • Added product creation for missing SKUs")  
    print(f"  • Updates both warehouses 17 and 18")
    print(f"  • Handles all ShipStation inventory (with deduplication)")

if __name__ == "__main__":
    main()
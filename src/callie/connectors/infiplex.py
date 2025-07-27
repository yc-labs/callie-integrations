"""
InfiPlex connector for reading and writing inventory data.
"""

import requests
import logging
from typing import Dict, List, Any, Optional
from ..exceptions import InfiPlexAPIError
from .base import BaseConnector, ConnectorCapability, ConnectorSchema, ConnectorField

logger = logging.getLogger(__name__)


class InfiPlexConnector(BaseConnector):
    """
    InfiPlex API connector for reading and writing inventory data.
    
    Supports both reading and writing inventory levels to InfiPlex system.
    """
    
    def _validate_credentials(self) -> None:
        """Validate that API key is provided."""
        if "api_key" not in self.credentials:
            raise ValueError("InfiPlex connector requires 'api_key' in credentials")
    
    def get_capabilities(self) -> ConnectorCapability:
        """InfiPlex can read and write inventory."""
        return ConnectorCapability(
            can_read_inventory=True,
            can_write_inventory=True,
            can_read_products=True,
            can_write_products=True
        )
    
    def get_inventory_schema(self) -> ConnectorSchema:
        """Return InfiPlex inventory schema."""
        return ConnectorSchema(fields=[
            ConnectorField(
                name="sku",
                description="Stock Keeping Unit identifier", 
                data_type="string",
                required=True,
                example="ABC-123"
            ),
            ConnectorField(
                name="quantity_to_set",
                description="Quantity to set for this SKU",
                data_type="integer",
                required=True,
                example=50
            ),
            ConnectorField(
                name="warehouse_id",
                description="Warehouse ID to update inventory for",
                data_type="integer",
                required=True,
                example=17
            ),
            ConnectorField(
                name="quantity",
                description="Current quantity in warehouse (read-only)",
                data_type="string",
                required=False,
                example="50"
            ),
            ConnectorField(
                name="product_name",
                description="Product name (read-only)",
                data_type="string",
                required=False,
                example="Sample Product"
            ),
            ConnectorField(
                name="warehouse_name",
                description="Warehouse name (read-only)",
                data_type="string",
                required=False,
                example="Main Warehouse"
            )
        ])
    
    def test_connection(self) -> bool:
        """Test connection to InfiPlex API."""
        try:
            # Try to search for inventory with limit 1
            response = requests.get(
                f"{self.base_url}/api/admin/shop/inventory/search",
                headers={"Authorization": f"Bearer {self.credentials['api_key']}"},
                params={"limit": 1},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"InfiPlex connection test failed: {e}")
            return False
    
    def _read_inventory(self, **filters) -> List[Dict[str, Any]]:
        """
        Read inventory from InfiPlex.
        
        Supported filters:
        - warehouse_id: Filter by specific warehouse
        - search_term: Search for specific SKUs
        - limit: Number of items to fetch
        - is_active: Filter active/inactive items
        """
        try:
            params = {}
            
            if "warehouse_id" in filters:
                params["warehouse_id"] = filters["warehouse_id"]
            if "search_term" in filters:
                params["search_term"] = filters["search_term"]
            if "limit" in filters:
                params["limit"] = filters["limit"]
            if "is_active" in filters:
                params["is_active"] = filters["is_active"]
            
            logger.info(f"Fetching InfiPlex inventory with params: {params}")
            
            response = requests.get(
                f"{self.base_url}/api/admin/shop/inventory/search",
                headers={"Authorization": f"Bearer {self.credentials['api_key']}"},
                params=params,
                timeout=30
            )
            
            if response.status_code != 200:
                raise InfiPlexAPIError(f"HTTP {response.status_code}: {response.text}")
            
            data = response.json()
            inventory_items = data.get("inventory", [])
            
            # Convert to standard format
            result = []
            for item in inventory_items:
                result.append({
                    "sku": item.get("base_sku") or item.get("item_sku"),
                    "quantity": item.get("quantity"),
                    "product_name": item.get("product_name"),
                    "warehouse_id": item.get("shop_warehouseid"),
                    "warehouse_name": item.get("warehouse_name")
                })
            
            logger.info(f"Successfully fetched {len(result)} inventory items from InfiPlex")
            return result
            
        except requests.exceptions.RequestException as e:
            raise InfiPlexAPIError(f"Request failed: {e}")
        except Exception as e:
            raise InfiPlexAPIError(f"Unexpected error: {e}")
    
    def _write_inventory(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Write inventory to InfiPlex.
        
        Args:
            items: List of inventory items with sku, quantity_to_set, warehouse_id
            
        Returns:
            Dictionary with sync results
        """
        if not items:
            return {"success": 0, "failed": 0, "total": 0}
        
        # Get default warehouse_id from config if not specified
        default_warehouse_id = self.config.get("warehouse_id")
        
        try:
            # Use bulk update if multiple items
            if len(items) > 1:
                return self._bulk_update_inventory(items, default_warehouse_id)
            else:
                return self._single_update_inventory(items[0], default_warehouse_id)
                
        except Exception as e:
            logger.error(f"Failed to write inventory to InfiPlex: {e}")
            raise InfiPlexAPIError(f"Write inventory failed: {e}")
    
    def _single_update_inventory(self, item: Dict[str, Any], default_warehouse_id: Optional[int]) -> Dict[str, Any]:
        """Update a single inventory item."""
        sku = item.get("sku")
        quantity = item.get("quantity_to_set")
        warehouse_id = item.get("warehouse_id", default_warehouse_id)
        
        if not sku:
            raise InfiPlexAPIError("SKU is required for inventory update")
        if quantity is None:
            raise InfiPlexAPIError("quantity_to_set is required for inventory update")
        if not warehouse_id:
            raise InfiPlexAPIError("warehouse_id is required for inventory update")
        
        try:
            payload = {
                "quantity_to_set": quantity,
                "warehouse_id": warehouse_id
            }
            
            response = requests.put(
                f"{self.base_url}/api/admin/shop/inventory/{sku}",
                headers={
                    "Authorization": f"Bearer {self.credentials['api_key']}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully updated inventory for SKU {sku} to quantity {quantity}")
                return {"success": 1, "failed": 0, "total": 1}
            else:
                logger.error(f"Failed to update SKU {sku}: HTTP {response.status_code} - {response.text}")
                return {"success": 0, "failed": 1, "total": 1}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for SKU {sku}: {e}")
            return {"success": 0, "failed": 1, "total": 1}
    
    def _bulk_update_inventory(self, items: List[Dict[str, Any]], default_warehouse_id: Optional[int]) -> Dict[str, Any]:
        """Update multiple inventory items using bulk endpoint."""
        
        # Prepare bulk payload
        bulk_items = []
        for item in items:
            sku = item.get("sku")
            quantity = item.get("quantity_to_set")
            warehouse_id = item.get("warehouse_id", default_warehouse_id)
            
            if not sku or quantity is None or not warehouse_id:
                logger.warning(f"Skipping invalid item: {item}")
                continue
                
            bulk_items.append({
                "sku": sku,
                "warehouse_id": warehouse_id,
                "quantity_to_set": quantity
            })
        
        if not bulk_items:
            return {"success": 0, "failed": len(items), "total": len(items)}
        
        try:
            payload = {"inventory_items": bulk_items} # Wrap the list in a dictionary
            response = requests.post(
                f"{self.base_url}/api/admin/shop/inventory/bulk_update",
                headers={
                    "Authorization": f"Bearer {self.credentials['api_key']}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                results = response.json()
                success_count = len([r for r in results if r.get("warehouse_inventory") is not None])
                failed_count = len(bulk_items) - success_count
                
                logger.info(f"Bulk update completed: {success_count} success, {failed_count} failed")
                return {
                    "success": success_count,
                    "failed": failed_count,
                    "total": len(bulk_items),
                    "details": results
                }
            else:
                logger.error(f"Bulk update failed: HTTP {response.status_code} - {response.text}")
                return {"success": 0, "failed": len(bulk_items), "total": len(bulk_items)}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Bulk update request failed: {e}")
            return {"success": 0, "failed": len(bulk_items), "total": len(bulk_items)}


def create_infiplex_connector(api_key: str, base_url: str, warehouse_id: Optional[int] = None) -> InfiPlexConnector:
    """
    Create an InfiPlex connector instance.
    
    Args:
        api_key: InfiPlex API key (Bearer token)
        base_url: InfiPlex API base URL
        warehouse_id: Default warehouse ID for operations
        
    Returns:
        Configured InfiPlex connector
    """
    return InfiPlexConnector(
        credentials={"api_key": api_key},
        base_url=base_url,
        warehouse_id=warehouse_id
    ) 
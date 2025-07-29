"""
InfiPlex connector for reading and writing inventory data.
"""

import requests
import logging
import urllib.parse
from typing import Dict, List, Any, Optional
from ..exceptions import InfiPlexAPIError
from .base import BaseConnector, ConnectorCapability, ConnectorSchema, ConnectorField

logger = logging.getLogger(__name__)


class InfiPlexConnector(BaseConnector):
    """
    InfiPlex API connector for inventory and product management.
    """
    
    # No _validate_credentials needed here anymore
    
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
    
    def _read_inventory(self, api_key: str, base_url: str, **filters) -> List[Dict[str, Any]]:
        """
        Read inventory from InfiPlex with automatic pagination to fetch ALL items.
        
        Supported filters:
        - warehouse_id: Filter by specific warehouse
        - search_term: Search for specific SKUs
        - limit: Number of items to fetch per page (default 100, max 100)
        - max_items: Maximum total items to fetch across all pages (optional, fetches ALL items if not specified)
        - is_active: Filter active/inactive items
        """
        try:
            all_items = []
            page_size = min(filters.get("limit", 100), 100)  # Max 100 per API call
            max_items = filters.get("max_items")  # No default limit - fetch ALL items unless specified
            limit_start = 0
            
            while True:
                # Stop if we've reached the max_items limit (if specified)
                if max_items is not None and len(all_items) >= max_items:
                    break
                
                params = {
                    "limit": page_size,
                    "limit_start": limit_start
                }
                
                # Add other filters
                if "warehouse_id" in filters:
                    params["warehouse_id"] = filters["warehouse_id"]
                if "search_term" in filters:
                    params["search_term"] = filters["search_term"]
                if "is_active" in filters:
                    params["is_active"] = filters["is_active"]
                
                logger.info(f"Fetching InfiPlex inventory page: limit={page_size}, limit_start={limit_start}, max_items={max_items}")
                
                response = requests.get(
                    f"{base_url}/api/admin/shop/inventory/search",
                    headers={"Authorization": f"Bearer {api_key}"},
                    params=params,
                    timeout=30
                )
                
                if response.status_code != 200:
                    raise InfiPlexAPIError(f"HTTP {response.status_code}: {response.text}")
                
                data = response.json()
                inventory_items = data.get("inventory", [])
                
                if not inventory_items:
                    # No more items, we've reached the end
                    break
                    
                # Convert to standard format and add to results
                for item in inventory_items:
                    if max_items is not None and len(all_items) >= max_items:
                        break
                    all_items.append({
                        "sku": item.get("base_sku") or item.get("item_sku"),
                        "quantity": item.get("quantity"),
                        "product_name": item.get("product_name"),
                        "warehouse_id": item.get("shop_warehouseid"),
                        "warehouse_name": item.get("warehouse_name")
                    })
                
                logger.info(f"Fetched {len(inventory_items)} items from page (total so far: {len(all_items)})")
                
                # If we got fewer items than requested, we've reached the end
                if len(inventory_items) < page_size:
                    break
                    
                # Move to next page
                limit_start += page_size
            
            pages_fetched = (limit_start // page_size) + 1
            if max_items is not None and len(all_items) >= max_items:
                logger.warning(f"Reached max_items limit of {max_items}. There may be more inventory items available.")
            
            logger.info(f"Successfully fetched {len(all_items)} total inventory items from InfiPlex across {pages_fetched} pages")
            return all_items
            
        except requests.exceptions.RequestException as e:
            raise InfiPlexAPIError(f"Request failed: {e}")
        except Exception as e:
            raise InfiPlexAPIError(f"Unexpected error: {e}")
    
    def _write_inventory(self, items: List[Dict[str, Any]] = None, api_key: str = None, base_url: str = None, **kwargs) -> Dict[str, Any]:
        """
        Write inventory to InfiPlex.
        """
        if items is None:
            for key, value in kwargs.items():
                if ('inventory' in key or 'payload' in key) and isinstance(value, list):
                    items = value
                    break
        
        if not items:
            return {"success": 0, "failed": 0, "total": 0}

        default_warehouse_id = self.config.get("warehouse_id")

        try:
            filtered_items = self._filter_existing_skus(items, default_warehouse_id, api_key, base_url)
            
            if not filtered_items:
                return {"success": 0, "failed": len(items), "total": len(items)}

            if len(filtered_items) > 1:
                return self._bulk_update_inventory(filtered_items, default_warehouse_id, api_key, base_url)
            else:
                return self._single_update_inventory(filtered_items[0], default_warehouse_id, api_key, base_url)
                
        except Exception as e:
            logger.error(f"An unexpected error occurred in _write_inventory: {e}", exc_info=True)
            return {"success": 0, "failed": len(items), "total": len(items), "error": str(e)}
    
    def _filter_existing_skus(self, items: List[Dict[str, Any]], default_warehouse_id: Optional[int], api_key: str, base_url: str) -> List[Dict[str, Any]]:
        """
        Filter items to only include SKUs that exist in InfiPlex.
        
        Args:
            items: List of inventory items to filter
            default_warehouse_id: Default warehouse ID to use
            
        Returns:
            List of items with SKUs that exist in InfiPlex
        """
        if not items:
            return []
        
        # Get the warehouse_id to filter by
        warehouse_id = items[0].get("warehouse_id", default_warehouse_id)
        
        try:
            # Use the passed-in warehouse_id for the check, not a hardcoded one.
            warehouse_id_to_check = default_warehouse_id
            existing_inventory = self._read_inventory(api_key=api_key, base_url=base_url, warehouse_id=warehouse_id_to_check)
            existing_skus = set(item.get("sku") for item in existing_inventory if item.get("sku"))
            
            filtered_items = [item for item in items if item.get("sku") in existing_skus]
            
            return filtered_items
            
        except Exception as e:
            logger.error(f"Error filtering existing SKUs in InfiPlex: {e}")
            # In case of failure, return the original list to attempt all updates
            return items
    
    def _single_update_inventory(self, item: Dict[str, Any], default_warehouse_id: Optional[int], api_key: str, base_url: str) -> Dict[str, Any]:
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
                f"{base_url}/api/admin/shop/inventory/{sku}",
                headers={
                    "Authorization": f"Bearer {api_key}",
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
    
    def _bulk_update_inventory(self, items: List[Dict[str, Any]], default_warehouse_id: Optional[int], api_key: str, base_url: str) -> Dict[str, Any]:
        """Update multiple inventory items using bulk endpoint."""
        
        # Prepare bulk payload
        bulk_items = []
        skipped_items = []
        
        for item in items:
            sku = item.get("sku")
            quantity = item.get("quantity_to_set")
            warehouse_id = item.get("warehouse_id", default_warehouse_id)
            
            # Use default warehouse "17" if no warehouse_id is specified
            if not warehouse_id:
                warehouse_id = "17"  # Default to main warehouse
            
            if not sku or quantity is None:
                skipped_items.append(item)
                continue
            
            # Clean and encode SKU to handle special characters
            clean_sku = str(sku).strip()
            
            bulk_items.append({
                "sku": clean_sku,
                "warehouse_id": str(warehouse_id),  # Convert to string to match InfiPlex format
                "quantity_to_set": int(quantity)    # Ensure it's an integer
            })
        
        if not bulk_items:
            return {"success": 0, "failed": len(items), "total": len(items)}
        
        try:
            # InfiPlex expects an array directly, NOT wrapped in an object
            payload = bulk_items  # Send array directly
            
            response = requests.post(
                f"{base_url}/api/admin/shop/inventory/bulk_update",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                results = response.json()
                
                # Enhanced result analysis
                successful_results = [r for r in results if r.get("warehouse_inventory") is not None]
                failed_results = [r for r in results if r.get("warehouse_inventory") is None]
                
                success_count = len(successful_results)
                failed_count = len(failed_results)
                
                return {
                    "success": success_count,
                    "failed": failed_count,
                    "total": len(bulk_items),
                    "items": successful_results,  # Add items field for workflow engine
                    "results": results[:10]  # Sample results for debugging
                }
            else:
                logger.error(f"Bulk update failed: HTTP {response.status_code} - {response.text}")
                raise InfiPlexAPIError(f"Bulk update failed: HTTP {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Bulk update request failed: {e}")
            return {"success": 0, "failed": len(bulk_items), "total": len(bulk_items)}

    def _create_products(self, items: List[Dict[str, Any]] = None, api_key: str = None, base_url: str = None, **kwargs) -> Dict[str, Any]:
        """
        Create products in InfiPlex using the Products Create API.
        
        Args:
            items: List of product items with sku, title/product_name, etc.
            api_key: InfiPlex API key
            base_url: InfiPlex base URL
            
        Returns:
            Dictionary with creation results
        """
        
        # Handle case where items are passed via kwargs (from workflow engine input_variables)
        if items is None:
            for key, value in kwargs.items():
                if (key == 'new_products_to_create' or key.startswith('items') or 'product' in key.lower() or 'inventory' in key.lower()) and isinstance(value, list):
                    items = value
                    break
        
        if not items:
            return {"success": 0, "failed": 0, "total": 0, "items": []}
        
        # Prepare products for creation
        products_to_create = []
        for item in items:
            sku = item.get("sku")
            if not sku:
                continue
                
            # Create product payload matching InfiPlex Products Create API
            product = {
                "sku": sku,
                "title": item.get("product_name") or item.get("title") or sku,  # Use product name or fallback to SKU
                "price": float(item.get("price", 0.0)),  # Default price to 0 if not provided
                "ship_weight_oz": float(item.get("weight_oz", 1.0)),  # Default weight
                "ship_length_inches": float(item.get("length_inches", 1.0)),
                "ship_width_inches": float(item.get("width_inches", 1.0)), 
                "ship_height_inches": float(item.get("height_inches", 1.0)),
                "upc": item.get("upc", ""),
                "description": item.get("description", ""),
                "image_url": item.get("image_url", "")
            }
            products_to_create.append(product)
        
        if not products_to_create:
            return {"success": 0, "failed": 0, "total": 0, "items": []}
        
        try:
            # Make API call to create products
            
            response = requests.post(
                f"{base_url}/api/admin/shop/products/",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json=products_to_create,
                timeout=60
            )
            
            if response.status_code == 200:
                result_data = response.json()
                
                success_count = len([r for r in result_data if "Product Created" in r.get("message", "")])
                failed_count = len(result_data) - success_count
                
                return {
                    "success": success_count,
                    "failed": failed_count,
                    "total": len(result_data),
                    "items": result_data,
                    "results": result_data[:10]  # Sample results for debugging
                }
            else:
                logger.error(f"Products Create API failed: {response.status_code} - {response.text}")
                return {"success": 0, "failed": len(products_to_create), "total": len(products_to_create), "items": []}
                
        except Exception as e:
            logger.error(f"Exception in _create_products: {str(e)}")
            return {"success": 0, "failed": len(products_to_create), "total": len(products_to_create), "items": []}


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
"""
ShipStation connector for reading inventory data.
"""

import requests
import logging
from typing import Dict, List, Any, Optional
from ..exceptions import ShipStationAPIError
from .base import BaseConnector, ConnectorCapability, ConnectorSchema, ConnectorField

logger = logging.getLogger(__name__)


class ShipStationConnector(BaseConnector):
    """
    ShipStation API connector for reading inventory data.
    
    Supports reading inventory levels and product information from ShipStation V2 API.
    """
    
    def _validate_credentials(self) -> None:
        """Validate that API key is provided."""
        if "api_key" not in self.credentials:
            raise ValueError("ShipStation connector requires 'api_key' in credentials")
    
    def get_capabilities(self) -> ConnectorCapability:
        """ShipStation can read inventory but not write."""
        return ConnectorCapability(
            can_read_inventory=True,
            can_write_inventory=False,
            can_read_products=True,
            can_write_products=False
        )
    
    def get_inventory_schema(self) -> ConnectorSchema:
        """Return ShipStation inventory schema."""
        return ConnectorSchema(fields=[
            ConnectorField(
                name="sku",
                description="Stock Keeping Unit identifier",
                data_type="string",
                required=True,
                example="ABC-123"
            ),
            ConnectorField(
                name="on_hand",
                description="Total quantity on hand",
                data_type="integer",
                required=True,
                example=100
            ),
            ConnectorField(
                name="allocated",
                description="Quantity allocated to orders",
                data_type="integer",
                required=False,
                example=5
            ),
            ConnectorField(
                name="available",
                description="Available quantity (on_hand - allocated)",
                data_type="integer", 
                required=True,
                example=95
            ),
            ConnectorField(
                name="average_cost",
                description="Average cost per unit",
                data_type="object",
                required=False,
                example={"amount": 10.50, "currency": "USD"}
            ),
            ConnectorField(
                name="inventory_warehouse_id",
                description="Warehouse ID where inventory is located",
                data_type="string",
                required=False,
                example="warehouse-123"
            ),
            ConnectorField(
                name="inventory_location_id", 
                description="Location ID within warehouse",
                data_type="string",
                required=False,
                example="location-456"
            )
        ])
    
    def test_connection(self) -> bool:
        """Test connection to ShipStation API."""
        try:
            response = requests.get(
                f"{self.base_url}/v2/inventory",
                headers={"API-Key": self.credentials["api_key"]},
                params={"limit": 1},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"ShipStation connection test failed: {e}")
            return False
    
    def _read_inventory(self, **filters) -> List[Dict[str, Any]]:
        """
        Read inventory from ShipStation.
        
        Supported filters:
        - limit: Number of items to fetch
        - sku: Specific SKU to filter
        - sku_list: List of specific SKUs to fetch
        - inventory_warehouse_id: Filter by warehouse
        - inventory_location_id: Filter by location
        - group_by: Group results by 'warehouse' or 'location'
        """
        # DEBUG: Log all parameters received
        logger.info(f"ShipStation _read_inventory called with filters: {list(filters.keys())}")
        for key, value in filters.items():
            if key == "sku_list" and isinstance(value, list):
                logger.info(f"sku_list parameter received with {len(value)} SKUs: {value[:5]}...")
            else:
                logger.info(f"Parameter {key}: {type(value).__name__} = {str(value)[:100]}...")
        
        # Handle specific SKU list for targeted sync
        limit = filters.get("limit")
        if "sku_list" in filters:
            sku_list = filters["sku_list"]
            if limit:
                sku_list = sku_list[:limit] # Respect the limit
            logger.info(f"Fetching ShipStation inventory for {len(sku_list)} specific SKUs")
            return self._read_inventory_for_sku_list(sku_list)

        # Original pagination logic for general inventory fetch
        all_items = []
        page = 1
        
        # Build query parameters
        # Note: ShipStation appears to have a fixed page size of ~50 items regardless of limit
        params = {"limit": 500}  # ShipStation max per page is 500
        if limit:
            # If a specific limit is requested, respect it
            params["limit"] = min(limit, 500)
        if "sku" in filters:
            params["sku"] = filters["sku"]
        if "inventory_warehouse_id" in filters:
            params["inventory_warehouse_id"] = filters["inventory_warehouse_id"]
        if "inventory_location_id" in filters:
            params["inventory_location_id"] = filters["inventory_location_id"]
        if "group_by" in filters:
            params["group_by"] = filters["group_by"]
        
        try:
            total_pages = None
            while True:
                params["page"] = page
                
                logger.info(f"Fetching ShipStation inventory page {page} with params: {params}")
                
                response = requests.get(
                    f"{self.base_url}/v2/inventory",
                    headers={"API-Key": self.credentials["api_key"]},
                    params=params,
                    timeout=30
                )
                
                if response.status_code != 200:
                    raise ShipStationAPIError(f"HTTP {response.status_code}: {response.text}")
                
                data = response.json()
                inventory_items = data.get("inventory", [])
                
                # Get total pages from first response
                if total_pages is None:
                    total_pages = data.get("pages", 1)
                    total_items = data.get("total", 0)
                    logger.info(f"ShipStation API reports {total_items} total items across {total_pages} pages")
                
                if not inventory_items:
                    logger.info(f"No inventory items returned on page {page}, stopping")
                    break
                
                # Convert to standard format
                for item in inventory_items:
                    all_items.append({
                        "sku": item.get("sku"),
                        "on_hand": item.get("on_hand", 0),
                        "allocated": item.get("allocated", 0),
                        "available": item.get("available", 0),
                        "average_cost": item.get("average_cost"),
                        "inventory_warehouse_id": item.get("inventory_warehouse_id"),
                        "inventory_location_id": item.get("inventory_location_id")
                    })
                
                logger.info(f"Fetched {len(inventory_items)} items from page {page}, total so far: {len(all_items)}")
                
                # Check if we've fetched enough items (respect user's limit)
                if limit and len(all_items) >= limit:
                    logger.info(f"Reached requested limit of {limit} items")
                    break
                    
                # Check if we've reached the last page
                if page >= total_pages:
                    logger.info(f"Reached last page {total_pages}")
                    break
                    
                page += 1
            
            final_items = all_items[:limit] if limit else all_items  # Ensure we don't exceed requested limit
            logger.info(f"Successfully fetched {len(final_items)} inventory items from ShipStation (out of {len(all_items)} total fetched)")
            return final_items
            
        except requests.exceptions.RequestException as e:
            raise ShipStationAPIError(f"Request failed: {e}")
        except Exception as e:
            raise ShipStationAPIError(f"Unexpected error: {e}")

    def _read_inventory_for_sku_list(self, sku_list: List[str]) -> List[Dict[str, Any]]:
        """Fetch inventory for a specific list of SKUs."""
        all_items = []
        for sku in sku_list:
            try:
                params = {"sku": sku}
                response = requests.get(
                    f"{self.base_url}/v2/inventory",
                    headers={"API-Key": self.credentials["api_key"]},
                    params=params,
                    timeout=15
                )
                if response.status_code == 200:
                    data = response.json()
                    inventory_items = data.get("inventory", [])
                    if inventory_items:
                        item = inventory_items[0] # Should only be one
                        all_items.append({
                            "sku": item.get("sku"),
                            "on_hand": item.get("on_hand", 0),
                            "allocated": item.get("allocated", 0),
                            "available": item.get("available", 0),
                            "average_cost": item.get("average_cost"),
                            "inventory_warehouse_id": item.get("inventory_warehouse_id"),
                            "inventory_location_id": item.get("inventory_location_id")
                        })
                    else:
                        # No inventory record found, check if SKU exists as a product
                        logger.info(f"No inventory record for SKU {sku}, checking if it exists as a product...")
                        product_response = requests.get(
                            f"{self.base_url}/v2/products",
                            headers={"API-Key": self.credentials["api_key"]},
                            params={"sku": sku},
                            timeout=15
                        )
                        if product_response.status_code == 200:
                            product_data = product_response.json()
                            products = product_data.get("products", [])
                            if products and products[0].get("active", False):
                                # Product exists and is active, treat as zero inventory
                                logger.info(f"SKU {sku} exists as active product but has no inventory. Setting to zero.")
                                all_items.append({
                                    "sku": sku,
                                    "on_hand": 0,
                                    "allocated": 0,
                                    "available": 0,
                                    "average_cost": None,
                                    "inventory_warehouse_id": None,
                                    "inventory_location_id": None
                                })
                            else:
                                logger.warning(f"SKU {sku} either doesn't exist as a product or is inactive in ShipStation.")
                        else:
                            logger.error(f"Failed to check product for SKU {sku}: HTTP {product_response.status_code}")
                else:
                    logger.error(f"Failed to fetch SKU {sku}: HTTP {response.status_code} - {response.text}")

            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed for SKU {sku}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error for SKU {sku}: {e}")
        
        logger.info(f"Successfully fetched inventory for {len(all_items)} out of {len(sku_list)} requested SKUs.")
        return all_items
    
    def _write_inventory(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """ShipStation connector is read-only for inventory."""
        raise NotImplementedError("ShipStation connector does not support writing inventory")

    def _find_missing_skus(self, target_skus: List[str], found_inventory: List[Dict[str, Any]]) -> List[str]:
        """Find SKUs that were requested but not found in inventory."""
        found_skus = {item.get("sku") for item in found_inventory if item.get("sku")}
        missing_skus = [sku for sku in target_skus if sku not in found_skus]
        logger.info(f"Found {len(missing_skus)} SKUs missing from inventory out of {len(target_skus)} requested")
        return missing_skus

    def _combine_inventory_data(self, actual_inventory: List[Dict[str, Any]], zero_inventory: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Combine actual inventory data with zero inventory items."""
        combined = actual_inventory.copy()
        combined.extend(zero_inventory)
        logger.info(f"Combined {len(actual_inventory)} actual inventory items with {len(zero_inventory)} zero inventory items")
        return combined

    def read_products(self, **filters) -> List[Dict[str, Any]]:
        """
        Read products from ShipStation.
        
        Supported filters:
        - sku_list: List of specific SKUs to fetch
        - limit: Number of items to fetch
        - active: Filter by active status
        """
        try:
            if "sku_list" in filters:
                return self._read_products_for_sku_list(filters["sku_list"])
            
            # General product read (paginated)
            all_products = []
            page = 1
            limit = filters.get("limit")
            
            while True:
                params = {"page": page, "page_size": 100}
                
                # Add filters
                if "active" in filters:
                    params["active"] = filters["active"]
                
                response = requests.get(
                    f"{self.base_url}/v2/products",
                    headers={"API-Key": self.credentials["api_key"]},
                    params=params,
                    timeout=30
                )
                
                if response.status_code != 200:
                    raise ShipStationAPIError(f"HTTP {response.status_code}: {response.text}")
                
                data = response.json()
                products = data.get("products", [])
                
                if not products:
                    break
                
                all_products.extend(products)
                
                # Check if we've reached the limit
                if limit and len(all_products) >= limit:
                    break
                
                # Check if we've reached the last page
                if len(products) < 100:  # Less than page size means last page
                    break
                
                page += 1
            
            final_products = all_products[:limit] if limit else all_products
            logger.info(f"Successfully fetched {len(final_products)} products from ShipStation")
            return final_products
            
        except requests.exceptions.RequestException as e:
            raise ShipStationAPIError(f"Request failed: {e}")
        except Exception as e:
            raise ShipStationAPIError(f"Unexpected error: {e}")

    def _read_products_for_sku_list(self, sku_list: List[str]) -> List[Dict[str, Any]]:
        """Fetch products for a specific list of SKUs."""
        all_products = []
        
        for sku in sku_list:
            try:
                params = {"sku": sku}
                response = requests.get(
                    f"{self.base_url}/v2/products",
                    headers={"API-Key": self.credentials["api_key"]},
                    params=params,
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    products = data.get("products", [])
                    all_products.extend(products)
                else:
                    logger.warning(f"Failed to fetch product for SKU {sku}: HTTP {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed for SKU {sku}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error for SKU {sku}: {e}")
        
        logger.info(f"Successfully fetched {len(all_products)} products for {len(sku_list)} requested SKUs")
        return all_products


def create_shipstation_connector(api_key: str, base_url: str = "https://api.shipstation.com") -> ShipStationConnector:
    """
    Create a ShipStation connector instance.
    
    Args:
        api_key: ShipStation API key
        base_url: ShipStation API base URL
        
    Returns:
        Configured ShipStation connector
    """
    return ShipStationConnector(
        credentials={"api_key": api_key},
        base_url=base_url
    ) 
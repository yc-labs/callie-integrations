"""InfiPlex API client for inventory management operations."""

import os
import logging
from typing import List, Optional, Dict, Any
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ...core.exceptions import InfiPlexAPIError

logger = logging.getLogger(__name__)


# Exception is imported from core.exceptions


class InfiPlexClient:
    """Client for interacting with InfiPlex API."""
    
    def __init__(self, api_key: str, base_url: str = "https://calibratenetwork.infiplex.com"):
        """Initialize the InfiPlex client.
        
        Args:
            api_key: InfiPlex API key/token
            base_url: Base URL for InfiPlex API
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        
        # Configure session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'User-Agent': 'ShipStation-InfiPlex-Sync/0.1.0'
        })
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, 
                     data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request to the InfiPlex API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            data: Request body data
            
        Returns:
            JSON response data
            
        Raises:
            InfiPlexAPIError: If the API request fails
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.debug(f"Making {method} request to {url} with params: {params}")
            response = self.session.request(method, url, params=params, json=data)
            response.raise_for_status()
            
            # InfiPlex might return empty responses for some operations
            if response.content:
                return response.json()
            else:
                return {"status": "success"}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"InfiPlex API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    raise InfiPlexAPIError(f"API Error: {error_data}")
                except ValueError:
                    raise InfiPlexAPIError(f"HTTP {e.response.status_code}: {e.response.text}")
            else:
                raise InfiPlexAPIError(f"Request failed: {str(e)}")
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to InfiPlex API.
        
        Returns:
            Connection test result
        """
        try:
            # Try to search inventory with a small limit to test the connection
            result = self._make_request('GET', '/api/admin/shop/inventory/search', 
                                      params={'limit': 1})
            return {"status": "success", "message": "Connected to InfiPlex API", "sample_data": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_inventory_info(self, sku: str, warehouse_id: Optional[int] = None) -> Optional[str]:
        """Get inventory quantity for a specific SKU.
        
        Args:
            sku: The SKU to look up
            warehouse_id: Optional warehouse ID to get specific warehouse inventory
            
        Returns:
            Inventory quantity as string, or None if not found
        """
        try:
            endpoint = f'/api/admin/shop/inventory/{sku}'
            params = {}
            if warehouse_id:
                params['warehouse_id'] = warehouse_id
            
            result = self._make_request('GET', endpoint, params=params)
            
            # InfiPlex returns the quantity as a simple string like "984"
            if isinstance(result, str):
                return result
            elif isinstance(result, dict) and 'quantity' in result:
                return str(result['quantity'])
            else:
                return str(result) if result else None
            
        except InfiPlexAPIError as e:
            logger.error(f"Failed to get inventory info for SKU {sku}: {e}")
            return None
    
    def update_inventory(self, sku: str, quantity: int, warehouse_id: Optional[int] = None) -> bool:
        """Update inventory quantity for a specific SKU.
        
        Args:
            sku: The SKU to update
            quantity: New quantity to set
            warehouse_id: Optional warehouse ID, if not provided updates total inventory
            
        Returns:
            True if successful, False otherwise
        """
        inventory_data = {
            "quantity_to_set": quantity
        }
        
        if warehouse_id:
            inventory_data["warehouse_id"] = warehouse_id
        
        try:
            endpoint = f'/api/admin/shop/inventory/{sku}'
            result = self._make_request('PUT', endpoint, data=inventory_data)
            
            logger.info(f"Successfully updated inventory for SKU {sku} to quantity {quantity}")
            return True
            
        except InfiPlexAPIError as e:
            logger.error(f"Failed to update inventory for SKU {sku}: {e}")
            return False
    
    def bulk_update_inventory(self, inventory_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update multiple inventory items in bulk.
        
        Args:
            inventory_updates: List of inventory update dictionaries with keys:
                               'sku', 'quantity_to_set', and optionally 'warehouse_id'
            
        Returns:
            Results summary and API response
        """
        try:
            # Format the data for InfiPlex bulk update API
            bulk_data = []
            for update in inventory_updates:
                item = {
                    "sku": update['sku'],
                    "quantity_to_set": update['quantity_to_set']
                }
                if 'warehouse_id' in update:
                    item['warehouse_id'] = update['warehouse_id']
                bulk_data.append(item)
            
            result = self._make_request('POST', '/api/admin/shop/inventory/bulk_update', data=bulk_data)
            
            # Count successful vs failed updates from response
            successful_updates = 0
            failed_updates = 0
            errors = []
            
            if isinstance(result, list):
                for item in result:
                    if 'warehouse_inventory' in item and item['warehouse_inventory'] is not None:
                        successful_updates += 1
                    else:
                        failed_updates += 1
                        errors.append(f"Failed to update SKU: {item.get('sku', 'unknown')}")
            else:
                # If we get a non-list response, assume success if no exception was raised
                successful_updates = len(inventory_updates)
            
            return {
                "successful": successful_updates,
                "failed": failed_updates,
                "errors": errors,
                "total": len(inventory_updates),
                "api_response": result
            }
            
        except InfiPlexAPIError as e:
            logger.error(f"Failed to bulk update inventory: {e}")
            return {
                "successful": 0,
                "failed": len(inventory_updates),
                "errors": [f"Bulk update failed: {str(e)}"],
                "total": len(inventory_updates),
                "api_response": None
            }
    
    def search_inventory(self, search_term: Optional[str] = None, warehouse_id: Optional[int] = None, 
                        limit: int = 10, limit_start: int = 0) -> Optional[Dict[str, Any]]:
        """Search inventory items.
        
        Args:
            search_term: Optional search term to filter SKUs
            warehouse_id: Optional warehouse ID to filter by
            limit: Maximum number of results to return
            limit_start: Number of results to skip (for pagination)
            
        Returns:
            Search results with inventory information
        """
        try:
            params = {
                'limit': limit,
                'limit_start': limit_start
            }
            
            if search_term:
                params['search_term'] = search_term
            if warehouse_id:
                params['warehouse_id'] = warehouse_id
            
            result = self._make_request('GET', '/api/admin/shop/inventory/search', params=params)
            return result
            
        except InfiPlexAPIError as e:
            logger.error(f"Failed to search inventory: {e}")
            return None


def create_infiplex_client_from_env() -> InfiPlexClient:
    """Create an InfiPlex client using environment variables.
    
    Returns:
        Configured InfiPlexClient instance
        
    Raises:
        ValueError: If required environment variables are missing
    """
    api_key = os.getenv('INFIPLEX_API_KEY')
    if not api_key:
        raise ValueError("INFIPLEX_API_KEY environment variable is required")
    
    base_url = os.getenv('INFIPLEX_BASE_URL', 'https://calibratenetwork.infiplex.com')
    
    return InfiPlexClient(api_key=api_key, base_url=base_url) 
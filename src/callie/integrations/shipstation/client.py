"""ShipStation API client for inventory operations."""

import os
import logging
from typing import List, Optional, Dict, Any
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ...core.models import InventoryResponse, InventoryFilter, InventoryItem
from ...core.exceptions import ShipStationAPIError

logger = logging.getLogger(__name__)


# Exception is imported from core.exceptions


class ShipStationClient:
    """Client for interacting with ShipStation V2 API."""
    
    def __init__(self, api_key: str, base_url: str = "https://ssapi.shipstation.com"):
        """Initialize the ShipStation client.
        
        Args:
            api_key: ShipStation API key
            base_url: Base URL for ShipStation API
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
            'API-Key': self.api_key,
            'Content-Type': 'application/json',
            'User-Agent': 'ShipStation-InfiPlex-Sync/0.1.0'
        })
    
    def _make_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request to the ShipStation API.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            params: Query parameters
            
        Returns:
            JSON response data
            
        Raises:
            ShipStationAPIError: If the API request fails
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.debug(f"Making {method} request to {url} with params: {params}")
            response = self.session.request(method, url, params=params)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"ShipStation API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    raise ShipStationAPIError(f"API Error: {error_data}")
                except ValueError:
                    raise ShipStationAPIError(f"HTTP {e.response.status_code}: {e.response.text}")
            else:
                raise ShipStationAPIError(f"Request failed: {str(e)}")
    
    def get_inventory(self, filters: Optional[InventoryFilter] = None) -> InventoryResponse:
        """Get inventory levels from ShipStation.
        
        Args:
            filters: Optional filters to apply to the request
            
        Returns:
            InventoryResponse containing inventory data
        """
        params = {}
        if filters:
            # Convert filter model to dict, excluding None values
            filter_dict = filters.model_dump(exclude_none=True)
            params.update(filter_dict)
        
        logger.info(f"Fetching inventory with filters: {params}")
        data = self._make_request('GET', '/v2/inventory', params=params)
        
        return InventoryResponse(**data)
    
    def get_all_inventory(self, filters: Optional[InventoryFilter] = None) -> List[InventoryItem]:
        """Get all inventory items, handling pagination automatically.
        
        Args:
            filters: Optional filters to apply to the request
            
        Returns:
            List of all inventory items
        """
        all_items = []
        page = 1
        
        # Set a reasonable limit if not specified
        if filters is None:
            filters = InventoryFilter()
        if filters.limit is None:
            filters.limit = 100
        
        while True:
            # Add page parameter to filters
            current_filters = filters.copy()
            filter_dict = current_filters.model_dump(exclude_none=True)
            filter_dict['page'] = page
            
            logger.info(f"Fetching page {page} of inventory")
            data = self._make_request('GET', '/v2/inventory', params=filter_dict)
            response = InventoryResponse(**data)
            
            all_items.extend(response.inventory)
            
            # Check if we have more pages
            if page >= response.pages:
                break
                
            page += 1
        
        logger.info(f"Retrieved {len(all_items)} total inventory items")
        return all_items
    
    def get_inventory_by_sku(self, sku: str) -> List[InventoryItem]:
        """Get inventory for a specific SKU.
        
        Args:
            sku: The SKU to look up
            
        Returns:
            List of inventory items for the SKU
        """
        filters = InventoryFilter(sku=sku)
        response = self.get_inventory(filters)
        return response.inventory


def create_client_from_env() -> ShipStationClient:
    """Create a ShipStation client using environment variables.
    
    Returns:
        Configured ShipStationClient instance
        
    Raises:
        ValueError: If required environment variables are missing
    """
    api_key = os.getenv('SHIPSTATION_API_KEY')
    if not api_key:
        raise ValueError("SHIPSTATION_API_KEY environment variable is required")
    
    base_url = os.getenv('SHIPSTATION_BASE_URL', 'https://ssapi.shipstation.com')
    
    return ShipStationClient(api_key=api_key, base_url=base_url) 
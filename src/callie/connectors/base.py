"""
Base connector class for all service integrations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class ConnectorCapability(BaseModel):
    """Defines what operations a connector supports."""
    can_read_inventory: bool = False
    can_write_inventory: bool = False
    can_read_products: bool = False
    can_write_products: bool = False
    can_read_orders: bool = False
    can_write_orders: bool = False


class ConnectorField(BaseModel):
    """Defines a field that a connector can read or write."""
    name: str
    description: str
    data_type: str  # "string", "integer", "float", "boolean"
    required: bool = False
    example: Optional[Any] = None


class ConnectorSchema(BaseModel):
    """Defines the schema for a connector's input/output."""
    fields: List[ConnectorField]
    
    def get_field_names(self) -> List[str]:
        """Get list of field names."""
        return [field.name for field in self.fields]


class BaseConnector(ABC):
    """Abstract base class for connectors."""
    
    def __init__(self, credentials: Optional[Dict[str, Any]] = None, base_url: Optional[str] = None, **kwargs):
        """
        Initialize the connector.
        
        Args:
            credentials: Optional authentication credentials (can be provided per-method)
            base_url: Optional base URL for API (can be provided per-method)
            **kwargs: Additional configuration parameters
        """
        self.credentials = credentials or {}
        self.base_url = base_url
        self.config = kwargs
        # self._validate_credentials() # This is now handled by each connector method
        logger.info(f"Initialized {self.__class__.__name__} connector")
    
    @abstractmethod
    def _validate_credentials(self) -> None:
        """Validate that required credentials are provided."""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> ConnectorCapability:
        """Return what operations this connector supports."""
        pass
    
    @abstractmethod
    def get_inventory_schema(self) -> ConnectorSchema:
        """Return the schema for inventory data this connector uses."""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test if the connector can successfully connect to the service."""
        pass
    
    # Inventory Operations
    def read_inventory(self, **filters) -> List[Dict[str, Any]]:
        """
        Read inventory data from the service.
        
        Args:
            **filters: Service-specific filters
            
        Returns:
            List of inventory items as dictionaries
        """
        if not self.get_capabilities().can_read_inventory:
            raise NotImplementedError(f"{self.__class__.__name__} does not support reading inventory")
        return self._read_inventory(**filters)
    
    def write_inventory(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Write inventory data to the service.
        
        Args:
            items: List of inventory items to write
            
        Returns:
            Dictionary with sync results
        """
        if not self.get_capabilities().can_write_inventory:
            raise NotImplementedError(f"{self.__class__.__name__} does not support writing inventory")
        return self._write_inventory(items)
    
    @abstractmethod
    def _read_inventory(self, **filters) -> List[Dict[str, Any]]:
        """Service-specific inventory reading implementation."""
        pass
    
    @abstractmethod
    def _write_inventory(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Service-specific inventory writing implementation.""" 
        pass
    
    # Product Operations (for future use)
    def get_products_schema(self) -> ConnectorSchema:
        """Return the schema for product data this connector uses."""
        return ConnectorSchema(fields=[])
    
    def read_products(self, **filters) -> List[Dict[str, Any]]:
        """Read product data from the service."""
        if not self.get_capabilities().can_read_products:
            raise NotImplementedError(f"{self.__class__.__name__} does not support reading products")
        return self._read_products(**filters)
    
    def write_products(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Write product data to the service."""
        if not self.get_capabilities().can_write_products:
            raise NotImplementedError(f"{self.__class__.__name__} does not support writing products")
        return self._write_products(items)
    
    def _read_products(self, **filters) -> List[Dict[str, Any]]:
        """Service-specific product reading implementation."""
        raise NotImplementedError()
    
    def _write_products(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Service-specific product writing implementation."""
        raise NotImplementedError() 
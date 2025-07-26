"""
Connector framework for Callie Integrations.

This package contains all service connectors that can be used as sources or targets
for data synchronization operations.
"""

from .base import BaseConnector
from .shipstation import ShipStationConnector
from .infiplex import InfiPlexConnector

__all__ = [
    "BaseConnector",
    "ShipStationConnector", 
    "InfiPlexConnector",
]

# Connector registry for dynamic loading
CONNECTOR_REGISTRY = {
    "shipstation": ShipStationConnector,
    "infiplex": InfiPlexConnector,
}

def get_connector(service_type: str) -> BaseConnector:
    """Get a connector instance by service type."""
    if service_type not in CONNECTOR_REGISTRY:
        raise ValueError(f"Unknown service type: {service_type}")
    return CONNECTOR_REGISTRY[service_type] 
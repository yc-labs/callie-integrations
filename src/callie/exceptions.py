"""
Custom exceptions for Callie integrations.
"""

class CallieIntegrationError(Exception):
    """Base exception for all Callie integration errors."""
    pass

class ConnectorError(CallieIntegrationError):
    """Base exception for connector-related errors."""
    pass

class ShipStationAPIError(ConnectorError):
    """Exception raised for ShipStation API errors."""
    pass

class InfiPlexAPIError(ConnectorError):
    """Exception raised for InfiPlex API errors."""
    pass

class SyncError(CallieIntegrationError):
    """Exception raised during sync operations."""
    pass

class ConfigurationError(CallieIntegrationError):
    """Exception raised for configuration errors."""
    pass

class ValidationError(CallieIntegrationError):
    """Exception raised for validation errors."""
    pass

class APIError(CallieIntegrationError):
    """Generic API error."""
    pass 
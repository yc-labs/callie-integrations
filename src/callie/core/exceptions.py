"""
Shared exception classes for Callie Integrations.
"""


class CallieIntegrationError(Exception):
    """Base exception for all Callie integration errors."""
    pass


class APIError(CallieIntegrationError):
    """Base class for API-related errors."""
    pass


class ConfigurationError(CallieIntegrationError):
    """Raised when there's a configuration issue."""
    pass


class ShipStationAPIError(APIError):
    """Exception raised for ShipStation API errors."""
    pass


class InfiPlexAPIError(APIError):
    """Exception raised for InfiPlex API errors."""
    pass 
"""
Custom exceptions for the Callie application.
"""

class CallieException(Exception):
    """Base exception for all application-specific errors."""
    pass

class InitializationError(CallieException):
    """Error during service initialization."""
    pass

class ConfigurationError(CallieException):
    """Error related to sync or workflow configuration."""
    pass

class ExecutionError(CallieException):
    """Error during sync or workflow execution."""
    pass

class ConnectorError(CallieException):
    """Error related to a connector."""
    pass

class TransformationError(CallieException):
    """Error during data transformation."""
    pass

# Specific API error classes for connectors
class ShipStationAPIError(ConnectorError):
    """Exception raised for ShipStation API errors."""
    pass

class InfiPlexAPIError(ConnectorError):
    """Exception raised for InfiPlex API errors."""
    pass 
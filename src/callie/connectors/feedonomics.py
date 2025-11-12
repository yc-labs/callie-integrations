"""
Feedonomics connector for reading and writing order data, fulfillments, cancellations, and returns.
"""

import requests
import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
from ..exceptions import FeedonomicsAPIError
from .base import BaseConnector, ConnectorCapability, ConnectorSchema, ConnectorField

logger = logging.getLogger(__name__)

# --- Pydantic Models for Feedonomics API ---

class FulfillmentLine(BaseModel):
    line_id: str
    quantity: int

class Shipment(BaseModel):
    shipped_date: str
    carrier: str
    tracking_number: str

class FulfillmentPayload(BaseModel):
    fulfillment_type: str = "shipment"
    fulfillment_lines: List[FulfillmentLine]
    shipment: Shipment

class CancellationLine(BaseModel):
    line_id: str
    quantity: int

class CancellationPayload(BaseModel):
    cancellation_lines: List[CancellationLine]
    reason: str

class RefundAdjustment(BaseModel):
    # Define fields for refund adjustment based on documentation
    # This is a placeholder, as the documentation does not specify the fields
    amount: float
    reason: str

class RefundApplication(BaseModel):
    # Define fields for applying a refund to a return
    # Placeholder, as documentation is not specific
    refund_id: str
    amount: float

# --- Connector Class ---

class FeedonomicsConnector(BaseConnector):
    """
    Feedonomics API connector for syncing order data and related entities.
    """

    def __init__(self, credentials: Dict[str, Any], base_url: str, **kwargs):
        super().__init__(credentials, base_url, **kwargs)
        self.token = None
        self._authenticate()

    def _validate_credentials(self) -> None:
        """Validate that required credentials are provided."""
        if "username" not in self.credentials or "password" not in self.credentials:
            raise ValueError("Feedonomics connector requires 'username' and 'password' in credentials")
        if "client_id" not in self.credentials:
            logger.warning("Consider adding 'client_id' to credentials for Feedonomics connector.")

    def _authenticate(self) -> None:
        """Get an authentication token from the Feedonomics API."""
        try:
            response = requests.get(
                f"{self.base_url}/get_token",
                auth=(self.credentials['username'], self.credentials['password']),
                timeout=10
            )
            if response.status_code == 401:
                logger.error(f"Authentication failed: Invalid credentials")
                logger.debug(f"Response: {response.text}")
            response.raise_for_status()
            self.token = response.json().get("token")
            if not self.token:
                raise FeedonomicsAPIError("Authentication failed: No token received.")
            logger.info("Successfully authenticated with Feedonomics API.")
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Auth response status: {e.response.status_code}")
                logger.error(f"Auth response body: {e.response.text}")
            raise FeedonomicsAPIError(f"Authentication request failed: {e}")

    def get_capabilities(self) -> ConnectorCapability:
        """Feedonomics can read and write orders and related entities."""
        return ConnectorCapability(
            can_read_orders=True,
            can_write_orders=True,
        )

    # --- Schemas ---

    def get_orders_schema(self) -> ConnectorSchema:
        """Return Feedonomics order schema."""
        return ConnectorSchema(fields=[
            ConnectorField(name="id", data_type="string", required=True, description="FeedAMP Order ID"),
            ConnectorField(name="marketplace_order_number", data_type="string", description="Marketplace Order Number"),
        ])

    def get_fulfillments_schema(self) -> ConnectorSchema:
        """Return Feedonomics fulfillment schema."""
        return ConnectorSchema(fields=[
            ConnectorField(name="fulfillment_type", data_type="string", required=True),
        ])

    def get_cancellations_schema(self) -> ConnectorSchema:
        """Return Feedonomics cancellation schema."""
        return ConnectorSchema(fields=[
            ConnectorField(name="reason", data_type="string", required=True),
        ])
        
    def get_returns_schema(self) -> ConnectorSchema:
        """Return the schema for returns data."""
        return ConnectorSchema(fields=[
            ConnectorField(name="id", data_type="string", required=True, description="FeedAMP Return ID"),
        ])

    def get_refunds_schema(self) -> ConnectorSchema:
        """Return the schema for refunds data."""
        return ConnectorSchema(fields=[
            ConnectorField(name="id", data_type="string", required=True, description="FeedAMP Refund ID"),
        ])

    # --- API Calls ---

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Helper method to make authenticated API requests."""
        if not self.token:
            self._authenticate()

        headers = {
            "Authorization": f"Bearer {self.token}",
            "client": str(self.credentials.get("client_id", "")),
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.request(
                method,
                f"{self.base_url}/{endpoint}",
                headers=headers,
                timeout=30,
                **kwargs
            )
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.warning("Received 401 Unauthorized. Re-authenticating...")
                self._authenticate()
                headers["Authorization"] = f"Bearer {self.token}"
                response = requests.request(method, f"{self.base_url}/{endpoint}", headers=headers, timeout=30, **kwargs)
                response.raise_for_status()
                return response.json() if response.content else {}
            logger.error(f"HTTP Error: {e.response.status_code} - {e.response.text}")
            raise FeedonomicsAPIError(f"API request to {endpoint} failed: {e.response.text}")
        except requests.exceptions.RequestException as e:
            raise FeedonomicsAPIError(f"Request failed: {e}")

    # --- Connection Test ---
    
    def test_connection(self) -> bool:
        """Test connection to Feedonomics API by trying to fetch one order."""
        try:
            self._read_orders(limit=1)
            return True
        except FeedonomicsAPIError as e:
            logger.error(f"Feedonomics connection test failed: {e}")
            return False

    # --- Order Operations ---

    def _read_orders(self, **filters) -> List[Dict[str, Any]]:
        """Read orders from Feedonomics with automatic pagination."""
        all_items = []
        params = filters.copy()
        
        while True:
            data = self._make_request("get", "orders", params=params)
            all_items.extend(data.get("orders", []))
            next_cursor = data.get("next_cursor")
            if next_cursor:
                params['cursor'] = next_cursor
            else:
                break
        return all_items
        
    def get_order(self, order_id: str) -> Dict[str, Any]:
        """Get a single order by its ID."""
        return self._make_request("get", f"orders/{order_id}")

    def confirm_order(self, order_id: str, merchant_order_number: str) -> Dict[str, Any]:
        """Confirm receipt of an order."""
        payload = {"merchant_order_number": merchant_order_number}
        return self._make_request("post", f"orders/{order_id}/confirm", json=payload)

    def run_order_operation(self, order_id: str, operation: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run an operation on an order."""
        return self._make_request("post", f"orders/{order_id}/run-operation?op={operation}", json=payload or {})

    # --- Fulfillment Request Operations ---

    def get_fulfillment_requests(self, **filters) -> List[Dict[str, Any]]:
        """Get fulfillment requests."""
        return self._make_request("get", "fulfillment-requests", params=filters).get("fulfillment_requests", [])

    # --- Fulfillment Operations ---

    def create_fulfillment(self, order_id: str, payload: FulfillmentPayload) -> Dict[str, Any]:
        """Create a fulfillment on an order."""
        return self._make_request("post", f"orders/{order_id}/fulfillments", json=payload.model_dump())

    def list_fulfillments(self, order_id: str) -> List[Dict[str, Any]]:
        """List fulfillments for an order."""
        return self._make_request("get", f"orders/{order_id}/fulfillments").get("fulfillments", [])

    def get_fulfillment(self, fulfillment_id: str) -> Dict[str, Any]:
        """Get details of a single fulfillment."""
        return self._make_request("get", f"fulfillments/{fulfillment_id}")

    def update_fulfillment(self, fulfillment_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update details of a fulfillment."""
        return self._make_request("put", f"fulfillments/{fulfillment_id}", json=payload)

    def delete_fulfillment(self, fulfillment_id: str) -> None:
        """Delete a fulfillment."""
        self._make_request("delete", f"fulfillments/{fulfillment_id}")

    # --- Cancellation Operations ---

    def create_cancellation(self, order_id: str, payload: CancellationPayload) -> Dict[str, Any]:
        """Create a cancellation on an order."""
        return self._make_request("post", f"orders/{order_id}/cancellations", json=payload.model_dump())

    def list_cancellations(self, order_id: str) -> List[Dict[str, Any]]:
        """List all cancellations on an order."""
        return self._make_request("get", f"orders/{order_id}/cancellations").get("cancellations", [])

    def get_cancellation(self, cancellation_id: str) -> Dict[str, Any]:
        """Get details of a single cancellation."""
        return self._make_request("get", f"cancellations/{cancellation_id}")

    def update_cancellation(self, cancellation_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update details of a cancellation."""
        return self._make_request("put", f"cancellations/{cancellation_id}", json=payload)

    def delete_cancellation(self, cancellation_id: str) -> None:
        """Delete a cancellation."""
        self._make_request("delete", f"cancellations/{cancellation_id}")

    # --- Refund Operations ---

    def create_refund_adjustment(self, order_id: str, payload: RefundAdjustment) -> Dict[str, Any]:
        """Create a refund adjustment on an order."""
        return self._make_request("post", f"orders/{order_id}/refund-adjustments", json=payload.model_dump())

    def list_refunds(self, order_id: str) -> List[Dict[str, Any]]:
        """List all refunds on an order."""
        return self._make_request("get", f"orders/{order_id}/refunds").get("refunds", [])

    def get_refund(self, refund_id: str) -> Dict[str, Any]:
        """Get details of a single refund."""
        return self._make_request("get", f"refunds/{refund_id}")

    def apply_refund_on_return(self, return_id: str, payload: RefundApplication) -> Dict[str, Any]:
        """Apply a refund on a return."""
        return self._make_request("post", f"returns/{return_id}/apply-refund", json=payload.model_dump())

    # --- Return Operations ---
    
    def read_returns(self, **filters) -> List[Dict[str, Any]]:
        """Read returns from Feedonomics with pagination."""
        all_items = []
        params = filters.copy()
        
        while True:
            data = self._make_request("get", "returns", params=params)
            all_items.extend(data.get("returns", []))
            next_cursor = data.get("next_cursor")
            if next_cursor:
                params['cursor'] = next_cursor
            else:
                break
        return all_items

    def get_return(self, return_id: str) -> Dict[str, Any]:
        """Get an individual return."""
        return self._make_request("get", f"returns/{return_id}")

    def run_return_operation(self, return_id: str, operation: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run an operation on a return."""
        return self._make_request("post", f"returns/{return_id}/run-operation?op={operation}", json=payload or {})


    # --- Not Implemented ---

    def _write_orders(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        raise NotImplementedError("Use specific methods like create_fulfillment or create_cancellation.")

    def get_inventory_schema(self) -> ConnectorSchema:
        return ConnectorSchema(fields=[])

    def _read_inventory(self, **filters) -> List[Dict[str, Any]]:
        raise NotImplementedError("Feedonomics connector does not support inventory operations.")

    def _write_inventory(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        raise NotImplementedError("Feedonomics connector does not support inventory operations.")

    def get_products_schema(self) -> ConnectorSchema:
        return ConnectorSchema(fields=[])

    def _read_products(self, **filters) -> List[Dict[str, Any]]:
        raise NotImplementedError("Feedonomics connector does not support product operations.")

    def _write_products(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        raise NotImplementedError("Feedonomics connector does not support product operations.")

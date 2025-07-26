"""Data models for inventory sync."""

from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, field_validator


class Money(BaseModel):
    """Represents a monetary amount with currency."""
    amount: float
    currency: str


class Link(BaseModel):
    """Represents a pagination link."""
    href: Optional[str] = None


class PaginationLinks(BaseModel):
    """Pagination links from API response."""
    first: Optional[Link] = None
    last: Optional[Link] = None
    prev: Optional[Link] = None
    next: Optional[Link] = None
    
    @field_validator('first', 'last', 'prev', 'next', mode='before')
    @classmethod
    def validate_link(cls, v):
        # Handle empty objects {} as None
        if v == {} or v is None:
            return None
        return v


class InventoryItem(BaseModel):
    """Represents an inventory item from ShipStation."""
    sku: str
    on_hand: int
    allocated: Optional[int] = None  # Not always present in V2 API
    available: int
    average_cost: Money
    inventory_warehouse_id: Optional[str] = None  # Not always present
    inventory_location_id: Optional[str] = None  # Not always present


class InventoryResponse(BaseModel):
    """Response from ShipStation inventory API."""
    inventory: List[InventoryItem]
    total: int
    page: int
    pages: int
    links: PaginationLinks


class InventoryFilter(BaseModel):
    """Filter parameters for inventory requests."""
    sku: Optional[str] = None
    inventory_warehouse_id: Optional[str] = None
    inventory_location_id: Optional[str] = None
    group_by: Optional[str] = Field(None, pattern="^(warehouse|location)$")
    limit: Optional[int] = None 
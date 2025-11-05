from __future__ import annotations

from datetime import date
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field


# -----------------------------
# Domain models (Pydantic v2)
# -----------------------------
DepartmentName = Literal["Clothing", "Electronics", "Grocery", "Furniture"]

class DepartmentInfo(BaseModel):
    department: DepartmentName
    aisle: Optional[int]
    shelf: Optional[int]
    location_code: str


class ClothingDetails(BaseModel):
    kind: Literal["clothing"] = "clothing"
    dept: DepartmentInfo
    size: Literal["XS", "S", "M", "L", "XL"]
    material: str


class ElectronicsDetails(BaseModel):
    kind: Literal["electronics"] = "electronics"
    dept: DepartmentInfo
    warranty_years: int
    voltage: int


class GroceryDetails(BaseModel):
    kind: Literal["grocery"] = "grocery"
    dept: DepartmentInfo
    expiration_date: date
    is_organic: bool


class FurnitureDetails(BaseModel):
    kind: Literal["furniture"] = "furniture"
    dept: DepartmentInfo
    material: str
    weight_limit_lbs: int


ProductDetails = Annotated[
    Union[ClothingDetails, ElectronicsDetails, GroceryDetails, FurnitureDetails],
    Field(discriminator="kind"),
]


class Product(BaseModel):
    product_id: int
    sku: str
    name: str
    price: float
    launch_date: date
    is_available: bool
    details: ProductDetails


# -----------------------------
# Test cases for various type annotations
# -----------------------------

# Test case 1: Union of basic types (str, int)
FlexibleId = Union[str, int]

# Test case 2: Union of basic types with None (Optional alternative)
MaybeNumber = Union[int, float, None]

# Test case 3: Union mixing Literal and basic types
StatusCode = Union[Literal["success", "error", "pending"], int]

# Test case 4: Nested Union with Literal values
Priority = Union[Literal["low", "medium", "high"], int]

# Test case 5: Example model using these types
class TestAnnotations(BaseModel):
    """Model to test various annotation patterns for DDL generation."""
    flexible_id: FlexibleId
    maybe_number: MaybeNumber
    status: StatusCode
    priority: Priority
    simple_union: Union[str, int, bool]

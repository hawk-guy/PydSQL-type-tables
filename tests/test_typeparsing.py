from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field


# Type-annotation-first approach (no ABCs yet):
# - Departments are represented via a Literal type alias.
# - Each concrete *Details model has a dept: DepartmentInfo field and a
#   discriminating "kind" literal for use in unions.

DepartmentName = Literal["clothing", "electronics", "grocery", "furniture"]

class DepartmentInfo(BaseModel):
	"""Basic info tying a product to a department/location in a store.

	Notes for future SQL mapping:
	- department: ideal candidate for an enum or a child reference table.
	- aisle/shelf: optional location metadata; could be VARCHAR/INT.
	- location_code: can hold custom store codes; consider indexing.
	"""

	department: DepartmentName
	aisle: Optional[str] = None
	shelf: Optional[str] = None
	location_code: Optional[str] = Field(default=None, max_length=32)


class ClothingDetails(BaseModel):
	kind: Literal["clothing"] = "clothing"
	dept: DepartmentInfo
	size: Literal["XS", "S", "M", "L", "XL"]
	color: str = Field(min_length=1, max_length=30)
	material: Optional[str] = Field(default=None, max_length=40)


class ElectronicsDetails(BaseModel):
	kind: Literal["electronics"] = "electronics"
	dept: DepartmentInfo
	brand: str = Field(min_length=1, max_length=60)
	watts: int = Field(ge=0)
	warranty_months: int = Field(ge=0, le=60)


class GroceryDetails(BaseModel):
	kind: Literal["grocery"] = "grocery"
	dept: DepartmentInfo
	perishable: bool = True
	expiration_date: Optional[date] = None


class FurnitureDetails(BaseModel):
	kind: Literal["furniture"] = "furniture"
	dept: DepartmentInfo
	material: str
	weight_kg: float = Field(gt=0)


ProductDetails = Annotated[
	Union[ClothingDetails, ElectronicsDetails, GroceryDetails, FurnitureDetails],
	Field(discriminator="kind"),
]


class Product(BaseModel):
	product_id: int
	sku: str = Field(min_length=3, max_length=32)
	name: str = Field(min_length=1, max_length=255)
	price: Decimal = Field(ge=0)
	launch_date: date
	is_available: bool = True
	details: ProductDetails


# ---------------------------
# Smoke tests for abstraction
# ---------------------------

def test_product_schema_discriminated_union_and_dept_info():
	schema = Product.model_json_schema()

	# Ensure details field is a discriminated union by "kind"
	details_schema = schema["properties"]["details"]
	assert "discriminator" in details_schema
	assert details_schema["discriminator"]["propertyName"] == "kind"

	# Ensure DepartmentInfo is present in each details schema as nested field "dept"
	found_any_of = details_schema.get("anyOf") or details_schema.get("oneOf")
	assert found_any_of and isinstance(found_any_of, list)
	for variant in found_any_of:
		props = variant.get("properties", {})
		assert "dept" in props
		dept_props = props["dept"].get("properties", {})
		# DepartmentInfo has a "department" field shaped by our DepartmentName
		assert "department" in dept_props


def test_can_instantiate_products_for_multiple_departments():
	# Clothing product
	p1 = Product(
		product_id=1,
		sku="TSHIRT-001",
		name="Basic Tee",
		price=Decimal("19.99"),
		launch_date=date(2024, 5, 1),
		details=ClothingDetails(
			dept=DepartmentInfo(department="clothing", aisle="A1"),
			size="M",
			color="Navy",
		),
	)
	assert p1.details.kind == "clothing"
	assert p1.details.dept.department == "clothing"

	# Electronics product
	p2 = Product(
		product_id=2,
		sku="HEADSET-200",
		name="Wireless Headset",
		price=Decimal("89.50"),
		launch_date=date(2024, 7, 15),
		details=ElectronicsDetails(
			dept=DepartmentInfo(department="electronics", aisle="E3"),
			brand="Acme",
			watts=10,
			warranty_months=24,
		),
	)
	assert p2.details.kind == "electronics"
	assert p2.details.dept.department == "electronics"

	# Grocery product (optional expiration)
	p3 = Product(
		product_id=3,
		sku="APPLE-GALA",
		name="Gala Apples (1kg)",
		price=Decimal("3.49"),
		launch_date=date(2024, 9, 10),
		details=GroceryDetails(
			dept=DepartmentInfo(department="grocery", aisle="G5"),
			perishable=True,
		),
	)
	assert p3.details.kind == "grocery"
	assert p3.details.dept.department == "grocery"

	# Furniture product
	p4 = Product(
		product_id=4,
		sku="SOFA-3S",
		name="3-Seater Sofa",
		price=Decimal("599.00"),
		launch_date=date(2024, 3, 20),
		details=FurnitureDetails(
			dept=DepartmentInfo(department="furniture", aisle="F2"),
			material="Leather",
			weight_kg=42.5,
		),
	)
	assert p4.details.kind == "furniture"
	assert p4.details.dept.department == "furniture"


# ---------------------------
# Example SQL DDL (PostgreSQL)
# ---------------------------
# Object-table pattern with reciprocal FKs per your latest design.
#
# Pseudocode for generator-side type checks (future):
# - For any discriminated union field, e.g., details: Union[A, B, ...],
#   map each variant to a corresponding *_row_id column on base_model.
# - When materializing an object:
#     if count_set([A_row_id, B_row_id, ...]) > 1:
#         error("Only one variant foreign key can be set for union field")

EXAMPLE_SQL_DDL = {
    "base_model": (
        "CREATE TABLE base_model (\n"
        "    object_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,\n"
        "    product_row_id INTEGER REFERENCES product(id) DEFERRABLE INITIALLY DEFERRED,\n"
        "    department_info_row_id INTEGER REFERENCES department_info(id) DEFERRABLE INITIALLY DEFERRED,\n"
        "    clothing_details_row_id INTEGER REFERENCES clothing_details(id) DEFERRABLE INITIALLY DEFERRED,\n"
        "    electronics_details_row_id INTEGER REFERENCES electronics_details(id) DEFERRABLE INITIALLY DEFERRED,\n"
		"    grocery_details_row_id INTEGER REFERENCES grocery_details(id) DEFERRABLE INITIALLY DEFERRED,\n"
		"    furniture_details_row_id INTEGER REFERENCES furniture_details(id) DEFERRABLE INITIALLY DEFERRED\n"
        ");"
    ),
    # TODO: Type checking/triggers to enforce row_id -> type consistency will be added here later.
    "department_info": (
        "CREATE TABLE department_info (\n"
        "    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,\n"
        "    base_object_id INTEGER NOT NULL UNIQUE REFERENCES base_model(object_id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,\n"
        "    department TEXT NOT NULL CHECK (department IN ('clothing','electronics','grocery','furniture')),\n"
        "    aisle TEXT NULL,\n"
        "    shelf TEXT NULL,\n"
        "    location_code VARCHAR(32) NULL\n"
        ");"
    ),
    "clothing_details": (
        "CREATE TABLE clothing_details (\n"
        "    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,\n"
        "    base_object_id INTEGER NOT NULL UNIQUE REFERENCES base_model(object_id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,\n"
        "    dept_object_id INTEGER NOT NULL REFERENCES base_model(object_id) DEFERRABLE INITIALLY DEFERRED,\n"
        "    size TEXT NOT NULL CHECK (size IN ('XS','S','M','L','XL')),\n"
        "    color VARCHAR(30) NOT NULL,\n"
        "    material VARCHAR(40) NULL\n"
        ");"
    ),
    "electronics_details": (
        "CREATE TABLE electronics_details (\n"
        "    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,\n"
        "    base_object_id INTEGER NOT NULL UNIQUE REFERENCES base_model(object_id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,\n"
        "    dept_object_id INTEGER NOT NULL REFERENCES base_model(object_id) DEFERRABLE INITIALLY DEFERRED,\n"
        "    brand VARCHAR(60) NOT NULL,\n"
        "    watts INTEGER CHECK (watts >= 0),\n"
        "    warranty_months INTEGER CHECK (warranty_months >= 0 AND warranty_months <= 60)\n"
        ");"
    ),
    "grocery_details": (
        "CREATE TABLE grocery_details (\n"
        "    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,\n"
        "    base_object_id INTEGER NOT NULL UNIQUE REFERENCES base_model(object_id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,\n"
        "    dept_object_id INTEGER NOT NULL REFERENCES base_model(object_id) DEFERRABLE INITIALLY DEFERRED,\n"
        "    perishable BOOLEAN NOT NULL DEFAULT TRUE,\n"
        "    expiration_date DATE NULL\n"
        ");"
    ),
    "furniture_details": (
        "CREATE TABLE furniture_details (\n"
        "    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,\n"
        "    base_object_id INTEGER NOT NULL UNIQUE REFERENCES base_model(object_id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,\n"
        "    dept_object_id INTEGER NOT NULL REFERENCES base_model(object_id) DEFERRABLE INITIALLY DEFERRED,\n"
        "    material TEXT NOT NULL,\n"
        "    weight_kg REAL CHECK (weight_kg > 0)\n"
        ");"
    ),
    "product": (
        "CREATE TABLE product (\n"
        "    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,\n"
        "    base_object_id INTEGER NOT NULL UNIQUE REFERENCES base_model(object_id) ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,\n"
        "    product_id INTEGER NOT NULL,\n"
        "    sku VARCHAR(32) NOT NULL,\n"
        "    name VARCHAR(255) NOT NULL,\n"
        "    price NUMERIC NOT NULL CHECK (price >= 0),\n"
        "    launch_date DATE NOT NULL,\n"
        "    is_available BOOLEAN NOT NULL DEFAULT TRUE,\n"
        "    details_object_id INTEGER REFERENCES base_model(object_id) DEFERRABLE INITIALLY DEFERRED,\n"
        "    UNIQUE (sku)\n"
        ");"
    ),
}
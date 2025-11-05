import unittest
from pprint import pprint
from pydantic import BaseModel
from pydsql.typeParser import (
    collect_base_models,
    describe_annotation,
    find_defined_type_aliases,
    retrieve_types_and_basemodels,
)
import tests.fixtures.product_models_annotated as product_module
from tests.fixtures.product_models_annotated import (
    Product,
    DepartmentInfo,
    DepartmentName,
    ProductDetails,
    ClothingDetails,
    ElectronicsDetails,
    GroceryDetails,
    FurnitureDetails,
    TestAnnotations,
    FlexibleId,
    MaybeNumber,
    StatusCode,
    Priority,
)


class TestTypeParsing(unittest.TestCase):
    """
    Test parsing of extracting type and class information from Pydantic
    models, especially those with complex type annotations like Unions
    and Literals.
    """

    @classmethod
    def setUpClass(cls):
        cls.module = product_module
        cls.product = Product
        cls.model_set = {
            Product,
            DepartmentInfo,
            ClothingDetails,
            ElectronicsDetails,
            GroceryDetails,
            FurnitureDetails,
            TestAnnotations,
        }
        cls.annotation_set = {
            "DepartmentName",
            "ProductDetails",
            "FlexibleId",
            "MaybeNumber",
            "StatusCode",
            "Priority",
        }

    def test_collect_base_models(self):
        """Test detection of Pydantic BaseModel subclasses in the
        product models module.
        """
        print("BaseModel subclasses found:")
        base_models = collect_base_models(self.module)
        self.assertTrue(BaseModel not in base_models.values())
        model_set = set(base_models.values())
        self.assertSetEqual(model_set, self.model_set)
        pprint(base_models)

    def test_type_alias_detection(self):
        """Test detection of type aliases in the product models module."""
        print("Type aliases found:")
        table_aliases = find_defined_type_aliases(self.module)
        pprint(table_aliases)

    def test_retrieve_types_and_basemodels(self):
        """Test retrieval of both BaseModel classes and type aliases from
        the module.
        """
        print("\nAll types and BaseModels found:")
        all_types = retrieve_types_and_basemodels(self.module)
        pprint(all_types)

        # Check that all expected BaseModel classes are present
        model_names = {
            name
            for name in all_types.keys()
            if name in {cls.__name__ for cls in self.model_set}
        }
        expected_model_names = {cls.__name__ for cls in self.model_set}
        self.assertSetEqual(model_names, expected_model_names)

        # Check that all expected type aliases are present
        annotation_names = {
            name for name in all_types.keys() if name in self.annotation_set
        }
        self.assertSetEqual(annotation_names, self.annotation_set)

    def test_literal_type_description(self):
        """Test that Literal types are correctly described with kind
        'literal' and contain all values.
        """
        result = describe_annotation(DepartmentName)
        self.assertEqual(result["kind"], "literal")
        self.assertFalse(result["optional"])
        self.assertSetEqual(
            set(result["values"]),
            {"Clothing", "Electronics", "Grocery", "Furniture"},
        )

    def test_union_without_none_not_optional(self):
        """Test that Union types without None are not marked as optional."""
        result = describe_annotation(FlexibleId)
        self.assertEqual(result["kind"], "union")
        self.assertFalse(result["optional"])
        self.assertEqual(len(result["options"]), 2)

    def test_union_with_none_is_optional(self):
        """Test that Union types with None are marked as optional."""
        result = describe_annotation(MaybeNumber)
        self.assertEqual(result["kind"], "union")
        self.assertTrue(result["optional"])
        # Should have int, float, and NoneType
        self.assertEqual(len(result["options"]), 3)

    def test_annotated_type_structure(self):
        """Test that Annotated types have correct structure with base and
        metadata.
        """
        result = describe_annotation(ProductDetails)
        self.assertEqual(result["kind"], "annotated")
        self.assertIn("base", result)
        self.assertIn("metadata", result)
        self.assertFalse(result["optional"])
        # Base should be a union of model references
        self.assertEqual(result["base"]["kind"], "union")

    def test_basemodel_reference_format(self):
        """Test that BaseModel classes are returned as model_ref with
        name.
        """
        result = describe_annotation(ClothingDetails)
        self.assertEqual(result["kind"], "model_ref")
        self.assertEqual(result["name"], "ClothingDetails")
        self.assertFalse(result["optional"])

    def test_basic_type_format(self):
        """Test that basic types (str, int, etc.) are returned with kind
        'type' and name.
        """
        result = describe_annotation(str)
        self.assertEqual(result["kind"], "type")
        self.assertEqual(result["name"], "str")
        self.assertFalse(result["optional"])

        result = describe_annotation(int)
        self.assertEqual(result["kind"], "type")
        self.assertEqual(result["name"], "int")
        self.assertFalse(result["optional"])

    def test_all_type_descriptions_have_kind(self):
        """Verify the obsession: every type description MUST have a
        'kind' field.
        """
        all_types = retrieve_types_and_basemodels(self.module)

        for type_name, type_info in all_types.items():
            # For BaseModel classes, check each field's annotation
            if isinstance(type_info, dict) and "kind" not in type_info:
                # This is a BaseModel with fields
                for field_name, field_info in type_info.items():
                    self.assertIn(
                        "annotation",
                        field_info,
                        f"{type_name}.{field_name} missing annotation",
                    )
                    self.assertIn(
                        "kind",
                        field_info["annotation"],
                        f"{type_name}.{field_name} annotation missing 'kind'",
                    )
            else:
                # This is a type alias
                self.assertIn(
                    "kind",
                    type_info,
                    f"Type alias {type_name} missing 'kind'",
                )

    def test_nested_union_options_have_kind(self):
        """Test that options within Union types also have 'kind' field."""
        result = describe_annotation(StatusCode)
        self.assertEqual(result["kind"], "union")

        for option in result["options"]:
            self.assertIn(
                "kind", option, "Union option missing 'kind' field"
            )

    def test_product_details_field_is_type_ref(self):
        """Test that Product.details field shows as type_ref to
        ProductDetails for lookups.
        """
        all_types = retrieve_types_and_basemodels(self.module)
        product_info = all_types["Product"]

        details_field = product_info["details"]
        annotation = details_field["annotation"]

        self.assertEqual(annotation["kind"], "type_ref")
        self.assertEqual(annotation["name"], "ProductDetails")

    def test_department_field_is_type_ref(self):
        """Test that DepartmentInfo.department field shows as type_ref to
        DepartmentName.
        """
        all_types = retrieve_types_and_basemodels(self.module)
        dept_info = all_types["DepartmentInfo"]

        department_field = dept_info["department"]
        annotation = department_field["annotation"]

        self.assertEqual(annotation["kind"], "type_ref")
        self.assertEqual(annotation["name"], "DepartmentName")


if __name__ == "__main__":
    unittest.main()

import unittest
from pprint import pprint
from pydsql.typeParser import collect_base_models, find_defined_type_aliases
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
)
from pydantic import BaseModel


class TestTypeParsing(unittest.TestCase):
    """
    Test parsing of extracting type and class information from Pydantic models,
    especially those with complex type annotations like Unions and Literals."""

    @classmethod
    def setUpClass(cls):
        cls.module = product_module
        cls.product = Product
        cls.fixtures_set = {
            Product,
            DepartmentInfo,
            ClothingDetails,
            ElectronicsDetails,
            GroceryDetails,
            FurnitureDetails,
        }

    def test_collect_base_models(self):
        """
        Test detection of Pydantic BaseModel subclasses in the product models module."""
        print("BaseModel subclasses found:")
        base_models = collect_base_models(self.module)
        self.assertTrue(BaseModel not in base_models.values())
        model_set = set(base_models.values())
        self.assertSetEqual(model_set, self.fixtures_set)
        pprint(base_models)

    def test_type_alias_detection(self):
        """
        Test detection of type aliases in the product models module."""
        # Also list defined type aliases (e.g., DepartmentName, ProductDetails)
        print("Type aliases found:")
        table_aliases = find_defined_type_aliases(self.module)
        # pprint(table_aliases)

    # def test_base_model_detection(self):
    #     classes_found = retrieve_types_and_basemodels(self.module)
    #     print("\nPydantic BaseModel classes found:")
    #     pprint(classes_found)
    #     pass


if __name__ == "__main__":
    unittest.main()

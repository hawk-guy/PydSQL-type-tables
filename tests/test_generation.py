import unittest
from datetime import date

from pydantic import BaseModel

from pydsql.generator import generate_sql


class TestGeneration(unittest.TestCase):
    def test_basic_product_model(self):
        class Product(BaseModel):
            product_id: int
            name: str
            price: float
            launch_date: date
            is_available: bool

        expected_sql = (
            "CREATE TABLE product (\n"
            "    product_id INTEGER,\n"
            "    name TEXT,\n"
            "    price REAL,\n"
            "    launch_date DATE,\n"
            "    is_available BOOLEAN\n"
            ");"
        )

        actual_sql = generate_sql(Product)
        self.assertEqual(actual_sql, expected_sql)


if __name__ == "__main__":
    unittest.main()
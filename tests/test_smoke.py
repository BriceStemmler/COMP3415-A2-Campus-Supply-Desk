"""A small starting test suite for the order desk."""

from pathlib import Path
import tempfile
import unittest

from supplydesk.service import OrderService, ValidateService, DisplayService


class OrderSmokeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "state.json"
        self.order = OrderService(self.path)
        self.validate = ValidateService(self.path)
        self.display = DisplayService(self.path)

    def test_regular_pickup_quote(self):
        quote = self.validate.validateOrder("regular", [{"product_id": "notebook", "quantity": 2}])
        self.assertEqual(quote["subtotal_cents"], 1000)
        self.assertEqual(quote["discount_cents"], 0)
        self.assertEqual(quote["delivery_cents"], 0)
        self.assertEqual(quote["total_cents"], 1000)

    def test_student_delivery_quote(self):
        quote = self.validate.validateOrder("student", [{"product_id": "hoodie", "quantity": 2}], "delivery")
        self.assertEqual(quote["discount_cents"], 800)
        self.assertEqual(quote["delivery_cents"], 600)
        self.assertEqual(quote["total_cents"], 7800)

    def test_order_can_be_reopened(self):
        order = self.order.place_order("regular", [{"product_id": "mug", "quantity": 1}])
        self.assertEqual(order["order_id"], "ORD-0001")
        self.assertEqual(order["status"], "placed")
        self.assertEqual(ValidateService(self.path).validateOrderID(order["order_id"]), order)

    def test_cancel_order_restores_stock(self):
        before = self.display.catalog()
        order = self.order.place_order("regular", [{"product_id": "pen-pack", "quantity": 2}])
        cancelled = self.order.cancel_order(order["order_id"])
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(self.display.catalog(), before)

    def test_student_receives_discount(self):
        catalog = self.display.catalog()

        hoodie = next(
            product for product in catalog
            if product["product_id"] == "hoodie")
        hoodie_price = hoodie["unit_price_cents"]

        quote = self.validate.validateOrder(
            "student",
            [{"product_id": "hoodie", "quantity": 2}])

        subtotal = hoodie_price * 2
        expected_discount = (
            (subtotal * 10 + 50) // 100
            if subtotal >= 5000 else 0)
        expected_total = subtotal - expected_discount

        self.assertEqual(quote["subtotal_cents"], subtotal)
        self.assertEqual(quote["discount_cents"], expected_discount)
        self.assertEqual(quote["total_cents"], expected_total)

    def test_purchace_quantity_within_available_limits(self):
        catalog = self.display.catalog()

        hoodie = next(
            item for item in catalog
            if item["product_id"] == "hoodie")
        stock = hoodie["stock"]

        if stock >= 1:
            quote = self.validate.validateOrder(
                "regular",
                [{"product_id": "hoodie", "quantity": 2}])

            self.assertGreaterEqual(quote["items"][0]["quantity"], 1)
            self.assertLessEqual(quote["items"][0]["quantity"], stock)

        with self.assertRaises(ValueError):
            self.validate.validateOrder(
                "regular",
                [{"product_id": "hoodie", "quantity": stock + 1}])

    def test_find_order_by_order_id(self):
        order = self.order.place_order(
            "regular",
            [{"product_id": "mug", "quantity": 1}])
        
        order_id = order["order_id"]
        found_order = self.validate.validateOrderID(order_id)

        self.assertIsNotNone(found_order)
        self.assertEqual(found_order["order_id"], order_id)
        self.assertEqual(found_order, order)

    def test_invalid_product_id(self):
        with self.assertRaisesRegex(ValueError, "Unknown product."):
            self.validate.validateOrder(
                "regular",
                [{"product_id": "invalid-product", "quantity": 1}])


if __name__ == "__main__":
    unittest.main()

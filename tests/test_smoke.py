"""A small starting test suite for the order desk."""

from pathlib import Path
import tempfile
import unittest

from supplydesk.service import OrderService


class OrderSmokeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "state.json"
        self.service = OrderService(self.path)

    def test_regular_pickup_quote(self):
        quote = self.service.quote("regular", [{"product_id": "notebook", "quantity": 2}])
        self.assertEqual(quote["subtotal_cents"], 1000)
        self.assertEqual(quote["discount_cents"], 0)
        self.assertEqual(quote["delivery_cents"], 0)
        self.assertEqual(quote["total_cents"], 1000)

    def test_student_delivery_quote(self):
        quote = self.service.quote("student", [{"product_id": "hoodie", "quantity": 2}], "delivery")
        self.assertEqual(quote["discount_cents"], 800)
        self.assertEqual(quote["delivery_cents"], 600)
        self.assertEqual(quote["total_cents"], 7800)

    def test_order_can_be_reopened(self):
        order = self.service.place_order("regular", [{"product_id": "mug", "quantity": 1}])
        self.assertEqual(order["order_id"], "ORD-0001")
        self.assertEqual(order["status"], "placed")
        self.assertEqual(OrderService(self.path).get_order(order["order_id"]), order)

    def test_cancel_order_restores_stock(self):
        before = self.service.catalog()
        order = self.service.place_order("regular", [{"product_id": "pen-pack", "quantity": 2}])
        cancelled = self.service.cancel_order(order["order_id"])
        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(self.service.catalog(), before)

    def test_student_receives_discount(self):
        catalog = self.service.catalog()

        hoodie = next(
            product for product in catalog
            if product["product_id"] == "hoodie")

        hoodie_price = hoodie["unit_price_cents"]

        quote = self.service.quote(
            "student",
            [{"product_id": "hoodie", "quantity": 2}])

        subtotal = hoodie_price * 2

        expected_discount = (
            (subtotal * 10 + 50) // 100
            if subtotal >= 5000 else 0
        )

        expected_total = subtotal - expected_discount

        self.assertEqual(quote["subtotal_cents"], subtotal)
        self.assertEqual(quote["discount_cents"], expected_discount)
        self.assertEqual(quote["total_cents"], expected_total)


if __name__ == "__main__":
    unittest.main()

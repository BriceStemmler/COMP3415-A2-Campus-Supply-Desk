"""Operations used by the command-line order desk."""

from supplydesk.storage import JsonStore

class ValidateService:
    def __init__(self, state_path=".supplydesk/state.json"):
        self.store = JsonStore(state_path)

    def validateOrder(self, state, customer_type, items, fulfillment="pickup"):
        if customer_type not in ("regular", "student"):
            raise ValueError("Customer type must be regular or student.")
        if fulfillment not in ("pickup", "delivery"):
            raise ValueError("Fulfillment must be pickup or delivery.")
        if not isinstance(items, list) or not items:
            raise ValueError("An order must contain at least one item.")
        lines = []
        subtotal = 0

        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Each item must contain a product_id and quantity.")
            product = None
            for candidate in state["catalog"]:
                if candidate["product_id"] == item.get("product_id"):
                    product = candidate
                    break
            if product is None:
                raise ValueError("Unknown product.")
            quantity = item.get("quantity")
            if type(quantity) is not int or quantity < 1 or quantity > 99:
                raise ValueError("Quantity must be an integer from 1 to 99.")
            if quantity > product["stock"]:
                raise ValueError("Not enough stock for " + product["product_id"] + ".")
            
            line_total = product["unit_price_cents"] * quantity
            subtotal += line_total
            lines.append({
                "product_id": product["product_id"],
                "name": product["name"],
                "unit_price_cents": product["unit_price_cents"],
                "quantity": quantity,
                "line_total_cents": line_total,
            })
        discount = 0
        if customer_type == "student" and subtotal > 5000:
            discount = (subtotal * 10 + 50) // 100
        delivery = 0
        if fulfillment == "delivery" and subtotal - discount < 10000:
            delivery = 600
        return {
            "customer_type": customer_type,
            "fulfillment": fulfillment,
            "items": lines,
            "subtotal_cents": subtotal,
            "discount_cents": discount,
            "delivery_cents": delivery,
            "total_cents": subtotal - discount + delivery,
        }

    def validateOrderID(self, state, order_id):
            for order in state["orders"]:
                if order["order_id"] == order_id:
                    return order
            raise ValueError("Unknown order: " + order_id)

class DisplayService:
    def __init__(self, state_path=".supplydesk/state.json"):
        self.store = JsonStore(state_path)

    def load(self, thing_to_load):
        return self.store.load()[thing_to_load]

    def catalog(self):
        return self.load("catalog")

    def list_orders(self):
        return self.load("orders")

class OrderService:
    def __init__(self, state_path=".supplydesk/state.json"):
        self.store = JsonStore(state_path)
        self.validator = ValidateService()

    def place_order(self, customer_type, items, fulfillment="pickup"):
        state = self.store.load()
        order_details = self.validator.validateOrder(state, customer_type, items, fulfillment)

        order = {
            "order_id": "ORD-" + str(state["next_order_number"]).zfill(4),
            "status": "placed",
            **order_details,
        }

        for line in order["items"]:
            for product in state["catalog"]:
                if product["product_id"] == line["product_id"]:
                    product["stock"] -= line["quantity"]

        state["next_order_number"] += 1
        state["orders"].append(order)

        self.store.save(state)
        return order

    def cancel_order(self, order_id):
        state = self.store.load()
        order = self.validator.validateOrderID(state, order_id)
        for line in order["items"]:
            for product in state["catalog"]:
                if product["product_id"] == line["product_id"]:
                    product["stock"] += line["quantity"]
        order["status"] = "cancelled"

        self.store.save(state)
        return order





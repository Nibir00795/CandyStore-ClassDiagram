from datetime import datetime
from typing import List

from .person import User
from .product import Candy
from .payment import PaymentMethod


class CartItem:
    """Represents a candy in the cart."""
    
    def __init__(self, candy: Candy, quantity: int):
        self.candy = candy
        self.quantity = quantity

    def subtotal(self):
        """Calculate the subtotal for this cart item."""
        return self.candy.price * self.quantity


class ShoppingCart:
    """User's temporary basket."""
    
    def __init__(self, user: User):
        self.user = user
        self._items: List[CartItem] = []  # Protected: internal state

    def add_item(self, candy: Candy, quantity: int):
        """Add candy to the shopping cart."""
        for item in self._items:
            if item.candy == candy:
                item.quantity += quantity
                return
        self._items.append(CartItem(candy, quantity))

    # def calculate_total(self):
    #     """Calculate the total amount in the cart."""
    #     return sum(item.subtotal() for item in self._items)

    def calculate_total(self):
        """Calculate subtotal, tax and total (with optional tax_rate).

        Returns a tuple: (subtotal, tax, total)
        Also sets `self.subtotal`, `self.tax_rate` (if present) and `self.total`.
        """
        # Compute subtotal from cart items
        self.subtotal = round(sum(item.candy.price * item.quantity for item in self._items), 2)
        # Use a tax_rate attribute on the cart if present, default to 0.0
        self.tax_rate = float(getattr(self, "tax_rate", 0.0))
        tax = round(self.subtotal * self.tax_rate, 2)
        self.total = round(self.subtotal + tax, 2)
        return (self.subtotal, tax, self.total)



    def create_order(self, payment_method: PaymentMethod) -> "Order":
        """Create an order from the current cart contents."""
        subtotal, tax, total = self.calculate_total()
        order_items = [OrderItem(i.candy, i.quantity) for i in self._items]
        return Order(self.user, order_items, total, payment_method)

    def clear(self):
        """Clear all items from the cart."""
        self._items.clear()

    def get_items(self) -> List[CartItem]:
        """Get a copy of the cart items."""
        return self._items.copy()


class Order:
    """Represents a confirmed order."""
    
    order_counter = 1000

    def __init__(self, user: User, items: List["OrderItem"], total_amount: float, payment_method: PaymentMethod):
        self.order_id = Order.order_counter
        Order.order_counter += 1
        self.user = user
        self.items = items
        self.total_amount = total_amount
        self.payment_method = payment_method
        self.status = "Pending"
        self.timestamp = datetime.now()

    def confirm_payment(self):
        """Process payment and mark the order as paid."""
        if self.payment_method.process_payment(self.total_amount):
            self.status = "Paid"
            return True
        else:
            self.status = "Payment Failed"
            return False

    def ship_order(self):
        """Mark the order as shipped."""
        self.status = "Shipped"

    def to_dict(self) -> dict:
        """Serialize Order to a plain dict (safe for JSON)."""
        # Normalize the serialization to match this class' attributes.
        # Use `order_id` and `user`/`user_id` consistently, and ensure items are serializable.
        user_id = None
        if hasattr(self, "user") and self.user is not None:
            # Person/User classes use `person_id`/`user_id` as identifier
            user_id = getattr(self.user, "person_id", None) or getattr(self.user, "user_id", None)
        else:
            user_id = getattr(self, "user_id", None)

        return {
            "order_id": getattr(self, "order_id", None),
            "user_id": user_id,
            "items": [i.to_dict() for i in getattr(self, "items", [])],
            "total_amount": float(getattr(self, "total_amount", 0.0)),
            "status": getattr(self, "status", "Pending"),
            "timestamp": (getattr(self, "timestamp", None).isoformat() if getattr(self, "timestamp", None) else None),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Order":
        """Construct Order from a dict; missing fields get sensible defaults."""
        # Create object without calling __init__ because callers may only have ids
        obj = cls.__new__(cls)
        obj.order_id = data.get("order_id")
        obj.user = None
        obj.user_id = data.get("user_id")
        # Reconstruct items as OrderItem instances if possible
        raw_items = data.get("items", [])
        reconstructed = []
        for it in raw_items:
            try:
                reconstructed.append(OrderItem.from_dict(it))
            except Exception:
                # Fallback: keep raw dict
                reconstructed.append(it)
        obj.items = reconstructed
        obj.total_amount = float(data.get("total_amount", 0.0))
        obj.payment_method = None
        obj.status = data.get("status", "Pending")
        ts = data.get("timestamp")
        try:
            obj.timestamp = datetime.fromisoformat(ts) if ts else None
        except Exception:
            obj.timestamp = ts
        return obj



class OrderItem:
    """A candy included in an order."""
    
    def __init__(self, candy: Candy, quantity: int):
        self.candy = candy
        self.quantity = quantity
        self.subtotal = candy.price * quantity

    def to_dict(self) -> dict:
        """Serialize the OrderItem. If the original Candy object is not available
        in a reconstructed context, this returns a lightweight representation.
        """
        return {
            "candy_id": getattr(self.candy, "product_id", None),
            "name": getattr(self.candy, "name", None),
            "price": float(getattr(self.candy, "price", 0.0)),
            "quantity": int(self.quantity),
            "subtotal": float(self.subtotal),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OrderItem":
        """Recreate an OrderItem from a dict. This will create a lightweight
        candy stub if a real Candy instance is not available in the scope.
        """
        # If a full Candy object is provided, use it. Otherwise create a stub.
        candy_obj = data.get("candy")
        if candy_obj is None:
            # Create a minimal stub object with required attributes
            class _CandyStub:
                pass

            candy_obj = _CandyStub()
            setattr(candy_obj, "product_id", data.get("candy_id"))
            setattr(candy_obj, "name", data.get("name"))
            setattr(candy_obj, "price", float(data.get("price", 0.0)))

        quantity = int(data.get("quantity", 0))
        return cls(candy_obj, quantity)

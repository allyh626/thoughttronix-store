"""Order placement — one of the codebase's two deliberate deep modules.

The interface is the product: one function that turns a cart and a
validated checkout into an order, all-or-nothing. Callers never touch
``Order`` construction directly.
"""

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction

from accounts.models import Address

from .models import Cart, Coupon, Order, OrderItem

ADDRESS_FIELDS = [
    "email",
    "shipping_name",
    "shipping_street",
    "shipping_line2",
    "shipping_city",
    "shipping_state",
    "shipping_zip",
    "billing_name",
    "billing_street",
    "billing_line2",
    "billing_city",
    "billing_state",
    "billing_zip",
]


@dataclass(frozen=True)
class Quote:
    """What a cart costs right now, with or without a coupon."""

    subtotal: Decimal
    coupon: Coupon | None = None
    discount: Decimal = Decimal("0.00")

    @property
    def total(self) -> Decimal:
        return self.subtotal - self.discount


def quote(cart: Cart, coupon_code: str | None = None) -> Quote:
    """Price the cart, applying ``coupon_code`` if one is given.

    The single source of the coupon math: checkout's Apply button shows
    this quote, and ``place_order`` charges it. A blank code means no
    coupon. Raises ``InvalidCoupon`` (a ``ValidationError`` whose
    message is customer-facing) if the code can't be used on this cart.
    """
    lines = list(cart.lines())
    subtotal = sum((line.line_total for line in lines), Decimal("0.00"))
    if not coupon_code or not coupon_code.strip():
        return Quote(subtotal)
    coupon = Coupon.objects.lookup(coupon_code)
    return Quote(subtotal, coupon, coupon.discount_for(lines))


@transaction.atomic
def place_order(
    cart: Cart,
    user: AbstractBaseUser,
    checkout_data: Mapping[str, Any],
    *,
    coupon_code: str | None = None,
    save_addresses: Collection[Literal["shipping", "billing"]] = (),
) -> Order:
    """Create an order from the cart's contents, then empty the cart.

    ``checkout_data`` is the ``cleaned_data`` of a valid ``CheckoutForm``.
    Addresses and line prices are denormalized onto the order — an order
    is a snapshot, immune to later catalog or address edits. Of the card,
    only the last four digits are stored; the full number and CVV never
    touch the database.

    ``save_addresses`` names the checkout sections the customer asked to
    keep; each is saved to their address book (skipped if they already
    have it). Saving never sets a default and never links the order to
    the saved address — the order keeps its own copy.

    ``coupon_code`` is checked again here, whatever the customer saw on
    Apply — it may have expired since. The order stores the code and the
    amount saved; ``total`` is what the customer pays.

    All-or-nothing: runs in a transaction, so a failure partway through
    leaves no partial order, no saved addresses, and the cart intact.

    Raises ``ValueError`` if the cart is empty or holds a product that is
    no longer available, and ``InvalidCoupon`` if the coupon can't be used.
    """
    lines = list(cart.lines())
    if not lines:
        raise ValueError("Cannot place an order from an empty cart.")
    unavailable = [line.product.name for line in lines if not line.product.is_available]
    if unavailable:
        raise ValueError(
            f"No longer available: {', '.join(unavailable)}. "
            "Remove them from the cart to check out."
        )

    price = quote(cart, coupon_code)
    card_digits = checkout_data["card_number"].replace(" ", "").replace("-", "")
    order = Order.objects.create(
        user=user,
        total=price.total,
        coupon=price.coupon,
        coupon_code=price.coupon.code if price.coupon else "",
        discount_amount=price.discount,
        card_last4=card_digits[-4:],
        **{name: checkout_data[name] for name in ADDRESS_FIELDS},
    )
    for line in lines:
        OrderItem.objects.create(
            order=order,
            product=line.product,
            product_name=line.product.name,
            unit_price=line.product.price,
            quantity=line.quantity,
        )
    for kind in save_addresses:
        Address.objects.save_from_checkout(user, checkout_data, prefix=kind)
    cart.items.all().delete()
    return order

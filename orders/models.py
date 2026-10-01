from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from products.models import Product

CENT = Decimal("0.01")


class Cart(models.Model):
    """A customer's cart — one per user, created lazily on first touch."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
    )

    def __str__(self):
        return f"Cart for {self.user.username}"

    @classmethod
    def for_user(cls, user):
        """Return the user's cart, creating it on first touch."""
        cart, _ = cls.objects.get_or_create(user=user)
        return cart

    def add(self, product):
        """Add a product to the cart; a duplicate add increments its line."""
        item, created = self.items.get_or_create(product=product)
        if not created:
            item.quantity += 1
            item.save()
        return item

    def lines(self):
        """Line items with their products loaded, ready for display."""
        return self.items.select_related("product")

    def total(self):
        return sum((item.line_total for item in self.lines()), Decimal("0.00"))

    def item_count(self):
        """Total units across all lines — the navbar badge number."""
        return self.items.aggregate(count=models.Sum("quantity"))["count"] or 0


class CartItem(models.Model):
    """One product line in a cart; the cart–product pair is unique."""

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product"], name="unique_cart_product"
            )
        ]

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"

    @property
    def line_total(self):
        return self.product.price * self.quantity

    def increment(self):
        self.quantity += 1
        self.save()

    def decrement(self):
        """Step the quantity down, stopping at one — removal is explicit."""
        if self.quantity > 1:
            self.quantity -= 1
            self.save()


class InvalidCoupon(ValidationError):
    """A code that can't be used on this cart; the message is customer-facing."""


def short_date(day):
    """``Dec 1, 2026`` — how promotion dates read in customer messages."""
    return f"{day:%b} {day.day}, {day.year}"


class CouponQuerySet(models.QuerySet):
    def lookup(self, code):
        """The coupon for a typed code — case and surrounding spaces ignored.

        Raises ``InvalidCoupon`` if no coupon has that code.
        """
        try:
            return self.get(code=code.strip().upper())
        except self.model.DoesNotExist:
            raise InvalidCoupon(
                "We don't recognize that code.", code="unknown"
            ) from None


class Coupon(models.Model):
    """A promotion code: a percentage or dollar amount off, for a date window.

    Covers the whole order or a fixed list of products. Codes are stored
    upper-case so lookups ignore case. Orders keep their own copy of the
    code and the amount it saved, so editing or retiring a coupon never
    changes a placed order; a coupon any order used can't be deleted.
    """

    class Kind(models.TextChoices):
        PERCENT = "PERCENT", "Percent off"
        AMOUNT = "AMOUNT", "Dollars off"

    class Scope(models.TextChoices):
        ORDER = "ORDER", "The whole order"
        PRODUCTS = "PRODUCTS", "Selected products only"

    code = models.CharField(
        max_length=30,
        unique=True,
        validators=[
            RegexValidator(
                r"^[A-Za-z0-9-]+$", "Use only letters, numbers, and hyphens."
            )
        ],
        help_text="What customers type, e.g. FALL20. Capitalization doesn't matter.",
    )
    kind = models.CharField(
        "discount type", max_length=7, choices=Kind.choices, default=Kind.PERCENT
    )
    value = models.DecimalField(
        "discount",
        max_digits=10,
        decimal_places=2,
        help_text="A percentage (1–100) or a dollar amount, depending on the type.",
    )
    scope = models.CharField(
        "applies to", max_length=8, choices=Scope.choices, default=Scope.ORDER
    )
    products = models.ManyToManyField(Product, blank=True, related_name="coupons")
    starts_on = models.DateField("first day")
    ends_on = models.DateField("last day")
    is_retired = models.BooleanField(default=False)

    objects = CouponQuerySet.as_manager()

    class Meta:
        ordering = ["-starts_on", "code"]

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    def clean(self):
        errors = {}
        if self.value is not None:
            if self.kind == self.Kind.PERCENT and not 1 <= self.value <= 100:
                errors["value"] = "A percentage must be between 1 and 100."
            elif self.kind == self.Kind.AMOUNT and self.value < CENT:
                errors["value"] = "Enter an amount greater than $0."
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            errors["ends_on"] = "The last day can't be before the first day."
        if errors:
            raise ValidationError(errors)

    @property
    def label(self):
        """``20% off`` or ``$10.00 off``."""
        if self.kind == self.Kind.PERCENT:
            return f"{self.value.normalize():f}% off"
        return f"${self.value} off"

    def status(self, today=None):
        """One of ``retired``, ``scheduled``, ``expired``, or ``live``."""
        today = today or timezone.localdate()
        if self.is_retired:
            return "retired"
        if today < self.starts_on:
            return "scheduled"
        if today > self.ends_on:
            return "expired"
        return "live"

    def retire(self):
        self.is_retired = True
        self.save(update_fields=["is_retired"])

    def reinstate(self):
        self.is_retired = False
        self.save(update_fields=["is_retired"])

    def discount_for(self, lines, today=None):
        """The discount this coupon gives on cart ``lines``, to the cent.

        Raises ``InvalidCoupon`` with the customer-facing reason if the
        code is expired, retired, not started, or covers nothing in the
        lines. The discount never exceeds the subtotal of the lines it
        covers; a dollar amount comes off once per order.
        """
        today = today or timezone.localdate()
        if today > self.ends_on:
            raise InvalidCoupon(
                f"This code expired on {short_date(self.ends_on)}.", code="expired"
            )
        if self.is_retired:
            raise InvalidCoupon("This code is no longer available.", code="retired")
        if today < self.starts_on:
            raise InvalidCoupon(
                f"This code starts on {short_date(self.starts_on)}.",
                code="not_started",
            )

        if self.scope == self.Scope.ORDER:
            covered = list(lines)
        else:
            product_ids = set(self.products.values_list("pk", flat=True))
            covered = [line for line in lines if line.product_id in product_ids]
        covered_total = sum((line.line_total for line in covered), Decimal("0.00"))
        if not covered_total:
            raise InvalidCoupon(
                "This code doesn't apply to anything in your cart.",
                code="nothing_covered",
            )

        if self.kind == self.Kind.PERCENT:
            discount = (covered_total * self.value / 100).quantize(
                CENT, rounding=ROUND_HALF_UP
            )
        else:
            discount = self.value
        return min(discount, covered_total)


class Order(models.Model):
    """A placed order — a snapshot, never a live view of the catalog.

    Addresses are flat denormalized fields: the order must not change if
    the customer later edits anything. Of the card, only the last four
    digits survive checkout. ``total`` is what the customer paid; a
    coupon's code and savings are copied on too, so retiring or editing
    the coupon never changes the order.
    """

    class Status(models.TextChoices):
        PLACED = "PLACED", "Placed"
        SHIPPED = "SHIPPED", "Shipped"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PLACED
    )
    total = models.DecimalField(max_digits=10, decimal_places=2)
    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders",
    )
    coupon_code = models.CharField(max_length=30, blank=True)
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    email = models.EmailField()

    shipping_name = models.CharField(max_length=100)
    shipping_street = models.CharField(max_length=200)
    shipping_line2 = models.CharField(max_length=200, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=2)
    shipping_zip = models.CharField(max_length=10)

    billing_name = models.CharField(max_length=100)
    billing_street = models.CharField(max_length=200)
    billing_line2 = models.CharField(max_length=200, blank=True)
    billing_city = models.CharField(max_length=100)
    billing_state = models.CharField(max_length=2)
    billing_zip = models.CharField(max_length=10)

    card_last4 = models.CharField(max_length=4)

    # default (not auto_now_add) so the seed can backdate orders.
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.number

    @property
    def number(self):
        """The customer-facing order number, e.g. ``TT-2026-00042``."""
        return f"TT-{self.created_at.year}-{self.pk:05d}"

    @property
    def subtotal(self):
        """The price before any coupon."""
        return self.total + self.discount_amount


class OrderItem(models.Model):
    """One line of an order, priced as of purchase time.

    Name and unit price are denormalized: order history must not change
    when the catalog does. The product FK survives for linking while the
    product exists.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=200)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    class Meta:
        ordering = ["pk"]

    def __str__(self):
        return f"{self.quantity} × {self.product_name}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity

from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from orders.models import Order
from products.models import Product


def censor(username: str) -> str:
    """First letter, four stars, last letter — the same length for every
    username, so the stars never reveal how long it is."""
    return f"{username[0]}****{username[-1]}"


class ReviewQuerySet(models.QuerySet):
    # Reviews per page on the product page; "Show more" loads the next page.
    PAGE_SIZE = 5

    def others_than(self, user):
        """Everyone else's reviews, newest first — a signed-in customer's
        own review is pinned on its own, never repeated in the list.

        The pk tie-break keeps pages stable, so "Show more" never skips or
        repeats reviews posted at the same moment.
        """
        others = self.exclude(author=user) if user.is_authenticated else self
        return others.order_by("-created_at", "-pk")

    def rating_summary(self) -> dict:
        """The average rating, rounded half up to one decimal place, and
        the count. The average is ``None`` when there are no reviews."""
        totals = self.aggregate(average=models.Avg("rating"), count=models.Count("pk"))
        if totals["average"] is not None:
            totals["average"] = Decimal(str(totals["average"])).quantize(
                Decimal("0.1"), ROUND_HALF_UP
            )
        return totals

    def can_write(self, user, product) -> bool:
        """Only a customer who has received the product — a Delivered
        order containing it — and hasn't reviewed it yet. Never staff."""
        if user.is_staff:
            return False
        delivered = Order.objects.filter(
            user=user, status=Order.Status.DELIVERED, items__product=product
        ).exists()
        return delivered and not self.filter(author=user, product=product).exists()


class Review(models.Model):
    """One customer's review of one product.

    ``display_name`` is the censored username, saved on create and never
    changed, so a review keeps its public name after ``deactivate()``
    renames the account — the same way orders copy product names.
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=50)
    comment = models.TextField(max_length=1000)
    display_name = models.CharField(max_length=6, editable=False)
    is_flagged = models.BooleanField(default=False)
    # default (not auto_now_add) so the seed can backdate reviews.
    created_at = models.DateTimeField(default=timezone.now)
    edited_at = models.DateTimeField(null=True, blank=True)

    objects = ReviewQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "author"], name="unique_review_product_author"
            )
        ]

    def __str__(self):
        return f"{self.title} ({self.rating}★)"

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.display_name = censor(self.author.username)
        super().save(*args, **kwargs)

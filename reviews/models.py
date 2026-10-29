import re
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone

from orders.models import Order
from products.models import Product


def censor(username: str) -> str:
    """First letter, four stars, last letter — the same length for every
    username, so the stars never reveal how long it is."""
    return f"{username[0]}****{username[-1]}"


# Words that flag a review for staff to look at. Edit the list here; there
# is no back-office screen for it. Matching is by whole word, so each
# variant is listed — that keeps lookalikes such as "scampi" unflagged.
BANNED_WORDS = {
    *("crap", "crappy"),
    *("damn", "damned", "damnit", "dammit"),
    *("idiot", "idiots", "idiotic", "idiocy"),
    *("scam", "scams", "scammed", "scammer", "scammers", "scamming", "scammy"),
    *("stupid", "stupidity", "stupidly"),
}

_BANNED_PATTERN = re.compile(
    r"\b(?:" + "|".join(map(re.escape, sorted(BANNED_WORDS))) + r")\b",
    re.IGNORECASE,
)


def contains_banned_word(text: str) -> bool:
    """Whether the text has a banned word in it, as a whole word, in any
    letter case."""
    return bool(_BANNED_PATTERN.search(text))


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
        return others.with_reported_by(user).order_by("-created_at", "-pk")

    def with_reported_by(self, user):
        """Mark each review ``reported_by_viewer`` — whether this user has
        reported it — so its card shows "Reported" instead of Report."""
        if not user.is_authenticated:
            return self.annotate(reported_by_viewer=models.Value(False))
        return self.annotate(
            reported_by_viewer=models.Exists(
                ReviewReport.objects.filter(review=models.OuterRef("pk"), reporter=user)
            )
        )

    def editable_by(self, user):
        """The reviews this user may edit or delete: staff any of them, a
        customer only their own — anyone else's is out of reach."""
        return self if user.is_staff else self.filter(author=user)

    def for_moderation(self):
        """The back office's order: flagged reviews first, so staff deal
        with problems before anything else, then newest first."""
        return self.order_by("-is_flagged", "-created_at", "-pk")

    def rating_summary(self) -> dict:
        """The average rating, rounded half up to one decimal place, and
        the count. The average is ``None`` when there are no reviews."""
        totals = self.aggregate(average=models.Avg("rating"), count=models.Count("pk"))
        if totals["average"] is not None:
            totals["average"] = Decimal(str(totals["average"])).quantize(
                Decimal("0.1"), ROUND_HALF_UP
            )
        return totals

    @staticmethod
    def _received(user, product) -> bool:
        """Whether the user has a Delivered order containing the product."""
        return Order.objects.filter(
            user=user, status=Order.Status.DELIVERED, items__product=product
        ).exists()

    def can_write(self, user, product) -> bool:
        """Only a customer who has received the product — a Delivered
        order containing it — and hasn't reviewed it yet. Never staff."""
        if user.is_staff:
            return False
        return (
            self._received(user, product)
            and not self.filter(author=user, product=product).exists()
        )

    def prompt_for(self, user, product, reviewed: bool | None = None) -> str | None:
        """What sits above the list: ``"form"`` (an eligible customer),
        ``"sign_in"`` (a signed-out visitor), ``"ineligible"`` (no Delivered
        order of the product), or ``None`` (staff, or already reviewed).

        Pass ``reviewed`` when the caller already knows whether the user has
        a review of the product, to skip looking it up again.
        """
        if not user.is_authenticated:
            return "sign_in"
        if user.is_staff:
            return None
        if reviewed is None:
            reviewed = self.filter(author=user, product=product).exists()
        if reviewed:
            return None
        return "form" if self._received(user, product) else "ineligible"


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
            self._flag_if_banned()
        super().save(*args, **kwargs)

    def save_edit(self, editor):
        """Save a change to the review and mark it edited, which shows the
        "edited" tag. No Delivered order is needed to edit. The author and
        saved display name never change, whoever edits.

        A staff edit clears the flag — staff have fixed the review. The
        author's edit is re-checked for banned words; a clean edit leaves
        an existing flag alone, since only staff clear flags."""
        self.edited_at = timezone.now()
        if editor.is_staff:
            self.is_flagged = False
        else:
            self._flag_if_banned()
        self.save()

    def can_be_reported_by(self, user) -> bool:
        """Only a signed-in customer, never staff, never its author, and
        once per customer, ever."""
        return (
            user.is_authenticated
            and not user.is_staff
            and self.author_id != user.pk
            and not self.reports.filter(reporter=user).exists()
        )

    def flag(self):
        """Put the review on staff's flagged list. Not an edit, so no
        "edited" tag."""
        self.is_flagged = True
        self.save(update_fields=["is_flagged"])

    def clear_flag(self):
        """Staff have checked the review: it leaves the flagged list. Not an
        edit, so no "edited" tag."""
        self.is_flagged = False
        self.save(update_fields=["is_flagged"])

    def _flag_if_banned(self):
        if contains_banned_word(f"{self.title}\n{self.comment}"):
            self.is_flagged = True


class ReviewReport(models.Model):
    """One customer's report of someone else's review, at most once ever —
    even after staff clear the flag it raised."""

    class Reason(models.TextChoices):
        SPAM = "spam", "Spam"
        OFFENSIVE = "offensive", "Offensive language"
        OFF_TOPIC = "off_topic", "Off-topic"
        OTHER = "other", "Other"

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="review_reports",
    )
    reason = models.CharField(max_length=20, choices=Reason)
    note = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["review", "reporter"], name="unique_report_review_reporter"
            )
        ]

    def __str__(self):
        return f"{self.get_reason_display()} report on {self.review}"

    def save(self, *args, **kwargs):
        """Any new report flags the review — even one staff have cleared.
        Both writes happen together or not at all."""
        adding = self._state.adding
        with transaction.atomic():
            super().save(*args, **kwargs)
            if adding:
                self.review.flag()

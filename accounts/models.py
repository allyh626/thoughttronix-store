from collections.abc import Mapping
from typing import Any

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models, transaction

from .validators import US_STATES, zip_validator

# The fields one checkout address section holds, without its prefix:
# ``shipping_city`` and ``billing_city`` both map to ``Address.city``.
ADDRESS_FIELDS = ["name", "street", "line2", "city", "state", "zip"]


class User(AbstractUser):
    """The store's user model.

    Roles use Django's own vocabulary and nothing else: customers are
    plain users, employees are ``is_staff``, the admin is ``is_superuser``.
    """

    # Nullable per the PRD: an absent job title is unknown, not empty.
    job_title = models.CharField(max_length=150, null=True, blank=True)  # noqa: DJ001


class AddressQuerySet(models.QuerySet):
    def default_for(self, kind):
        """The default address of ``kind`` (shipping or billing), or None."""
        return self.filter(**{Address.default_flag(kind): True}).first()


class AddressManager(models.Manager.from_queryset(AddressQuerySet)):
    def save_from_checkout(
        self, user: Any, checkout_data: Mapping[str, Any], *, prefix: str
    ) -> "Address":
        """Save one checkout section to ``user``'s address book.

        ``prefix`` is ``"shipping"`` or ``"billing"``. If the customer
        already has the same address — compared case-insensitively,
        surrounding whitespace ignored, label ignored — nothing is saved
        and the existing address is returned. Never sets a default.
        """
        values = {
            field: str(checkout_data.get(f"{prefix}_{field}", "")).strip()
            for field in ADDRESS_FIELDS
        }
        existing = self.filter(
            user=user, **{f"{field}__iexact": value for field, value in values.items()}
        ).first()
        if existing:
            return existing
        return self.create(user=user, **values)


class Address(models.Model):
    """A saved address in a customer's address book.

    Usable for shipping or billing. Orders never point here — they copy
    the fields onto themselves — so editing or deleting an address never
    changes a placed order. Defaults are two flags, each unique per user,
    set only by the customer via ``make_default``.
    """

    KINDS = ("shipping", "billing")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    label = models.CharField(
        "Label (optional)",
        max_length=50,
        blank=True,
        help_text="A nickname like “Home” or “Work”.",
    )
    name = models.CharField("Full name", max_length=100)
    street = models.CharField("Street address", max_length=200)
    line2 = models.CharField("Apt, suite, etc. (optional)", max_length=200, blank=True)
    city = models.CharField("City", max_length=100)
    state = models.CharField("State", max_length=2, choices=US_STATES)
    zip = models.CharField("ZIP code", max_length=10, validators=[zip_validator])
    is_default_shipping = models.BooleanField(default=False)
    is_default_billing = models.BooleanField(default=False)

    objects = AddressManager()

    class Meta:
        ordering = ["pk"]
        verbose_name_plural = "addresses"
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default_shipping=True),
                name="one_default_shipping_address_per_user",
            ),
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default_billing=True),
                name="one_default_billing_address_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.label or self.name} — {self.street}, {self.city}, {self.state}"

    @staticmethod
    def default_flag(kind):
        """The flag field for ``kind``; rejects anything but the two kinds."""
        if kind not in Address.KINDS:
            raise ValueError(f"Unknown address kind: {kind!r}")
        return f"is_default_{kind}"

    @transaction.atomic
    def make_default(self, kind):
        """Make this the user's default ``kind`` address, replacing any other.

        The old default is unset before this one is set, so the
        one-default-per-user constraint never sees two.
        """
        flag = self.default_flag(kind)
        Address.objects.filter(user=self.user_id, **{flag: True}).exclude(
            pk=self.pk
        ).update(**{flag: False})
        setattr(self, flag, True)
        self.save(update_fields=[flag])

    def as_checkout_initial(self, prefix):
        """This address as checkout form initial data for one section."""
        return {f"{prefix}_{field}": getattr(self, field) for field in ADDRESS_FIELDS}

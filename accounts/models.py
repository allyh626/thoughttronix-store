from collections.abc import Mapping
from typing import Any

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core import signing
from django.core.mail import send_mail
from django.db import models, transaction
from django.template.loader import render_to_string
from django.urls import reverse

from .validators import US_STATES, zip_validator

# The fields one checkout address section holds, without its prefix:
# ``shipping_city`` and ``billing_city`` both map to ``Address.city``.
ADDRESS_FIELDS = ["name", "street", "line2", "city", "state", "zip"]

# Keeps verification tokens from being valid anywhere else Django signs data.
VERIFY_EMAIL_SALT = "accounts.verify-email"


class User(AbstractUser):
    """The store's user model.

    Roles use Django's own vocabulary and nothing else: customers are
    plain users, employees are ``is_staff``, the admin is ``is_superuser``.
    """

    # Nullable per the PRD: an absent job title is unknown, not empty.
    job_title = models.CharField(max_length=150, null=True, blank=True)  # noqa: DJ001
    # Unique but nullable: accounts made before emails were required have
    # none, and NULLs never collide. Stored lowercase (see ``save``), so
    # uniqueness ignores capitalization.
    email = models.EmailField(  # noqa: DJ001
        "email address", unique=True, null=True, blank=True
    )
    email_verified = models.BooleanField(default=False)
    # A new address waiting for its link to be clicked. Until then the
    # current email stays in effect. Not unique: two accounts may both
    # claim an address, and only the first to confirm gets it.
    pending_email = models.EmailField(null=True, blank=True)  # noqa: DJ001

    def save(self, *args, **kwargs):
        # Django's user manager turns a missing email into "", which would
        # collide under the unique rule — store it as NULL instead.
        self.email = self.email.strip().lower() if self.email else None
        self.pending_email = (
            self.pending_email.strip().lower() if self.pending_email else None
        )
        super().save(*args, **kwargs)

    @property
    def email_to_confirm(self) -> str | None:
        """The address a verification link confirms: a pending change if
        there is one, else an unverified current email, else None."""
        if self.pending_email:
            return self.pending_email
        if self.email and not self.email_verified:
            return self.email
        return None

    def email_verification_token(self) -> str:
        """A signed, timestamped token that confirms ``email_to_confirm``.

        It names the address itself, so it stops working once that
        address is verified or replaced.
        """
        return signing.dumps(
            {"user": self.pk, "email": self.email_to_confirm}, salt=VERIFY_EMAIL_SALT
        )

    def send_verification_email(self, request) -> None:
        """Mail a verification link for ``email_to_confirm`` to that address."""
        path = reverse("accounts:verify_email", args=[self.email_verification_token()])
        message = render_to_string(
            "accounts/emails/verify_email.txt",
            {
                "user": self,
                "email": self.email_to_confirm,
                "verify_url": request.build_absolute_uri(path),
            },
        )
        send_mail(
            "Confirm your ThoughtTronix email",
            message,
            None,
            [self.email_to_confirm],
        )

    def send_email_changed_notice(self, old_email: str) -> None:
        """Tell the old address that the account's email has changed."""
        message = render_to_string(
            "accounts/emails/email_changed.txt",
            {"user": self, "old_email": old_email, "new_email": self.email},
        )
        send_mail("Your ThoughtTronix email was changed", message, None, [old_email])

    @classmethod
    def verify_email_token(cls, token: str) -> "User":
        """Confirm the address named in ``token`` and return its user.

        A pending address moves into ``email``, and the old address (if
        any) is told. Raises ``signing.BadSignature`` when the token is
        tampered with or already used (its address is no longer the one
        waiting for confirmation) or its address now belongs to another
        account, and its subclass ``signing.SignatureExpired`` when it is
        older than ``EMAIL_VERIFICATION_TIMEOUT``.
        """
        data = signing.loads(
            token, salt=VERIFY_EMAIL_SALT, max_age=settings.EMAIL_VERIFICATION_TIMEOUT
        )
        user = cls.objects.filter(pk=data["user"]).first()
        if user is None or data["email"] != user.email_to_confirm:
            raise signing.BadSignature("This link has already been used.")
        old_email = None
        if user.pending_email:
            if cls.objects.filter(email=user.pending_email).exists():
                raise signing.BadSignature("This address belongs to another account.")
            old_email, user.email, user.pending_email = (
                user.email,
                user.pending_email,
                None,
            )
        user.email_verified = True
        user.save(update_fields=["email", "pending_email", "email_verified"])
        if old_email:
            user.send_email_changed_notice(old_email)
        return user


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

"""The checkout form — the codebase's showcase of declarative validation.

Every rule is visible at its field declaration, in the style of data
annotations: field types validate (``EmailField``), field arguments
validate (``required``, ``max_length``, ``ChoiceField``), and the
``validators=[...]`` list carries the rest. No ``clean_*`` methods
and no ``clean()`` — none of its current rules need imperative validation.
"""

from django import forms
from django.core.validators import RegexValidator

from accounts.validators import US_STATES, zip_validator
from products.forms import StyledModelForm
from products.models import Category

from .models import Coupon, Order
from .validators import validate_card_number, validate_expiry

cvv_validator = RegexValidator(r"^\d{3,4}$", "Enter the 3- or 4-digit CVV.")


class CheckoutForm(forms.Form):
    """One page, one POST: contact, shipping, billing, payment."""

    email = forms.EmailField(label="Email")

    shipping_name = forms.CharField(label="Full name", max_length=100)
    shipping_street = forms.CharField(label="Street address", max_length=200)
    shipping_line2 = forms.CharField(
        label="Apt, suite, etc. (optional)", max_length=200, required=False
    )
    shipping_city = forms.CharField(label="City", max_length=100)
    shipping_state = forms.ChoiceField(label="State", choices=US_STATES)
    shipping_zip = forms.CharField(
        label="ZIP code", max_length=10, validators=[zip_validator]
    )
    save_shipping_address = forms.BooleanField(
        label="Save this address to my account", required=False
    )

    billing_name = forms.CharField(label="Full name", max_length=100)
    billing_street = forms.CharField(label="Street address", max_length=200)
    billing_line2 = forms.CharField(
        label="Apt, suite, etc. (optional)", max_length=200, required=False
    )
    billing_city = forms.CharField(label="City", max_length=100)
    billing_state = forms.ChoiceField(label="State", choices=US_STATES)
    billing_zip = forms.CharField(
        label="ZIP code", max_length=10, validators=[zip_validator]
    )
    save_billing_address = forms.BooleanField(
        label="Save this address to my account", required=False
    )

    card_number = forms.CharField(
        label="Card number", max_length=23, validators=[validate_card_number]
    )
    card_expiry = forms.CharField(
        label="Expiry (MM/YY)", max_length=5, validators=[validate_expiry]
    )
    card_cvv = forms.CharField(label="CVV", max_length=4, validators=[cvv_validator])

    # The applied coupon, carried from the order summary's Apply button.
    # Whether it can still be used is place_order's call, not the form's.
    coupon_code = forms.CharField(
        max_length=30, required=False, widget=forms.HiddenInput
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.Select):
                widget.attrs["class"] = "select w-full"
            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "checkbox"
            else:
                widget.attrs["class"] = "input w-full"

    # Field groups for the template — the form owns its own structure.

    def address_fields(self, kind):
        """One address section's fields; ``kind`` is shipping or billing."""
        return [self[name] for name in self.fields if name.startswith(f"{kind}_")]

    def shipping_fields(self):
        return self.address_fields("shipping")

    def billing_fields(self):
        return self.address_fields("billing")

    def card_fields(self):
        return [self[name] for name in self.fields if name.startswith("card_")]


class CouponForm(StyledModelForm):
    """The back-office coupon form; the model's ``clean`` checks the numbers.

    Products render as a checklist grouped by category (see
    ``product_groups``), each group with HTMX select-all/clear buttons.
    """

    class Meta:
        model = Coupon
        fields = ["code", "kind", "value", "scope", "products", "starts_on", "ends_on"]
        widgets = {
            "products": forms.CheckboxSelectMultiple,
            "starts_on": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "ends_on": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
        }

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper()

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("scope") == Coupon.Scope.PRODUCTS and not cleaned.get(
            "products"
        ):
            self.add_error("products", "Pick at least one product.")
        elif cleaned.get("scope") == Coupon.Scope.ORDER:
            cleaned["products"] = []  # a whole-order code keeps no list
        return cleaned

    def selected_product_ids(self):
        return {str(pk) for pk in self["products"].value() or []}

    def product_groups(self):
        """``[(category, [(product, checked), ...]), ...]`` for the checklist."""
        selected = self.selected_product_ids()
        return [
            (category, [(p, str(p.pk) in selected) for p in category.products.all()])
            for category in Category.objects.prefetch_related("products")
            if category.products.all()
        ]


class OrderStatusForm(forms.ModelForm):
    """The back-office status dropdown — any of the four states, anytime.

    Guarding the workflow (no un-cancelling, no re-shipping a delivered
    order) is deliberately left as a student exercise.
    """

    class Meta:
        model = Order
        fields = ["status"]
        widgets = {"status": forms.Select(attrs={"class": "select"})}

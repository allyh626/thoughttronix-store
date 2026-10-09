"""Back-office forms for the catalog models.

ModelForms inherit the models' own rules (name required, slug unique);
the explicit ``price`` declaration adds the one rule the model doesn't
carry — the price must be positive. Widgets get their DaisyUI classes
in one shared ``__init__`` loop, as on ``CheckoutForm``.

The product image goes through ``ProductImageField``, so the employee
only ever sees the messages from ``products.validators``.
"""

from decimal import Decimal
from pathlib import Path

from django import forms

from .models import Category, Product, Tag
from .validators import validate_product_image


class ProductImageField(forms.FileField):
    """An image upload checked only by ``validate_product_image``.

    Replaces ``forms.ImageField``, whose own Pillow and extension checks
    would answer first with Django's wording. A file that passes is
    renamed to its detected format's extension (a JPEG sent as ``.png``
    is saved as ``.jpg``).
    """

    default_error_messages = {
        "contradiction": (
            'Please either choose a new image or tick "Remove current image," not both.'
        ),
    }

    def to_python(self, data):
        if data in self.empty_values:
            return None
        extension = validate_product_image(data)
        data.name = f"{Path(data.name).stem}.{extension}"
        return data


class ImageInput(forms.ClearableFileInput):
    """ClearableFileInput's remove-checkbox handling, drawn as a bare input.

    The current-image preview and the "Remove current image" checkbox are
    drawn by ``products/partials/_image_field.html``.
    """

    template_name = "django/forms/widgets/file.html"

    def format_value(self, value):
        return None  # a file input never carries a value


class StyledModelForm(forms.ModelForm):
    """Base form that dresses every widget in DaisyUI classes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "toggle toggle-primary"
            elif isinstance(widget, forms.Textarea):
                widget.attrs["class"] = "textarea w-full"
                widget.attrs.setdefault("rows", 6)
            elif isinstance(widget, forms.SelectMultiple):
                widget.attrs["class"] = "select h-auto w-full"
                widget.attrs.setdefault("size", 8)
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "select w-full"
            elif isinstance(widget, forms.FileInput):
                widget.attrs["class"] = "file-input w-full"
            else:
                widget.attrs["class"] = "input w-full"


class ProductForm(StyledModelForm):
    price = forms.DecimalField(
        label="Price (USD)",
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )

    class Meta:
        model = Product
        fields = [
            "name",
            "slug",
            "tagline",
            "description",
            "price",
            "category",
            "tags",
            "image",
            "is_available",
        ]
        field_classes = {"image": ProductImageField}
        widgets = {
            "image": ImageInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        }


class CategoryForm(StyledModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug"]


class TagForm(StyledModelForm):
    class Meta:
        model = Tag
        fields = ["name", "slug"]

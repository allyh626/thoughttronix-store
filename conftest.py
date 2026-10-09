"""Project-wide pytest fixtures.

Shared test data lives here as plain fixtures — no factories. The suite
grows with the project.
"""

import io
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from PIL import Image

from accounts.models import Address
from orders.models import Cart, CartItem
from products.models import Category, Product, Tag


@pytest.fixture
def customer(db):
    return get_user_model().objects.create_user(
        username="customer", password="customer123"
    )


@pytest.fixture
def other_customer(db):
    return get_user_model().objects.create_user(
        username="someone-else", password="someone123"
    )


@pytest.fixture
def staff_user(db):
    return get_user_model().objects.create_user(
        username="employee",
        password="employee123",
        is_staff=True,
        job_title="Junior Thought Curator",
    )


@pytest.fixture
def category(db):
    return Category.objects.create(name="Home Assistants", slug="home-assistants")


@pytest.fixture
def product(category):
    return Product.objects.create(
        name="Seraphine Home Hub",
        slug="seraphine-home-hub",
        tagline="She's always listening. In a good way.",
        description="The flagship Seraphine hub with a seven-microphone array.",
        price=Decimal("349.99"),
        category=category,
    )


@pytest.fixture
def media_root(settings, tmp_path):
    """Uploads go to a throwaway folder; use in every test that writes files."""
    settings.MEDIA_ROOT = tmp_path / "media"
    return settings.MEDIA_ROOT


@pytest.fixture
def product_with_image(product, media_root):
    """The product with a small PNG saved as products/seraphine-home-hub.png."""
    buffer = io.BytesIO()
    Image.new("RGB", (40, 30), "purple").save(buffer, "PNG")
    product.image.save("seraphine-home-hub.png", ContentFile(buffer.getvalue()))
    return product


@pytest.fixture
def unavailable_product(category):
    return Product.objects.create(
        name="EchoPatch",
        slug="echopatch",
        tagline="Never miss a word. Anyone's.",
        price=Decimal("139.00"),
        is_available=False,
        category=category,
    )


@pytest.fixture
def tag(db):
    return Tag.objects.create(name="bestseller", slug="bestseller")


@pytest.fixture
def cart(customer):
    return Cart.for_user(customer)


@pytest.fixture
def cart_item(cart, product):
    return CartItem.objects.create(cart=cart, product=product, quantity=2)


@pytest.fixture
def address(customer):
    """The customer's saved home address — not a default."""
    return Address.objects.create(
        user=customer,
        label="Home",
        name="Casey Monroe",
        street="12 Cortex Lane",
        line2="Unit 7",
        city="Canyon",
        state="TX",
        zip="79015",
    )


@pytest.fixture
def other_address(other_customer):
    """An address in someone else's book — never reachable by customer."""
    return Address.objects.create(
        user=other_customer,
        name="Sam Elsewhere",
        street="9 Axon Avenue",
        city="Norman",
        state="OK",
        zip="73019",
    )

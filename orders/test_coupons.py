"""Discount codes: the math, the five customer messages, checkout's Apply
button and final re-check, orders as snapshots, and the back office."""

from datetime import timedelta
from decimal import Decimal
from http import HTTPStatus
from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from products.models import Product

from .models import Coupon, InvalidCoupon, Order
from .services import place_order, quote
from .test_checkout_form import VALID_DATA

pytestmark = pytest.mark.django_db

TODAY = timezone.localdate


def make_coupon(code="FALL20", *, products=(), **fields):
    """A live, whole-order 20% coupon unless told otherwise."""
    defaults = {
        "kind": Coupon.Kind.PERCENT,
        "value": Decimal("20"),
        "scope": Coupon.Scope.PRODUCTS if products else Coupon.Scope.ORDER,
        "starts_on": TODAY() - timedelta(days=1),
        "ends_on": TODAY() + timedelta(days=1),
    }
    coupon = Coupon.objects.create(code=code, **{**defaults, **fields})
    coupon.products.set(products)
    return coupon


def line(price, quantity=1, product_id=None):
    """A stand-in cart line: all ``discount_for`` reads."""
    return SimpleNamespace(product_id=product_id, line_total=Decimal(price) * quantity)


@pytest.fixture
def pillow(category):
    return Product.objects.create(
        name="Charging Pillow",
        slug="charging-pillow",
        price=Decimal("69.00"),
        category=category,
    )


@pytest.fixture
def mixed_cart(cart, cart_item, pillow):
    """2 × Seraphine at $349.99 plus 1 × Charging Pillow at $69.00."""
    cart.add(pillow)
    return cart


# --- The math -------------------------------------------------------------------


def test_percent_off_the_whole_order_rounds_to_the_cent(cart, cart_item):
    make_coupon(value=Decimal("20"))

    price = quote(cart, "FALL20")

    assert price.subtotal == Decimal("699.98")
    assert price.discount == Decimal("140.00")  # 139.996, rounded
    assert price.total == Decimal("559.98")


def test_half_a_cent_rounds_up():
    coupon = Coupon(
        kind=Coupon.Kind.PERCENT,
        value=Decimal("10"),
        starts_on=TODAY(),
        ends_on=TODAY(),
    )

    assert coupon.discount_for([line("0.25")]) == Decimal("0.03")  # 0.025


def test_dollars_off_come_off_once_per_order():
    coupon = Coupon(
        kind=Coupon.Kind.AMOUNT,
        value=Decimal("10.00"),
        starts_on=TODAY(),
        ends_on=TODAY(),
    )

    assert coupon.discount_for([line("50.00", quantity=3)]) == Decimal("10.00")


def test_a_discount_never_exceeds_what_it_covers(cart, cart_item):
    make_coupon("BIG", kind=Coupon.Kind.AMOUNT, value=Decimal("5000"))

    price = quote(cart, "BIG")

    assert price.discount == Decimal("699.98")
    assert price.total == Decimal("0.00")


def test_a_product_code_discounts_only_its_products(mixed_cart, pillow):
    make_coupon("PILLOW50", value=Decimal("50"), products=[pillow])

    price = quote(mixed_cart, "PILLOW50")

    assert price.discount == Decimal("34.50")  # half the pillow only


def test_a_product_dollar_code_is_capped_at_its_products(mixed_cart, pillow):
    make_coupon(
        "PILLOW100", kind=Coupon.Kind.AMOUNT, value=Decimal("100"), products=[pillow]
    )

    assert quote(mixed_cart, "PILLOW100").discount == Decimal("69.00")


# --- The five messages ----------------------------------------------------------


def test_codes_ignore_case_and_spaces(cart, cart_item):
    make_coupon()

    assert quote(cart, "  fall20 ").coupon.code == "FALL20"


def test_unknown_code(cart, cart_item):
    with pytest.raises(InvalidCoupon, match="We don't recognize that code."):
        quote(cart, "NOPE")


def test_expired_code_names_its_last_day(cart, cart_item):
    ended = TODAY() - timedelta(days=1)
    make_coupon(starts_on=ended - timedelta(days=30), ends_on=ended)

    with pytest.raises(InvalidCoupon) as excinfo:
        quote(cart, "FALL20")

    message = excinfo.value.message
    assert message.startswith("This code expired on ")
    assert f"{ended.day}, {ended.year}" in message


def test_a_code_works_through_the_end_of_its_last_day(cart, cart_item):
    make_coupon(ends_on=TODAY())

    assert quote(cart, "FALL20").discount > 0


def test_code_not_started_yet(cart, cart_item):
    starts = TODAY() + timedelta(days=3)
    make_coupon(starts_on=starts, ends_on=starts + timedelta(days=3))

    with pytest.raises(InvalidCoupon, match="This code starts on "):
        quote(cart, "FALL20")


def test_retired_code_is_no_longer_available(cart, cart_item):
    make_coupon().retire()

    with pytest.raises(InvalidCoupon, match="This code is no longer available."):
        quote(cart, "FALL20")


def test_an_expired_and_retired_code_says_expired(cart, cart_item):
    ended = TODAY() - timedelta(days=1)
    make_coupon(starts_on=ended, ends_on=ended, is_retired=True)

    with pytest.raises(InvalidCoupon, match="expired"):
        quote(cart, "FALL20")


def test_code_that_covers_nothing_in_the_cart(cart, cart_item, pillow):
    make_coupon(products=[pillow])

    with pytest.raises(
        InvalidCoupon, match="This code doesn't apply to anything in your cart."
    ):
        quote(cart, "FALL20")


# --- Coupon rules -------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "value", "field"),
    [
        (Coupon.Kind.PERCENT, "0", "value"),
        (Coupon.Kind.PERCENT, "101", "value"),
        (Coupon.Kind.AMOUNT, "0", "value"),
    ],
)
def test_discount_values_must_make_sense(kind, value, field):
    coupon = Coupon(
        code="X", kind=kind, value=Decimal(value), starts_on=TODAY(), ends_on=TODAY()
    )

    with pytest.raises(ValidationError) as excinfo:
        coupon.full_clean()

    assert field in excinfo.value.message_dict


def test_the_last_day_cannot_precede_the_first():
    coupon = Coupon(
        code="X",
        kind=Coupon.Kind.PERCENT,
        value=Decimal("10"),
        starts_on=TODAY(),
        ends_on=TODAY() - timedelta(days=1),
    )

    with pytest.raises(ValidationError) as excinfo:
        coupon.full_clean()

    assert "ends_on" in excinfo.value.message_dict


@pytest.mark.parametrize(
    ("start", "end", "retired", "status"),
    [
        (-1, 1, False, "live"),
        (2, 4, False, "scheduled"),
        (-4, -2, False, "expired"),
        (-1, 1, True, "retired"),
    ],
)
def test_status(start, end, retired, status):
    coupon = make_coupon(
        starts_on=TODAY() + timedelta(days=start),
        ends_on=TODAY() + timedelta(days=end),
        is_retired=retired,
    )

    assert coupon.status() == status


# --- place_order and the snapshot rule ------------------------------------------


def test_the_order_keeps_the_code_and_the_savings(cart, cart_item):
    coupon = make_coupon()

    order = place_order(cart, cart.user, VALID_DATA, coupon_code="fall20")

    assert order.coupon == coupon
    assert order.coupon_code == "FALL20"
    assert order.discount_amount == Decimal("140.00")
    assert order.total == Decimal("559.98")
    assert order.subtotal == Decimal("699.98")


def test_retiring_or_editing_a_coupon_never_changes_an_order(cart, cart_item):
    coupon = make_coupon()
    order = place_order(cart, cart.user, VALID_DATA, coupon_code="FALL20")

    coupon.retire()
    coupon.value = Decimal("90")
    coupon.code = "RENAMED"
    coupon.save()

    order.refresh_from_db()
    assert order.coupon_code == "FALL20"
    assert order.discount_amount == Decimal("140.00")
    assert order.total == Decimal("559.98")


def test_an_expired_coupon_places_no_order(cart, cart_item):
    ended = TODAY() - timedelta(days=1)
    make_coupon(starts_on=ended, ends_on=ended)

    with pytest.raises(InvalidCoupon):
        place_order(cart, cart.user, VALID_DATA, coupon_code="FALL20")

    assert not Order.objects.exists()
    assert cart.items.exists()


def test_old_orders_read_as_undiscounted(customer):
    order = Order.objects.create(user=customer, total=Decimal("9.00"))

    assert order.discount_amount == Decimal("0.00")
    assert order.subtotal == Decimal("9.00")


# --- Checkout: the Apply button -------------------------------------------------


def apply(client, code, applied=""):
    return client.post(
        reverse("orders:checkout_coupon"), {"coupon_code": code, "applied": applied}
    )


def test_apply_shows_the_discount_and_carries_the_code(client, customer, cart_item):
    make_coupon()
    client.force_login(customer)

    response = apply(client, "fall20")

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "<html" not in page  # a partial, never base.html
    assert "−$140.00" in page
    assert 'name="coupon_code" value="FALL20" form="checkout-form"' in page
    assert 'id="place-order-total" hx-swap-oob="true">$559.98' in page


@pytest.mark.parametrize(
    ("setup", "message"),
    [
        ({}, "We don&#x27;t recognize that code."),
        ({"ends_on": -1, "starts_on": -5}, "This code expired on"),
        ({"starts_on": 3, "ends_on": 5}, "This code starts on"),
        ({"is_retired": True}, "This code is no longer available."),
    ],
)
def test_apply_explains_a_bad_code_in_the_summary(
    client, customer, cart_item, setup, message
):
    if setup:
        dates = {
            k: TODAY() + timedelta(days=v)
            for k, v in setup.items()
            if k != "is_retired"
        }
        make_coupon("TRYME", is_retired=setup.get("is_retired", False), **dates)
    client.force_login(customer)

    response = apply(client, "TRYME")

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert message in page
    assert 'form="checkout-form"' not in page  # nothing applied
    assert "$699.98" in page


def test_apply_says_when_a_code_covers_nothing(client, customer, cart_item, pillow):
    make_coupon(products=[pillow])
    client.force_login(customer)

    page = apply(client, "FALL20").content.decode()

    assert "apply to anything in your cart" in page


def test_a_bad_new_code_keeps_the_applied_one(client, customer, cart_item):
    make_coupon()
    client.force_login(customer)

    page = apply(client, "NOPE", applied="FALL20").content.decode()

    assert "recognize that code" in page
    assert 'name="coupon_code" value="FALL20" form="checkout-form"' in page


def test_a_second_code_replaces_the_first(client, customer, cart_item):
    make_coupon()
    make_coupon("TENOFF", kind=Coupon.Kind.AMOUNT, value=Decimal("10"))
    client.force_login(customer)

    page = apply(client, "TENOFF", applied="FALL20").content.decode()

    assert "TENOFF replaced FALL20" in page
    assert 'value="TENOFF" form="checkout-form"' in page


def test_a_blank_code_removes_the_coupon(client, customer, cart_item):
    make_coupon()
    client.force_login(customer)

    page = apply(client, "", applied="FALL20").content.decode()

    assert 'form="checkout-form"' not in page
    assert "recognize" not in page


def test_apply_requires_login(client):
    response = apply(client, "FALL20")

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url


# --- Checkout: placing the order ------------------------------------------------


def test_checkout_page_has_the_discount_box(client, customer, cart_item):
    client.force_login(customer)

    page = client.get(reverse("orders:checkout")).content.decode()

    assert "Have a discount code?" in page
    assert 'id="place-order-total">$699.98' in page


def test_checkout_places_a_discounted_order(client, customer, cart_item):
    make_coupon()
    client.force_login(customer)

    response = client.post(
        reverse("orders:checkout"), {**VALID_DATA, "coupon_code": "FALL20"}
    )

    order = Order.objects.get()
    assert response.status_code == HTTPStatus.FOUND
    assert order.total == Decimal("559.98")
    confirmation = client.get(response.url).content.decode()
    assert "FALL20 saved you $140.00" in confirmation


def test_a_code_that_expires_before_place_order_is_explained(
    client, customer, cart, cart_item
):
    """Applied while live, then the promotion ends before the click."""
    coupon = make_coupon()
    client.force_login(customer)
    apply(client, "FALL20")
    coupon.ends_on = coupon.starts_on = TODAY() - timedelta(days=1)
    coupon.save()

    response = client.post(
        reverse("orders:checkout"), {**VALID_DATA, "coupon_code": "FALL20"}
    )

    assert response.status_code == HTTPStatus.OK  # the page, not an error
    page = response.content.decode()
    assert "This code expired on" in page
    assert 'id="place-order-total">$699.98' in page  # the new, honest total
    assert not Order.objects.exists()
    assert cart.items.exists()


def test_order_pages_show_the_discount(client, customer, cart, cart_item, staff_user):
    make_coupon()
    order = place_order(cart, customer, VALID_DATA, coupon_code="FALL20")

    client.force_login(customer)
    page = client.get(reverse("orders:detail", args=[order.pk])).content.decode()
    assert "FALL20" in page and "−$140.00" in page and "$699.98" in page

    client.force_login(staff_user)
    page = client.get(
        reverse("orders:manage_order_detail", args=[order.pk])
    ).content.decode()
    assert "FALL20" in page and "−$140.00" in page


# --- The back office ------------------------------------------------------------


def coupon_urls(coupon, category):
    return [
        reverse("orders:manage_coupons"),
        reverse("orders:manage_coupon_create"),
        reverse("orders:manage_coupon_update", args=[coupon.pk]),
        reverse("orders:manage_coupon_retire", args=[coupon.pk]),
        reverse("orders:manage_coupon_delete", args=[coupon.pk]),
        reverse("orders:coupon_product_group", args=[category.pk]),
    ]


def test_anonymous_users_are_sent_to_login(client, category):
    for url in coupon_urls(make_coupon(), category):
        response = client.get(url)

        assert response.status_code == HTTPStatus.FOUND, url
        assert reverse("accounts:login") in response.url


def test_customers_get_403(client, customer, category):
    client.force_login(customer)

    for url in coupon_urls(make_coupon(), category):
        assert client.get(url).status_code == HTTPStatus.FORBIDDEN, url


def test_list_has_a_designed_empty_state(client, staff_user):
    client.force_login(staff_user)

    page = client.get(reverse("orders:manage_coupons")).content.decode()

    assert "No coupons yet" in page


def test_list_shows_status_and_filters(client, staff_user):
    make_coupon("LIVE1")
    make_coupon("GONE1", is_retired=True)
    client.force_login(staff_user)

    page = client.get(reverse("orders:manage_coupons")).content.decode()
    assert "LIVE1" in page and "GONE1" in page
    assert "Live" in page and "Retired" in page

    page = client.get(
        reverse("orders:manage_coupons"), {"show": "retired"}
    ).content.decode()
    assert "GONE1" in page and "LIVE1" not in page


def coupon_form_data(**overrides):
    return {
        "code": "winter15",
        "kind": "PERCENT",
        "value": "15",
        "scope": "ORDER",
        "starts_on": TODAY().isoformat(),
        "ends_on": (TODAY() + timedelta(days=7)).isoformat(),
        **overrides,
    }


def test_staff_create_a_coupon(client, staff_user):
    client.force_login(staff_user)

    response = client.post(
        reverse("orders:manage_coupon_create"), coupon_form_data(), follow=True
    )

    assert Coupon.objects.get().code == "WINTER15"
    assert "WINTER15 created." in response.content.decode()


def test_codes_are_unique_whatever_the_case(client, staff_user):
    make_coupon("WINTER15")
    client.force_login(staff_user)

    response = client.post(reverse("orders:manage_coupon_create"), coupon_form_data())

    assert response.status_code == HTTPStatus.OK
    assert "code" in response.context["form"].errors
    assert Coupon.objects.count() == 1


def test_a_product_code_needs_products(client, staff_user):
    client.force_login(staff_user)

    response = client.post(
        reverse("orders:manage_coupon_create"), coupon_form_data(scope="PRODUCTS")
    )

    assert "Pick at least one product." in response.content.decode()
    assert not Coupon.objects.exists()


def test_a_product_code_saves_its_products(client, staff_user, product):
    client.force_login(staff_user)

    client.post(
        reverse("orders:manage_coupon_create"),
        coupon_form_data(scope="PRODUCTS", products=[product.pk]),
    )

    assert list(Coupon.objects.get().products.all()) == [product]


def test_the_form_groups_products_by_category(client, staff_user, product):
    client.force_login(staff_user)

    page = client.get(reverse("orders:manage_coupon_create")).content.decode()

    assert "Home Assistants" in page
    assert "Select all" in page
    assert f'value="{product.pk}"' in page


def test_select_all_ticks_the_whole_category(client, staff_user, product, category):
    client.force_login(staff_user)

    page = client.get(
        reverse("orders:coupon_product_group", args=[category.pk]), {"checked": "1"}
    ).content.decode()

    assert "<html" not in page
    assert f'value="{product.pk}"' in page
    assert "checked" in page


def test_retire_and_reactivate(client, staff_user):
    coupon = make_coupon()
    client.force_login(staff_user)
    url = reverse("orders:manage_coupon_retire", args=[coupon.pk])

    client.post(url)
    coupon.refresh_from_db()
    assert coupon.is_retired

    client.post(url)
    coupon.refresh_from_db()
    assert not coupon.is_retired


def test_an_unused_coupon_can_be_deleted(client, staff_user):
    coupon = make_coupon()
    client.force_login(staff_user)

    client.post(reverse("orders:manage_coupon_delete", args=[coupon.pk]))

    assert not Coupon.objects.exists()


def test_a_used_coupon_cannot_be_deleted(client, staff_user, cart, cart_item):
    coupon = make_coupon()
    order = place_order(cart, cart.user, VALID_DATA, coupon_code="FALL20")
    client.force_login(staff_user)

    response = client.post(
        reverse("orders:manage_coupon_delete", args=[coupon.pk]), follow=True
    )

    assert "can&#x27;t be deleted" in response.content.decode()
    assert Coupon.objects.filter(pk=coupon.pk).exists()
    order.refresh_from_db()
    assert order.coupon == coupon

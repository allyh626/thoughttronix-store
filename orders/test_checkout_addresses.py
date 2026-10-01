"""Checkout meets the address book: default pre-fill, the HTMX fill
endpoint, "Save this address", and the order-as-snapshot rule."""

from http import HTTPStatus

import pytest
from django.urls import reverse

from .models import Order
from .services import place_order
from .test_checkout_form import VALID_DATA

# --- Pre-fill and the picker ----------------------------------------------------


def test_checkout_opens_blank_without_defaults(client, customer, cart_item, address):
    client.force_login(customer)

    response = client.get(reverse("orders:checkout"))

    assert response.context["form"].initial == {}


def test_checkout_prefills_each_section_from_its_default(
    client, customer, cart_item, address
):
    address.make_default("billing")
    client.force_login(customer)

    response = client.get(reverse("orders:checkout"))

    initial = response.context["form"].initial
    assert initial["billing_street"] == "12 Cortex Lane"
    assert "shipping_street" not in initial  # no default shipping: blank
    assert 'value="12 Cortex Lane"' in response.content.decode()


def test_no_picker_with_an_empty_address_book(client, customer, cart_item):
    client.force_login(customer)

    page = client.get(reverse("orders:checkout")).content.decode()

    assert "Use a saved address" not in page
    assert "Save this address to my account" in page


def test_the_picker_lists_only_my_addresses(
    client, customer, cart_item, address, other_address
):
    client.force_login(customer)

    page = client.get(reverse("orders:checkout")).content.decode()

    assert "Use a saved address" in page
    assert "— New address —" in page
    assert str(address) in page
    assert str(other_address) not in page


# --- The HTMX fill endpoint -----------------------------------------------------


def fill_url(kind):
    return reverse("orders:checkout_address_fields", args=[kind])


def test_fill_returns_the_section_prefilled(client, customer, address):
    client.force_login(customer)

    response = client.get(fill_url("shipping"), {"address": address.pk})

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert 'name="shipping_street"' in page
    assert 'value="12 Cortex Lane"' in page
    assert "<html" not in page  # a partial, never base.html


def test_fill_uses_the_requested_section(client, customer, address):
    client.force_login(customer)

    page = client.get(fill_url("billing"), {"address": address.pk}).content.decode()

    assert 'name="billing_street"' in page
    assert 'name="shipping_street"' not in page


def test_new_address_returns_blank_fields(client, customer, address):
    client.force_login(customer)

    page = client.get(fill_url("shipping"), {"address": ""}).content.decode()

    assert 'name="shipping_street"' in page
    assert "12 Cortex Lane" not in page


def test_fill_404s_for_another_customers_address(client, customer, other_address):
    client.force_login(customer)

    response = client.get(fill_url("shipping"), {"address": other_address.pk})

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize(
    ("kind", "pk"), [("gift", ""), ("shipping", "abc"), ("shipping", "99999")]
)
def test_fill_404s_for_nonsense(client, customer, kind, pk):
    client.force_login(customer)

    response = client.get(fill_url(kind), {"address": pk})

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_fill_requires_login(client, address):
    response = client.get(fill_url("shipping"), {"address": address.pk})

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url


# --- Saving at checkout ---------------------------------------------------------


def test_checkout_saves_nothing_unless_asked(client, customer, cart_item):
    client.force_login(customer)

    client.post(reverse("orders:checkout"), VALID_DATA)

    assert Order.objects.exists()
    assert not customer.addresses.exists()


def test_checkout_saves_a_ticked_section(client, customer, cart_item):
    client.force_login(customer)

    client.post(
        reverse("orders:checkout"), {**VALID_DATA, "save_billing_address": "on"}
    )

    saved = customer.addresses.get()
    assert saved.zip == "79015-1234"  # the billing section, not shipping
    assert not saved.is_default_billing  # saving never sets a default


def test_identical_sections_ticked_together_save_once(client, customer, cart_item):
    same = {
        **VALID_DATA,
        "billing_line2": VALID_DATA["shipping_line2"],
        "billing_zip": VALID_DATA["shipping_zip"],
        "save_shipping_address": "on",
        "save_billing_address": "on",
    }
    client.force_login(customer)

    client.post(reverse("orders:checkout"), same)

    assert customer.addresses.count() == 1


def test_an_invalid_checkout_saves_nothing(client, customer, cart_item):
    client.force_login(customer)

    client.post(
        reverse("orders:checkout"),
        {**VALID_DATA, "card_cvv": "x", "save_shipping_address": "on"},
    )

    assert not customer.addresses.exists()


# --- place_order and save_addresses --------------------------------------------


def test_place_order_saves_the_named_sections(cart, cart_item):
    place_order(cart, cart.user, VALID_DATA, save_addresses=["shipping"])

    assert cart.user.addresses.get().street == "12 Cortex Lane"


def test_a_failed_order_saves_no_addresses(cart):
    with pytest.raises(ValueError):
        place_order(cart, cart.user, VALID_DATA, save_addresses=["shipping"])

    assert not cart.user.addresses.exists()


def test_saving_does_not_change_the_order(cart, cart_item):
    order = place_order(
        cart, cart.user, VALID_DATA, save_addresses=["shipping", "billing"]
    )

    assert order.shipping_street == "12 Cortex Lane"
    assert order.billing_zip == "79015-1234"


# --- Orders are snapshots -------------------------------------------------------


def test_editing_a_saved_address_never_changes_a_placed_order(
    client, customer, cart, cart_item, address
):
    order = place_order(cart, customer, VALID_DATA)
    client.force_login(customer)

    client.post(
        reverse("accounts:address_update", args=[address.pk]),
        {
            "label": "Home",
            "name": "Casey Monroe",
            "street": "1 Brand New Road",
            "line2": "",
            "city": "Austin",
            "state": "TX",
            "zip": "78701",
        },
    )

    order.refresh_from_db()
    assert order.shipping_street == "12 Cortex Lane"
    assert order.shipping_city == "Canyon"


def test_deleting_a_saved_address_never_changes_a_placed_order(
    client, customer, cart, cart_item, address
):
    order = place_order(cart, customer, VALID_DATA)
    client.force_login(customer)

    client.post(reverse("accounts:address_delete", args=[address.pk]))

    order.refresh_from_db()
    assert order.shipping_street == "12 Cortex Lane"

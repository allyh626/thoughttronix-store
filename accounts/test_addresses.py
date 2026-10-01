"""The address book: the model, its defaults and duplicate rule, and the
My account pages — always scoped to the owner."""

from http import HTTPStatus

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from .models import Address

CHECKOUT_SHIPPING = {
    "shipping_name": "Casey Monroe",
    "shipping_street": "12 Cortex Lane",
    "shipping_line2": "Unit 7",
    "shipping_city": "Canyon",
    "shipping_state": "TX",
    "shipping_zip": "79015",
}

FORM_DATA = {
    "label": "Work",
    "name": "Casey Monroe",
    "street": "77 Cortex Lane",
    "line2": "",
    "city": "Amarillo",
    "state": "TX",
    "zip": "79101",
}


# --- The model ----------------------------------------------------------------


def test_str_leads_with_the_label(address):
    assert str(address) == "Home — 12 Cortex Lane, Canyon, TX"


def test_str_falls_back_to_the_name(address):
    address.label = ""

    assert str(address) == "Casey Monroe — 12 Cortex Lane, Canyon, TX"


def test_as_checkout_initial_maps_onto_one_section(address):
    assert address.as_checkout_initial("billing") == {
        "billing_name": "Casey Monroe",
        "billing_street": "12 Cortex Lane",
        "billing_line2": "Unit 7",
        "billing_city": "Canyon",
        "billing_state": "TX",
        "billing_zip": "79015",
    }


# --- Defaults -----------------------------------------------------------------


def test_a_new_address_is_never_a_default(address):
    assert not address.is_default_shipping
    assert not address.is_default_billing


def test_make_default_moves_the_flag(customer, address):
    work = Address.objects.create(
        user=customer,
        name="Casey",
        street="1 Way",
        city="Canyon",
        state="TX",
        zip="79015",
    )
    address.make_default("shipping")

    work.make_default("shipping")

    address.refresh_from_db()
    assert not address.is_default_shipping
    assert customer.addresses.default_for("shipping") == work
    assert customer.addresses.filter(is_default_shipping=True).count() == 1


def test_make_default_is_per_kind(customer, address):
    address.make_default("billing")

    assert customer.addresses.default_for("billing") == address
    assert customer.addresses.default_for("shipping") is None


def test_make_default_rejects_unknown_kinds(address):
    with pytest.raises(ValueError):
        address.make_default("gift")


def test_the_database_refuses_two_defaults(customer, address):
    address.make_default("shipping")

    with pytest.raises(IntegrityError), transaction.atomic():
        Address.objects.create(
            user=customer,
            name="Casey",
            street="1 Way",
            city="Canyon",
            state="TX",
            zip="79015",
            is_default_shipping=True,
        )


def test_defaults_are_per_customer(address, other_address):
    address.make_default("shipping")
    other_address.make_default("shipping")

    assert address.user.addresses.default_for("shipping") == address


def test_deleting_a_default_leaves_no_default(customer, address):
    other = Address.objects.create(
        user=customer,
        name="Casey",
        street="1 Way",
        city="Canyon",
        state="TX",
        zip="79015",
    )
    address.make_default("shipping")

    address.delete()

    assert customer.addresses.default_for("shipping") is None
    other.refresh_from_db()
    assert not other.is_default_shipping  # nothing is promoted


# --- Saving from checkout -----------------------------------------------------


def test_save_from_checkout_creates_an_address(customer):
    saved = Address.objects.save_from_checkout(
        customer, CHECKOUT_SHIPPING, prefix="shipping"
    )

    assert saved.user == customer
    assert saved.street == "12 Cortex Lane"
    assert saved.label == ""
    assert not saved.is_default_shipping  # the first address is not promoted


def test_saving_an_existing_address_is_a_no_op(customer, address):
    saved = Address.objects.save_from_checkout(
        customer, CHECKOUT_SHIPPING, prefix="shipping"
    )

    assert saved == address
    assert customer.addresses.count() == 1


def test_duplicates_ignore_case_and_surrounding_whitespace(customer, address):
    shouting = {
        key: f"  {value.upper()} " if key != "shipping_state" else value
        for key, value in CHECKOUT_SHIPPING.items()
    }

    Address.objects.save_from_checkout(customer, shouting, prefix="shipping")

    assert customer.addresses.count() == 1


def test_a_different_address_is_saved(customer, address):
    Address.objects.save_from_checkout(
        customer, {**CHECKOUT_SHIPPING, "shipping_line2": "Unit 8"}, prefix="shipping"
    )

    assert customer.addresses.count() == 2


def test_another_customers_identical_address_is_not_a_duplicate(
    other_customer, address
):
    Address.objects.save_from_checkout(
        other_customer, CHECKOUT_SHIPPING, prefix="shipping"
    )

    assert other_customer.addresses.count() == 1


# --- My account ---------------------------------------------------------------


def test_my_account_requires_login(client, db):
    response = client.get(reverse("accounts:account"))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url


def test_my_account_has_a_designed_empty_state(client, customer):
    client.force_login(customer)

    page = client.get(reverse("accounts:account")).content.decode()

    assert "No saved addresses yet" in page
    assert "customer" in page


def test_my_account_lists_only_my_addresses(client, customer, address, other_address):
    client.force_login(customer)

    response = client.get(reverse("accounts:account"))

    assert list(response.context["addresses"]) == [address]
    page = response.content.decode()
    assert "12 Cortex Lane" in page
    assert "9 Axon Avenue" not in page


def test_my_account_shows_default_badges(client, customer, address):
    address.make_default("billing")
    client.force_login(customer)

    page = client.get(reverse("accounts:account")).content.decode()

    assert "Default billing" in page
    assert "Default shipping" not in page


def test_navbar_links_to_my_account(client, customer):
    client.force_login(customer)

    page = client.get(reverse("products:catalog")).content.decode()

    assert reverse("accounts:account") in page


# --- Add and edit ---------------------------------------------------------------


def test_add_address_page_returns_200(client, customer):
    client.force_login(customer)

    response = client.get(reverse("accounts:address_create"))

    assert response.status_code == HTTPStatus.OK


def test_adding_an_address_saves_it_to_my_book(client, customer):
    client.force_login(customer)

    response = client.post(reverse("accounts:address_create"), FORM_DATA)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == reverse("accounts:account")
    saved = customer.addresses.get()
    assert saved.label == "Work"
    assert not saved.is_default_shipping


def test_the_address_form_uses_the_checkout_rules(client, customer):
    client.force_login(customer)

    response = client.post(
        reverse("accounts:address_create"),
        {**FORM_DATA, "zip": "7910", "state": "ZZ"},
    )

    assert response.status_code == HTTPStatus.OK
    errors = response.context["form"].errors
    assert errors["zip"] == ["Enter a ZIP code like 79016 or 79016-1234."]
    assert "state" in errors
    assert not customer.addresses.exists()


def test_editing_my_address(client, customer, address):
    client.force_login(customer)

    response = client.post(
        reverse("accounts:address_update", args=[address.pk]),
        {**FORM_DATA, "label": "Home"},
    )

    assert response.status_code == HTTPStatus.FOUND
    address.refresh_from_db()
    assert address.street == "77 Cortex Lane"


def test_editing_keeps_the_default(client, customer, address):
    address.make_default("shipping")
    client.force_login(customer)

    client.post(reverse("accounts:address_update", args=[address.pk]), FORM_DATA)

    address.refresh_from_db()
    assert address.is_default_shipping


# --- Delete -------------------------------------------------------------------


def test_delete_confirmation_warns_about_a_default(client, customer, address):
    address.make_default("shipping")
    client.force_login(customer)

    response = client.get(reverse("accounts:address_delete", args=[address.pk]))

    assert response.status_code == HTTPStatus.OK
    assert "This is your default" in response.content.decode()


def test_delete_confirmation_has_no_warning_for_other_addresses(
    client, customer, address
):
    client.force_login(customer)

    response = client.get(reverse("accounts:address_delete", args=[address.pk]))

    assert "This is your default" not in response.content.decode()


def test_deleting_my_address(client, customer, address):
    client.force_login(customer)

    response = client.post(reverse("accounts:address_delete", args=[address.pk]))

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == reverse("accounts:account")
    assert not customer.addresses.exists()


# --- Set default --------------------------------------------------------------


def test_setting_a_default(client, customer, address):
    client.force_login(customer)

    response = client.post(
        reverse("accounts:address_set_default", args=[address.pk, "shipping"])
    )

    assert response.status_code == HTTPStatus.FOUND
    assert customer.addresses.default_for("shipping") == address


def test_set_default_rejects_unknown_kinds(client, customer, address):
    client.force_login(customer)

    response = client.post(
        reverse("accounts:address_set_default", args=[address.pk, "gift"])
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_set_default_is_post_only(client, customer, address):
    client.force_login(customer)

    response = client.get(
        reverse("accounts:address_set_default", args=[address.pk, "shipping"])
    )

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


# --- Ownership: someone else's address is a 404, never a 403 ---------------------


@pytest.mark.parametrize(
    ("method", "url_name", "extra_args"),
    [
        ("get", "accounts:address_update", []),
        ("post", "accounts:address_update", []),
        ("get", "accounts:address_delete", []),
        ("post", "accounts:address_delete", []),
        ("post", "accounts:address_set_default", ["shipping"]),
    ],
)
def test_another_customers_address_is_a_404(
    client, customer, other_address, method, url_name, extra_args
):
    client.force_login(customer)
    url = reverse(url_name, args=[other_address.pk, *extra_args])

    response = getattr(client, method)(url, FORM_DATA if method == "post" else None)

    assert response.status_code == HTTPStatus.NOT_FOUND
    other_address.refresh_from_db()
    assert other_address.street == "9 Axon Avenue"
    assert not other_address.is_default_shipping


@pytest.mark.parametrize(
    "url_name",
    ["accounts:address_update", "accounts:address_delete"],
)
def test_address_pages_require_login(client, address, url_name):
    response = client.get(reverse(url_name, args=[address.pk]))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url

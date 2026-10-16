"""The Account Security Center: emails on the user, signup's email rules,
and the Sign-in & security section of My account."""

from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.urls import reverse

SIGNUP_DATA = {
    "username": "fresh-thinker",
    "email": "fresh@example.com",
    "password1": "neural-implant-9000",
    "password2": "neural-implant-9000",
}


# --- The model ----------------------------------------------------------------


def test_email_is_stored_lowercase(db):
    user = get_user_model().objects.create_user(
        username="casey", email="  Casey@Example.com ", password="x"
    )

    user.refresh_from_db()
    assert user.email == "casey@example.com"


def test_a_missing_email_is_stored_as_null(customer):
    customer.refresh_from_db()

    assert customer.email is None


def test_many_accounts_can_have_no_email(customer, other_customer):
    assert get_user_model().objects.filter(email=None).count() == 2


def test_email_is_unique_regardless_of_capitalization(db):
    User = get_user_model()
    User.objects.create_user(username="casey", email="casey@example.com")

    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(username="casey2", email="CASEY@example.com")


def test_email_starts_unverified(customer):
    assert not customer.email_verified


# --- Signup -------------------------------------------------------------------


def test_signup_requires_an_email(client, db):
    response = client.post(reverse("accounts:signup"), {**SIGNUP_DATA, "email": ""})

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["email"]
    assert not get_user_model().objects.filter(username="fresh-thinker").exists()


def test_signup_rejects_an_email_in_use_ignoring_capitalization(client, db):
    get_user_model().objects.create_user(username="casey", email="casey@example.com")

    response = client.post(
        reverse("accounts:signup"), {**SIGNUP_DATA, "email": "Casey@Example.com"}
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["email"] == [
        "An account with this email already exists."
    ]
    assert not get_user_model().objects.filter(username="fresh-thinker").exists()


def test_signup_saves_the_email_lowercase_and_unverified(client, db):
    client.post(
        reverse("accounts:signup"), {**SIGNUP_DATA, "email": "Fresh@Example.COM"}
    )

    user = get_user_model().objects.get(username="fresh-thinker")
    assert user.email == "fresh@example.com"
    assert not user.email_verified


# --- My account: Sign-in & security -------------------------------------------


def test_security_section_comes_before_the_address_book(client, customer):
    client.force_login(customer)

    page = client.get(reverse("accounts:account")).content.decode()

    assert page.index("Sign-in &amp; security") < page.index("Saved addresses")


def test_security_section_shows_a_verified_email(client, customer):
    customer.email = "customer@example.com"
    customer.email_verified = True
    customer.save()
    client.force_login(customer)

    page = client.get(reverse("accounts:account")).content.decode()

    assert "customer@example.com" in page
    assert "Verified" in page
    assert "Unverified" not in page


def test_security_section_shows_an_unverified_email(client, customer):
    customer.email = "customer@example.com"
    customer.save()
    client.force_login(customer)

    page = client.get(reverse("accounts:account")).content.decode()

    assert "customer@example.com" in page
    assert "Unverified" in page


def test_security_section_shows_when_there_is_no_email(client, customer):
    client.force_login(customer)

    page = client.get(reverse("accounts:account")).content.decode()

    assert "No email on file." in page

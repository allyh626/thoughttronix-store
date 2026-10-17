"""The Account Security Center: emails on the user, signup's email rules,
verification links, and the Sign-in & security section of My account."""

import re
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


# --- Verification links -------------------------------------------------------


def link_in(message):
    """The verification link's path, pulled from an email's body."""
    return re.search(r"https?://[^/\s]+(/\S+)", message.body).group(1)


@pytest.fixture
def unverified(customer):
    customer.email = "customer@example.com"
    customer.save()
    return customer


def test_signup_sends_a_verification_email_then_redirects_to_sign_in(
    client, db, mailoutbox
):
    response = client.post(reverse("accounts:signup"), SIGNUP_DATA)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == reverse("accounts:login")
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["fresh@example.com"]
    assert "/accounts/verify-email/" in mailoutbox[0].body


def test_following_the_signup_link_verifies_the_email(client, db, mailoutbox):
    client.post(reverse("accounts:signup"), SIGNUP_DATA)

    response = client.get(link_in(mailoutbox[0]), follow=True)

    assert get_user_model().objects.get(username="fresh-thinker").email_verified
    assert "fresh@example.com is verified" in response.content.decode()


def test_a_signed_in_customer_returns_to_my_account(client, unverified, mailoutbox):
    unverified.send_verification_email(client.get("/").wsgi_request)
    client.force_login(unverified)

    response = client.get(link_in(mailoutbox[0]))

    assert response.url == reverse("accounts:account")


def test_a_used_link_stops_working(client, unverified, mailoutbox):
    unverified.send_verification_email(client.get("/").wsgi_request)
    link = link_in(mailoutbox[0])
    client.get(link)

    response = client.get(link)

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "verification link doesn't work" in response.content.decode()


def test_an_expired_link_stops_working(client, unverified, mailoutbox, settings):
    unverified.send_verification_email(client.get("/").wsgi_request)
    settings.EMAIL_VERIFICATION_TIMEOUT = -1

    response = client.get(link_in(mailoutbox[0]))

    assert response.status_code == HTTPStatus.BAD_REQUEST
    unverified.refresh_from_db()
    assert not unverified.email_verified


def test_a_tampered_link_stops_working(client, unverified):
    token = unverified.email_verification_token()

    response = client.get(reverse("accounts:verify_email", args=[token + "x"]))

    assert response.status_code == HTTPStatus.BAD_REQUEST
    unverified.refresh_from_db()
    assert not unverified.email_verified


def test_a_link_for_a_replaced_address_stops_working(client, unverified):
    token = unverified.email_verification_token()
    unverified.email = "new@example.com"
    unverified.save()

    response = client.get(reverse("accounts:verify_email", args=[token]))

    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_the_error_page_offers_a_way_to_resend(client, db):
    response = client.get(reverse("accounts:verify_email", args=["nonsense"]))

    assert reverse("accounts:account") in response.content.decode()
    assert "Resend verification email" in response.content.decode()


# --- Resend -------------------------------------------------------------------


def test_resend_button_shows_for_an_unverified_email(client, unverified):
    client.force_login(unverified)

    page = client.get(reverse("accounts:account")).content.decode()

    assert "Resend verification email" in page


def test_resend_button_is_hidden_for_a_verified_email(client, unverified):
    unverified.email_verified = True
    unverified.save()
    client.force_login(unverified)

    page = client.get(reverse("accounts:account")).content.decode()

    assert "Resend verification email" not in page


def test_resend_button_is_hidden_with_no_email(client, customer):
    client.force_login(customer)

    page = client.get(reverse("accounts:account")).content.decode()

    assert "Resend verification email" not in page


def test_resend_sends_a_fresh_link_that_works(client, unverified, mailoutbox):
    client.force_login(unverified)

    response = client.post(reverse("accounts:resend_verification"), follow=True)

    assert "Verification email sent to customer@example.com." in (
        response.content.decode()
    )
    assert mailoutbox[0].to == ["customer@example.com"]
    client.get(link_in(mailoutbox[0]))
    unverified.refresh_from_db()
    assert unverified.email_verified


def test_resend_sends_nothing_for_a_verified_email(client, unverified, mailoutbox):
    unverified.email_verified = True
    unverified.save()
    client.force_login(unverified)

    client.post(reverse("accounts:resend_verification"))

    assert mailoutbox == []


def test_resend_requires_sign_in(client, db, mailoutbox):
    response = client.post(reverse("accounts:resend_verification"))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url
    assert mailoutbox == []

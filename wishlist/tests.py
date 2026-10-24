from http import HTTPStatus

import pytest
from django.contrib import admin
from django.db import IntegrityError
from django.urls import reverse

from .models import Wishlist, WishlistItem

# --- Model behavior ---------------------------------------------------------


def test_wishlist_str(wishlist):
    assert str(wishlist) == "Wishlist for customer"


def test_for_user_creates_the_wishlist_once(customer):
    first = Wishlist.for_user(customer)
    second = Wishlist.for_user(customer)

    assert first == second
    assert Wishlist.objects.count() == 1


def test_add_saves_the_product(wishlist, product):
    item = wishlist.add(product)

    assert str(item) == "Seraphine Home Hub"
    assert item.added_at is not None
    assert wishlist.items.count() == 1


def test_add_twice_keeps_one_item(wishlist, product):
    first = wishlist.add(product)
    second = wishlist.add(product)

    assert first == second
    assert wishlist.items.count() == 1


def test_remove_twice_leaves_the_product_unsaved(wishlist, product):
    wishlist.add(product)

    wishlist.remove(product)
    wishlist.remove(product)

    assert wishlist.items.count() == 0


def test_wishlist_product_pair_is_unique(wishlist, product):
    wishlist.add(product)

    with pytest.raises(IntegrityError):
        WishlistItem.objects.create(wishlist=wishlist, product=product)


def test_deleting_the_user_deletes_the_wishlist(customer, wishlist, product):
    wishlist.add(product)

    customer.delete()

    assert not Wishlist.objects.exists()
    assert not WishlistItem.objects.exists()


def test_deleting_the_product_deletes_its_items(wishlist, product):
    wishlist.add(product)

    product.delete()

    assert Wishlist.objects.exists()
    assert not WishlistItem.objects.exists()


# --- Add to wishlist (HTMX) --------------------------------------------------


def test_anonymous_add_redirects_to_login(client, product):
    response = client.post(reverse("wishlist:add", kwargs={"pk": product.pk}))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url
    assert not WishlistItem.objects.exists()


def test_add_rejects_get(client, customer, product):
    client.force_login(customer)

    response = client.get(reverse("wishlist:add", kwargs={"pk": product.pk}))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert not WishlistItem.objects.exists()


def test_add_returns_partial_in_saved_state(client, customer, product):
    client.force_login(customer)

    response = client.post(reverse("wishlist:add", kwargs={"pk": product.pk}))

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "<html" not in page
    assert "In wishlist (remove)" in page
    assert customer.wishlist.items.get().product == product


def test_add_unavailable_product_is_allowed(client, customer, unavailable_product):
    client.force_login(customer)

    response = client.post(
        reverse("wishlist:add", kwargs={"pk": unavailable_product.pk})
    )

    assert response.status_code == HTTPStatus.OK
    assert customer.wishlist.items.get().product == unavailable_product


def test_add_twice_keeps_one_item_via_endpoint(client, customer, product):
    client.force_login(customer)
    client.post(reverse("wishlist:add", kwargs={"pk": product.pk}))

    response = client.post(reverse("wishlist:add", kwargs={"pk": product.pk}))

    assert "In wishlist (remove)" in response.content.decode()
    assert customer.wishlist.items.count() == 1


def test_add_missing_product_404s(client, customer):
    client.force_login(customer)

    response = client.post(reverse("wishlist:add", kwargs={"pk": 9999}))

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_add_only_touches_your_own_wishlist(client, customer, other_customer, product):
    other_wishlist = Wishlist.for_user(other_customer)
    client.force_login(customer)

    client.post(reverse("wishlist:add", kwargs={"pk": product.pk}))

    assert customer.wishlist.items.count() == 1
    assert other_wishlist.items.count() == 0


# --- Remove from wishlist (HTMX) ---------------------------------------------


def test_anonymous_remove_redirects_to_login(client, wishlist, product):
    wishlist.add(product)

    response = client.post(reverse("wishlist:remove", kwargs={"pk": product.pk}))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url
    assert wishlist.items.count() == 1


def test_remove_rejects_get(client, customer, wishlist, product):
    wishlist.add(product)
    client.force_login(customer)

    response = client.get(reverse("wishlist:remove", kwargs={"pk": product.pk}))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert wishlist.items.count() == 1


def test_remove_returns_partial_in_unsaved_state(client, customer, wishlist, product):
    wishlist.add(product)
    client.force_login(customer)

    response = client.post(
        reverse("wishlist:remove", kwargs={"pk": product.pk}),
        headers={"HX-Request": "true"},
    )

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "<html" not in page
    assert reverse("wishlist:add", kwargs={"pk": product.pk}) in page
    assert not customer.wishlist.items.exists()


def test_remove_twice_via_endpoint_is_harmless(client, customer, wishlist, product):
    wishlist.add(product)
    client.force_login(customer)
    url = reverse("wishlist:remove", kwargs={"pk": product.pk})
    client.post(url, headers={"HX-Request": "true"})

    response = client.post(url, headers={"HX-Request": "true"})

    assert response.status_code == HTTPStatus.OK
    assert (
        reverse("wishlist:add", kwargs={"pk": product.pk}) in response.content.decode()
    )
    assert not wishlist.items.exists()


def test_remove_only_touches_your_own_wishlist(
    client, customer, other_customer, wishlist, product
):
    wishlist.add(product)
    other_wishlist = Wishlist.for_user(other_customer)
    other_wishlist.add(product)
    client.force_login(customer)

    client.post(
        reverse("wishlist:remove", kwargs={"pk": product.pk}),
        headers={"HX-Request": "true"},
    )

    assert not wishlist.items.exists()
    assert other_wishlist.items.get().product == product


# --- The detail page button --------------------------------------------------


def test_detail_prompts_anonymous_users_to_sign_in(client, product):
    response = client.get(product.get_absolute_url())

    page = response.content.decode()
    assert f"{reverse('accounts:login')}?next=" in page
    assert reverse("wishlist:add", kwargs={"pk": product.pk}) not in page


def test_detail_shows_add_button_when_not_saved(client, customer, product):
    client.force_login(customer)

    response = client.get(product.get_absolute_url())

    page = response.content.decode()
    assert reverse("wishlist:add", kwargs={"pk": product.pk}) in page
    assert "In wishlist (remove)" not in page


def test_detail_shows_saved_state(client, customer, wishlist, product):
    wishlist.add(product)
    client.force_login(customer)

    response = client.get(product.get_absolute_url())

    page = response.content.decode()
    assert "In wishlist (remove)" in page
    assert reverse("wishlist:remove", kwargs={"pk": product.pk}) in page


def test_detail_saved_state_is_per_customer(client, other_customer, wishlist, product):
    wishlist.add(product)
    client.force_login(other_customer)

    response = client.get(product.get_absolute_url())

    assert "In wishlist (remove)" not in response.content.decode()


# --- Admin -------------------------------------------------------------------


def test_wishlist_is_registered_in_admin():
    assert admin.site.is_registered(Wishlist)

import re
from datetime import timedelta
from decimal import Decimal
from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone

from orders.models import Order, OrderItem

from .models import Review


def _order(user, product, status=Order.Status.DELIVERED):
    """An order of one unit of the product, in the given status."""
    order = Order.objects.create(
        user=user,
        status=status,
        total=product.price,
        email="casey@example.com",
        shipping_name="Casey Monroe",
        shipping_street="9 Synapse Court",
        shipping_city="Canyon",
        shipping_state="TX",
        shipping_zip="79015",
        billing_name="Casey Monroe",
        billing_street="9 Synapse Court",
        billing_city="Canyon",
        billing_state="TX",
        billing_zip="79015",
        card_last4="4242",
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        product_name=product.name,
        unit_price=Decimal(product.price),
        quantity=1,
    )
    return order


def _review(product, author, **fields):
    return Review.objects.create(
        product=product,
        author=author,
        rating=fields.pop("rating", 4),
        title=fields.pop("title", "Reads my mind"),
        comment=fields.pop("comment", "It finished my sentences all week."),
        **fields,
    )


# --- Model behavior ---------------------------------------------------------


@pytest.mark.parametrize(
    ("username", "expected"),
    [("allison", "a****n"), ("ay", "a****y"), ("a", "a****a")],
)
def test_review_saves_a_fixed_length_censored_name(product, username, expected):
    author = get_user_model().objects.create_user(username=username, password="pw")

    review = _review(product, author)

    review.refresh_from_db()
    assert review.display_name == expected


@pytest.mark.parametrize(
    ("status", "eligible"),
    [
        (Order.Status.DELIVERED, True),
        (Order.Status.PLACED, False),
        (Order.Status.SHIPPED, False),
        (Order.Status.CANCELLED, False),
    ],
)
def test_only_a_delivered_order_makes_a_customer_eligible(
    customer, product, status, eligible
):
    _order(customer, product, status)

    assert Review.objects.can_write(customer, product) is eligible


def test_a_delivered_order_of_another_product_is_not_enough(
    customer, product, unavailable_product
):
    _order(customer, unavailable_product)

    assert Review.objects.can_write(customer, product) is False


def test_a_customer_who_already_reviewed_is_not_eligible(customer, product):
    _order(customer, product)
    _review(product, customer)

    assert Review.objects.can_write(customer, product) is False


def test_staff_are_never_eligible(staff_user, product):
    _order(staff_user, product)

    assert Review.objects.can_write(staff_user, product) is False


def _reviews_rated(product, *ratings):
    """One review per rating, each by a different customer."""
    User = get_user_model()
    for number, rating in enumerate(ratings):
        author = User.objects.create_user(username=f"reviewer{number}", password="pw")
        _review(product, author, rating=rating)


@pytest.mark.parametrize(
    ("ratings", "average"),
    [
        ((5, 4, 4), Decimal("4.3")),
        ((4, 4, 4, 5), Decimal("4.3")),  # 4.25 rounds half up
        ((1,), Decimal("1.0")),
    ],
)
def test_rating_summary_rounds_the_average_to_one_decimal(product, ratings, average):
    _reviews_rated(product, *ratings)

    assert product.reviews.rating_summary() == {
        "average": average,
        "count": len(ratings),
    }


def test_rating_summary_of_a_product_without_reviews(product, unavailable_product):
    _reviews_rated(unavailable_product, 5)

    assert product.reviews.rating_summary() == {"average": None, "count": 0}


# --- Post a review (HTMX) ----------------------------------------------------

VALID_REVIEW = {"rating": "5", "title": "Reads my mind", "comment": "Every time."}


def test_create_refuses_a_customer_without_a_delivered_order(client, customer, product):
    _order(customer, product, Order.Status.SHIPPED)
    client.force_login(customer)

    response = client.post(
        reverse("reviews:create", kwargs={"pk": product.pk}), VALID_REVIEW
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert not Review.objects.exists()


def test_create_saves_the_review_and_returns_its_card(client, customer, product):
    _order(customer, product)
    client.force_login(customer)

    response = client.post(
        reverse("reviews:create", kwargs={"pk": product.pk}), VALID_REVIEW
    )

    review = Review.objects.get()
    assert (review.author, review.product, review.rating) == (customer, product, 5)
    assert review.edited_at is None
    page = response.content.decode()
    assert f'id="review-{review.pk}"' in page
    assert "c****r" in page
    assert 'hx-swap-oob="afterbegin:#review-list"' in page
    assert "Post review" not in page  # the form is gone


def test_create_refuses_a_second_review_of_the_same_product(client, customer, product):
    _order(customer, product)
    _order(customer, product)  # bought twice — still one review
    _review(product, customer)
    client.force_login(customer)

    response = client.post(
        reverse("reviews:create", kwargs={"pk": product.pk}), VALID_REVIEW
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert Review.objects.count() == 1


def test_create_refuses_staff(client, staff_user, product):
    _order(staff_user, product)
    client.force_login(staff_user)

    response = client.post(
        reverse("reviews:create", kwargs={"pk": product.pk}), VALID_REVIEW
    )

    assert response.status_code == HTTPStatus.FORBIDDEN


def test_anonymous_create_redirects_to_login(client, product):
    url = reverse("reviews:create", kwargs={"pk": product.pk})

    response = client.post(url, VALID_REVIEW)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == f"{reverse('accounts:login')}?next={url}"
    assert not Review.objects.exists()


def test_create_is_post_only(client, customer, product):
    _order(customer, product)
    client.force_login(customer)

    response = client.get(reverse("reviews:create", kwargs={"pk": product.pk}))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


@pytest.mark.parametrize(
    ("changes", "field", "message"),
    [
        ({"rating": ""}, "rating", "This field is required."),
        ({"rating": "6"}, "rating", "less than or equal to 5"),
        ({"rating": "0"}, "rating", "greater than or equal to 1"),
        ({"title": ""}, "title", "This field is required."),
        ({"comment": ""}, "comment", "This field is required."),
        ({"title": "x" * 51}, "title", "at most 50 characters"),
        ({"comment": "x" * 1001}, "comment", "at most 1000 characters"),
    ],
)
def test_create_shows_errors_in_place(
    client, customer, product, changes, field, message
):
    _order(customer, product)
    client.force_login(customer)

    response = client.post(
        reverse("reviews:create", kwargs={"pk": product.pk}),
        {**VALID_REVIEW, **changes},
    )

    assert response.status_code == HTTPStatus.OK
    assert message in response.context["form"].errors[field][0]
    assert 'id="review-form"' in response.content.decode()
    assert not Review.objects.exists()


def test_title_and_comment_at_their_limits_are_accepted(client, customer, product):
    _order(customer, product)
    client.force_login(customer)

    client.post(
        reverse("reviews:create", kwargs={"pk": product.pk}),
        {"rating": "3", "title": "x" * 50, "comment": "y" * 1000},
    )

    assert Review.objects.count() == 1


# --- The reviews section on the product page --------------------------------


def _detail(client, product):
    return client.get(product.get_absolute_url()).content.decode()


INELIGIBLE_HINT = (
    "You can review this product once an order containing it has been delivered."
)


def test_eligible_customer_sees_the_form(client, customer, product):
    _order(customer, product)
    client.force_login(customer)

    page = _detail(client, product)

    assert "Post review" in page
    assert reverse("reviews:create", kwargs={"pk": product.pk}) in page
    assert INELIGIBLE_HINT not in page


def test_signed_out_visitor_sees_a_sign_in_hint(client, product):
    page = _detail(client, product)

    assert f"{reverse('accounts:login')}?next={product.get_absolute_url()}" in page
    assert "to leave a review." in page
    assert "Post review" not in page


@pytest.mark.parametrize(
    "status", [None, Order.Status.PLACED, Order.Status.SHIPPED, Order.Status.CANCELLED]
)
def test_ineligible_customer_sees_the_delivered_hint(client, customer, product, status):
    if status:
        _order(customer, product, status)
    client.force_login(customer)

    page = _detail(client, product)

    assert INELIGIBLE_HINT in page
    assert "Post review" not in page


def test_staff_see_no_form_and_no_hint(client, staff_user, product):
    _order(staff_user, product)
    client.force_login(staff_user)

    page = _detail(client, product)

    assert "Post review" not in page
    assert INELIGIBLE_HINT not in page
    assert "to leave a review." not in page


def test_customer_who_already_reviewed_sees_no_form(client, customer, product):
    _order(customer, product)
    _review(product, customer)
    client.force_login(customer)

    page = _detail(client, product)

    assert "Post review" not in page
    assert INELIGIBLE_HINT not in page


def test_product_page_lists_reviews_newest_first(client, product, customer):
    older = get_user_model().objects.create_user(username="olivia", password="pw")
    _review(
        product,
        older,
        title="Older thoughts",
        created_at=timezone.now() - timedelta(days=3),
    )
    _review(
        product,
        customer,
        title="Newer thoughts",
        rating=2,
        comment="It knew what I wanted for lunch.",
    )

    page = _detail(client, product)

    assert page.index("Newer thoughts") < page.index("Older thoughts")
    assert "c****r" in page and "o****a" in page
    assert "It knew what I wanted for lunch." in page
    assert 'aria-label="2 out of 5 stars"' in page
    assert timezone.localdate().strftime("%b") in page
    assert "No reviews yet." not in page


def _others(product, count):
    """``count`` reviews by other customers, one a day, newest first."""
    User = get_user_model()
    return [
        _review(
            product,
            User.objects.create_user(username=f"other{days}", password="pw"),
            created_at=timezone.now() - timedelta(days=days),
        )
        for days in range(count)
    ]


def _card_ids(page):
    return [int(pk) for pk in re.findall(r'id="review-(\d+)"', page)]


def test_own_review_is_pinned_first_then_the_five_newest_others(
    client, customer, product
):
    own = _review(product, customer, created_at=timezone.now() - timedelta(days=30))
    others = _others(product, 7)
    client.force_login(customer)

    page = _detail(client, product)

    assert _card_ids(page) == [own.pk] + [review.pk for review in others[:5]]


def test_show_more_returns_the_next_five_and_hides_on_the_last_page(client, product):
    others = _others(product, 12)
    url = reverse("reviews:more", kwargs={"pk": product.pk})

    second = client.get(url, {"page": 2}).content.decode()
    last = client.get(url, {"page": 3}).content.decode()

    assert _card_ids(second) == [review.pk for review in others[5:10]]
    assert f"{url}?page=3" in second and "Show more" in second
    assert _card_ids(last) == [review.pk for review in others[10:]]
    assert "Show more" not in last


def test_show_more_never_repeats_the_pinned_own_review(client, customer, product):
    own = _review(product, customer, created_at=timezone.now() - timedelta(days=30))
    others = _others(product, 7)
    client.force_login(customer)

    response = client.get(
        reverse("reviews:more", kwargs={"pk": product.pk}), {"page": 2}
    )

    assert own.pk not in _card_ids(response.content.decode())
    assert _card_ids(response.content.decode()) == [r.pk for r in others[5:]]


@pytest.mark.parametrize(("count", "shown"), [(5, False), (6, True)])
def test_product_page_offers_show_more_only_past_five(client, product, count, shown):
    _others(product, count)

    page = _detail(client, product)

    assert ("Show more" in page) is shown


def test_product_page_shows_the_average_and_count(client, product):
    _reviews_rated(product, 5, 4, 4)

    page = _detail(client, product)

    assert "4.3 ★" in page
    assert "(3 reviews)" in page
    assert "No reviews yet." not in page


def test_product_page_counts_a_single_review_in_the_singular(client, product):
    _reviews_rated(product, 4)

    assert "(1 review)" in _detail(client, product)


def test_create_updates_the_average_and_count_in_place(client, customer, product):
    _reviews_rated(product, 2)
    _order(customer, product)
    client.force_login(customer)

    response = client.post(
        reverse("reviews:create", kwargs={"pk": product.pk}), VALID_REVIEW
    )

    page = response.content.decode()
    assert re.search(r'id="review-summary"[^>]*hx-swap-oob="true"', page)
    assert "3.5 ★" in page and "(2 reviews)" in page


def test_product_page_shows_an_empty_state_without_reviews(client, product):
    assert "No reviews yet." in _detail(client, product)


def test_reviews_of_other_products_are_not_listed(
    client, customer, product, unavailable_product
):
    _review(unavailable_product, customer, title="About EchoPatch")

    assert "About EchoPatch" not in _detail(client, product)


# --- Edit and delete your own review (HTMX) ---------------------------------


def _other_customer():
    return get_user_model().objects.create_user(username="olivia", password="pw")


def test_only_the_author_sees_edit_and_delete(client, customer, product):
    own = _review(product, customer)
    other = _review(product, _other_customer())
    client.force_login(customer)

    page = _detail(client, product)

    assert reverse("reviews:edit", kwargs={"pk": own.pk}) in page
    assert reverse("reviews:delete", kwargs={"pk": own.pk}) in page
    assert reverse("reviews:edit", kwargs={"pk": other.pk}) not in page
    assert reverse("reviews:delete", kwargs={"pk": other.pk}) not in page
    assert 'hx-confirm="Delete your review?' in page


def test_signed_out_visitor_sees_no_edit_or_delete(client, customer, product):
    _review(product, customer)

    page = _detail(client, product)

    assert "/edit/" not in page and "/delete/" not in page


def test_edit_get_returns_a_prefilled_form(client, customer, product):
    review = _review(product, customer, title="First thoughts")
    client.force_login(customer)

    response = client.get(reverse("reviews:edit", kwargs={"pk": review.pk}))

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].instance == review
    page = response.content.decode()
    assert 'value="First thoughts"' in page
    assert f'hx-get="{reverse("reviews:card", kwargs={"pk": review.pk})}"' in page


@pytest.mark.parametrize(
    ("method", "name"), [("get", "edit"), ("post", "edit"), ("post", "delete")]
)
def test_another_customers_review_is_not_found(client, customer, product, method, name):
    review = _review(product, _other_customer())
    client.force_login(customer)

    response = getattr(client, method)(
        reverse(f"reviews:{name}", kwargs={"pk": review.pk}), VALID_REVIEW
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    review.refresh_from_db()
    assert review.title == "Reads my mind"


@pytest.mark.parametrize("name", ["edit", "delete"])
def test_anonymous_edit_and_delete_redirect_to_login(client, customer, product, name):
    review = _review(product, customer)
    url = reverse(f"reviews:{name}", kwargs={"pk": review.pk})

    response = client.post(url, VALID_REVIEW)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == f"{reverse('accounts:login')}?next={url}"
    assert Review.objects.filter(pk=review.pk, edited_at=None).exists()


def test_edit_saves_marks_edited_and_returns_the_card(client, customer, product):
    review = _review(product, customer)
    client.force_login(customer)

    response = client.post(
        reverse("reviews:edit", kwargs={"pk": review.pk}),
        {"rating": "2", "title": "Second thoughts", "comment": "It got moody."},
    )

    review.refresh_from_db()
    assert (review.rating, review.title) == (2, "Second thoughts")
    assert review.edited_at is not None
    assert (review.author, review.display_name) == (customer, "c****r")
    page = response.content.decode()
    assert f'id="review-{review.pk}"' in page
    assert "Second thoughts" in page and "edited</span>" in page


def test_edit_works_after_the_order_is_cancelled(client, customer, product):
    order = _order(customer, product)
    review = _review(product, customer)
    order.status = Order.Status.CANCELLED
    order.save()
    client.force_login(customer)

    client.post(reverse("reviews:edit", kwargs={"pk": review.pk}), VALID_REVIEW)

    review.refresh_from_db()
    assert review.edited_at is not None


def test_edit_shows_errors_in_place(client, customer, product):
    review = _review(product, customer)
    client.force_login(customer)

    response = client.post(
        reverse("reviews:edit", kwargs={"pk": review.pk}),
        {**VALID_REVIEW, "title": "x" * 51},
    )

    assert response.status_code == HTTPStatus.OK
    assert "at most 50 characters" in response.context["form"].errors["title"][0]
    review.refresh_from_db()
    assert (review.title, review.edited_at) == ("Reads my mind", None)


def test_unedited_review_has_no_edited_tag(client, customer, product):
    _review(product, customer)

    assert "edited</span>" not in _detail(client, product)


def test_card_returns_the_unchanged_card_for_cancel(client, customer, product):
    review = _review(product, customer, title="As it was")
    client.force_login(customer)

    response = client.get(reverse("reviews:card", kwargs={"pk": review.pk}))

    page = response.content.decode()
    assert response.status_code == HTTPStatus.OK
    assert f'id="review-{review.pk}"' in page and "As it was" in page
    assert "<form" not in page


def test_edit_updates_the_average_and_count_in_place(client, customer, product):
    _reviews_rated(product, 2)
    review = _review(product, customer, rating=4)
    client.force_login(customer)

    response = client.post(
        reverse("reviews:edit", kwargs={"pk": review.pk}), VALID_REVIEW
    )

    page = response.content.decode()
    assert re.search(r'id="review-summary"[^>]*hx-swap-oob="true"', page)
    assert "3.5 ★" in page and "(2 reviews)" in page


def test_delete_is_post_only(client, customer, product):
    review = _review(product, customer)
    client.force_login(customer)

    response = client.get(reverse("reviews:delete", kwargs={"pk": review.pk}))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert Review.objects.exists()


def test_delete_removes_the_review_and_brings_the_form_back(client, customer, product):
    _order(customer, product)
    review = _review(product, customer)
    _reviews_rated(product, 2)
    client.force_login(customer)

    response = client.post(reverse("reviews:delete", kwargs={"pk": review.pk}))

    assert not Review.objects.filter(pk=review.pk).exists()
    page = response.content.decode()
    assert f'id="review-{review.pk}"' not in page
    assert re.search(r'id="review-prompt"[^>]*hx-swap-oob="true"', page)
    assert "Post review" in page
    assert "2.0 ★" in page and "(1 review)" in page


def test_delete_without_a_delivered_order_shows_the_hint(client, customer, product):
    review = _review(product, customer)
    client.force_login(customer)

    response = client.post(reverse("reviews:delete", kwargs={"pk": review.pk}))

    page = response.content.decode()
    assert INELIGIBLE_HINT in page and "Post review" not in page
    assert "No reviews yet." in page


# --- Reviews outlive orders and accounts, not products ----------------------


def test_review_stays_after_its_order_is_cancelled(customer, product):
    order = _order(customer, product)
    review = _review(product, customer)

    order.status = Order.Status.CANCELLED
    order.save()

    assert Review.objects.filter(pk=review.pk).exists()


def test_review_keeps_its_censored_name_after_deactivate(client, customer, product):
    _review(product, customer, title="Still here")

    customer.deactivate()

    review = Review.objects.get()
    assert review.author.username == f"deleted-user-{customer.pk}"
    assert review.display_name == "c****r"
    page = _detail(client, product)
    assert "Still here" in page and "c****r" in page


def test_deleting_the_product_deletes_its_reviews(customer, product):
    _review(product, customer)

    product.delete()

    assert not Review.objects.exists()


def test_product_author_pair_is_unique(customer, product):
    _review(product, customer)

    with pytest.raises(IntegrityError):
        _review(product, customer)

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

from .forms import ReviewReportForm
from .models import Review, ReviewReport


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


def test_saving_without_changes_is_not_an_edit(client, customer, product):
    review = _review(product, customer)
    client.force_login(customer)

    response = client.post(
        reverse("reviews:edit", kwargs={"pk": review.pk}),
        {"rating": "4", "title": review.title, "comment": review.comment},
    )

    review.refresh_from_db()
    assert review.edited_at is None
    page = response.content.decode()
    assert f'id="review-{review.pk}"' in page and "edited</span>" not in page


@pytest.mark.parametrize(("reviewed", "queries"), [(True, 0), (False, 1)])
def test_prompt_for_skips_the_review_lookup_when_told(
    customer, product, django_assert_num_queries, reviewed, queries
):
    with django_assert_num_queries(queries):
        Review.objects.prompt_for(customer, product, reviewed=reviewed)


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


# --- Banned words flag a review ----------------------------------------------


@pytest.mark.parametrize("field", ["title", "comment"])
def test_a_banned_word_flags_the_review_on_create_and_on_edit(
    client, customer, other_customer, product, field
):
    _order(customer, product)
    client.force_login(customer)
    client.post(
        reverse("reviews:create", kwargs={"pk": product.pk}),
        {**VALID_REVIEW, field: "Total SCAM, sadly."},
    )
    assert Review.objects.get(author=customer).is_flagged

    clean = _review(product, other_customer)
    client.force_login(other_customer)
    client.post(
        reverse("reviews:edit", kwargs={"pk": clean.pk}),
        {**VALID_REVIEW, field: "What a Scam."},
    )
    clean.refresh_from_db()
    assert clean.is_flagged


@pytest.mark.parametrize(
    ("comment", "flagged"),
    [
        ("Total scams, all of them.", True),
        ("A scammy little gadget.", True),
        ("Run by scammers.", True),
        ("I got scammed.", True),
        ("Crappy battery.", True),
        ("An idiotic design.", True),
        ("Pure stupidity.", True),
        ("Damned if I know.", True),
        ("They are scamming people.", True),
        ("Pure idiocy.", True),
        ("It works stupidly.", True),
        ("It made my cat scamper off.", False),
        ("It only suggests scampi recipes.", False),
    ],
)
def test_banned_word_variants_flag_but_lookalikes_do_not(
    customer, product, comment, flagged
):
    review = _review(product, customer, comment=comment)

    assert review.is_flagged is flagged


def test_a_clean_customer_edit_keeps_an_existing_flag(client, customer, product):
    review = _review(product, customer, comment="Honestly a scam.")
    client.force_login(customer)

    client.post(
        reverse("reviews:edit", kwargs={"pk": review.pk}),
        {**VALID_REVIEW, "comment": "Honestly fine."},
    )

    review.refresh_from_db()
    assert review.comment == "Honestly fine."
    assert review.is_flagged


# --- The back-office Reviews tab --------------------------------------------


def test_reviews_tab_lists_flagged_first_then_newest_first(client, staff_user, product):
    User = get_user_model()
    now = timezone.now()
    reviews = {}
    for name, days_ago, flagged in [
        ("old-flagged", 3, True),
        ("new-clean", 0, False),
        ("new-flagged", 1, True),
        ("old-clean", 2, False),
    ]:
        author = User.objects.create_user(username=name, password="pw")
        reviews[name] = _review(
            product,
            author,
            title=name,
            created_at=now - timedelta(days=days_ago),
            is_flagged=flagged,
        )
    client.force_login(staff_user)

    response = client.get(reverse("reviews:manage"))

    assert list(response.context["reviews"]) == [
        reviews["new-flagged"],
        reviews["old-flagged"],
        reviews["new-clean"],
        reviews["old-clean"],
    ]


def _manage_requests(review):
    """Each back-office review endpoint, with the method it accepts."""
    return [
        ("get", reverse("reviews:manage")),
        ("post", reverse("reviews:clear_flag", kwargs={"pk": review.pk})),
        ("get", reverse("reviews:manage_edit", kwargs={"pk": review.pk})),
        ("post", reverse("reviews:manage_edit", kwargs={"pk": review.pk})),
        ("get", reverse("reviews:manage_delete", kwargs={"pk": review.pk})),
        ("post", reverse("reviews:manage_delete", kwargs={"pk": review.pk})),
    ]


def test_reviews_tab_sends_anonymous_users_to_login(client, customer, product):
    review = _review(product, customer, is_flagged=True)

    for method, url in _manage_requests(review):
        response = getattr(client, method)(url)

        assert response.status_code == HTTPStatus.FOUND, url
        assert reverse("accounts:login") in response.url
    review.refresh_from_db()
    assert review.is_flagged


def test_reviews_tab_refuses_customers(client, customer, product):
    review = _review(product, customer, is_flagged=True)
    client.force_login(customer)

    for method, url in _manage_requests(review):
        assert getattr(client, method)(url).status_code == HTTPStatus.FORBIDDEN, url
    review.refresh_from_db()
    assert review.is_flagged


def test_flagged_filter_shows_only_flagged_reviews(
    client, staff_user, customer, other_customer, product
):
    _review(product, customer, title="Flagged one", is_flagged=True)
    _review(product, other_customer, title="Clean one")
    client.force_login(staff_user)

    response = client.get(reverse("reviews:manage"), {"filter": "flagged"})

    assert [review.title for review in response.context["reviews"]] == ["Flagged one"]
    assert "Clean one" not in response.content.decode()


def test_flagged_filter_has_an_empty_state(client, staff_user, customer, product):
    _review(product, customer)
    client.force_login(staff_user)

    page = client.get(reverse("reviews:manage"), {"filter": "flagged"}).content.decode()

    assert "No flagged reviews" in page


def test_unknown_filter_shows_all_reviews(client, staff_user, customer, product):
    _review(product, customer, title="Clean one")
    client.force_login(staff_user)

    response = client.get(reverse("reviews:manage"), {"filter": "teleported"})

    assert response.context["active_filter"] == ""
    assert "Clean one" in response.content.decode()


def test_reviews_tab_shows_the_comment_that_was_flagged(
    client, staff_user, customer, product
):
    _review(product, customer, title="Great hub", comment="Honestly a scam.")
    client.force_login(staff_user)

    page = client.get(reverse("reviews:manage")).content.decode()

    assert "Great hub" in page and "Honestly a scam." in page


def test_reviews_tab_shows_full_usernames_and_marks_deactivated_authors(
    client, staff_user, customer, other_customer, product
):
    _review(product, customer)
    _review(product, other_customer)
    other_customer.deactivate()
    client.force_login(staff_user)

    page = client.get(reverse("reviews:manage")).content.decode()

    assert customer.username in page
    assert f"deleted-user-{other_customer.pk}" in page
    assert page.count("Deactivated account") == 1
    assert "c****r" not in page


def test_clear_flag_clears_it_and_redirects_back_with_a_message(
    client, staff_user, customer, product
):
    review = _review(product, customer, title="Was it a scam", is_flagged=True)
    client.force_login(staff_user)
    url = reverse("reviews:clear_flag", kwargs={"pk": review.pk})

    response = client.post(url, {"filter": "flagged"})

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == f"{reverse('reviews:manage')}?filter=flagged"
    review.refresh_from_db()
    assert not review.is_flagged
    assert review.edited_at is None
    page = client.get(response.url).content.decode()
    assert "Flag cleared on “Was it a scam”." in page


def test_clear_flag_is_post_only(client, staff_user, customer, product):
    review = _review(product, customer, is_flagged=True)
    client.force_login(staff_user)

    response = client.get(reverse("reviews:clear_flag", kwargs={"pk": review.pk}))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    review.refresh_from_db()
    assert review.is_flagged


def test_reviews_tab_is_in_the_back_office_tab_bar(client, staff_user):
    client.force_login(staff_user)

    orders_page = client.get(reverse("orders:manage_orders")).content.decode()
    reviews_page = client.get(reverse("reviews:manage")).content.decode()

    assert f'href="{reverse("reviews:manage")}">Reviews</a>' in orders_page
    assert re.search(
        r'class="tab tab-active"\s+href="/backoffice/reviews/"', reviews_page
    )


# --- Staff edit and delete any review ---------------------------------------


def test_staff_edit_keeps_the_author_marks_edited_and_clears_the_flag(
    client, staff_user, customer, product
):
    review = _review(product, customer, comment="Honestly a scam.")
    client.force_login(staff_user)

    response = client.post(
        reverse("reviews:edit", kwargs={"pk": review.pk}),
        {**VALID_REVIEW, "comment": "Honestly [removed]."},
    )

    assert response.status_code == HTTPStatus.OK
    review.refresh_from_db()
    assert review.comment == "Honestly [removed]."
    assert (review.author, review.display_name) == (customer, "c****r")
    assert review.edited_at is not None
    assert not review.is_flagged


def test_staff_can_delete_any_review_but_customers_cannot(
    client, staff_user, customer, product
):
    review = _review(product, _other_customer())
    _reviews_rated(product, 2)
    url = reverse("reviews:delete", kwargs={"pk": review.pk})

    client.force_login(customer)
    assert client.post(url).status_code == HTTPStatus.NOT_FOUND
    assert Review.objects.filter(pk=review.pk).exists()

    client.force_login(staff_user)
    response = client.post(url)

    assert response.status_code == HTTPStatus.OK
    assert not Review.objects.filter(pk=review.pk).exists()
    page = response.content.decode()
    assert "2.0 ★" in page and "(1 review)" in page
    assert "Post review" not in page


def test_staff_see_edit_and_delete_on_every_review(
    client, staff_user, customer, product
):
    reviews = [_review(product, customer), _review(product, _other_customer())]
    client.force_login(staff_user)

    page = _detail(client, product)

    for review in reviews:
        assert reverse("reviews:edit", kwargs={"pk": review.pk}) in page
        assert reverse("reviews:delete", kwargs={"pk": review.pk}) in page
    assert page.count('hx-confirm="Delete this review?') == 2
    assert "Delete your review?" not in page


def test_reviews_tab_rows_link_to_edit_and_delete(
    client, staff_user, customer, product
):
    review = _review(product, customer)
    client.force_login(staff_user)

    page = client.get(reverse("reviews:manage")).content.decode()

    assert reverse("reviews:manage_edit", kwargs={"pk": review.pk}) in page
    assert reverse("reviews:manage_delete", kwargs={"pk": review.pk}) in page


def test_manage_edit_shows_a_prefilled_form_with_the_full_username(
    client, staff_user, customer, product
):
    review = _review(product, customer, title="First thoughts")
    client.force_login(staff_user)

    response = client.get(reverse("reviews:manage_edit", kwargs={"pk": review.pk}))

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert 'value="First thoughts"' in page
    assert customer.username in page and "c****r" not in page


def test_manage_edit_keeps_the_author_clears_the_flag_and_redirects(
    client, staff_user, customer, product
):
    review = _review(product, customer, comment="Honestly a scam.")
    client.force_login(staff_user)

    response = client.post(
        reverse("reviews:manage_edit", kwargs={"pk": review.pk}),
        {**VALID_REVIEW, "title": "Tidied up", "comment": "Honestly [removed]."},
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == reverse("reviews:manage")
    review.refresh_from_db()
    assert (review.title, review.comment) == ("Tidied up", "Honestly [removed].")
    assert (review.author, review.display_name) == (customer, "c****r")
    assert review.edited_at is not None
    assert not review.is_flagged
    assert "“Tidied up” saved." in client.get(response.url).content.decode()


def test_manage_edit_without_changes_says_so_and_keeps_the_flag(
    client, staff_user, customer, product
):
    review = _review(product, customer, comment="Honestly a scam.")
    client.force_login(staff_user)

    response = client.post(
        reverse("reviews:manage_edit", kwargs={"pk": review.pk}),
        {"rating": "4", "title": review.title, "comment": review.comment},
    )

    review.refresh_from_db()
    assert review.is_flagged and review.edited_at is None
    page = client.get(response.url).content.decode()
    assert "No changes to “Reads my mind”." in page
    assert "“Reads my mind” saved." not in page


def test_manage_edit_shows_errors_in_place(client, staff_user, customer, product):
    review = _review(product, customer)
    client.force_login(staff_user)

    response = client.post(
        reverse("reviews:manage_edit", kwargs={"pk": review.pk}),
        {**VALID_REVIEW, "comment": ""},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["comment"]
    review.refresh_from_db()
    assert review.edited_at is None


def test_manage_delete_confirms_first(client, staff_user, customer, product):
    review = _review(product, customer, title="Going soon")
    client.force_login(staff_user)

    response = client.get(reverse("reviews:manage_delete", kwargs={"pk": review.pk}))

    assert response.status_code == HTTPStatus.OK
    assert "Delete “Going soon”?" in response.content.decode()
    assert Review.objects.filter(pk=review.pk).exists()


def test_manage_delete_deletes_and_redirects_with_a_message(
    client, staff_user, customer, product
):
    review = _review(product, customer, title="Going soon")
    client.force_login(staff_user)

    response = client.post(reverse("reviews:manage_delete", kwargs={"pk": review.pk}))

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == reverse("reviews:manage")
    assert not Review.objects.filter(pk=review.pk).exists()
    assert "“Going soon” deleted." in client.get(response.url).content.decode()


# --- Report a review --------------------------------------------------------


def test_a_report_flags_the_review_and_a_new_reporter_flags_it_again(
    customer, other_customer, product
):
    review = _review(product, _other_customer())

    ReviewReport.objects.create(
        review=review, reporter=customer, reason=ReviewReport.Reason.SPAM
    )
    review.refresh_from_db()
    assert review.is_flagged

    review.clear_flag()
    ReviewReport.objects.create(
        review=review, reporter=other_customer, reason=ReviewReport.Reason.OFF_TOPIC
    )
    review.refresh_from_db()
    assert review.is_flagged


@pytest.mark.parametrize(
    ("reason", "note", "valid"),
    [
        ("spam", "", True),
        ("offensive", "", True),
        ("off_topic", "", True),
        ("other", "", False),
        ("other", "   ", False),
        ("other", "Links to a rival store.", True),
    ],
)
def test_report_form_requires_a_note_only_for_other(reason, note, valid):
    form = ReviewReportForm({"reason": reason, "note": note})

    assert form.is_valid() is valid
    if not valid:
        assert "note" in form.errors


def test_report_refuses_the_author_staff_and_a_second_report(
    client, customer, staff_user, product
):
    review = _review(product, _other_customer())
    url = reverse("reviews:report", kwargs={"pk": review.pk})

    for user in (review.author, staff_user):
        client.force_login(user)
        assert client.post(url, {"reason": "spam"}).status_code == HTTPStatus.FORBIDDEN
    assert not review.reports.exists()

    client.force_login(customer)
    response = client.post(url, {"reason": "spam"})

    assert response.status_code == HTTPStatus.OK
    assert "Reported" in response.content.decode()
    assert review.reports.get().reporter == customer

    again = client.post(url, {"reason": "offensive"})

    assert again.status_code == HTTPStatus.FORBIDDEN
    assert review.reports.count() == 1


def test_a_simultaneous_second_report_says_reported_instead_of_crashing(
    client, customer, product, monkeypatch
):
    review = _review(product, _other_customer())
    ReviewReport.objects.create(
        review=review, reporter=customer, reason=ReviewReport.Reason.SPAM
    )
    # Both requests passed the "already reported?" check before either saved.
    monkeypatch.setattr(Review, "can_be_reported_by", lambda self, user: True)
    client.force_login(customer)

    response = client.post(
        reverse("reviews:report", kwargs={"pk": review.pk}), {"reason": "spam"}
    )

    assert response.status_code == HTTPStatus.OK
    assert "Reported" in response.content.decode()
    assert review.reports.count() == 1


def test_report_get_returns_the_form_in_place(client, customer, product):
    review = _review(product, _other_customer())
    client.force_login(customer)

    response = client.get(reverse("reviews:report", kwargs={"pk": review.pk}))

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "<html" not in page
    for label in ("Spam", "Offensive language", "Off-topic", "Other"):
        assert label in page
    assert f'hx-get="{reverse("reviews:card", kwargs={"pk": review.pk})}"' in page
    assert not review.reports.exists()


def test_report_get_refuses_the_author(client, product):
    author = _other_customer()
    review = _review(product, author)
    client.force_login(author)

    response = client.get(reverse("reviews:report", kwargs={"pk": review.pk}))

    assert response.status_code == HTTPStatus.FORBIDDEN


def test_report_shows_errors_in_place(client, customer, product):
    review = _review(product, _other_customer())
    client.force_login(customer)

    response = client.post(
        reverse("reviews:report", kwargs={"pk": review.pk}), {"reason": "other"}
    )

    assert response.status_code == HTTPStatus.OK
    assert "Tell us what&#x27;s wrong when choosing Other." in response.content.decode()
    assert not review.reports.exists()
    review.refresh_from_db()
    assert not review.is_flagged


def test_anonymous_report_redirects_to_login(client, product):
    review = _review(product, _other_customer())
    url = reverse("reviews:report", kwargs={"pk": review.pk})

    response = client.post(url, {"reason": "spam"})

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == f"{reverse('accounts:login')}?next={url}"
    assert not review.reports.exists()


def test_report_button_shows_only_on_other_customers_reviews(
    client, customer, staff_user, product
):
    own = _review(product, customer)
    other = _review(product, _other_customer())
    own_url = reverse("reviews:report", kwargs={"pk": own.pk})
    other_url = reverse("reviews:report", kwargs={"pk": other.pk})

    anonymous_page = _detail(client, product)
    client.force_login(staff_user)
    staff_page = _detail(client, product)
    client.force_login(customer)
    customer_page = _detail(client, product)

    assert other_url in customer_page and own_url not in customer_page
    assert "/report/" not in anonymous_page
    assert "/report/" not in staff_page


def test_reported_shows_on_load_for_a_review_already_reported(
    client, customer, product
):
    reported = _review(product, _other_customer())
    unreported = _review(product, get_user_model().objects.create_user("nadia"))
    ReviewReport.objects.create(
        review=reported, reporter=customer, reason=ReviewReport.Reason.SPAM
    )
    client.force_login(customer)

    page = _detail(client, product)
    card = client.get(reverse("reviews:card", kwargs={"pk": reported.pk}))

    assert reverse("reviews:report", kwargs={"pk": reported.pk}) not in page
    assert reverse("reviews:report", kwargs={"pk": unreported.pk}) in page
    assert page.count(">Reported<") == 1
    assert ">Reported<" in card.content.decode()


def test_show_more_marks_reviews_already_reported(client, customer, product):
    reviews = _others(product, 6)
    oldest = reviews[-1]
    ReviewReport.objects.create(
        review=oldest, reporter=customer, reason=ReviewReport.Reason.SPAM
    )
    client.force_login(customer)

    response = client.get(
        reverse("reviews:more", kwargs={"pk": product.pk}), {"page": 2}
    )

    page = response.content.decode()
    assert f'id="review-{oldest.pk}"' in page
    assert ">Reported<" in page


def test_reviews_tab_shows_report_counts_and_reasons(
    client, staff_user, customer, other_customer, product
):
    review = _review(product, _other_customer(), title="Reported one")
    _review(product, get_user_model().objects.create_user("nadia"))
    ReviewReport.objects.create(
        review=review, reporter=customer, reason=ReviewReport.Reason.SPAM
    )
    ReviewReport.objects.create(
        review=review,
        reporter=other_customer,
        reason=ReviewReport.Reason.OTHER,
        note="Links to a rival store.",
    )
    client.force_login(staff_user)

    page = client.get(reverse("reviews:manage")).content.decode()

    assert "2 reports" in page
    assert "Spam" in page
    assert "Other: “Links to a rival store.”" in page


def test_deleting_the_product_deletes_its_reviews_reports(customer, product):
    review = _review(product, _other_customer())
    ReviewReport.objects.create(
        review=review, reporter=customer, reason=ReviewReport.Reason.SPAM
    )

    product.delete()

    assert not ReviewReport.objects.exists()


def test_review_reporter_pair_is_unique(customer, product):
    review = _review(product, _other_customer())
    ReviewReport.objects.create(
        review=review, reporter=customer, reason=ReviewReport.Reason.SPAM
    )

    with pytest.raises(IntegrityError):
        ReviewReport.objects.create(
            review=review, reporter=customer, reason=ReviewReport.Reason.OFF_TOPIC
        )


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

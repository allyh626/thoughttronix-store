"""``{% review_section product %}`` — the reviews block on a product page.

Lives here rather than in the product detail view, so the reviews app
owns everything about reviews and the products app only places the tag.
"""

from django import template
from django.core.paginator import Paginator

from ..forms import ReviewForm
from ..models import Review, ReviewQuerySet

register = template.Library()


@register.inclusion_tag("reviews/partials/_section.html", takes_context=True)
def review_section(context, product):
    """The visitor's own review pinned first, then the first page of
    everyone else's, newest first, plus what this visitor may do.

    ``prompt`` is one of ``"form"`` (an eligible customer), ``"sign_in"``
    (a signed-out visitor), ``"ineligible"`` (no Delivered order of the
    product), or ``None`` (staff, or a customer who already reviewed it).
    """
    user = context["user"]
    own_review = (
        product.reviews.filter(author=user).first() if user.is_authenticated else None
    )
    if not user.is_authenticated:
        prompt = "sign_in"
    elif Review.objects.can_write(user, product):
        prompt = "form"
    elif user.is_staff or own_review:
        prompt = None
    else:
        prompt = "ineligible"
    others = product.reviews.others_than(user)
    return {
        "product": product,
        "summary": product.reviews.rating_summary(),
        "own_review": own_review,
        "page": Paginator(others, ReviewQuerySet.PAGE_SIZE).get_page(1),
        "prompt": prompt,
        "form": ReviewForm() if prompt == "form" else None,
        "request": context["request"],
    }

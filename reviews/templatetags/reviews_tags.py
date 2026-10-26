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

    ``prompt`` comes from ``Review.objects.prompt_for``.
    """
    user = context["user"]
    own_review = (
        product.reviews.filter(author=user).first() if user.is_authenticated else None
    )
    prompt = Review.objects.prompt_for(user, product)
    others = product.reviews.others_than(user)
    return {
        "user": user,
        "product": product,
        "summary": product.reviews.rating_summary(),
        "own_review": own_review,
        "page": Paginator(others, ReviewQuerySet.PAGE_SIZE).get_page(1),
        "prompt": prompt,
        "form": ReviewForm() if prompt == "form" else None,
        "request": context["request"],
    }

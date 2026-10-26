"""``{% review_section product %}`` — the reviews block on a product page.

Lives here rather than in the product detail view, so the reviews app
owns everything about reviews and the products app only places the tag.
"""

from django import template

from ..forms import ReviewForm
from ..models import Review

register = template.Library()


@register.inclusion_tag("reviews/partials/_section.html", takes_context=True)
def review_section(context, product):
    """Every review, newest first, plus what this visitor may do.

    ``prompt`` is one of ``"form"`` (an eligible customer), ``"sign_in"``
    (a signed-out visitor), ``"ineligible"`` (no Delivered order of the
    product), or ``None`` (staff, or a customer who already reviewed it).
    """
    user = context["user"]
    if not user.is_authenticated:
        prompt = "sign_in"
    elif Review.objects.can_write(user, product):
        prompt = "form"
    elif user.is_staff or product.reviews.filter(author=user).exists():
        prompt = None
    else:
        prompt = "ineligible"
    return {
        "product": product,
        "reviews": product.reviews.all(),
        "prompt": prompt,
        "form": ReviewForm() if prompt == "form" else None,
        "request": context["request"],
    }

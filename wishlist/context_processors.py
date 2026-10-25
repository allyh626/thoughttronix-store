"""Wishlist context for every page render.

``base.html`` shows the navbar wishlist badge on every page, and the
product detail page's wishlist button needs to know whether the product
is saved — one small query per authenticated request supplies both.
"""

from .models import WishlistItem


def wishlist(request):
    if not request.user.is_authenticated:
        return {"wishlist_item_count": 0, "wishlist_product_ids": set()}
    product_ids = set(
        WishlistItem.objects.filter(wishlist__user=request.user).values_list(
            "product_id", flat=True
        )
    )
    return {
        "wishlist_item_count": len(product_ids),
        "wishlist_product_ids": product_ids,
    }

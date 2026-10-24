"""Wishlist context for every page render.

The product detail page's wishlist button needs to know whether the
product is saved — one small query per authenticated request supplies
the saved product ids.
"""

from .models import WishlistItem


def wishlist(request):
    if not request.user.is_authenticated:
        return {"wishlist_product_ids": set()}
    return {
        "wishlist_product_ids": set(
            WishlistItem.objects.filter(wishlist__user=request.user).values_list(
                "product_id", flat=True
            )
        )
    }

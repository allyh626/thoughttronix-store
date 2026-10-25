"""Wishlist views — thin per the architecture convention.

Every view reaches data only through the signed-in user's own wishlist,
never by a bare wishlist or item id. HTMX endpoints render the button
partial (never ``base.html``) with the navbar badge as an out-of-band
swap via the ``oob_badge`` context flag; the wishlist context processor
runs at render time, so both always show the state after the change.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import ListView

from products.models import Product

from .models import Wishlist, WishlistItem


class WishlistView(LoginRequiredMixin, ListView):
    """The My wishlist page: the signed-in user's saved products."""

    template_name = "wishlist/wishlist.html"
    context_object_name = "items"

    def get_queryset(self):
        return WishlistItem.objects.filter(
            wishlist__user=self.request.user
        ).select_related("product__category")


class AddToWishlistView(LoginRequiredMixin, View):
    """HTMX: save a product; the button swaps to its saved state.

    Any product can be saved, unavailable ones included, so the lookup
    does not go through ``available()`` the way add-to-cart does.
    """

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        Wishlist.for_user(request.user).add(product)
        return render(
            request,
            "wishlist/partials/_wishlist_button.html",
            {"product": product, "oob_badge": True},
        )


class RemoveFromWishlistView(LoginRequiredMixin, View):
    """Unsave a product, for two callers.

    HTMX (the detail page): the button swaps back to its unsaved state.
    A plain form post (the My wishlist page): redirect back to the list
    with a success message.
    """

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        Wishlist.for_user(request.user).remove(product)
        if not request.headers.get("HX-Request"):
            messages.success(request, f"Removed {product} from your wishlist.")
            return redirect("wishlist:list")
        return render(
            request,
            "wishlist/partials/_wishlist_button.html",
            {"product": product, "oob_badge": True},
        )

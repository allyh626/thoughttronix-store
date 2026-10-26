"""Review views — thin per the architecture convention.

HTMX endpoints render partials from ``reviews/partials/`` (never
``base.html``).
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.views import View

from products.models import Product

from .forms import ReviewForm
from .models import Review


class CreateReviewView(LoginRequiredMixin, View):
    """HTMX: post a review of a product.

    A valid review replaces the form (the customer now has a review, so no
    form comes back) and joins the top of the list out-of-band. Errors
    re-render the form in place.
    """

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        if not Review.objects.can_write(request.user, product):
            return HttpResponseForbidden("You can't review this product.")
        form = ReviewForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                "reviews/partials/_form.html",
                {"form": form, "product": product},
            )
        review = form.save(commit=False)
        review.product = product
        review.author = request.user
        review.save()
        return render(request, "reviews/partials/_created.html", {"review": review})

"""Review views — thin per the architecture convention.

HTMX endpoints render partials from ``reviews/partials/`` (never
``base.html``).
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.views import View

from products.models import Product

from .forms import ReviewForm
from .models import Review, ReviewQuerySet


class CreateReviewView(LoginRequiredMixin, View):
    """HTMX: post a review of a product.

    A valid review replaces the form (the customer now has a review, so no
    form comes back) and joins the top of the list out-of-band, with the
    average and count. Errors re-render the form in place.
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
        return render(
            request,
            "reviews/partials/_created.html",
            {"review": review, "summary": product.reviews.rating_summary()},
        )


class MoreReviewsView(View):
    """HTMX: "Show more" — the next page of everyone else's reviews.

    The cards append to the list out-of-band; the button replaces itself
    with the one for the following page, or with nothing on the last.
    """

    def get(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        others = product.reviews.others_than(request.user)
        page = Paginator(others, ReviewQuerySet.PAGE_SIZE).get_page(
            request.GET.get("page")
        )
        return render(
            request, "reviews/partials/_more.html", {"product": product, "page": page}
        )


class ReviewCardView(View):
    """HTMX: one review card — what Cancel on the edit form swaps back."""

    def get(self, request, pk):
        review = get_object_or_404(Review, pk=pk)
        return render(request, "reviews/partials/_card.html", {"review": review})


class EditReviewView(LoginRequiredMixin, View):
    """HTMX: edit your own review in place.

    GET swaps the card for a pre-filled form; a valid POST swaps the
    updated card back, with the average and count out-of-band. Reviews are
    reached through ``request.user``, so anyone else's is a 404.
    """

    def get(self, request, pk):
        review = get_object_or_404(request.user.reviews, pk=pk)
        return render(
            request,
            "reviews/partials/_edit_form.html",
            {"review": review, "form": ReviewForm(instance=review)},
        )

    def post(self, request, pk):
        review = get_object_or_404(request.user.reviews, pk=pk)
        form = ReviewForm(request.POST, instance=review)
        if not form.is_valid():
            return render(
                request,
                "reviews/partials/_edit_form.html",
                {"review": review, "form": form},
            )
        review = form.save(commit=False)
        review.save_edit()
        return render(
            request,
            "reviews/partials/_edited.html",
            {"review": review, "summary": review.product.reviews.rating_summary()},
        )


class DeleteReviewView(LoginRequiredMixin, View):
    """HTMX: delete your own review.

    The empty response removes the card; out-of-band, the average and
    count update and the prompt returns — the form, if the customer is
    still eligible to write a new review.
    """

    def post(self, request, pk):
        review = get_object_or_404(request.user.reviews, pk=pk)
        product = review.product
        review.delete()
        prompt = Review.objects.prompt_for(request.user, product)
        return render(
            request,
            "reviews/partials/_deleted.html",
            {
                "product": product,
                "summary": product.reviews.rating_summary(),
                "prompt": prompt,
                "form": ReviewForm() if prompt == "form" else None,
            },
        )

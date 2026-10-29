"""Review views — thin per the architecture convention.

HTMX endpoints render partials from ``reviews/partials/`` (never
``base.html``).
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import DeleteView, ListView, UpdateView

from accounts.mixins import StaffRequiredMixin
from products.models import Product

from .forms import ReviewForm, ReviewReportForm
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
    """HTMX: one review card — what Cancel on the edit and report forms
    swaps back."""

    def get(self, request, pk):
        review = get_object_or_404(Review.objects.with_reported_by(request.user), pk=pk)
        return render(request, "reviews/partials/_card.html", {"review": review})


class EditReviewView(LoginRequiredMixin, View):
    """HTMX: edit a review in place — your own, or any review for staff.

    GET swaps the card for a pre-filled form; a valid POST swaps the
    updated card back, with the average and count out-of-band. A customer
    reaches only their own reviews, so anyone else's is a 404.
    """

    def get(self, request, pk):
        review = get_object_or_404(Review.objects.editable_by(request.user), pk=pk)
        return render(
            request,
            "reviews/partials/_edit_form.html",
            {"review": review, "form": ReviewForm(instance=review)},
        )

    def post(self, request, pk):
        review = get_object_or_404(Review.objects.editable_by(request.user), pk=pk)
        form = ReviewForm(request.POST, instance=review)
        if not form.is_valid():
            return render(
                request,
                "reviews/partials/_edit_form.html",
                {"review": review, "form": form},
            )
        if form.has_changed():  # an unchanged save isn't an edit
            review = form.save(commit=False)
            review.save_edit(request.user)
        return render(
            request,
            "reviews/partials/_edited.html",
            {"review": review, "summary": review.product.reviews.rating_summary()},
        )


class DeleteReviewView(LoginRequiredMixin, View):
    """HTMX: delete a review — your own, or any review for staff.

    The empty response removes the card; out-of-band, the average and
    count update and the prompt returns — the form, if the customer is
    still eligible to write a new review (never for staff).
    """

    def post(self, request, pk):
        review = get_object_or_404(Review.objects.editable_by(request.user), pk=pk)
        product = review.product
        review.delete()
        prompt = Review.objects.prompt_for(request.user, product, reviewed=False)
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


class ReportReviewView(LoginRequiredMixin, View):
    """HTMX: report someone else's review.

    GET swaps the Report button for the reason and note form; a valid POST
    flags the review and swaps in "Reported". Errors re-render the form.
    """

    def _form(self, review, data=None):
        # Ids unique per review, so two open report forms never clash.
        return ReviewReportForm(data, auto_id=f"id_report_{review.pk}_%s")

    def _review(self, request, pk):
        """The review, or ``None`` when this user may not report it."""
        review = get_object_or_404(Review, pk=pk)
        return review if review.can_be_reported_by(request.user) else None

    def get(self, request, pk):
        review = self._review(request, pk)
        if review is None:
            return HttpResponseForbidden("You can't report this review.")
        return render(
            request,
            "reviews/partials/_report_form.html",
            {"review": review, "form": self._form(review)},
        )

    def post(self, request, pk):
        review = self._review(request, pk)
        if review is None:
            return HttpResponseForbidden("You can't report this review.")
        form = self._form(review, request.POST)
        if not form.is_valid():
            return render(
                request,
                "reviews/partials/_report_form.html",
                {"review": review, "form": form},
            )
        report = form.save(commit=False)
        report.review = review
        report.reporter = request.user
        try:
            report.save()
        except IntegrityError:
            pass  # a simultaneous request already filed this customer's report
        return render(request, "reviews/partials/_reported.html")


# --- The back office --------------------------------------------------------
#
# Staff-only oversight of every review, with the full username the product
# page never shows. The ``section`` context entry drives the active tab.


class ManageReviewListView(StaffRequiredMixin, ListView):
    """Every review, flagged first, filterable via ``?filter=flagged``."""

    template_name = "reviews/manage_reviews.html"
    context_object_name = "reviews"
    paginate_by = 20
    extra_context = {"section": "reviews"}

    def _active_filter(self):
        """``"flagged"`` or ``""`` (All) — an unknown value means All."""
        return "flagged" if self.request.GET.get("filter") == "flagged" else ""

    def get_queryset(self):
        reviews = (
            Review.objects.select_related("product", "author")
            .prefetch_related("reports")
            .for_moderation()
        )
        if self._active_filter():
            reviews = reviews.filter(is_flagged=True)
        return reviews

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["active_filter"] = self._active_filter()
        return context


class ClearFlagView(StaffRequiredMixin, View):
    """POST-only: staff have checked a flagged review and it's fine.

    Redirects back to the filter tab the form was on.
    """

    def post(self, request, pk):
        review = get_object_or_404(Review, pk=pk)
        review.clear_flag()
        messages.success(request, f"Flag cleared on “{review.title}”.")
        url = reverse("reviews:manage")
        if request.POST.get("filter") == "flagged":
            url += "?filter=flagged"
        return redirect(url)


class ManageReviewUpdateView(StaffRequiredMixin, UpdateView):
    """Edit any review. As on the product page, the author and censored
    name stay, the review is marked edited, and its flag clears."""

    queryset = Review.objects.select_related("product", "author")
    form_class = ReviewForm
    context_object_name = "review"
    template_name = "reviews/manage_review_form.html"
    success_url = reverse_lazy("reviews:manage")
    extra_context = {"section": "reviews"}

    def form_valid(self, form):
        # An unchanged save isn't an edit: nothing is written and a flag
        # stays, so say so rather than "saved".
        if form.has_changed():
            form.instance.save_edit(self.request.user)
            messages.success(self.request, f"“{form.instance.title}” saved.")
        else:
            messages.info(self.request, f"No changes to “{form.instance.title}”.")
        return redirect(self.success_url)


class ManageReviewDeleteView(StaffRequiredMixin, SuccessMessageMixin, DeleteView):
    """Delete any review, after a confirmation page."""

    queryset = Review.objects.select_related("product", "author")
    context_object_name = "review"
    template_name = "reviews/manage_review_confirm_delete.html"
    success_url = reverse_lazy("reviews:manage")
    extra_context = {"section": "reviews"}

    def get_success_message(self, cleaned_data):
        return f"“{self.object.title}” deleted."

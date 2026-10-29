"""The customer's review form.

The model carries the rules — a 1–5 rating, a 50-character title, a
1,000-character comment, all required — and the ModelForm inherits them.
"""

from django import forms

from products.forms import StyledModelForm

from .models import Review, ReviewReport

RATING_CHOICES = [("", "Choose a rating")] + [
    (stars, f"{'★' * stars}{'☆' * (5 - stars)} ({stars})") for stars in range(5, 0, -1)
]


class ReviewForm(StyledModelForm):
    class Meta:
        model = Review
        fields = ["rating", "title", "comment"]
        widgets = {
            "rating": forms.Select(choices=RATING_CHOICES),
            "comment": forms.Textarea(attrs={"rows": 4}),
        }


class ReviewReportForm(StyledModelForm):
    class Meta:
        model = ReviewReport
        fields = ["reason", "note"]
        widgets = {"note": forms.Textarea(attrs={"rows": 2})}

    def clean(self):
        """The note is optional, except that "Other" needs one — staff
        can't act on a report that says nothing about what is wrong."""
        cleaned_data = super().clean()
        if cleaned_data.get(
            "reason"
        ) == ReviewReport.Reason.OTHER and not cleaned_data.get("note"):
            self.add_error("note", "Tell us what's wrong when choosing Other.")
        return cleaned_data

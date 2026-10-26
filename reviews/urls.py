from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path(
        "reviews/product/<int:pk>/new/",
        views.CreateReviewView.as_view(),
        name="create",
    ),
    path(
        "reviews/product/<int:pk>/more/",
        views.MoreReviewsView.as_view(),
        name="more",
    ),
]

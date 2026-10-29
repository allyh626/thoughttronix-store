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
    path("reviews/<int:pk>/", views.ReviewCardView.as_view(), name="card"),
    path("reviews/<int:pk>/edit/", views.EditReviewView.as_view(), name="edit"),
    path("reviews/<int:pk>/delete/", views.DeleteReviewView.as_view(), name="delete"),
    path("reviews/<int:pk>/report/", views.ReportReviewView.as_view(), name="report"),
    path(
        "backoffice/reviews/",
        views.ManageReviewListView.as_view(),
        name="manage",
    ),
    path(
        "backoffice/reviews/<int:pk>/edit/",
        views.ManageReviewUpdateView.as_view(),
        name="manage_edit",
    ),
    path(
        "backoffice/reviews/<int:pk>/delete/",
        views.ManageReviewDeleteView.as_view(),
        name="manage_delete",
    ),
    path(
        "backoffice/reviews/<int:pk>/clear-flag/",
        views.ClearFlagView.as_view(),
        name="clear_flag",
    ),
]

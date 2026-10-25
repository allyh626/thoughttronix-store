from django.urls import path

from . import views

app_name = "wishlist"

urlpatterns = [
    path("wishlist/", views.WishlistView.as_view(), name="list"),
    path("wishlist/add/<int:pk>/", views.AddToWishlistView.as_view(), name="add"),
    path(
        "wishlist/remove/<int:pk>/",
        views.RemoveFromWishlistView.as_view(),
        name="remove",
    ),
]

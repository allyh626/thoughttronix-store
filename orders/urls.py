from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("cart/", views.CartView.as_view(), name="cart"),
    path("cart/add/<int:pk>/", views.AddToCartView.as_view(), name="add"),
    path(
        "cart/items/<int:pk>/increment/",
        views.IncrementCartItemView.as_view(),
        name="increment",
    ),
    path(
        "cart/items/<int:pk>/decrement/",
        views.DecrementCartItemView.as_view(),
        name="decrement",
    ),
    path(
        "cart/items/<int:pk>/remove/",
        views.RemoveCartItemView.as_view(),
        name="remove",
    ),
    path("checkout/", views.CheckoutView.as_view(), name="checkout"),
    path(
        "checkout/address-fields/<str:kind>/",
        views.CheckoutAddressFieldsView.as_view(),
        name="checkout_address_fields",
    ),
    path(
        "checkout/coupon/",
        views.ApplyCouponView.as_view(),
        name="checkout_coupon",
    ),
    path("orders/", views.OrderHistoryView.as_view(), name="history"),
    path("orders/<int:pk>/", views.OrderDetailView.as_view(), name="detail"),
    path(
        "orders/<int:pk>/confirmation/",
        views.OrderConfirmationView.as_view(),
        name="confirmation",
    ),
    # Back office — staff-only, pk URLs per the URL conventions.
    path(
        "backoffice/orders/",
        views.ManageOrderListView.as_view(),
        name="manage_orders",
    ),
    path(
        "backoffice/orders/<int:pk>/",
        views.ManageOrderDetailView.as_view(),
        name="manage_order_detail",
    ),
    path(
        "backoffice/orders/<int:pk>/status/",
        views.UpdateOrderStatusView.as_view(),
        name="manage_order_status",
    ),
    path(
        "backoffice/coupons/",
        views.ManageCouponListView.as_view(),
        name="manage_coupons",
    ),
    path(
        "backoffice/coupons/new/",
        views.ManageCouponCreateView.as_view(),
        name="manage_coupon_create",
    ),
    path(
        "backoffice/coupons/<int:pk>/edit/",
        views.ManageCouponUpdateView.as_view(),
        name="manage_coupon_update",
    ),
    path(
        "backoffice/coupons/<int:pk>/retire/",
        views.RetireCouponView.as_view(),
        name="manage_coupon_retire",
    ),
    path(
        "backoffice/coupons/<int:pk>/delete/",
        views.ManageCouponDeleteView.as_view(),
        name="manage_coupon_delete",
    ),
    path(
        "backoffice/coupons/products/<int:pk>/",
        views.CouponProductGroupView.as_view(),
        name="coupon_product_group",
    ),
]

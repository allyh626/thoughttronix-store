from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.AccountView.as_view(), name="account"),
    path("signup/", views.SignupView.as_view(), name="signup"),
    path("login/", views.SignInView.as_view(), name="login"),
    path("logout/", views.SignOutView.as_view(), name="logout"),
    # Before the token route, or "resend" would be read as a token.
    path(
        "verify-email/resend/",
        views.ResendVerificationView.as_view(),
        name="resend_verification",
    ),
    path(
        "verify-email/<str:token>/",
        views.VerifyEmailView.as_view(),
        name="verify_email",
    ),
    path("email/change/", views.ChangeEmailView.as_view(), name="change_email"),
    path(
        "password/change/",
        views.ChangePasswordView.as_view(),
        name="change_password",
    ),
    path(
        "password/reset/",
        views.PasswordResetRequestView.as_view(),
        name="password_reset",
    ),
    path(
        "password/reset/done/",
        views.PasswordResetSentView.as_view(),
        name="password_reset_done",
    ),
    path(
        "password/reset/<uidb64>/<token>/",
        views.PasswordResetSetView.as_view(),
        name="password_reset_confirm",
    ),
    path("addresses/new/", views.AddressCreateView.as_view(), name="address_create"),
    path(
        "addresses/<int:pk>/edit/",
        views.AddressUpdateView.as_view(),
        name="address_update",
    ),
    path(
        "addresses/<int:pk>/delete/",
        views.AddressDeleteView.as_view(),
        name="address_delete",
    ),
    path(
        "addresses/<int:pk>/default/<str:kind>/",
        views.SetDefaultAddressView.as_view(),
        name="address_set_default",
    ),
]

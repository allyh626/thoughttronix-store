from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.core import signing
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    FormView,
    TemplateView,
    UpdateView,
)

from .forms import (
    AddressForm,
    ChangeEmailForm,
    ChangePasswordForm,
    PasswordResetRequestForm,
    ResetPasswordForm,
    SignInForm,
    SignupForm,
)
from .models import Address, SignInAttempt, User


class SignupView(SuccessMessageMixin, CreateView):
    """Create a customer account, mail a verification link, then hand off
    to the login page.

    New users sign in themselves — auto-login after signup is left as a
    student exercise.
    """

    form_class = SignupForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("accounts:login")
    success_message = (
        "Account created — check your email for a verification link, then sign in."
    )

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.send_verification_email(self.request)
        return response


class VerifyEmailView(View):
    """The link from a verification email. No sign-in needed — the signed
    token says who it is for."""

    def get(self, request, token):
        try:
            user = User.verify_email_token(token)
        except signing.BadSignature:
            return render(request, "accounts/verify_email_failed.html", status=400)
        messages.success(request, f"Thanks — {user.email} is verified.")
        return redirect(
            "accounts:account" if request.user.is_authenticated else "accounts:login"
        )


class ResendVerificationView(LoginRequiredMixin, View):
    """POST-only: mail a fresh verification link for an unverified or
    pending email."""

    def post(self, request):
        user = request.user
        if user.email_to_confirm:
            user.send_verification_email(request)
            messages.success(
                request, f"Verification email sent to {user.email_to_confirm}."
            )
        else:
            messages.info(request, "There's no unverified email to confirm.")
        return redirect("accounts:account")


class ChangeEmailView(LoginRequiredMixin, FormView):
    """Add or change the email. The new address waits as ``pending_email``
    until its link is opened, so a typo can't lock the customer out."""

    form_class = ChangeEmailForm
    template_name = "accounts/change_email.html"
    success_url = reverse_lazy("accounts:account")

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.request.user}

    def form_valid(self, form):
        user = form.save()
        user.send_verification_email(self.request)
        messages.success(
            self.request,
            f"Check {user.pending_email} for a confirmation link. "
            "The change takes effect once you open it.",
        )
        return super().form_valid(form)


class ChangePasswordView(PasswordChangeView):
    """Django's own password change. It keeps this session signed in;
    every other session ends because its fingerprint was the old password.
    """

    form_class = ChangePasswordForm
    template_name = "accounts/change_password.html"
    success_url = reverse_lazy("accounts:account")

    def form_valid(self, form):
        response = super().form_valid(form)
        form.user.send_password_changed_notice()
        messages.success(
            self.request,
            "Password changed. Every other device has been signed out.",
        )
        return response


# --- Forgotten password -------------------------------------------------------
#
# Django's own reset views. No sign-in needed: the emailed link says who it
# is for, lasts PASSWORD_RESET_TIMEOUT, and stops working once the password
# changes.


class PasswordResetRequestView(PasswordResetView):
    """Ask for a reset link. Every email lands on the same "check your
    email" page, so the page never reveals who has an account."""

    form_class = PasswordResetRequestForm
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/emails/password_reset.txt"
    subject_template_name = "accounts/emails/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class PasswordResetSentView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class PasswordResetSetView(PasswordResetConfirmView):
    """Choose a new password from a reset link, then sign in with it —
    there's no automatic sign-in."""

    form_class = ResetPasswordForm
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:login")

    def form_valid(self, form):
        response = super().form_valid(form)
        form.user.send_password_changed_notice()
        SignInAttempt.objects.record(
            form.user.username, succeeded=True, kind=SignInAttempt.Kind.PASSWORD_RESET
        )
        messages.success(
            self.request, "Your password has been reset. Sign in with the new one."
        )
        return response


class SignInView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = SignInForm


class SignOutView(LogoutView):
    def post(self, request, *args, **kwargs):
        # Flash after super() has flushed the session, or the message
        # would be wiped along with it.
        response = super().post(request, *args, **kwargs)
        messages.info(request, "You have signed out.")
        return response


# --- My account and the address book -----------------------------------------
#
# Every address view goes through the owner's own book — never a bare pk —
# so another customer's address 404s. All of them return to My account.


class AccountView(LoginRequiredMixin, TemplateView):
    """My account: the username, sign-in & security, then the address book.
    Future account features arrive as new sections on this page."""

    template_name = "accounts/account.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["addresses"] = sorted(
            user.addresses.all(), key=lambda a: (a.label or a.name).lower()
        )
        context["recent_attempts"] = SignInAttempt.objects.for_user(user)[:5]
        return context


class OwnAddressesMixin(LoginRequiredMixin):
    """Addresses are always fetched through the owner — never by bare pk."""

    success_url = reverse_lazy("accounts:account")

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)


class AddressCreateView(OwnAddressesMixin, SuccessMessageMixin, CreateView):
    form_class = AddressForm
    template_name = "accounts/address_form.html"
    success_message = "Address saved."

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)


class AddressUpdateView(OwnAddressesMixin, SuccessMessageMixin, UpdateView):
    form_class = AddressForm
    template_name = "accounts/address_form.html"
    success_message = "Address updated."


class AddressDeleteView(OwnAddressesMixin, SuccessMessageMixin, DeleteView):
    """Confirm, then delete. Deleting a default leaves no default — the
    flag goes with the row; nothing is promoted in its place."""

    template_name = "accounts/address_confirm_delete.html"
    context_object_name = "address"
    success_message = "Address deleted."


class SetDefaultAddressView(OwnAddressesMixin, View):
    """POST-only: make an address the default for shipping or billing."""

    def post(self, request, pk, kind):
        if kind not in Address.KINDS:
            raise Http404
        address = get_object_or_404(self.get_queryset(), pk=pk)
        address.make_default(kind)
        messages.success(request, f"{address} is now your default {kind} address.")
        return redirect(self.success_url)

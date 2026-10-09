from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.messages.views import SuccessMessageMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, TemplateView, UpdateView

from .forms import AddressForm, SignInForm, SignupForm
from .models import Address


class SignupView(SuccessMessageMixin, CreateView):
    """Create a customer account, then hand off to the login page.

    New users sign in themselves — auto-login after signup is left as a
    student exercise.
    """

    form_class = SignupForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("accounts:login")
    success_message = "Account created — you can now sign in."


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
    """My account: the username, then the address book. Future account
    features arrive as new sections on this page."""

    template_name = "accounts/account.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["addresses"] = sorted(
            self.request.user.addresses.all(), key=lambda a: (a.label or a.name).lower()
        )
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

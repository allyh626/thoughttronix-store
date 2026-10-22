from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)

from .models import Address, SignInAttempt, User


class SignupForm(UserCreationForm):
    """Django's stock signup fields plus a required email.

    The email is unique ignoring capitalization, and saved lowercase. The
    widgets carry DaisyUI classes because plain Django forms own their own
    styling here.
    """

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The model allows no email (older accounts); new signups must give one.
        self.fields["email"].required = True
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


class ChangeEmailForm(forms.Form):
    """Add or change the account's email, confirmed with the current password.

    The new address is only saved as ``pending_email``; it takes over once
    the link sent to it is opened.
    """

    email = forms.EmailField(label="New email")
    password = forms.CharField(
        label="Current password", strip=False, widget=forms.PasswordInput
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if email == self.user.email:
            raise forms.ValidationError("That's already your email.")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError(
                "Your current password was entered incorrectly."
            )
        return password

    def save(self):
        self.user.pending_email = self.cleaned_data["email"]
        self.user.save(update_fields=["pending_email"])
        return self.user


class ConfirmPasswordForm(forms.Form):
    """Confirm a sensitive action, like signing out other devices, with the
    current password."""

    password = forms.CharField(
        label="Current password", strip=False, widget=forms.PasswordInput
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["password"].widget.attrs["class"] = "input w-full"

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError(
                "Your current password was entered incorrectly."
            )
        return password


class ChangePasswordForm(PasswordChangeForm):
    """The stock password change form — current password, then the new one
    twice, checked against ``AUTH_PASSWORD_VALIDATORS`` — in DaisyUI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class PasswordResetRequestForm(PasswordResetForm):
    """The stock "email me a reset link" form, in DaisyUI.

    Mail goes only to active users with a usable password (Django's own
    rule) and a verified email (ours). The page looks the same either way.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"

    def get_users(self, email):
        return (user for user in super().get_users(email) if user.email_verified)


class ResetPasswordForm(SetPasswordForm):
    """The stock "choose a new password" form from a reset link, in DaisyUI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class SignInForm(AuthenticationForm):
    """The stock authentication form, dressed in DaisyUI.

    Every real attempt — a username and password both given — is recorded
    as a ``SignInAttempt``, succeeded or failed, whether or not the
    username exists. A locked-out username is refused before the password
    is checked, and that refusal isn't recorded, so retrying while paused
    never extends the pause.
    """

    error_messages = {
        **AuthenticationForm.error_messages,
        "locked_out": (
            "Too many failed attempts — try again in a few minutes, "
            "or reset your password."
        ),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"

    def clean(self):
        username = self.cleaned_data.get("username")
        if not (username and self.cleaned_data.get("password")):
            return super().clean()
        if SignInAttempt.objects.is_locked_out(username):
            raise forms.ValidationError(
                self.error_messages["locked_out"], code="locked_out"
            )
        try:
            cleaned_data = super().clean()
        except forms.ValidationError:
            # ``user_cache`` is set only when the password matched; a match
            # refused by ``confirm_login_allowed`` is recorded there instead.
            if self.user_cache is None:
                SignInAttempt.objects.record(username, succeeded=False)
            raise
        SignInAttempt.objects.record(username, succeeded=True)
        return cleaned_data


class AdminSignInForm(SignInForm, AdminAuthenticationForm):
    """The Django admin's login form with the same lockout and recording as
    the storefront's, so ``/admin/`` is no back door for guessing.

    ``SignInForm.clean`` runs first; its ``super().clean()`` then reaches the
    admin form's staff-only rule. A customer's right password refused by that
    rule is recorded as an admin sign-in refused, which shows in their
    recent activity but never counts toward the lockout.
    """

    error_messages = {
        **AdminAuthenticationForm.error_messages,
        "locked_out": SignInForm.error_messages["locked_out"],
    }

    def confirm_login_allowed(self, user):
        try:
            super().confirm_login_allowed(user)
        except forms.ValidationError:
            SignInAttempt.objects.record(
                user.username, succeeded=False, kind=SignInAttempt.Kind.ADMIN_DENIED
            )
            raise


class AddressForm(forms.ModelForm):
    """Add or edit a saved address. The rules come from the model fields,
    which share ``accounts.validators`` with checkout. Defaults are set
    from My account, never here."""

    class Meta:
        model = Address
        fields = ["label", "name", "street", "line2", "city", "state", "zip"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.Select):
                widget.attrs["class"] = "select w-full"
            else:
                widget.attrs["class"] = "input w-full"

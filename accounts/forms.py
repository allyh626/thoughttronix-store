from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    UserCreationForm,
)

from .models import Address, User


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


class ChangePasswordForm(PasswordChangeForm):
    """The stock password change form — current password, then the new one
    twice, checked against ``AUTH_PASSWORD_VALIDATORS`` — in DaisyUI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class SignInForm(AuthenticationForm):
    """The stock authentication form, dressed in DaisyUI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


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

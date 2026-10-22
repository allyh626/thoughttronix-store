from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .forms import AdminSignInForm
from .models import Address, User

# /admin/ gets the same sign-in lockout as the storefront.
admin.site.login_form = AdminSignInForm


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        *DjangoUserAdmin.fieldsets,
        ("ThoughtTronix", {"fields": ("job_title",)}),
    )
    list_display = ("username", "email", "job_title", "is_staff")


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """Superusers only — the staff back office never shows saved addresses."""

    list_display = (
        "user",
        "label",
        "city",
        "state",
        "is_default_shipping",
        "is_default_billing",
    )
    search_fields = ("user__username",)

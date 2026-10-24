from django.contrib import admin

from .models import Wishlist, WishlistItem


class WishlistItemInline(admin.TabularInline):
    model = WishlistItem
    extra = 0
    readonly_fields = ("added_at",)


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("user",)
    search_fields = ("user__username",)
    inlines = [WishlistItemInline]

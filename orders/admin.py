from django.contrib import admin

from .models import Cart, CartItem, Coupon, Order, OrderItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "item_count", "total")
    search_fields = ("user__username",)
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "user", "status", "total", "coupon_code", "created_at")
    list_filter = ("status",)
    search_fields = ("user__username", "shipping_name", "coupon_code")
    date_hierarchy = "created_at"
    inlines = [OrderItemInline]


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "kind",
        "value",
        "scope",
        "starts_on",
        "ends_on",
        "is_retired",
    )
    list_filter = ("kind", "scope", "is_retired")
    search_fields = ("code",)
    filter_horizontal = ("products",)

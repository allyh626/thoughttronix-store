"""Cart and checkout views — thin per the architecture convention.

The three HTMX interactions of the core live here: add-to-cart, quantity
change, and line removal. Each renders a partial (never ``base.html``);
the responses carry the navbar badge as an out-of-band swap via the
``oob_badge`` context flag. Checkout is conventional full-page work:
validate the form, hand everything to ``place_order`` — plus HTMX
endpoints that fill an address section from the customer's address book
and apply a coupon to the order summary.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, ProtectedError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from accounts.mixins import StaffRequiredMixin
from accounts.models import Address
from products.models import Category, Product

from .forms import CheckoutForm, CouponForm, OrderStatusForm
from .models import Cart, CartItem, Coupon, InvalidCoupon, Order
from .services import place_order, quote


class CartView(LoginRequiredMixin, TemplateView):
    """The customer's cart page."""

    template_name = "orders/cart.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cart"] = Cart.for_user(self.request.user)
        return context


class AddToCartView(LoginRequiredMixin, View):
    """HTMX: add a product; the button swaps and the badge updates OOB.

    Looks the product up through ``available()``, so adding an
    unavailable product 404s — the same not-for-sale semantics as the
    public catalog.
    """

    def post(self, request, pk):
        product = get_object_or_404(Product.objects.available(), pk=pk)
        item = Cart.for_user(request.user).add(product)
        return render(
            request,
            "orders/partials/_add_button.html",
            {"product": product, "in_cart": item.quantity, "oob_badge": True},
        )


class CartItemActionView(LoginRequiredMixin, View):
    """Base for HTMX line mutations: act, then re-render the cart contents.

    Items are always fetched through the owner's cart — never by bare pk.
    """

    def post(self, request, pk):
        item = get_object_or_404(CartItem, pk=pk, cart__user=request.user)
        self.act(item)
        return render(
            request,
            "orders/partials/_cart_contents.html",
            {"cart": item.cart, "oob_badge": True},
        )

    def act(self, item):
        raise NotImplementedError


class IncrementCartItemView(CartItemActionView):
    def act(self, item):
        item.increment()


class DecrementCartItemView(CartItemActionView):
    def act(self, item):
        item.decrement()


class RemoveCartItemView(CartItemActionView):
    def act(self, item):
        item.delete()


def order_summary(cart, code="", applied=""):
    """Context for the checkout order summary with ``code`` tried on it.

    A code that can't be used leaves the previously ``applied`` code in
    place (if it still works) and carries the reason as ``coupon_error``.
    """
    context = {"coupon_input": code}
    try:
        context["quote"] = quote(cart, code)
    except InvalidCoupon as error:
        context["coupon_error"] = error.message
        try:
            context["quote"] = quote(cart, applied)
        except InvalidCoupon:
            context["quote"] = quote(cart)
        return context
    coupon = context["quote"].coupon
    if coupon and applied and applied.strip().upper() != coupon.code:
        context["replaced"] = applied.strip().upper()
    return context


class CheckoutView(LoginRequiredMixin, FormView):
    """The single checkout page: validate the form, hand off to the service.

    A cart that can't check out (empty, or holding a product that has
    since become unavailable) is sent back to the cart page to be fixed —
    ``place_order`` enforces the same rules transactionally as the
    backstop.
    """

    template_name = "orders/checkout.html"
    form_class = CheckoutForm

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        cart = Cart.for_user(request.user)
        if not cart.items.exists():
            messages.info(request, "Your cart is empty — add something first.")
            return redirect("orders:cart")
        unavailable = [
            line.product.name for line in cart.lines() if not line.product.is_available
        ]
        if unavailable:
            messages.warning(
                request,
                f"No longer available: {', '.join(unavailable)}. "
                "Remove them from the cart to check out.",
            )
            return redirect("orders:cart")
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        """Pre-fill each address section from the customer's default."""
        initial = super().get_initial()
        for kind in Address.KINDS:
            address = self.request.user.addresses.default_for(kind)
            if address:
                initial.update(address.as_checkout_initial(kind))
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cart"] = Cart.for_user(self.request.user)
        context["saved_addresses"] = self.request.user.addresses.all()
        # After a failed POST, re-price with the code that was submitted —
        # if it stopped working since Apply, the summary says why.
        code = context["form"].data.get("coupon_code", "")
        context.update(order_summary(context["cart"], code))
        # The pickers start on the defaults only on a fresh page; after a
        # failed POST the fields hold what was typed, not the default.
        if not context["form"].is_bound:
            for kind in Address.KINDS:
                context[f"default_{kind}"] = self.request.user.addresses.default_for(
                    kind
                )
        return context

    def form_valid(self, form):
        cart = Cart.for_user(self.request.user)
        try:
            order = place_order(
                cart,
                self.request.user,
                form.cleaned_data,
                coupon_code=form.cleaned_data["coupon_code"],
                save_addresses=[
                    kind
                    for kind in Address.KINDS
                    if form.cleaned_data[f"save_{kind}_address"]
                ],
            )
        except InvalidCoupon as error:
            form.add_error("coupon_code", error)
            return self.form_invalid(form)
        messages.success(self.request, f"Order {order.number} placed. Thank you!")
        return redirect(reverse("orders:confirmation", kwargs={"pk": order.pk}))


class ApplyCouponView(LoginRequiredMixin, View):
    """HTMX: try a coupon on the cart and re-render the order summary.

    POSTs ``coupon_code`` (the code typed; blank removes the coupon) and
    ``applied`` (the code already on the summary, kept if the new one
    fails). Every outcome renders the summary — a bad code is a message
    in it, never an error page.
    """

    def post(self, request):
        cart = Cart.for_user(request.user)
        context = order_summary(
            cart,
            request.POST.get("coupon_code", ""),
            applied=request.POST.get("applied", ""),
        )
        return render(
            request,
            "orders/partials/_order_summary.html",
            {**context, "cart": cart, "oob_total": True},
        )


class CheckoutAddressFieldsView(LoginRequiredMixin, View):
    """HTMX: one checkout address section, filled from a saved address.

    The section's dropdown sends ``?address=<pk>``; an empty value is
    "— New address —" and returns blank fields. The address is fetched
    through the customer's own book, so anyone else's pk 404s.
    """

    def get(self, request, kind):
        if kind not in Address.KINDS:
            raise Http404
        initial = {}
        if pk := request.GET.get("address"):
            if not pk.isdigit():
                raise Http404
            address = get_object_or_404(request.user.addresses, pk=pk)
            initial = address.as_checkout_initial(kind)
        form = CheckoutForm(initial=initial)
        return render(
            request,
            "orders/partials/_address_fields.html",
            {"fields": form.address_fields(kind)},
        )


class OwnOrdersMixin(LoginRequiredMixin):
    """Orders are always fetched through the owner — never by bare pk."""

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


class OrderConfirmationView(OwnOrdersMixin, DetailView):
    template_name = "orders/confirmation.html"
    context_object_name = "order"


class OrderHistoryView(OwnOrdersMixin, ListView):
    """The customer's orders, most recent first per the model ordering."""

    template_name = "orders/order_history.html"
    context_object_name = "orders"


class OrderDetailView(OwnOrdersMixin, DetailView):
    template_name = "orders/order_detail.html"
    context_object_name = "order"

    def get_queryset(self):
        return super().get_queryset().prefetch_related("items")


# --- The back office --------------------------------------------------------
#
# Staff-only order oversight: every customer's orders, filterable by
# status, with the status dropdown on the detail page. The ``section``
# context entry drives the active tab in the staff shell.


class ManageOrderListView(StaffRequiredMixin, ListView):
    """All orders, most recent first, filterable via ``?status=``."""

    template_name = "orders/manage_orders.html"
    context_object_name = "orders"
    paginate_by = 20
    extra_context = {"section": "orders"}

    def get_queryset(self):
        orders = Order.objects.select_related("user")
        status = self.request.GET.get("status", "")
        if status in Order.Status.values:
            orders = orders.filter(status=status)
        return orders

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["statuses"] = Order.Status.choices
        context["active_status"] = self.request.GET.get("status", "")
        return context


class ManageOrderDetailView(StaffRequiredMixin, DetailView):
    """Any order's detail, with the status form alongside."""

    template_name = "orders/manage_order_detail.html"
    context_object_name = "order"
    queryset = Order.objects.select_related("user").prefetch_related("items")
    extra_context = {"section": "orders"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_form"] = OrderStatusForm(instance=self.object)
        return context


class UpdateOrderStatusView(StaffRequiredMixin, View):
    """POST-only: set an order's status from the back-office dropdown."""

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        form = OrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"{order.number} is now {order.get_status_display().lower()}.",
            )
        else:
            messages.error(request, "That isn't a status an order can have.")
        return redirect("orders:manage_order_detail", pk=order.pk)


# Staff-only coupon management, so marketing can run promotions without
# engineering. Retiring is a reversible switch; a coupon any order used
# can't be deleted (Order.coupon is PROTECT).


class ManageCouponListView(StaffRequiredMixin, ListView):
    """Every coupon with its use count, filterable via ``?show=active|retired``."""

    template_name = "orders/manage_coupons.html"
    context_object_name = "coupons"
    extra_context = {"section": "coupons"}

    def get_queryset(self):
        coupons = Coupon.objects.annotate(
            times_used=Count("orders", distinct=True),
            product_count=Count("products", distinct=True),
        )
        show = self.request.GET.get("show", "")
        if show == "active":
            coupons = coupons.filter(is_retired=False)
        elif show == "retired":
            coupons = coupons.filter(is_retired=True)
        return coupons

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show"] = self.request.GET.get("show", "")
        return context


class CouponFormViewMixin(StaffRequiredMixin, SuccessMessageMixin):
    model = Coupon
    form_class = CouponForm
    template_name = "orders/manage_coupon_form.html"
    success_url = reverse_lazy("orders:manage_coupons")
    extra_context = {"section": "coupons"}


class ManageCouponCreateView(CouponFormViewMixin, CreateView):
    success_message = "%(code)s created."


class ManageCouponUpdateView(CouponFormViewMixin, UpdateView):
    success_message = "%(code)s saved. Orders that already used it don't change."


class CouponProductGroupView(StaffRequiredMixin, View):
    """HTMX: one category's product checklist, all ticked or all cleared.

    The group's buttons send ``?checked=1`` (select all) or nothing
    (clear); only that category's checkboxes are swapped.
    """

    def get(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        checked = request.GET.get("checked") == "1"
        return render(
            request,
            "orders/partials/_coupon_product_group.html",
            {
                "category": category,
                "products": [(p, checked) for p in category.products.all()],
            },
        )


class RetireCouponView(StaffRequiredMixin, View):
    """POST-only: flip a coupon between retired and active."""

    def post(self, request, pk):
        coupon = get_object_or_404(Coupon, pk=pk)
        if coupon.is_retired:
            coupon.reinstate()
            messages.success(request, f"{coupon.code} is active again.")
        else:
            coupon.retire()
            messages.success(
                request,
                f"{coupon.code} retired. Customers can no longer use it; "
                "orders that already did are unchanged.",
            )
        return redirect("orders:manage_coupons")


class ManageCouponDeleteView(StaffRequiredMixin, SuccessMessageMixin, DeleteView):
    """Delete an unused coupon; a used one is refused with a nudge to retire."""

    model = Coupon
    context_object_name = "coupon"
    template_name = "orders/manage_coupon_confirm_delete.html"
    success_url = reverse_lazy("orders:manage_coupons")
    success_message = "Coupon deleted."
    extra_context = {"section": "coupons"}

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except ProtectedError:
            messages.error(
                self.request,
                f"{self.object.code} has been used on orders, so it can't be "
                "deleted. Retire it instead.",
            )
            return redirect("orders:manage_coupons")

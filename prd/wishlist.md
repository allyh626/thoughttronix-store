# PRD — Customer Wishlist

## Problem Statement

Customers browsing The ThoughtTronix Store often find products they are
interested in but are not ready to buy yet. Today their only option is to
put the product in the cart, which mixes "buying now" with "maybe later", or
to remember the product themselves and search for it again. Products that
are currently unavailable cannot be added to the cart at all, so a customer
has no way to keep track of something they want once it is back. There is
no place in their account to collect the products they care about.

## Solution

Every customer account gets exactly one wishlist. On a product's detail
page, a signed-in customer can add the product to their wishlist or remove
it with a single button, without the page reloading. A navbar "Wishlist"
link shows a live count of saved products and opens a My wishlist page,
which lists everything the customer has saved, newest first, with the
option to add each product to the cart or remove it from the wishlist.
A customer can only ever see and change their own wishlist.

## User Stories

1. As a customer, I want an "Add to wishlist" button on a product's detail page, so that I can save a product I am interested in for later.
2. As a customer, I want adding a product to my wishlist to happen without the page reloading, so that I keep my place on the product page.
3. As a customer, I want the button to change to show that the product is already in my wishlist, so that I know it has been saved.
4. As a customer, I want to remove a product from my wishlist from its detail page without the page reloading, so that I can change my mind quickly.
5. As a customer, I want clicking "add" twice (or in two browser tabs) to still leave the product saved only once, so that my wishlist never has duplicates or flips to the opposite of what I clicked.
6. As a customer, I want to save a product that is currently unavailable, so that I can remember to buy it when it is back.
7. As a signed-out visitor, I want the wishlist button to take me to sign in and then back to the product, so that I can save it once I have an account session.
8. As a customer, I want a "Wishlist" link in the navbar, so that I can reach my wishlist from any page.
9. As a customer, I want the navbar Wishlist link to show how many products I have saved, so that I can see my wishlist at a glance.
10. As a customer, I want the navbar count to update immediately when I add or remove a product on the detail page, so that it always matches my wishlist.
11. As a customer, I want a My wishlist page that lists every product I have saved, so that I can review them in one place.
12. As a customer, I want my most recently saved products at the top of the list, so that what I was just looking at is easy to find.
13. As a customer, I want each saved product to show its image, name, price, and the date I saved it, so that I can recognise it and remember when I saved it.
14. As a customer, I want each product name on my wishlist to link to its detail page, so that I can read more about it.
15. As a customer, I want saved products that are unavailable to show an "Unavailable" badge, so that I understand why I cannot buy them right now.
16. As a customer, I want an add-to-cart button on each wishlist row, so that I can buy a saved product without opening its page.
17. As a customer, I want a product to stay on my wishlist after I add it to my cart, so that I stay in control of my own list.
18. As a customer, I want a Remove button on each wishlist row, so that I can tidy up my wishlist.
19. As a customer, I want a confirmation message after removing a product from the My wishlist page, so that I know the removal worked.
20. As a customer with nothing saved, I want a friendly empty state that points me to the catalog, so that I am not looking at a blank page.
21. As a customer, I want my wishlist to be private, so that no other customer can see or change what I have saved.
22. As a customer, I want my wishlist to be deleted along with my account, so that none of my data stays behind.
23. As a customer, I want a product that the store deletes to disappear from my wishlist, so that I am never shown a product that no longer exists.
24. As a staff member, I want my own wishlist just like a customer, so that I can use the storefront normally.
25. As the site admin, I want to view customers' wishlists in the Django admin, so that I can support customers and debug problems.
26. As a developer or reviewer, I want the seed command to give the demo customer a few wishlist items, including an unavailable product, so that the feature is visible right after seeding.
27. As a developer, I want reseeding to clear all wishlists, so that the seed command still fully resets the demo world.

## Implementation Decisions

- **New app.** The wishlist lives in its own new Django app named
  `wishlist`, with the URL namespace `wishlist`, registered in installed
  apps and included in the root URLs. It does not live in `orders`
  (buying) or `products` (catalog).
- **Models — mirroring Cart / CartItem.**
  - `Wishlist`: one-to-one with the user (cascade on user delete), created
    lazily on first touch via a `for_user(user)` class method, exactly like
    `Cart.for_user`.
  - `WishlistItem`: foreign key to `Wishlist` (cascade, related name
    `items`), foreign key to `Product` (cascade on product delete), and an
    `added_at` timestamp set automatically on creation. The
    wishlist–product pair is unique. Default ordering is newest first
    (`-added_at`).
  - Model methods own the logic: `add(product)` and `remove(product)` are
    both idempotent — adding an already-saved product does nothing new;
    removing a product that is not saved does nothing harmful.
- **Any product can be saved.** Unlike add-to-cart, adding to the wishlist
  does not filter through `Product.objects.available()`; unavailable
  products can be saved and stay on the wishlist.
- **Views — thin, class-based, sign-in required.** Every view uses
  `LoginRequiredMixin` and reaches wishlist data only through the signed-in
  user's own wishlist — never by a bare wishlist or item id — so one
  customer can never read or change another's.
  - `wishlist:list` — the My wishlist page (GET).
  - `wishlist:add` — POST only, takes a product pk. HTMX endpoint: returns
    the wishlist button partial plus the navbar badge as an out-of-band
    swap.
  - `wishlist:remove` — POST only, takes a product pk. Serves two callers:
    an HTMX request from the detail page gets the button partial plus the
    out-of-band badge; a normal form POST from the My wishlist page
    redirects back to the list with a success message
    ("Removed <product> from your wishlist.").
  - Separate add and remove endpoints are used instead of a single toggle,
    so a double-click or stale tab never produces the opposite result.
- **Product detail page.** Shows a wishlist button partial (underscore
  prefixed, never extending the base template) with two states: "Add to
  wishlist" (posts to add) and "In wishlist (remove)" (posts to remove),
  swapped with `hx-swap="outerHTML"`. Signed-out visitors see a plain
  sign-in link with a `next` parameter back to the product, no HTMX —
  the same pattern as the add-to-cart button. The button appears on the
  detail page only.
- **Navbar badge.** A "Wishlist" link in the navbar beside Orders and
  Account, rendered from a badge partial with a stable id and an `oob`
  flag, following the cart badge pattern. A `wishlist` context processor
  supplies, on every signed-in request (one small query), the saved-item
  count for the badge and the set of saved product ids used to choose the
  detail button's state. Anonymous requests get a zero count and an empty
  set.
- **My wishlist page.** Extends the base template; opens with an h1
  (text-3xl font-bold) and a one-line description (opacity-70). Each row
  shows the product image, name linking to its detail page, price, the
  "Unavailable" badge when applicable, the saved date, the existing
  add-to-cart button partial (reused as-is, with its HTMX add, disabled
  unavailable state, and cart badge update), and a Remove button as a
  plain POST form with CSRF that reloads the page. A designed empty state
  links to the catalog. Adding to the cart does not remove the product
  from the wishlist.
- **Admin.** `Wishlist` is registered in the Django admin with
  `WishlistItem` as a tabular inline, mirroring the cart's admin. No
  back-office tab is added.
- **Seed.** The seed command deletes all wishlists during its reset and
  gives the demo customer three or four wishlist items, including at least
  one unavailable product. Its summary output reports the wishlist.
- **Styling.** Tailwind and DaisyUI classes only; no JavaScript beyond
  HTMX.
- **Testing.** pytest + pytest-django with plain fixtures in the
  project-level conftest (no factory-boy). Cover: add and remove
  (including idempotent repeats), unavailable products can be saved,
  anonymous users are redirected to sign in, one customer cannot affect
  another's wishlist, the HTMX responses render the partial and the
  out-of-band badge, the non-HTMX remove redirects with a message, the
  list page's newest-first order and empty state, cascade on account and
  product delete, and the seed reset.

## Out of Scope

- Named wishlists, multiple wishlists per account, and shared or public
  wishlists.
- Wishlist buttons on catalog and category product cards (the partial is
  reusable, so this can be added later).
- "Move to cart" behavior that removes a product from the wishlist when it
  is added to the cart.
- An HTMX (no-reload) Remove on the My wishlist page.
- A back-office Wishlists tab or wishlist analytics on the staff dashboard.
- Back-in-stock or price-drop notifications for saved products.
- Wishlists for signed-out visitors (session-based wishlists).

## Further Notes

- The cart is the reference implementation throughout: the one-to-one
  lazy-created container, the HTMX button partial, the out-of-band navbar
  badge, the context processor, the owner-scoped lookups, and the admin
  inline. Following it keeps the wishlist consistent with existing code.
- "Customers only have access to their own wishlist" is enforced by
  always looking up through the signed-in user; the site admin's access
  through the Django admin is intentional and matches carts, orders, and
  addresses.
- CLAUDE.md's project layout should gain a `wishlist/` entry, and the PRD
  and plan pair should be listed alongside the others, when the feature is
  built.

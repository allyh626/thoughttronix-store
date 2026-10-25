# Plan: Customer Wishlist

> Source PRD: `prd/wishlist.md`

## Architectural decisions

Durable decisions that apply across all phases:

- **Owning app**: a new `wishlist` app, registered in installed apps, with
  its URLs included from the root URLconf. The only changes outside it are
  the product detail page and navbar templates (Phases 1, 3 and 5) and the
  `seed` command in `products` (Phase 6).
- **URLs**: every view sits in the `wishlist` namespace:
  - `wishlist:list`, `/wishlist/`: the My wishlist page (GET)
  - `wishlist:add`: POST only, takes a product pk
  - `wishlist:remove`: POST only, takes a product pk. It answers HTMX
    requests with the button partial, and plain form posts with a redirect
    to `wishlist:list` plus a flash message.
  Separate add and remove endpoints, never a toggle, so a repeated click
  never flips the result.
- **Models**:
  - `Wishlist`: one-to-one with `accounts.User` (`CASCADE`), created lazily
    by `Wishlist.for_user(user)`, like `Cart.for_user`.
  - `WishlistItem`: FK to `Wishlist` (`CASCADE`, related name `items`), FK
    to `Product` (`CASCADE`), and `added_at` (set on creation). The
    wishlist–product pair is unique, and default ordering is `-added_at`.
  - `Wishlist.add(product)` and `Wishlist.remove(product)` are idempotent.
- **Product rule**: any product can be saved. Lookups do not go through
  `Product.objects.available()`.
- **Auth**: every wishlist view uses `LoginRequiredMixin` and reaches data
  only through `request.user`'s own wishlist, never by a bare wishlist or
  item id. Staff and the admin have wishlists like any customer. The site
  admin can view all wishlists in the Django admin. There is no back-office
  tab.
- **Templates**: HTMX responses render underscore-prefixed partials that
  never extend `base.html`. Tailwind and DaisyUI only, with no JavaScript
  beyond HTMX.
- **Architecture**: the cart is the reference implementation. There is no
  new service module, so CLAUDE.md's two deep modules stay two.

---

## Phase 1: Save a product from the detail page

**User stories**: 1, 2, 3, 5, 6, 7, 21 (add only), 22, 23, 24, 25

### What to build

The tracer bullet. The `wishlist` app and its two models exist, and the
product detail page shows a wishlist button. A signed-in customer clicks
"Add to wishlist", the product is saved, and the button swaps to
"In wishlist (remove)" without a reload. Clicking that state does nothing
useful yet, because removal arrives in Phase 2. Signed-out visitors see a
plain sign-in link that brings them back to the product. A context
processor tells the detail page which products are already saved, so the
button shows the right state on page load. The admin can see wishlists in
the Django admin.

### Acceptance criteria

- [x] The `wishlist` app is created, installed, and its URLs are included
      under the `wishlist` namespace
- [x] `Wishlist` and `WishlistItem` models and their migration exist as
      described in the architectural decisions
- [x] `Wishlist.for_user` creates the wishlist on first touch, and
      `Wishlist.add` is idempotent (adding twice leaves one item)
- [x] `wishlist:add` is POST only, requires sign-in, works for unavailable
      products, and returns the button partial in its saved state
- [x] The detail page shows "Add to wishlist" or "In wishlist (remove)" based
      on the saved product ids from the `wishlist` context processor
      (anonymous requests get an empty set)
- [x] Signed-out visitors see a sign-in link with `?next=` back to the
      product, with no HTMX
- [x] Deleting a user deletes their wishlist, and deleting a product deletes
      its wishlist items
- [x] `Wishlist` is registered in the Django admin with `WishlistItem` as a
      tabular inline, mirroring `CartAdmin`
- [x] Tests cover the model methods, the add endpoint (signed in,
      anonymous redirect, GET rejected, unavailable product, idempotent
      repeat, only touches the signed-in user's wishlist), the button states
      on the detail page, and both cascades

---

## Phase 2: Remove a product from the detail page

**User stories**: 4, 21

### What to build

The "In wishlist (remove)" button now works. Clicking it removes the
product and the button swaps back to "Add to wishlist" without a reload.

### Acceptance criteria

- [x] `Wishlist.remove` is idempotent (removing an unsaved product does no
      harm)
- [x] `wishlist:remove` is POST only, requires sign-in, and for an HTMX
      request returns the button partial in its unsaved state
- [x] The saved-state button posts to `wishlist:remove`
- [x] Removing only ever affects the signed-in user's wishlist
- [x] Tests cover the model method, the HTMX remove (signed in, anonymous
      redirect, GET rejected, idempotent repeat), and that another
      customer's wishlist is untouched

---

## Phase 3: My wishlist page

**User stories**: 8, 11, 12, 13, 14, 15, 20, 21

### What to build

A signed-in customer can open `/wishlist/` from a new "Wishlist" link in
the navbar, beside Orders and Account. The page lists their saved
products, newest first. Each row shows the product image, the name linking
to its detail page, the price, an "Unavailable" badge when applicable, and
the date it was saved. With nothing saved, a designed empty state points
to the catalog. The navbar link has no count yet.

### Acceptance criteria

- [x] `wishlist:list` requires sign-in and shows only the signed-in user's
      items
- [x] The page extends `base.html` and opens with a text-3xl font-bold h1
      and a one-line opacity-70 description
- [x] Rows are ordered newest saved first and show image, linked name,
      price, saved date, and the "Unavailable" badge for unavailable
      products
- [x] An empty wishlist shows a designed empty state linking to the catalog
- [x] The navbar shows a "Wishlist" link for signed-in users only
- [x] Tests cover anonymous redirect, ordering, row contents, the
      unavailable badge, the empty state, that another customer's items
      never appear, and the navbar link

---

## Phase 4: Act on items from the My wishlist page

**User stories**: 16, 17, 18, 19

### What to build

Each row on the My wishlist page gets the existing add-to-cart button,
reused as-is, and a Remove button. Add to cart works by HTMX as it does
elsewhere, and leaves the product on the wishlist. Remove is a plain form
post to `wishlist:remove`. The page reloads with the product gone and a
message: "Removed <product> from your wishlist."

### Acceptance criteria

- [x] Each row includes the existing add-to-cart partial, with its disabled
      state for unavailable products
- [x] Adding to the cart does not remove the product from the wishlist
- [x] Each row has a Remove form (POST with CSRF) targeting `wishlist:remove`
- [x] A non-HTMX remove redirects to `wishlist:list` with the success
      message
- [x] Removing the last item shows the empty state
- [x] Tests cover the redirect and message, the non-HTMX vs HTMX response
      difference, the add-to-cart button's presence, and that the item
      survives an add to cart

---

## Phase 5: Live navbar count badge

**User stories**: 9, 10

### What to build

The navbar "Wishlist" link becomes a badge partial that shows how many
products are saved, following the cart badge. When a customer adds or
removes a product on the detail page, the badge updates out-of-band in
the same HTMX response, without a reload.

### Acceptance criteria

- [x] The `wishlist` context processor also supplies the saved-item count
      (zero for anonymous requests), still in one query
- [x] The navbar link is a badge partial with a stable id and an `oob` flag,
      showing the count only when it is above zero
- [x] HTMX responses from `wishlist:add` and `wishlist:remove` include the
      badge as an out-of-band swap
- [x] The non-HTMX remove from the My wishlist page still redirects normally
- [x] Tests cover the count in the navbar and the out-of-band badge in both
      HTMX responses

---

## Phase 6: Seed the demo wishlist

**User stories**: 26, 27

### What to build

`seed` resets wishlists along with the rest of the demo world, and gives
the demo customer a few saved products, so the feature is visible as soon
as a reviewer signs in.

### Acceptance criteria

- [x] `seed` deletes all wishlists during its reset
- [x] The demo customer gets three or four wishlist items, including at
      least one unavailable product
- [x] The seed summary output reports the wishlist
- [x] Running `seed` twice gives the same result (idempotent)
- [x] CLAUDE.md's project layout gains a `wishlist/` entry, and the
      wishlist PRD and plan pair are listed alongside the others
- [x] Tests cover the reset and the seeded items

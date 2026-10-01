# PROMPTS.md — AI Usage Log

This file is the record of AI use on this codebase. At the end of every
agent session, direct the agent to write the session log with this prompt:

> Append a session log to PROMPTS.md at the repo root, under today's date,
> newest entry at the top. Record every prompt I gave you this session, in
> order, including any corrections. End the entry with a short summary:
> the outcome, any places where I deviated from a recommended answer or
> asked follow-up questions, and anything that went sideways.

Two rules:

- Entries are added only by that prompt, never unprompted.
- New entries go at the top. Never rewrite or delete an old entry — the
  log is part of your work, and an honest log of a session that went
  sideways is worth more than a tidy one.

Each entry has this shape:

    ## YYYY-MM-DD — <one-line summary>

    ### Prompts
    1. ...

    ### Summary
    - **Outcome:** what was built and what was kept
    - **Deviations:** recommendations overridden, follow-up questions asked
    - **Sideways:** failures, wrong turns, and how they were caught

## 2026-10-01 — Design (via /grill-me) and build discount codes for seasonal promotions

### Prompts
1. /grill-me I would like to add discount codes to the store for seasonal promotions. A customer types in a discount code at checkout, and the order total is decreased. codes expire when the promotions end, if an expired code is entered by a customer there should be a message informing them the coupon is expired. marketing will create and retire codes themselves, without filing a ticket with engineering, retiring a code must not change any order that already used it. Do not produce a server error, blank page, or an opportunity for the customer to contact legal. The coupon system must support both order-wide discounts and discounts limited to specific products.
2. i like c *(Q1, discount type: percent or dollar amount)*
3. could you make option A simpler for marketing and fix the trade off with that same option still? *(Q2, how product-limited codes pick products)*
4. A+ sounds good
5. a *(Q3, a dollar code on selected products comes off once per order)*
6. b *(Q4, start and end dates)*
7. a, America/Chicago *(Q5, switch the whole store's time zone)*
8. a *(Q6, retiring is a reversible switch; used codes can't be deleted)*
9. a *(Q7, a specific message for each of the five failure reasons)*
10. a *(Q8, an HTMX Apply button plus a re-check at Place order)*
11. a *(Q9, one code per order; a new code replaces the old one)*
12. a *(Q10, no usage limits)*
13. a *(Q11, a back-office Coupons tab open to all staff)*
14. a *(Q12, `Order.total` is what the customer paid)*
15. no thank you, can you implement this feature
16. and to run the test suite?
17. i would like to make a small change to the feature to make the discount code box more visible to users
18. can you implement this change
19. can you write the session log with the standard prompt in prompts.md

### Summary
- **Outcome:** A 12-question grill-me interview settled the design, and
  then the feature was built. New `Coupon` model in `orders/models.py`:
  a percentage or dollar amount; the whole order or selected products;
  start and end dates; a retired switch; codes stored upper-case. It also
  holds the discount math and the five customer messages (unknown,
  expired, not started, retired, covers nothing in the cart), raised as
  `InvalidCoupon`. `Order` gains `coupon` (FK, `PROTECT`), `coupon_code`,
  and `discount_amount`, plus a `subtotal` property; migration
  `orders/migrations/0003_coupons.py`. `orders/services.py` gains
  `quote()`, the single source of the math, and `place_order` now uses
  its `coupon_code` argument and re-checks the code when the order is
  placed. Checkout has a "Have a discount code?" box with an HTMX Apply
  button and a Remove button, and its order summary updates the Place
  order total. The order pages show the code and the savings. Back office
  has a new Coupons tab: list with active/retired filter and empty state,
  create/edit form with a product checklist grouped by category
  (HTMX select all/clear), retire/reactivate, and delete only for unused
  codes. `TIME_ZONE` is now `America/Chicago`; `seed` creates 5 demo
  coupons (one per state); Django admin registers `Coupon`; CLAUDE.md
  updated. 50 new tests in `orders/test_coupons.py`; suite at 279
  passed; ruff clean. Nothing committed.
- **Deviations:** Q2: instead of picking an option, asked for option A
  made easier with its trade-off fixed; the answer was "A+" (a checklist
  grouped by category with select-all buttons). The "new products aren't
  included" trade-off was kept as a deliberate choice, not fixed. Q5:
  named the time zone. Every other question took the recommended answer.
  Declined the offer to draft `prd/coupons.md`. Asked to implement,
  overriding the usual "I type the edits myself" approach, both for the
  feature and for the label change. Follow-up question: how to run the
  test suite (answered: `uv run pytest`). For visibility, took the label
  change and not the optional solid Apply button. The build differs from
  the agreed design in three places, all reported: "applies to" is an
  explicit field rather than "an empty product list means the whole
  order" (deleting a coupon's only product would otherwise make it
  order-wide); the subtotal is calculated, not stored; and orders link
  to the coupon so a used code can't be deleted.
- **Sideways:** A bad edit while building turned an `<a` tag in
  `checkout.html` into `<`; it was spotted and fixed right away, before
  any test run. As expected, the old test "the coupon argument is
  accepted and ignored" failed once coupons were real, and was replaced.
  `ruff format` re-wrapped an unrelated line in `accounts/views.py`,
  which was restored to the committed version. To protect the real
  database, the seed was tested against a scratch SQLite copy (run twice
  for idempotence). The HTMX behavior (Apply, Remove, the Place order
  total update) was checked only through server responses in tests, not
  in a browser. As before, `uv run` printed the harmless `VIRTUAL_ENV`
  mismatch warning.

## 2026-09-25 — Add `Product.is_featured` and a "Featured" badge on catalog and detail pages

### Prompts
1. what fields are contained in Product?
2. Add an is_featured field to Product, this will be a boolean field that defaults to the item not being featured, existing products should stay unfeatured.
3. no thank you, am i able to access djangos admin interface to confirm the existence of the  added field?
4. Display a "Featured" badge on the catalog listing page and the product detail page for all featured products.
5. what changes in the code base could possibly break the function of the "featured" banner?
6. no thank you, but could you append a session log to PROMPTS.md at the repo root, under today's date, newest entry at the top. Record every prompt I gave you this session, in order, including any corrections. End the entry with a short summary: the outcome, any places where I deviated from a recommended answer or asked follow-up questions, and anything that went sideways.

### Summary
- **Outcome:** Added `is_featured = models.BooleanField(default=False)` to
  `Product`, with migration `products/migrations/0003_product_is_featured.py`
  (existing rows default to unfeatured). Added a `badge-secondary` "Featured"
  badge to the product cards in `templates/products/catalog.html` and to the
  status row in `templates/products/detail.html`. Added two tests in
  `products/tests.py` (badge shown when featured, absent when not). Suite
  at 166 passed; ruff check and format clean. Nothing committed.
- **Deviations:** Declined the offer to wire `is_featured` into the
  back-office form, the admin `list_display`, the seed data, or a
  `featured()` queryset method — so the field is settable only via the
  Django admin change form and is reset by `seed`. Declined the offer to
  give the badge a stable test hook (`data-testid`) so the tests stop
  matching the bare word "Featured". Follow-up questions: how to confirm the
  field in the Django admin (answered: `/admin/`, seeded `admin / admin123`,
  product change form), and what changes could break the badge (answered
  with a risk list: field/context renames failing silently in templates,
  queryset rewrites, template or partial refactors, theme/Tailwind
  changes, reseeding, and the weak substring-based tests).
- **Sideways:** Nothing broke. Every `uv run` printed a warning that the
  outer `VIRTUAL_ENV` (`C:\Users\ally\CIDM3312\.venv`) doesn't match the
  project `.venv`; uv ignored it and used the project environment, so it
  was noise only. Known weakness left in place: the new tests assert on
  the plain string "Featured", which would give false results if that word
  appears elsewhere on the page.

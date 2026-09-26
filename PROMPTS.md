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

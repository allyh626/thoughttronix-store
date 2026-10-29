# Plan: Product Reviews

> Source PRD: `prd/product-reviews.md`

## Architectural decisions

Durable decisions that apply across all phases:

- **Owning app**: a new `reviews` app, registered in installed apps, with
  its URLs included from the root URLconf, like `wishlist`. The only
  changes outside it are the product detail page template (Phases 1–3, 5,
  6), the back-office tab bar (Phase 4), and the `seed` command in
  `products` (Phases 2 and 6).
- **URLs**: every view sits in the `reviews` namespace. Products are
  addressed by pk, like the cart and wishlist endpoints.
  - `reviews:create`, `/reviews/product/<int:pk>/new/`: POST only
  - `reviews:more`, `/reviews/product/<int:pk>/more/?page=N`: GET, the next
    5 reviews for "Show more"
  - `reviews:card`, `/reviews/<int:pk>/`: GET, one review card (used by
    Cancel on the edit form)
  - `reviews:edit`, `/reviews/<int:pk>/edit/`: GET the in-place form, POST
    to save
  - `reviews:delete`, `/reviews/<int:pk>/delete/`: POST only
  - `reviews:report`, `/reviews/<int:pk>/report/`: GET the in-place report
    form, POST to submit
  - `reviews:manage`, `/backoffice/reviews/`: the back-office Reviews tab,
    with `?filter=flagged` for the Flagged tab
  - `reviews:manage_edit`, `/backoffice/reviews/<int:pk>/edit/`
  - `reviews:manage_delete`, `/backoffice/reviews/<int:pk>/delete/`
  - `reviews:clear_flag`, `/backoffice/reviews/<int:pk>/clear-flag/`: POST
    only
- **Models**:
  - `Review`: FK to `Product` (`CASCADE`, related name `reviews`), FK to
    `accounts.User` as `author` (`CASCADE`, related name `reviews`;
    `deactivate()` keeps the user row, so reviews survive account
    deletion), `rating` (positive small integer, validated 1–5), `title`
    (max 50), `comment` (max 1,000), `display_name` (the censored name,
    saved on create and never changed), `is_flagged` (default false),
    `created_at` (a default, not `auto_now_add`, so `seed` can backdate),
    and `edited_at` (empty until the first edit; drives the "edited" tag).
    The product–author pair is unique. Default ordering is `-created_at`.
  - `ReviewReport` (Phase 6): FK to `Review` (`CASCADE`, related name
    `reports`), FK to `accounts.User` as `reporter` (`CASCADE`), `reason`
    (choices: Spam, Offensive language, Off-topic, Other), `note`
    (optional), and `created_at`. The review–reporter pair is unique.
- **Censored name**: `first letter + "****" + last letter` for every
  username; a one-letter username uses the same letter at both ends.
- **Eligibility**: only a non-staff customer with an order in status
  Delivered containing an order item for the product, and no review of it
  yet, can create a review. Editing and deleting need only ownership (or
  staff).
- **Auth**:
  - Customer actions use `LoginRequiredMixin`. The product-page edit and
    delete endpoints look reviews up through `request.user.reviews` for
    customers, and through all reviews for staff, so customers can only
    reach their own.
  - Back-office views use `StaffRequiredMixin` (anonymous to login,
    non-staff 403).
  - Staff never see the review form or the Report button.
- **Moderation**: the banned-word list is a constant in code. The check
  runs when a review is created and when its author edits it, and a match
  sets `is_flagged`. A clean customer edit does not clear a flag. A staff
  edit or Clear flag clears it, and a new report (Phase 6) sets it again.
- **Templates**: HTMX responses render underscore-prefixed partials that
  never extend `base.html`. Tailwind and DaisyUI only, with no JavaScript
  beyond HTMX. The back-office pages extend the back-office base and use
  plain forms with success messages, like the Coupons tab.
- **Architecture**: logic lives on the models and a custom queryset or
  manager (eligibility, censoring, the word check, the average). There is
  no new service module, so CLAUDE.md's two deep modules stay two.

---

## Phase 1: Write and see a review

**User stories**: 1, 2, 3, 4, 5, 6, 7, 8, 9, 14, 15, 16 (without the
"edited" tag), 19, 38, 39

### What to build

The tracer bullet. The `reviews` app and the `Review` model exist, and the
product detail page has a reviews section. An eligible customer fills in a
rating, title and comment, submits, and the new review appears at the top of
the list without a reload, under its saved censored name. The form then goes
away, because the customer already has a review. Validation errors (missing
fields, too long, rating out of range) re-render the form in place.
Everyone else sees the right hint instead of the form: signed-out visitors
a sign-in link back to the product, ineligible customers the "once an
order containing it has been delivered" message, and staff nothing. The list
shows every review for now, newest first, each with its censored name,
stars, title, comment and posted date.

### Acceptance criteria

- [x] The `reviews` app is created, installed, and its URLs are included
      under the `reviews` namespace
- [x] `Review` and its migration exist as described in the architectural
      decisions, with the product–author pair unique
- [x] The censored-name rule gives `a****n` for `allison`, `a****y` for
      `ay`, and `a****a` for `a`, and the name is saved on create
- [x] Eligibility is true only for a Delivered order containing the
      product; Placed, Shipped and Cancelled orders, staff, and customers
      with an existing review are not eligible
- [x] `reviews:create` is POST only, requires sign-in, rejects ineligible
      customers, and returns the new review card in place
- [x] Title (50), comment (1,000), required fields and the 1–5 rating are
      validated by the form, with errors shown in place
- [x] The detail page shows the form, the sign-in hint, the ineligible
      hint, or nothing (staff, or already reviewed) as appropriate
- [x] Reviews are listed newest first with censored name, stars, title,
      comment and posted date
- [x] A review stays after its order is cancelled, stays under the same
      censored name after `deactivate()`, and is deleted with its product
- [x] Tests cover all of the above

---

## Phase 2: Average, pinning, "Show more" and demo reviews

**User stories**: 17, 18, 20, 21, 40

### What to build

The reviews section opens with the product's average rating, rounded to
one decimal place, and the review count ("4.3 ★ (12 reviews)"), or "No
reviews yet." The signed-in customer's own review is pinned at the top and
not repeated below. Only the first 5 other reviews load with the page. A
"Show more" button fetches the next 5 and appends them without a reload,
and it disappears when there are no more. Creating a review in Phase 1's
form now also updates the average and count in place. The `seed` command
wipes all reviews during its reset and creates demo reviews, each backed by
a Delivered order for its author, including one product with more than 5
reviews so "Show more" is visible right after seeding.

### Acceptance criteria

- [x] The average and count are correct, rounded to one decimal place, and
      a product with no reviews shows "No reviews yet."
- [x] The signed-in customer's own review is pinned first and not
      duplicated in the list
- [x] The page shows 5 reviews, `reviews:more` returns the next 5 newest
      first, and the button hides on the last page
- [x] Creating a review updates the average and count without a reload
- [x] `seed` wipes reviews, creates demo reviews only for authors with a
      Delivered order of that product, gives one product more than 5
      reviews, and reports the reviews in its summary
- [x] Running `seed` twice gives the same result
- [x] Tests cover all of the above

---

## Phase 3: Edit and delete your own review

**User stories**: 10, 11, 12, 13, 16 (the "edited" tag)

### What to build

A customer's own review card shows Edit and Delete; nobody else's does.
Edit swaps the card for a pre-filled form in place. Save swaps back to the
updated card, which now shows an "edited" tag, and Cancel swaps back to the
unchanged card. Editing works even if the order has since been cancelled.
Delete asks first with `hx-confirm`, then removes the card in place. The
review form returns, because the customer can write a new review if they
are still eligible. Both actions update the average and count without a
reload.

### Acceptance criteria

- [x] Edit and Delete appear only on the signed-in customer's own review
- [x] `reviews:edit` and `reviews:delete` reach only the customer's own
      reviews; another customer's review returns 404
- [x] Editing sets `edited_at`, the card shows "edited", and editing does
      not need a Delivered order
- [x] `reviews:card` returns the unchanged card for Cancel
- [x] Delete uses `hx-confirm`, removes the card in place, and brings the
      form back for an eligible customer
- [x] The average and count update after edit and delete
- [x] Tests cover all of the above

---

## Phase 4: Banned-word flag and the Reviews tab

**User stories**: 26, 27, 29, 30, 31 (without reports), 32, 36

### What to build

A review whose title or comment contains a banned word is flagged when it
is posted, and again whenever its author edits it to contain one. A clean
edit leaves an existing flag alone. A new Reviews tab joins the back-office
tab bar. It lists every review, flagged first and then newest first, with
All and Flagged filter tabs. Each row shows the product, the author's full
username, rating, title and flag status. Reviews whose author has been
deactivated show a "Deactivated account" badge next to the account's
current username. Staff can clear a flag from a row, with a success
message.

### Acceptance criteria

- [x] The banned-word constant exists, and the check flags reviews on
      create and on customer edit, matching words regardless of case
- [x] A clean customer edit does not clear an existing flag
- [x] `reviews:manage` is staff-only and lists all reviews flagged first,
      then newest first
- [x] The Flagged tab shows only flagged reviews
- [x] Rows show the full username, and a "Deactivated account" badge for
      deactivated authors
- [x] `reviews:clear_flag` is staff-only, POST only, clears the flag, and
      redirects back with a success message
- [x] The Reviews tab link appears in the back-office tab bar
- [x] Tests cover all of the above

---

## Phase 5: Staff edit and delete any review

**User stories**: 33, 34, 35

### What to build

Staff see Edit and Delete on every review on the product page, and they
work in place exactly as they do for a customer's own review. Each row of
the Reviews tab also gets Edit and Delete, using plain back-office pages
with a delete confirmation and success messages. A staff edit keeps the
original author and saved censored name, marks the review edited, and
clears its flag.

### Acceptance criteria

- [x] Staff see Edit and Delete on every review on the product page, and
      `reviews:edit` and `reviews:delete` accept any review for staff
- [x] `reviews:manage_edit` and `reviews:manage_delete` are staff-only and
      redirect to the Reviews tab with a success message
- [x] A staff edit keeps the author and `display_name`, sets `edited_at`,
      and clears the flag
- [x] Tests cover all of the above

---

## Phase 6: Report a review

**User stories**: 22, 23, 24, 25, 28, 31 (reports), 37

### What to build

The `ReviewReport` model exists. Signed-in customers see a Report button
on other customers' reviews (never their own, and never for staff or
signed-out visitors). Clicking it opens a reason drop-down and a note in
place. The note is required only when the reason is Other. Submitting
flags the review and swaps the button for "Reported". A customer who has
already reported a review sees "Reported" from the start and can't report
it again, even after staff clear the flag, but a report from a new
customer flags it again. The Reviews tab now shows each review's report
count and reasons. `seed` adds a demo report so the Flagged tab has a row
right after seeding.

### Acceptance criteria

- [x] `ReviewReport` and its migration exist, with the review–reporter
      pair unique
- [x] `reviews:report` requires sign-in, rejects the author and staff, and
      returns the "Reported" state in place
- [x] The form requires a note only for Other
- [x] A report flags the review; a second report by the same customer is
      refused; a new customer's report re-flags a cleared review
- [x] The Report button shows "Reported" on load for reviews the customer
      already reported
- [x] The Reviews tab shows report counts and reasons
- [x] `seed` creates a demo report that flags a demo review
- [x] CLAUDE.md gains a `reviews/` layout entry and lists the reviews PRD
      and plan pair
- [x] Tests cover all of the above

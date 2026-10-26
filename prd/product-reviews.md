# PRD — Product Reviews

## Problem Statement

Customers shopping at The ThoughtTronix Store have nothing to go on but
the store's own product description. They cannot see what other buyers
thought of a product, and customers who have bought and used something
have no way to share their experience. The store has no way to collect
feedback on its products, and staff have no tools to keep customer-written
content clean.

## Solution

Customers who have received a product (an order containing it has been
delivered) can leave one review of it: a 1–5 star rating, a title, and a
comment. Reviews appear on the product's detail page, newest first, with
the customer's own review pinned at the top, under a censored version of
the author's username and an average rating. Writing, editing, deleting,
and reporting a review all happen in place on the product page, without a
full page reload, so the customer never loses their place.

Reviews go live immediately. Staff moderate afterward: an automatic
banned-word check and customer reports flag suspicious reviews, and a new
back-office Reviews tab lists every review, flagged ones first, where staff
can edit, delete, or clear the flag. Customers can edit or delete only their
own reviews; staff can edit or delete any review.

## User Stories

1. As a customer with a delivered order containing a product, I want a form on that product's page to write a review, so that I can share my experience with other shoppers.
2. As a customer, I want to give a whole-star rating from 1 to 5, so that my overall opinion is clear at a glance.
3. As a customer, I want to give my review a title and a comment, both required, so that every review explains itself.
4. As a customer, I want the title limited to 50 characters and the comment to 1,000 characters, with a clear error if I go over, so that reviews stay readable.
5. As a customer, I want to be able to write only one review per product, even if I bought it in several orders, so that each customer's voice counts once.
6. As a customer, I want my new review to appear on the page without a reload, so that I keep my place.
7. As a customer whose order has not been delivered yet, or who has not bought the product, I want a hint saying "You can review this product once an order containing it has been delivered." instead of the form, so that I understand why I cannot review yet.
8. As a signed-out visitor, I want a hint inviting me to sign in to leave a review, so that I know how to take part.
9. As a customer, I want my review to stay up even if the order is later cancelled, so that my feedback is not lost.
10. As a customer, I want to edit my review in place, with the review turning into a form, so that I can update my opinion without leaving the page.
11. As a customer, I want to be able to edit my review as long as it exists, without needing a delivered order again, so that I can always correct it.
12. As a customer, I want to delete my review after confirming, without a page reload, so that I can take it back without losing my place.
13. As a customer, I want only my own reviews to have edit and delete controls, so that nobody else can change what I wrote.
14. As a shopper, I want each review to show a censored username (first letter, four stars, last letter — for example `a****n`), so that I can tell reviewers apart while their identity stays private.
15. As a customer with a very short username, I want it censored in the same fixed format (`ay` shows as `a****y`, `a` as `a****a`), so that the length of my username is never revealed.
16. As a shopper, I want each review to show its rating, title, comment, and posted date, with an "edited" tag if it has been changed, so that I know how current it is.
17. As a shopper, I want to see a product's average rating and review count (for example "4.3 ★ (12 reviews)") on its detail page, so that I can judge the product quickly.
18. As a shopper, I want a product with no reviews to say "No reviews yet.", so that I am not shown an empty or misleading average.
19. As a shopper, I want reviews listed newest first, so that I see the most recent opinions.
20. As a customer, I want my own review pinned at the top of the list, so that I can find and manage it easily.
21. As a shopper, I want the first 5 reviews shown and a "Show more" button that loads 5 more without a reload, so that the page stays short and I keep my place.
22. As a signed-in customer, I want to report another customer's review, choosing a reason (Spam, Offensive language, Off-topic, Other), so that staff can look at inappropriate content.
23. As a customer reporting a review, I want the note to be optional, except required when I choose "Other", so that reporting is quick but staff still learn what "Other" means.
24. As a customer, I want the Report button to change to "Reported" in place after I report, so that I know my report was received.
25. As a customer, I want to be able to report a given review only once and never my own review, so that reports stay meaningful.
26. As a staff member, I want reviews containing banned words flagged automatically when posted, so that obvious problems reach me without waiting for a report.
27. As a staff member, I want a customer's edit re-checked against the banned words, so that a clean review cannot be quietly edited into an offensive one.
28. As a staff member, I want any report to flag a review, so that customers can catch what the word check misses.
29. As a staff member, I want a back-office Reviews tab listing every review, flagged or not, so that I can oversee all customer content in one place.
30. As a staff member, I want flagged reviews listed first, with filter tabs, so that I deal with problems before anything else.
31. As a staff member, I want each row to show the product, the author's full username, rating, title, flag status, and the number of reports with their reasons, so that I can decide what to do.
32. As a staff member, I want reviews from deleted accounts marked "Deactivated account", so that I know the author can no longer respond or edit.
33. As a staff member, I want to edit or delete any review, from both the product page and the Reviews tab, so that I can fix or remove problem content wherever I find it.
34. As a staff member, I want a review I edit to keep its original author, so that the review is still credited to the customer who wrote it.
35. As a staff member, I want my edit to clear the review's flag, so that I do not have to clear it separately after fixing it.
36. As a staff member, I want to clear a flag on a review I have checked, so that it leaves the flagged list.
37. As a staff member, I want new reports from customers who have not reported it before to flag a cleared review again, so that fresh problems still reach me.
38. As a customer who deletes my account, I want my reviews to stay up under the same censored name, so that my feedback keeps helping other shoppers without revealing that my account is gone.
39. As a shopper, I want a deleted product's reviews to disappear with it, so that I am never shown reviews of something that no longer exists.
40. As a developer or reviewer, I want the seed command to create demo reviews, including one product with more than five reviews, so that the feature and the "Show more" button are visible right after seeding.

## Implementation Decisions

- **New app.** Reviews live in a new Django app named `reviews`, with the
  URL namespace `reviews`, registered in installed apps and included in the
  root URLs, following the pattern of the `wishlist` app.
- **Models.**
  - `Review`: foreign key to `Product` (cascade on product delete), foreign
    key to the user (the author), a rating (positive small integer validated
    to 1–5), a title (max 50 characters), a comment (max 1,000 characters),
    a saved display name, a flag, and created and updated timestamps. The
    product–author pair is unique.
  - The **display name is saved on the review when it is created**, in the
    censored form `first letter + "****" + last letter` (a one-letter
    username uses the same letter at both ends). It never changes
    afterward, the same way orders copy product names at checkout. This
    keeps the public name stable when `User.deactivate()` renames the
    account to `deleted-user-<pk>`.
  - The "edited" tag shows when the review has been updated after creation,
    by its author or by staff.
  - `ReviewReport`: foreign key to `Review` (cascade), foreign key to the
    reporting user, a reason choice (Spam, Offensive language, Off-topic,
    Other), an optional note, and a created timestamp. The review–reporter
    pair is unique, so each customer reports a review at most once, ever.
  - Logic lives on the models and managers: eligibility to review, the
    censored-name rule, the banned-word check, flagging, and clearing.
- **Eligibility.** A customer may create a review of a product only if they
  have an order with status Delivered that contains an order item for that
  product, and they have no review of it yet. Editing and deleting need only
  ownership of the review. A later cancellation does not remove the review.
  Staff (`is_staff`) cannot write reviews.
- **Permissions.** Customers can edit and delete only their own reviews:
  every customer-side lookup goes through `request.user`. Staff can edit and
  delete any review. Customer-only actions use `LoginRequiredMixin`;
  back-office views use `StaffRequiredMixin` (anonymous to login, non-staff
  403). Signed-in customers may report any review except their own; staff
  do not report.
- **Moderation.**
  - Reviews are published immediately; there is no approval queue.
  - The banned-word list is a constant in code. A review is checked when
    created and every time its author edits it; a match flags it.
  - Any report flags the review.
  - A staff edit clears the flag. Staff can also clear a flag directly.
    Clearing keeps the existing reports; a report from a customer who has
    not reported that review before flags it again.
  - Report forms validate that the note is present when the reason is
    Other; it is optional otherwise.
- **Product detail page (HTMX).** A reviews section shows the average
  rating rounded to one decimal place and the review count, or "No reviews
  yet." It lists reviews newest first, with the signed-in customer's own
  review pinned at the top and not repeated below. The first 5 reviews load
  with the page; a "Show more" button fetches the next 5 and appends them.
  - Creating a review posts the form via HTMX and swaps the new review in at
    the top, with the average and count updated without a full reload.
    Validation errors re-render the form in place.
  - Edit swaps the review card for a pre-filled form; saving or cancelling
    swaps the card back.
  - Delete uses `hx-confirm` and removes the card in place, updating the
    average and count.
  - Report opens the reason drop-down and optional note in place; after
    submitting, the button reads "Reported". A customer who has already
    reported a review sees "Reported" from the start.
  - Signed-out visitors see a sign-in hint (with `next` back to the product)
    instead of the form. Signed-in customers who are not eligible see "You
    can review this product once an order containing it has been
    delivered." A customer who already has a review sees no form.
  - Partials are underscore-prefixed and never extend the base template.
- **Back-office Reviews tab.** A new Reviews tab in the back-office tab bar
  beside Products, Orders, Coupons, and Dashboard. It lists every review,
  flagged first, then newest first, with filter tabs (All and Flagged). Each
  row shows the product, the author's **full, uncensored username**, rating,
  title, flag status, and the number of reports with their reasons. Reviews
  whose author has been deactivated show a "Deactivated account" badge next
  to the account's current username. Staff can edit, delete, and clear the
  flag from here.
- **Account deletion.** `User.deactivate()` keeps the user row, so the
  author's reviews stay published under their saved censored name and still
  count toward the product's average. The deactivated author can no longer
  sign in, so only staff can change those reviews afterward.
- **Product deletion.** Deleting a product deletes its reviews and their
  reports.
- **Seed.** The seed command deletes all reviews and reports during its
  reset and creates demo reviews, backed by Delivered orders for their
  authors so the data obeys the eligibility rule. One product gets more than
  five reviews so the "Show more" button appears. Its summary output reports
  the reviews.
- **Styling.** Tailwind and DaisyUI classes only; no JavaScript beyond HTMX.
- **Testing.** pytest + pytest-django with plain fixtures in the
  project-level conftest. Cover: eligibility (Delivered only; placed,
  shipped, and cancelled orders do not qualify; staff cannot review),
  one review per product, editing without a delivered order, a review
  surviving cancellation, the censored-name rule including one- and
  two-character usernames, title and comment limits, ownership (a customer
  cannot edit or delete another's review), staff edit and delete keeping the
  author, the banned-word check on create and customer edit, a staff edit
  clearing the flag, reports (once per customer, never own, note required
  only for Other, re-flagging after a clear), the Reviews tab's ordering,
  filters, full usernames and deactivated badge, newest-first order with
  the pinned own review, the 5-per-page "Show more", the average and empty
  state, the HTMX responses, reviews kept after account deletion with their
  saved name, cascade on product delete, and the seed reset.

## Out of Scope

- Average ratings or stars on catalog and category product cards.
- Sorting or filtering reviews on the product page (by rating, helpfulness,
  and so on), and "helpful" votes.
- Photos or other attachments on reviews.
- Staff or store replies to reviews.
- An approval queue that holds reviews before they go live.
- Reviews written by staff.
- Reviewing a product more than once, or one review per order line.
- Email or other notifications about new reviews, reports, or staff edits.
- Editing the banned-word list from the back office (it is a constant in
  code).
- Review analytics on the staff dashboard.

## Further Notes

- The original grill-me interview ran in an earlier session and was not
  saved; its decisions were rebuilt from the user's saved answers and then
  confirmed and completed in a follow-up interview on 2026-10-26. This PRD
  reflects the confirmed decisions.
- The product page interactions follow the existing HTMX patterns in the
  cart and wishlist: button and form partials swapped in place, and
  owner-scoped lookups through `request.user`.
- Back-office edit, delete, and clear-flag actions follow the existing
  back-office tabs (Products, Orders, Coupons), which use plain forms and
  success messages; only the product page interactions were required to
  avoid a full reload.
- A clean customer edit does not clear an existing flag; only staff clear
  flags, either directly or by editing. This follows from "re-check
  customer edits, staff edits clear it".
- CLAUDE.md's project layout should gain a `reviews/` entry, and the PRD
  and plan pair should be listed alongside the others, when the feature is
  built.

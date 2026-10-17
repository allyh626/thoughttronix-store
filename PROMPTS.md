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

## 2026-10-17 — Build Phase 2 of the account security center (email delivery and the verification link)

### Prompts
1. @prd/account-security-center.md  @plans/account-security-center.md Do Phase 2.
2. have you seen my attempts at pasting the link displaying the verification link doesnt work page?
3. yes making that change would allow the user to just copy and paste the link as is without having to edit it themselves correct? if so implement this change and tests for the change as well
4. perfect, i double checked each file to make sure no features that werent agreed on were implemented without my knowledge, can you double check as well
5. okay thats alright, can you write the PROMPTS.md file entry for this session?

### Summary
- **Outcome:** Built Phase 2 of `plans/account-security-center.md`:
  - `config/settings.py` reads `EMAIL_BACKEND`, host, port, user,
    password, TLS, and `DEFAULT_FROM_EMAIL` from the environment, and adds
    `EMAIL_VERIFICATION_TIMEOUT` (3 days). The new keys are documented,
    commented out, in `.env.example`.
  - `accounts.User` gained `email_verification_token()` (a
    `django.core.signing` token naming the user and the address),
    `send_verification_email(request)`, and the classmethod
    `verify_email_token(token)`. A link only works while its address is
    still the account's unverified email, so it fails once used or once
    the address changes.
  - Signup sends the verification email and still redirects to sign-in.
    New `VerifyEmailView` (GET) and `ResendVerificationView` (POST,
    sign-in required). The resend URL sits before the token URL.
  - New templates: `templates/accounts/emails/verify_email.txt` and
    `templates/accounts/verify_email_failed.html` (status 400, with a link
    to My account to resend). My account shows a "Resend verification
    email" button only when the email is unverified.
  - After prompt 2: a new development backend,
    `config/email_backends.py` (`ReadableConsoleEmailBackend`), is now
    the default. It prints each email's plain body so the link can be
    copied as is.
  - 15 new tests in `accounts/test_security.py` and 2 in
    `config/test_email_backends.py`, one of which copies the link from
    captured terminal output and follows it. Phase 2's seven criteria are
    ticked off in the plan.

  Suite at 331 passed, and `ruff check` and `ruff format` are clean. No
  migrations. Nothing committed.
- **Deviations:** Following the saved preference, I explained each edit
  before making it, and each went through the approval prompt. The new
  console backend departs from the PRD's "defaults to the console
  backend". The user approved it. On review (prompt 4), I listed small
  choices the plan left open, and the user accepted all of them: the new
  signup message, the verify link going to My account or sign-in, the
  Resend message when there's nothing to confirm, one error message for
  expired, used, or tampered links, `DEFAULT_FROM_EMAIL` being
  overridable from `.env`, and verifying on a plain GET.
- **Sideways:**
  - The user's manual test failed: every pasted link showed "This
    verification link doesn't work". Django 6's console backend prints
    the encoded message. The link line is over 78 characters, so it came
    out quoted-printable, wrapped with a trailing `=`, and the pasted
    token was broken. My tests missed it because Django's in-memory
    outbox keeps the unencoded body. I reproduced it in the shell, then
    fixed it with the new backend and a test that reads the link from
    the terminal output. I didn't run the new test against the stock
    backend to watch it fail.
  - While building, I first put the resend URL after the token URL, where
    "resend" would have been read as a token. I caught it before running
    the tests. A test assertion expected `doesn&#x27;t`, but text written
    directly in a template isn't escaped, so I fixed the assertion.
  - `ruff format` re-wrapped two over-long lines I had written in
    `accounts/models.py` and `accounts/views.py`.
  - `db.sqlite3` shows as modified from the user's own manual testing.
    I didn't touch it. Whether to commit or restore it was left to the
    user.

## 2026-10-16 — Build Phase 1 of the account security center (email at signup, shown on My account)

### Prompts
1. @prd/account-security.md @plans/account-security-center.md Do Phase 1.
2. okay so i will first have to run uv run python manage.py seed and then that is the full walkthrough of how to verify this manually?
3. are these git bash or powershell commands?
4. it worked manually and i didnt pick up on any inconsistencies between the feature and the plan, can you double check that the work used the acceptance criteria fore the phase in plans/account-security-center.md?
5. you can tick them off if that means the phases impkementation is complete,  can you write a prompt in prompt.md for this session

### Summary
- **Outcome:** Built Phase 1 of `plans/account-security-center.md`:
  - `accounts.User` overrides `email` to be unique and nullable, and adds
    `email_verified` (default false). `User.save()` lowercases the email
    and stores a blank one as `null`.
  - Hand-written migration `accounts/migrations/0003_user_email_unique.py`
    in three steps: allow `null`, turn blanks into `null` and lowercase
    the rest, then add the unique rule. Several blank emails would
    otherwise have broken the unique rule.
  - `SignupForm` requires an email, and `clean_email()` rejects one
    already in use, ignoring capitalization.
  - My account has a "Sign-in & security" section above the address
    book, showing the email with a Verified / Unverified badge, or "No
    email on file."
  - The seed creates every user with `email_verified=True`.
  - 12 new tests in `accounts/test_security.py`. The two existing signup
    tests now send an email, and the seed test checks that every seeded
    user is verified.

  Suite at 315 passed, and `ruff check` and `ruff format` are clean. The
  migration ran on the user's dev database (no blank emails left). The
  user checked the feature manually in the browser, then asked me to
  check the work against the Phase 1 acceptance criteria. All 8 were met,
  so they were ticked off in the plan. Nothing committed.
- **Deviations:** Following the saved preference, I explained each edit
  before making it, and each went through the approval prompt. Follow-up
  questions: whether running `seed` was the whole manual check (I gave a
  7-step walkthrough), and whether the commands were for Git Bash or
  PowerShell (they work in both).
- **Sideways:**
  - The first prompt named `prd/account-security.md`, which doesn't
    exist. I used `prd/account-security-center.md`, the PRD the plan
    names.
  - `ruff format --check` flagged one over-long line in the new test file.
    I wrapped it by hand.
  - Gaps I reported but didn't fix: the data migration has no automated
    test, "unverified customers can check out" relies on the existing
    checkout tests rather than a test of its own, and a bulk `.update()`
    of emails would skip the lowercasing in `save()`.
  - After the migration, every user on the dev database showed
    "Unverified" until `seed` was rerun.
  - As before, every `uv run` printed the harmless `VIRTUAL_ENV`
    mismatch warning.

## 2026-10-14 — Design (via /grill-me) the account security center and write its PRD

### Prompts
1. /grill-me thoughttronix needs an improved account security center where customers can manage important account details: allowing users to provide an email when creating an account, change their password, and reset a forgotten password through email. Feel free to suggest any other features you feel would be an improvement and should be implemented in the new account security center.
2. a *(Q1, email required at signup)*
3. a is fine *(Q2, emails unique in the database, stored lowercase, blanks become `null`)*
4. a *(Q3, a gentle reminder on My account for accounts with no email)*
5. i like option b, under its implementation are the users able to checkout or complete an order with an unverified email address on their account? *(Q4, verify by link without blocking)*
6. c *(Q5, email change needs the current password, stays pending until confirmed, and sends a notice to the old address)*
7. a *(Q6, a "Sign-in & security" section on My account)*
8. b *(Q7, stay signed in after a password change, other devices signed out, notice email)*
9. a *(Q8, the reset page shows the same generic message every time)*
10. a *(Q9, after a reset, go to the sign-in page)*
11. yes i like b *(Q10, reset links last 1 hour, verify links 3 days, plus a resend button)*
12. yes B *(Q11, email settings from `.env`, console backend by default)*
13. a is fine *(Q12, plain-text emails)*
14. i like options 1, 2, 3, 4, and 5 *(Q13, which extras: sign-in limit, sign out other devices, recent activity, checkout email pre-fill, delete account)*
15. b *(Q14, build the sign-in limit by hand with a `SignInAttempt` model)*
16. a *(Q15, limit by username: 5 failures in 15 minutes pauses sign-in for 15 minutes)*
17. a *(Q16, a `session_salt` field for "sign out of all other devices")*
18. b *(Q17, a "Recent activity" list of the last 5 attempts, 90-day cleanup)*
19. a *(Q18, deleting an account deactivates and scrubs it; orders are kept)*
20. a *(Q19, deletion blocked while any order is Placed or Shipped)*
21. /to-prd
22. i have reviewed the prd manually to ensure it discusses all the design decisions we agreed upon. can you verify the decisions from the interview are being represented correctly and not adding any requirements I never agreed to? make sure all decisions I made are included in the file and the user stories correctly describe the feature we agreed on?
23. where is user story 37 located?
24. why are the user stories not under the user story headin gin the prd?
25. Append a session log to PROMPTS.md at the repo root, under today's date, newest entry at the top. Record every prompt I gave you this session, in order, including any corrections. End the entry with a short summary: the outcome, any places where I deviated from a recommended answer or asked follow-up questions, and anything that went sideways.

### Summary
- **Outcome:** A 19-question grill-me interview settled the account
  security center's design:
  - Email at signup: required, unique, lowercase, and verified by a link
    that doesn't block shopping.
  - Email change: needs the current password, stays pending until the new
    address is confirmed, and notifies the old address.
  - Password: change it with a notice email, and reset it through
    Django's built-in views. Resets go only to verified emails, and the
    reset page always shows the same generic message.
  - Links: reset links last 1 hour and verify links 3 days. Email
    settings come from `.env` with a console default, and all emails are
    plain text.
  - Extras: a hand-built per-username sign-in limit, "sign out of all
    other devices," a recent-activity list, checkout email pre-fill, and
    account deletion (deactivate and scrub, blocked while orders are
    open).

  `/to-prd` wrote it all to `prd/account-security-center.md`, with 42
  user stories. No feature code was written. The user asked me to check
  the PRD against the interview. That review confirmed all 19 decisions
  are in it and found 6 issues, listed under Sideways. None of the fixes
  have been applied to the PRD yet. Per the user's preference, I gave the
  replacement lines for the user to type rather than editing the file.
  The PRD is still uncommitted.
- **Deviations:** In Q13, the user picked items 1–5 instead of my
  recommended 1, 3, and 4. That added "sign out of all other devices"
  and "delete my account," which led to Q16, Q18, and Q19. In Q4, the
  user asked whether customers with an unverified email can still check
  out. I checked the code: checkout has its own email field and never
  reads `user.email`, so the answer was yes, and that's when checkout
  email pre-fill came up as an extra. In Q15, the user answered "a" but
  didn't comment on the proposed numbers (5 tries / 15 minutes /
  15 minutes), so the PRD treats those as accepted. Every other question
  took the recommended answer. Follow-up questions after the PRD asked
  where story 37 is (lines 157–158) and why the stories didn't seem to be
  under the User Stories heading.
- **Sideways:** The PRD review found six problems in what I wrote:
  - I added two details you never agreed to:
    - The `SignInAttempt` model stores usernames lowercase. That's a real
      bug, because Django usernames are case-sensitive.
    - `deactivate()` makes the password unusable and clears the pending
      email. Both are harmless, but they weren't decided.
  - I changed one decision: the email-change notice timing became
    "once confirmed." The safer timing, which I suggested, is "when
    requested."
  - Story 37 promises more than the design delivers. Orders keep copies
    of the name and address.
  - Two gaps:
    - The PRD never says which form adds a first email.
    - `deactivate()` leaves sign-in history behind under the freed-up
      username.

  In the interview, I also said option A of Q8 "needs no custom code."
  That's wrong: sending resets only to verified emails needs a small
  custom reset form. The PRD already says so correctly. Finally, I split
  the user stories into 11 `###` subgroups that the PRD template doesn't
  have. That made the stories look like they weren't under the User
  Stories heading, and I gave the user the 11 lines to delete to flatten
  the list.

## 2026-10-09 — Build product images (uploads, validation, cleanup, display, seed) from the handoff

### Prompts
1. @HANDOFF.md Implement this feature
2. *(Correction: rejected my question about how to work and where to put the unused image, to clarify first.)* can you implement the changes but get my permission and show me what change is being made before it is done? and you can just delete the unused image
3. can you fix the HEIC file inconsistency and correctly inform them that it is a HEIC (iphone) photo?
4. what steps do i take to manually verify the feature in the browser
5. yes if you could implement the test files
6. delete the tests folder? *(Correction: rejected my attempt to delete `Desktop\image-test-files`.)*
7. how can i run and check the test files just created?
8. uv run python manage.py seedhasa the handoff file been deleted?
9. yes can you delete it
10. write the session log for the implementation of the feature with the prompt in the prompts.md header

### Summary
- **Outcome:** Built the product-image design from `HANDOFF.md`:
  - Pillow added. `MEDIA_ROOT`/`MEDIA_URL` added, with defaults. Media
    served only while `DEBUG`. `media/` gitignored.
  - `Product.image`, plus migration `0004_product_image.py`.
  - One validator, `products/validators.py`, shared by the upload form
    and the seed, using the approved wording.
  - `ProductImageField` replaces Django's `forms.ImageField`, so only
    those messages are shown. Uploads are renamed to `<slug>.<detected
    extension>`.
  - The edit form got a preview, a DaisyUI `file-input`, a "Remove
    current image" checkbox (`_image_field.html`), `enctype`, and the
    rejection banner.
  - Old image files are deleted after commit, from `Product.save()` and
    `Product.delete()`.
  - `display_image_url` is used on the catalog (4:3 crop) and the detail
    page (uncropped, height-capped).
  - The 12 images moved to `products/seed_images/<slug>.png`. The seed
    validates and attaches them and empties `media/products/` on wipe.
  - 24 tests added in `products/test_images.py`, with `media_root` and
    `product_with_image` fixtures. The two existing seed tests now use
    `media_root`.

  On request, HEIC files are recognized by their header bytes and get
  the "unsupported type" message as "HEIC (iPhone)", where they used to
  get "isn't an image file". I generated 11 manual-test files in
  `Desktop\image-test-files` (outside the repo) and wrote browser
  verification steps. Final state: 303 passed, and `ruff check` and
  `ruff format` are clean. Nothing committed.
- **Deviations:**
  - The user changed the working mode from their saved preference (typing
    edits themselves) to me applying each edit after they approve it. I
    updated the saved memory.
  - The previous session planned to keep `SyncRest GPT Text.png` outside
    the repo. The user chose to delete it instead.
  - The "HEIC (iPhone)" wording is my fill of the approved
    `<FORMAT>` template, not wording the user approved separately.
  - Follow-up questions: how to verify in the browser, how to use the
    test files, and whether `HANDOFF.md` was deleted. The user then asked
    for it to be deleted, and it was.
  - The handoff's suggested `run`, `code-review`, and `simplify` skills
    weren't used, and I didn't run the seed against the user's own
    database or check anything in a browser.
- **Sideways:**
  - `ruff check` failed twice on DJ012 (model method order). While fixing
    it, I duplicated `_delete_image_file_on_commit`. I caught that by
    reading the file back and removed the duplicate.
  - I told the user I'd added "25 new tests". There were 23 (24 after the
    HEIC case). The miscount was found while writing this log.
  - The handoff said Django's model `ImageField` adds the extension
    validator. It's only the form field, so replacing the form field was
    enough.
  - I read "delete the tests folder?" as a request and tried to delete
    the Desktop test files. The user rejected it, so the folder still
    exists.
  - As in earlier sessions, every `uv run` printed the harmless
    `VIRTUAL_ENV` mismatch warning.

## 2026-10-09 — Design (via /grill-me) product images for the catalog and back office; hand off to the build session

### Prompts
1. /grill-me The thoughttronix store needs images displayed on the catalog, located in the product-images folder. Every product currently shows a placeholder, every product must display either its uploaded image when one is available or the existing placeholder. Employees will also upload product images through the back office, validate files are supported before accepting them. Do not accept a file and then discard it. If an uploaded image is not supported display a message informing the employee the uploaded image was rejected and explain the problem in easily understood language. Missing files and broken image icons should not be approved for display.
2. Option A *(Q1, an `ImageField` with uploads in `media/` and Pillow added)*
3. Option A *(Q2, accept JPEG, PNG, and WebP only, judged by the file's contents)*
4. yes lets do option a *(Q3, 5 MB maximum)*
5. yes option a *(Q4, decode the whole image so damaged files are rejected)*
6. yes option a *(Q5, a model property falls back to the placeholder if the file is missing)*
7. is there another image available for the mark II? wouldnt it be redundant to display an image for a product not for sale? *(Q6, which SoulSear product gets the one image)*
8. yes option a *(Q6 revised, SoulSear Mark II)*
9. yes option a *(Q7, the SyncRest image without text)*
10. yes option a *(Q8, move to `products/seed_images/<slug>.png` and commit)*
11. yes option a *(Q9, the seed empties `media/products/` on wipe)*
12. yes option a *(Q10, a "Remove current image" checkbox)*
13. yes option a *(Q11, delete old files after the save commits)*
14. yes option a *(Q12, error banner plus a field-level reason)*
15. yes option a *(Q13, 4:3 cropped cards; full image on the detail page)*
16. yes option a *(Q14, images on the catalog and detail pages plus the edit-form preview only)*
17. i agree with option b *(Q15, saved filename is `<slug>.<real extension>`)*
18. i approve of the wording *(Q16, the rejection messages, banner, and help text)*
19. yes option a *(Q17, the seed validates its images and fails loudly)*
20. yes option a *(Q18, serve media only while `DEBUG`; gitignore `media/`)*
21. i thought the change in safety/ was already committed
22. what was changed in urls.py
23. now we have come to a shared understanding of the designhave i correctly restored it?
24. /handoff the next session implements the design we just agreed upon
25. keep it outside the repo
26. follow the standard session-log prompt in the header of PROMPTS.md and write the session log for this session

### Summary
- **Outcome:** An 18-question grill-me interview settled the full design
  for product images: storage, validation rules, approved rejection
  wording, the seed image mapping, back-office upload and remove
  controls, file cleanup, display and cropping, and media serving. No
  feature code was written. The design and a build plan are recorded in
  `HANDOFF.md` for the next session. The user discarded a stray
  formatting-only change to `config/urls.py` themselves with
  `git restore`, and I confirmed the working tree is clean apart from
  `product-images/`, plus the new `HANDOFF.md` and this entry.
- **Deviations:** In Q6, the user challenged my first recommendation
  (SoulSear Mark I) by asking whether Mark II had its own image (it
  doesn't) and whether showing the only image on a product nobody can
  buy was wasteful. I changed my recommendation to Mark II, and the user
  took it. Every other question took the recommended answer. Follow-up
  questions covered the `config/urls.py` change: whether `safety/` was
  already committed (the route was, in `b9ce176`, and only a one-line
  reformat was uncommitted), what exactly had changed, and whether the
  restore worked (it did). I twice offered to write a PRD and plan in
  `prd/` and `plans/`. The user didn't take it up and asked for a handoff
  instead. On the unused `SyncRest GPT Text.png`, the user chose to keep
  it outside the repo; the next session will ask where.
- **Sideways:** My first Q6 recommendation missed that the image does
  more work on a product customers can buy. The user caught it. I also
  said the user had "squashed" the `safety/` route onto one line. What
  actually caused that change is unknown (most likely an editor
  auto-format), and I corrected the wording when asked. No tests or lint
  were run because no code changed.

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

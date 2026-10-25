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

## 2026-10-25 — Build Phase 6 of the wishlist (seed the demo wishlist)

### Prompts
1. /implement @prd/wishlist.md @plans/wishlist.md implement phase 6
2. okay i guess I didn't realize i should have combined this phase and
   completed it earlier on, this plan is acceptable

### Summary
- **Outcome:** Built Phase 6 of `plans/wishlist.md`, completing the
  wishlist feature:
  - `seed` wipes every wishlist in `_wipe()` (beside the carts), so even
    non-demo accounts' wishlists are cleared, not just the cascaded ones.
  - New `CUSTOMER_WISHLIST` constant and `_create_customer_wishlist()`:
    the `customer` demo login saves MindSync Duo, EchoPatch (unavailable),
    RecallPro, and Pulse Halo through `Wishlist.for_user` / `add`, then
    each `added_at` is backdated (3, 12, 25, 40 days) so the My wishlist
    page shows distinct dates in newest-first order.
  - The summary line reports "4 wishlist items"; the seed docstring,
    README demo-login table, and CLAUDE.md (new `wishlist/` layout entry,
    wishlist PRD/plan pair listed) were updated.
  - Tests: the demo-world test checks the four slugs in order and an
    unavailable item; the idempotence test compares `WishlistItem`
    counts; new `test_seed_resets_every_wishlist` covers a non-demo
    user's wishlist. Suite at 462 passed; ruff check and format clean;
    `seed` run twice by hand gave identical output.
- **Deviations:** No TDD behaviors — the phase is seed data and docs, which
  the TDD skill excludes; the user approved the plan and the four
  products as proposed. The user wondered whether this phase should have
  been folded into an earlier one; kept separate so seed changes only
  after the feature works.
- **Sideways:** None.

## 2026-10-25 — Build Phase 5 of the wishlist (live navbar count badge)

### Prompts
1. /implement @prd/wishlist.md @plans/wishlist.md implement phase 5
2. can option 2 be verified manually from the broswer? im not sure how id check that
3. yes, use tdd for both behaviors
4. yes, make it pass
5. yes you can now implement behavior 2
6. yes, make it pass
7. yes you can complete the phase

### Summary
- **Outcome:** Built Phase 5 of `plans/wishlist.md`, following the cart
  badge:
  - The `wishlist` context processor also returns `wishlist_item_count`
    (`len` of the saved-id set it already loads, so still one query; `0`
    for anonymous requests).
  - New `templates/wishlist/partials/_wishlist_badge.html` (stable
    `id="wishlist-badge"`, `oob` flag, count shown only above zero),
    included in the navbar in place of the plain Wishlist link.
  - `wishlist:add` and the HTMX branch of `wishlist:remove` pass
    `oob_badge: True`, and `_wishlist_button.html` then includes the
    badge with `hx-swap-oob="true"`. The plain-form remove still
    redirects before reaching that code.
  - TDD on two approved behaviors: the navbar count (no number when
    empty, `2` after saving two) and the out-of-band badge in both HTMX
    responses (`1` after add, no number after remove). A small
    `_wishlist_badge` test helper cuts the link out of the page so the
    cart badge can't satisfy the assertions. Suite at 461 passed; ruff
    check clean.
- **Deviations:** Follow-up question before approving the TDD list: whether
  the out-of-band swap can be checked in the browser. Answered: watch
  the navbar count change without a reload, or open DevTools → Network,
  click the button, and read the response for the
  `id="wishlist-badge" ... hx-swap-oob="true"` link. Both behaviors were
  then approved as listed.
- **Sideways:** Both first test runs failed with `ValueError: substring
  not found` instead of an assertion. Behavior 1 needed the badge
  partial's id in place first (scaffolding, then a real RED on the
  missing `2`). Behavior 2 got a mechanical test repair, an explicit
  `id="wishlist-badge"` check before the helper, which gave a real RED
  without changing what it asserts. `ruff format` re-wrapped one line
  of the new tests. No live browser run in this session; the swap is
  verified through server responses only. `uv run` printed the usual
  harmless `VIRTUAL_ENV` mismatch warning.

## 2026-10-25 — Build Phase 4 of the wishlist (act on items from My wishlist)

### Prompts
1. /implement @prd/wishlist.md @plans/wishlist.md implement phase 4
2. yes you can use tdd for those two behaviors
3. yes, make it pass
4. yes you can move onto behavior two
5. yes, make it pass
6. yes, continue with the rest of the phase

### Summary
- **Outcome:** Built Phase 4 of `plans/wishlist.md`:
  - `RemoveFromWishlistView` now serves two callers. With the
    `HX-Request` header (the detail page) it still returns the button
    partial; without it (a plain form post from My wishlist) it flashes
    "Removed <product> from your wishlist." and redirects to
    `wishlist:list`.
  - `templates/wishlist/wishlist.html` gained an Actions column: the
    existing `orders/partials/_add_button.html` included as-is (HTMX add,
    "In cart (N)", disabled "Unavailable", cart badge update) and a plain
    POST Remove form with `{% csrf_token %}`.
  - TDD on two approved behaviors: the plain remove's redirect and
    message (RED on `200 == 302`), and the row's add-to-cart button and
    Remove form (RED on the missing `/cart/add/1/`). Two more ordinary
    tests: the item stays saved after an add to cart, and removing the
    last item (following the redirect) shows the message and the empty
    state. Suite at 459 passed; ruff check and format clean. Phase 4
    boxes ticked in the plan, along with the Phase 1–3 ticks that were
    still uncommitted.
- **Deviations:** None — both proposed TDD behaviors were approved as
  listed, and every step took the suggested next action.
- **Sideways:** Nothing failed outside the planned RED runs. The CSRF
  token on the Remove form isn't asserted in tests, because `base.html`
  already prints one for sign-out (the assertion would always pass), so
  it is left to the browser check. Known edge left in place: a signed-out
  Remove would land on the remove URL as a GET (405) after sign-in, the
  same as add; it can't be reached from the UI, which requires sign-in.
  No live browser run in this session; the HTMX add from the wishlist
  page is verified through server responses only. `uv run` printed the
  usual harmless `VIRTUAL_ENV` mismatch warning.

## 2026-10-25 — Build Phase 3 of the wishlist (My wishlist page)

### Prompts
1. /implement @prd/wishlist.md @plans/wishlist.md implement phase 3
2. yes, go ahead
3. go ahead
4. yes, go ahead
5. yes could you do that check please
6. yes, go ahead

### Summary
- **Outcome:** Built Phase 3 of `plans/wishlist.md`:
  - `WishlistView` (`LoginRequiredMixin` + `ListView`) at `/wishlist/`
    (`wishlist:list`). It lists `WishlistItem`s filtered by
    `wishlist__user=request.user`, with `select_related("product__category")`
    so the page stays at 5 queries however many rows there are. Viewing the
    page never creates an empty wishlist.
  - `templates/wishlist/wishlist.html`: the h1 and opacity-70 description,
    then a table with image, a name linking to the product page, price,
    saved date, and the "Unavailable" badge. A 💭 empty state links to the
    catalog.
  - A "Wishlist" link in the navbar between Orders and Account, for
    signed-in users only (no count yet; that's Phase 5).
  - TDD for two behaviors: only your own items are listed, and newest
    saved first. Plus 7 normal tests: anonymous redirect, row contents,
    badge shown and not shown, empty state, and the navbar link signed in
    and signed out. Full suite: 455 passed; `ruff check` and
    `ruff format --check` clean.
- **Deviations:** No recommendations were overridden. Following the saved
  preference, each edit was explained before it was made and went through
  the approval prompt. Asked for the optional check that the newest-first
  test can really fail.
- **Sideways:** The newest-first test passed before any code was written,
  because Phase 1's `Meta.ordering = ["-added_at"]` already supplied the
  ordering, so there was no RED step. To prove the test wasn't passing by
  luck, the view was temporarily changed to `.order_by("added_at")`. The
  test failed as expected, and the change was undone. The smoke test ran
  against a scratch copy of the database to protect the real one. As
  before, `uv run` printed the harmless `VIRTUAL_ENV` mismatch warning.

## 2026-10-21 — Build Phase 10 of the account security center (checkout email pre-fill)

### Prompts
1. @prd/account-security-center.md @plans/account-security-center.md Do Phase 10.
2. append a session log to PROMPTS.md

### Summary
- **Outcome:** Built Phase 10 of `plans/account-security-center.md`, the
  last phase of the plan:
  - `CheckoutView.get_initial()` in `orders/views.py` now pre-fills the
    checkout email field with the account's email, verified or not,
    alongside the existing saved-address pre-fill. Accounts without an
    email get a blank field. The customer can still edit it, and the order
    copies whatever is submitted. No order or service code changed.
  - 3 tests in `orders/test_checkout_addresses.py`: the account email is
    pre-filled, an account with no email gets a blank field, and an edited
    email is what the order stores. Phase 10 boxes ticked in the plan. Full
    suite: 421 passed; `ruff check` and `ruff format --check` clean.
    Nothing committed.
- **Deviations:** No recommendations were overridden and no follow-up
  questions were asked. Following the saved preference, the agent explained
  each edit before making it and each one went through the approval prompt.
  The agent put the new tests in the existing checkout pre-fill test file
  rather than a new file, without asking.
- **Sideways:** Nothing broke. As in earlier sessions, every `uv run`
  printed a warning that the outer `VIRTUAL_ENV`
  (`C:\Users\ally\CIDM3312\.venv`) doesn't match the project `.venv`; uv
  used the project environment, so it was noise only.

## 2026-10-21 — Build Phase 9 of the account security center (delete account) and restyle its box

### Prompts
1. @prd/account-security-center.md @plans/account-security-center.md Do Phase 9.
2. can you move the delete account box below every other setting where saved addresses is shown, I would also like to make it more visible to the user, such as making the box darker
3. perfect can you update the prompts.md file with this sessionss logs

### Summary
- **Outcome:** Built Phase 9 of `plans/account-security-center.md`:
  - `accounts.User` gained `open_orders()` (orders still Placed or
    Shipped), `has_open_orders()`, and `deactivate()`. `deactivate()`
    keeps the row but sets `is_active=False`, renames the username to
    `deleted-user-<pk>`, clears the email, pending email, verification,
    and first and last name, makes the password unusable, picks a new
    `session_salt`, and deletes saved addresses. Orders stay attached.
    No migration was needed.
  - A new `DeleteAccountForm` in `accounts/forms.py`, built on Phase 8's
    `ConfirmPasswordForm`. It adds a required "I understand" checkbox, and
    its `clean()` refuses the deletion while there are open orders.
  - `DeleteAccountView` (`LoginRequiredMixin` + `UserPassesTestMixin` +
    `FormView`) at `/accounts/delete/` (`accounts:delete_account`). Staff
    and superusers get a 403. On success it deactivates the account, signs
    out, and redirects to the catalog with "Your account has been deleted.
    Thanks for thinking with us."
  - A confirmation page `templates/accounts/delete_account.html`. With open
    orders it lists each order number (linked to its detail page) and
    hides the form.
  - 19 tests in `accounts/test_security.py`, covering open orders by
    status, each part of `deactivate()`, a wrong password, a missing
    checkbox, open orders blocking deletion and being listed, staff and
    superusers refused, and success with orders kept and dashboard totals
    unchanged. Phase 9 boxes ticked in the plan. Full suite: 418 passed;
    `ruff check` and `ruff format --check` clean.
  - On request, the Delete account card moved out of Sign-in & security
    to its own section at the bottom of My account, below Saved
    addresses. It now has a darker background (`bg-base-300`), a red
    border, a red heading, and a filled red `btn-error` button. Staff
    still don't see it. Accounts tests re-run: 160 passed. Nothing
    committed.
- **Deviations:** The agent made several choices without asking:
  - `deactivate()` also clears first and last name, which the plan didn't
    list. The PRD says personal data is deleted, and this was reported to
    the user.
  - Staff get a 403 rather than a redirect.
  - The farewell lands on the catalog.
  - The delete link is hidden from staff on My account.
  - A deleted account's sign-in history stays under the old username
    until the 90-day prune; this was reported.

  As in Phase 8, the agent made the edits directly, explaining each one
  before making it, instead of asking at the start which way the user
  wanted to work. The user asked no follow-up questions; the restyle was
  their own design request.
- **Sideways:** Nothing failed. Right after writing the view, the agent
  noticed its staff check let through a superuser not marked `is_staff`,
  and fixed it before any test run. Neither the new page nor the restyled
  box was checked in a browser, only through tests; the user was told the
  new color classes need `tailwind runserver` or `tailwind build` to
  appear. As before, `uv run` printed the harmless `VIRTUAL_ENV` mismatch
  warning.

## 2026-10-21 — Build Phase 8 of the account security center (sign out of all other devices)

### Prompts
1. @prd/account-security-center.md @plans/account-security-center.md Do Phase 8.
2. can you run the tests for phase 8
3. so to test phase 8 manually i run the migrations?
4. okay thank you for giving me hte steps to verify it manually, can you update the prompts.md file with the decisions made in this session please

### Summary
- **Outcome:** Built Phase 8 of `plans/account-security-center.md`:
  - `accounts.User` gained `session_salt` (32 random hex characters from
    a module-level `new_session_salt()`), with migration
    `accounts/migrations/0007_user_session_salt.py`. The session
    fingerprint is now an HMAC of the password *plus* the salt, so a new
    salt ends every session the way a new password does. A new
    `rotate_session_salt()` method picks a fresh salt; Phase 9's
    `deactivate()` is meant to reuse it.
  - A new `ConfirmPasswordForm` in `accounts/forms.py` (one "Current
    password" field), written to be reused by Phase 9's delete-account
    page.
  - `SignOutOtherDevicesView` (`LoginRequiredMixin` + `FormView`) at
    `/accounts/sessions/sign-out-others/` (`accounts:sign_out_other_devices`).
    With the right password it rotates the salt, re-stamps the current
    session with `update_session_auth_hash`, and returns to My account
    with "Every other device has been signed out." A wrong password shows
    an error and changes nothing.
  - A confirmation page `templates/accounts/sign_out_other_devices.html`,
    modeled on the change-password page, and a new "Devices" card on My
    account between Password and Recent activity.
  - 7 tests in `accounts/test_security.py`, using two `Client()`s as two
    devices. Phase 8 boxes ticked in the plan. Full suite: 402 passed;
    `ruff check` and `ruff format --check` clean. The 7 Phase 8 tests were
    re-run on request and passed. Nothing committed.
- **Deviations:** The plan named `get_session_auth_hash` as the method to
  change. The agent overrode Django's private `_get_session_auth_hash`
  helper instead, because both `get_session_auth_hash` and its
  `SECRET_KEY_FALLBACKS` twin call it, and reported this to the user. The
  agent chose the URL, the "Devices" card, and the reusable form without
  asking. The agent made the edits directly, explaining each one before
  making it, rather than asking at the start which way the user wanted to
  work. Follow-up questions: how to run just the Phase 8 tests (answered
  with a `pytest -k` command, explained piece by piece), and whether
  manual testing starts with the migration (yes; answered with a
  checklist using a normal and a private browser window as two devices,
  signed in as the seeded `customer`). At the time of this entry the
  agent had not seen the migration applied or the manual check done.
- **Sideways:** Nothing failed. The migration's callable default runs
  once for existing rows, so users who existed before the migration
  share one salt until it is rotated. This is harmless, because the
  password is in the fingerprint too, but it was not raised with the
  user during the session. A first attempt to edit this log used the
  wrong anchor text and was refused before it changed anything. As
  before, `uv run` printed the harmless `VIRTUAL_ENV` mismatch warning.

## 2026-10-21 — Build Phase 7 of the account security center (sign-in lockout), extend it to the Django admin login

### Prompts
1. @prd/account-security-center.md @plans/account-security-center.md Do Phase 7.
2. yes could you add those few lines to close that gap in the design
3. i dont want to count it as a failed sign in attempt if they are not staff, i would like to let the user know it was an attempted admin sign in but i dont want it to count towards thier account lockout
4. okay perfect how would i manually check this phase in the browser
5. okay perect the phase has been tested could you update the prompts.md fiel with this sessions decisions please

### Summary
- **Outcome:** Built Phase 7 of `plans/account-security-center.md`:
  - `SignInAttempt` gained `LOCKOUT_THRESHOLD = 5` and
    `LOCKOUT_WINDOW = 15 minutes`, and its queryset gained
    `is_locked_out(username)`. It counts failed sign-ins in the last 15
    minutes, but only those after the latest successful sign-in or
    password reset (both recorded as succeeded).
  - `SignInForm.clean()` checks the lockout before the password, so a
    locked username is refused even with the right password, with "Too
    many failed attempts — try again in a few minutes, or reset your
    password." The message is the same for unknown usernames, and staff
    and superusers sign in through the same form.
  - 12 lockout tests in `accounts/test_security.py`. Phase 7 boxes were
    ticked in the plan.
  - Then, at the user's request, the Django admin login (`/admin/`) was
    brought under the lockout: a new `AdminSignInForm(SignInForm,
    AdminAuthenticationForm)` in `accounts/forms.py`, switched on with
    `admin.site.login_form` in `accounts/admin.py`. Failures at both login
    pages share one count. 4 more tests.
  - Then a new attempt kind, `ADMIN_DENIED`: a non-staff account's
    *correct* password at `/admin/` is recorded as that kind, shown on My
    account as "Attempted admin sign-in", and never counted toward the
    lockout. A wrong password at `/admin/` still counts as an ordinary
    failure. Migration `accounts/migrations/0006_signinattempt_admin_denied.py`
    (choices only, no column change). 4 more tests.
  - Final suite: 395 passed; `ruff check` and `ruff format` clean. The
    user tested the phase in the browser. Nothing committed.
- **Deviations:** Two design calls made by the agent and reported to the
  user: attempts refused *during* a lockout aren't recorded, so retrying
  can't keep an account locked past 15 minutes (the PRD's limit); and the
  15 minutes are a sliding window over the failures, so the pause can
  lift a little sooner than 15 minutes after the 5th failure. The agent
  pointed out that `/admin/` bypassed the lockout (the plan only named
  `SignInForm`), and the user asked for it to be closed. The agent first
  counted a customer's refused admin sign-in as a failure and
  recommended keeping it that way; the user overrode that, asking for it
  to be shown to the customer but not counted. Follow-up question: how
  to check the phase manually in the browser (answered with a
  step-by-step checklist using the seeded demo accounts; the 15-minute
  expiry is covered only by the automated tests).
- **Sideways:** The first `ruff format --check` flagged one over-long
  line in a new test helper; it was wrapped by hand and re-checked
  clean. As before, `uv run` printed the harmless `VIRTUAL_ENV`
  mismatch warning.

## 2026-10-20 — Manually verify Phase 6 of the account security center (sign-in attempt history) and log the build session

### Prompts
1. how would i manually verify the changes we agreed on in phase 6
2. does this confirm the acceptance criterea of phase 6?
3. okay thank you can you check off the acceptance critera in the plan and update the prompts.md file with a session log, and is there a way for you to log a previous session as well? the one where we agreed on phase six's design structure?

### Summary
- **Outcome:** Wrote a step-by-step manual check for Phase 6, built from
  the plan's acceptance criteria and the uncommitted code: setup
  (`migrate`, `seed`, `tailwind runserver`), then a successful sign-in, a
  failed one, the lowercase username, the 5-row limit, a password reset
  (link copied from the server terminal), an unknown username (checked
  in the Django shell), the prune command (one attempt made 91 days old
  and one 89 days old in the shell, so exactly one is deleted), and
  `uv run pytest accounts/test_security.py`. Then mapped each criterion
  to those steps. No code was changed this session. Only this log was
  added.
- **Deviations:** Follow-up question: does the walkthrough confirm every
  criterion? Answer: mostly. The "for the signed-in user" part of the
  My account criterion wasn't checked by hand, so an extra step was
  added: sign in as a different demo user and confirm none of
  customer's attempts show. For the "tests cover" criterion, the new
  test names were listed under recording, activity list, and prune,
  because a passing run alone doesn't show what is covered. The
  request to check off the criteria needed no edit: the build session
  had already ticked all six Phase 6 boxes. The previous session was
  logged by reading its saved transcript. That transcript showed the
  Phase 6 design wasn't agreed in that session. It came from the plan,
  which was designed in the 2026-10-14 `/grill-me` session (already
  logged). The build session only said "Do Phase 6."
- **Sideways:** Nothing broke. The manual steps were written but not run
  by the agent. The manual check itself is still the user's to do.

## 2026-10-19 — Build Phase 6 of the account security center (sign-in attempt history)

*Logged afterwards, on 2026-10-20, from the saved session transcript.*

### Prompts
1. @prd/account-security-center.md @plans/account-security-center.md Do Phase 6.
2. okay how do i puase this sesion
3. how can i vrify the changes weve agreed on manually

### Summary
- **Outcome:** Built Phase 6 of `plans/account-security-center.md`:
  - New `SignInAttempt` model in `accounts/models.py`: username (lowercased
    on save), `created_at`, `succeeded`, and `kind` (sign-in or password
    reset). It's keyed by the username as typed, not a foreign key, so
    attempts on usernames that don't exist are saved too. No IP address
    is kept. Its queryset has `record()`, `for_user()`, and `stale()`
    (older than `RETENTION`, 90 days). It has a `description` property
    that gives "Signed in", "Failed sign-in", or "Password reset".
  - Migration `accounts/migrations/0005_signinattempt.py`.
  - `SignInForm.clean()` records a success or failure whenever both a
    username and a password are given. If either box is empty, nothing
    is recorded.
  - `PasswordResetSetView.form_valid` records a "password reset" attempt.
    `AccountView` passes the 5 newest attempts to the page.
  - A "Recent activity" card on `templates/accounts/account.html`: a
    green or red dot, the label, and the time, or "No sign-in activity
    yet."
  - New command `accounts/management/commands/prune_signin_attempts.py`.
  - 10 new tests in `accounts/test_security.py`. The full suite passed
    (376), and after a final tidy-up in `views.py` the accounts tests
    passed (118). `ruff check` and `ruff format` were clean. Phase 6
    boxes were ticked in the plan. Nothing committed.
- **Deviations:** One addition the plan didn't list: `seed` now also
  deletes the demo users' sign-in attempts. Because attempts are matched
  by username, a reseeded `customer` would otherwise see the old
  account's activity. Follow-up questions: how to pause the session
  (answered: `/exit` or Ctrl+C twice, then `claude --continue` or
  `claude --resume` to come back), and how to verify the changes
  manually (answered with a browser checklist).
- **Sideways:** Remembering that `ruff format` had changed an unrelated
  line in `views.py` before, the agent checked its diff first and only
  formatted the new files. The session ended before the manual check,
  and the work was left uncommitted. As before, `uv run` printed the
  harmless `VIRTUAL_ENV` mismatch warning.

## 2026-10-18 — Check Phase 4 and build Phase 5 of the account security center (forgotten password reset)

### Prompts
1. @prd/account-security-center.md @plans/account-security-center.md i want you to do phase five but before that can you tell me if all the acceptance criteria for phase 4 has been met?
2. thank you cna you check off the acceptance criterea that we agreed on in both phase 4 and 5 in the plan?
3. acceptance criterea for phase 4 and 5 hav not been checked off
4. okay i have manually verified phase 5 can you update prompts.md

### Summary
- **Outcome:** First confirmed Phase 4: each of its five criteria is in
  the code and tested, and the suite was green (355 passed) before any
  Phase 5 work. Then built Phase 5 of `plans/account-security-center.md`:
  - `PASSWORD_RESET_TIMEOUT = 60 * 60` (one hour) in `config/settings.py`.
  - New `PasswordResetRequestForm` (Django's `PasswordResetForm`) in
    `accounts/forms.py`. Its `get_users` keeps Django's rule (active, usable
    password) and also drops users whose email isn't verified. Also new:
    `ResetPasswordForm` (Django's `SetPasswordForm`). Both are styled with
    DaisyUI's `input w-full`.
  - Three thin views in `accounts/views.py`, built on Django's reset views:
    `PasswordResetRequestView`, `PasswordResetSentView`, and
    `PasswordResetSetView`. The last one sends the existing
    `send_password_changed_notice()`, flashes a message, and redirects to
    sign-in with no automatic sign-in. Routes under `/accounts/password/reset/`
    are `accounts:password_reset`, `accounts:password_reset_done`, and
    `accounts:password_reset_confirm`.
  - New templates: `password_reset.html`, `password_reset_done.html` (the
    same message for every email), and `password_reset_confirm.html` (new
    password form, or a "this reset link doesn't work" page with a
    "Send a new link" button). Also the plain-text
    `emails/password_reset.txt` and `emails/password_reset_subject.txt`.
    The sign-in page got a "Forgot password?" link.
  - 11 new tests in `accounts/test_security.py`: the sign-in link, the
    one-hour setting, mail for a verified email (mixed case too), no mail for
    an unverified, unknown, or inactive one, an identical response for every
    email, a reset that lands on sign-in without signing in, the notice
    email, a reused link, and an expired link (the token generator's clock is
    monkeypatched 61 minutes ahead). Phase 5's seven criteria are ticked off
    in the plan.

  Suite at 366 passed, and `ruff check` and `ruff format` are clean. The
  user checked the reset flow by hand in the browser. Nothing committed.
- **Deviations:** As in earlier phases, following the saved preference, I
  explained each edit before making it and each went through the approval
  prompt. "do phase five" was taken as the go-ahead for that mode. Two
  departures from the PRD, both flagged to the user. First, the PRD lists
  Django's four reset views, but the plan's criterion says a reset leads to
  the sign-in page, so the confirm view redirects there with a flash message
  and the "complete" view isn't used. Second, the reset email has a second
  template for its subject line, because Django's reset view reads the
  subject from a template. Follow-up question: the user asked me to check
  off the Phase 4 and 5 criteria. They were already checked: Phase 4 in the
  Phase 4 commit, Phase 5 at the end of this build.
- **Sideways:** The user then reported that the boxes still looked
  unchecked. I confirmed the file on disk was ticked (`sed` plus
  `git status`), and suggested the editor tab was out of date (unsaved
  buffer, reverted with **File: Revert File**, a different copy, or a stale
  Markdown preview). The user also got `git diff` to check it. The user
  didn't come back to it, so the cause wasn't confirmed. Pylance flagged
  `import environs` as unresolved after the settings edit. That's the
  editor pointing at a different virtual environment, not a code problem.
  As before, `uv run` printed the harmless `VIRTUAL_ENV` mismatch warning.
  The PRD's "a reset clears the sign-in lockout" isn't done yet. It
  arrives with the attempt history and lockout in Phases 6–7.

## 2026-10-18 — Build Phase 4 of the account security center (change password)

### Prompts
1. @prd/account-security-center.md @plans/account-security-center.md Do Phase 4.
2. okay but i dont need that link to perform the behavior that was implemented in this session? i can just run the server and manually test it in the browser?
3. okay how would i open an ingocnito browser
4. okay i manualy verified the behavior in the browser,do i run  git restore db.sqlite3 after stopping the development server and then my changes are ready for commit?
5. okay perfect yet can you update the prompts.md file with the decisions made in this session

### Summary
- **Outcome:** Built Phase 4 of `plans/account-security-center.md`:
  - New `User.send_password_changed_notice()` in `accounts/models.py`. It
    mails `templates/accounts/emails/password_changed.txt` only when the
    email exists and is verified. It is a model method so Phase 5's
    password reset can reuse it.
  - New `ChangePasswordForm`: Django's `PasswordChangeForm` (current
    password, new password twice, `AUTH_PASSWORD_VALIDATORS`) with the
    DaisyUI `input w-full` class, the same way `SignInForm` is styled.
  - New `ChangePasswordView`, built on Django's `PasswordChangeView`, at
    `/accounts/password/change/` (`accounts:change_password`). The
    built-in view already requires sign-in and calls
    `update_session_auth_hash`, so this device stays signed in. Other
    sessions end because Django's session fingerprint comes from the
    password hash. No `session_salt` was needed (that's Phase 8). The
    override only adds the notice and the flash message, then returns to
    My account.
  - New `templates/accounts/change_password.html`, and a "Password" card
    with a Change password link in My account's Sign-in & security
    section.
  - 10 new tests in `accounts/test_security.py`: sign-in required, the
    My account link, a wrong current password, a weak password,
    mismatched new passwords, the redirect and message, two `Client`s
    showing one device stays and the other is signed out, and the email
    for verified, unverified, and missing addresses. Phase 4's five
    criteria are ticked off in the plan.

  Suite at 355 passed, and `ruff check` and `ruff format` are clean. The
  user checked the behavior by hand in the browser (a normal window plus
  a private window as the second device). Nothing committed.
- **Deviations:** As in Phase 3, following the saved preference, I
  explained each edit before making it and each went through the approval
  prompt. "Do Phase 4" was taken as the go-ahead for that mode. Follow-up
  questions: whether the reset link mentioned in the notice email is
  needed to test this phase (answered: no, it's only text in the email;
  the link arrives in Phase 5), with step-by-step browser testing using
  the seeded `customer` account and a private window as the "other
  device"; how to open a private window (answered: `Ctrl + Shift + N` in
  Chrome/Edge, `Ctrl + Shift + P` in Firefox); and whether to stop the
  server, run `git restore db.sqlite3`, then commit (answered: yes, check
  `git status` first). The offer to write this log was taken.
- **Sideways:** `ruff format` rejoined two new test signatures onto one
  line each. It was applied after the suite had passed, with no change in
  behavior. My end-of-build summary said 11 new tests; there are 10, and
  this entry corrects it. Browser testing changes the tracked
  `db.sqlite3` (the customer's password), so the user was told to restore
  it before committing. The notice email tells customers to reset from
  the sign-in page, but the "Forgot password?" link isn't built until
  Phase 5. As before, `uv run` printed the harmless `VIRTUAL_ENV`
  mismatch warning.

## 2026-10-18 — Build Phase 3 of the account security center (add or change email)

### Prompts
1. @prd/account-security-center.md @plans/account-security-center.md Do Phase 3.
2. can you give me a step by step of how to verify this in the browser after runninh the migrate command
3. okay if i run the seed command it wont change any committed changes to my database right?
4. if i manually changed the email back would i be able to commit my changes from there?
5. can you add the prompts.md entry for this phase we just implemented

### Summary
- **Outcome:** Built Phase 3 of `plans/account-security-center.md`:
  - `accounts.User` gained `pending_email` (nullable, not unique, saved
    lowercase; migration `accounts/migrations/0004_user_pending_email.py`)
    and an `email_to_confirm` property: the pending address if there is
    one, else an unverified current email. Tokens, the verification email,
    and Resend all use it, so a link stops working once its address is
    confirmed or replaced.
  - `verify_email_token` now moves a pending address into `email`, marks
    it verified, and calls the new `send_email_changed_notice(old_email)`
    when there was an old address. It refuses a pending address that
    another account took in the meantime.
  - New `ChangeEmailForm` (new email plus current password; rejects a
    wrong password, the current email, and emails used by another account,
    ignoring capitalization). Its `save()` only sets `pending_email`.
  - New `ChangeEmailView` (`FormView`, sign-in required) at
    `/accounts/email/change/` (`accounts:change_email`), and
    `ResendVerificationView` now also resends for pending emails.
  - New templates: `templates/accounts/change_email.html` (titled "Add
    email" when there's none) and `templates/accounts/emails/email_changed.txt`.
    `verify_email.txt` names the address being confirmed. My account shows
    "Pending change to …", the add-email reminder for accounts with no
    email, and a Change/Add email link.
  - 14 new tests in `accounts/test_security.py`. Phase 3's eight criteria
    are ticked off in the plan.

  Suite at 345 passed, and `ruff check` and `ruff format` are clean.
  `migrate` was left for the user to run. Nothing committed.
- **Deviations:** Following the saved preference, I explained each edit
  before making it, and each went through the approval prompt. I didn't
  ask at the start which mode to use, as the memory note suggests; "Do
  Phase 3" was taken as the go-ahead for that mode. Three choices the plan
  left open were reported, and the user hasn't answered them yet: two
  accounts may hold the same pending address (first to confirm wins); a
  pending change replaces an unverified email's link; and the notice goes
  to the old address even if it was never verified. Follow-up questions:
  how to test in the browser (answered with a 10-step walkthrough using
  the seeded `customer` account and links copied from the terminal);
  whether `seed` changes committed files (answered: no, only the local
  `db.sqlite3` and `media/products/`, recoverable with
  `git restore db.sqlite3 media/` and a fresh `migrate`); and whether
  changing the email back by hand is enough to commit (answered: yes, but
  admin can't reset the verified or pending fields and testing leaves
  other traces, so `git restore db.sqlite3` plus `migrate` was
  recommended).
- **Sideways:**
  - Pylance flagged `FormView` and `ChangeEmailForm` as undefined after
    the first `views.py` edit; the imports arrived in the very next edit.
  - `ruff format` wanted one long line in `accounts/forms.py` wrapped. It
    was fixed after the test run, and the suite wasn't run again because
    the change was formatting only.
  - My end-of-build summary named the notice template
    `emails/change_email.txt`; the real file is `emails/email_changed.txt`.
  - The browser walkthrough hasn't been confirmed by the user yet. As
    before, `uv run` printed the harmless `VIRTUAL_ENV` mismatch warning.

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

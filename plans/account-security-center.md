# Plan: Account Security Center

> Source PRD: `prd/account-security-center.md`

## Architectural decisions

Durable decisions that apply across all phases:

- **Owning app**: `accounts`. The only change outside it is the checkout
  pre-fill in `orders` (Phase 10) and the `seed` command in `products`
  (Phase 1).
- **URLs**: every new view sits in the `accounts` namespace under
  `/accounts/`. Each security action is its own small form page that returns
  to My account (`accounts:account`) with a flash message, following the
  address book's pattern.
- **Models**:
  - `accounts.User` gains: `email` overridden to unique and nullable, stored
    lowercase; `email_verified` (bool, default false); `pending_email`
    (nullable); `session_salt`. Methods: `get_session_auth_hash` (mixes in
    `session_salt`), `has_open_orders()`, `deactivate()`.
  - New `accounts.SignInAttempt`: username as typed (lowercase), timestamp,
    succeeded flag, `kind` (sign-in or password reset). It is not a FK to
    `User`, and stores no IP address. The lockout rule lives on its
    manager/queryset.
  - `Order.user` stays `CASCADE`. Deleted accounts are deactivated, never
    removed.
- **Auth**: every security view requires sign-in except signup, the
  password-reset flow, and email verification. Django's built-in auth views
  and forms are used wherever one exists, styled with DaisyUI.
- **Email**: plain text, one template per email in an `emails` folder with
  the other accounts templates. Settings read from environs, defaulting to
  the console backend. `DEFAULT_FROM_EMAIL` is a store-branded no-reply
  address.
- **Tokens**: built with Django's own signing/token tools, with no new
  dependency. Verification links last 3 days (their own setting), and reset
  links last 1 hour (`PASSWORD_RESET_TIMEOUT`).
- **Architecture**: no new service module. CLAUDE.md's two deep modules stay
  two.

---

## Phase 1: Email at signup, shown on My account

**User stories**: 1, 3, 4, 5, 8, 9 (verified / unverified only), 42

### What to build

New customers must give an email when they sign up. Emails are unique
regardless of capitalization. Existing accounts without an email keep
working. My account gets its first "Sign-in & security" section, above the
address book, showing the email and whether it is verified. No email is
sent yet. Seeded users have verified emails.

### Acceptance criteria

- [x] `email` is unique and nullable, and a data migration turns existing
      blank emails into `null`
- [x] Emails are stored lowercase (model save and forms)
- [x] `email_verified` field exists, defaulting to false
- [x] Signup requires an email and rejects one already in use, ignoring
      capitalization ("Casey@Example.com" vs "casey@example.com")
- [x] My account shows a "Sign-in & security" section with the email and a
      verified / unverified status
- [x] Unverified customers can still shop and check out
- [x] Seeded demo and background users have `email_verified = True`
- [x] Tests cover uniqueness, lowercasing, signup validation, and the
      section's display

---

## Phase 2: Email delivery and the verification link

**User stories**: 2, 10, 26, 27

### What to build

Email settings are wired up, and signup sends a verification link. Clicking
the link marks the email verified. Links last 3 days and stop working once
used. A "Resend verification email" button on My account sends a fresh
link.

### Acceptance criteria

- [x] `EMAIL_BACKEND`, host, port, user, password, and TLS are read from the
      environment, defaulting to the console backend, and the new keys are
      documented in the example env file
- [x] `DEFAULT_FROM_EMAIL` and the 3-day verification setting exist
- [x] Signup sends a plain-text verify-email message, then still redirects to
      sign-in
- [x] The verify view accepts a signed, time-limited token tied to the
      address being confirmed, and marks it verified
- [x] Used, expired, or tampered links show a clear error with a way to
      resend
- [x] The Resend button appears only when the email is unverified
- [x] Tests use Django's in-memory outbox to check the mail and follow the
      link

---

## Phase 3: Add or change email

**User stories**: 6, 7, 11, 12, 13, 14

### What to build

Customers can change their email, or add one if they have none, by
entering their current password. The new address waits in `pending_email`
until its link is clicked, so the old verified address stays in effect
until then. Once the change is confirmed, the old address gets an
"email changed" notice. Accounts without an email see a reminder to add
one.

### Acceptance criteria

- [x] `pending_email` field exists
- [x] The change-email form requires the current password, and rejects
      emails used by another account or matching the current one
- [x] Submitting saves `pending_email` and sends the link to the new address
- [x] Status shows "pending change to …" and Resend also works for pending
      emails
- [x] Confirming moves `pending_email` into `email`, marks it verified, and
      sends the notice to the old address (if there was one)
- [x] The old link stops working once its address is confirmed or replaced
- [x] Accounts with no email see the add-email reminder
- [x] Tests cover the wrong password, duplicates, the confirm swap, and the
      notice

---

## Phase 4: Change password

**User stories**: 15, 16, 17, 18, 19

### What to build

A change-password page built on Django's `PasswordChangeView`, styled like
the other forms. The current device stays signed in, other sessions end,
and a "password changed" notice goes to the verified email.

### Acceptance criteria

- [x] The form takes the current password and the new one twice, checked
      against `AUTH_PASSWORD_VALIDATORS`
- [x] The current session stays signed in, and another session is signed
      out
- [x] A plain-text "password changed" email is sent to a verified email (and
      not when the email is unverified or missing)
- [x] It returns to My account with a flash message
- [x] Tests cover the wrong current password, a weak password, session
      behavior, and the email

---

## Phase 5: Forgotten password reset

**User stories**: 20, 21, 22, 23, 24, 25

### What to build

A "Forgot password?" link on sign-in leads to Django's four reset views.
The request page always shows the same message. Mail goes only to active
users with a verified email. Links last one hour and work once. After the
reset, the customer is sent to sign-in and gets the "password changed"
notice.

### Acceptance criteria

- [x] The sign-in page links to the reset request page
- [x] The request page shows an identical response for known, unknown, and
      unverified emails
- [x] A customized reset form sends mail only to active users with a
      verified email
- [x] `PASSWORD_RESET_TIMEOUT` is one hour, and a used link no longer works
- [x] A completed reset leads to the sign-in page, with no automatic sign-in
- [x] The "password changed" notice is sent after a reset
- [x] Tests cover each recipient case, expiry, reuse, and the notice

---

## Phase 6: Sign-in attempt history

**User stories**: 33, 35

### What to build

Every sign-in attempt, successful or failed, is recorded, including for
usernames that don't exist. A completed password reset is recorded as kind
"password reset". My account lists the last 5 attempts with their times,
labeling resets "Password reset". A management command deletes attempts
older than 90 days.

### Acceptance criteria

- [x] `SignInAttempt` model and migration exist (username lowercase,
      timestamp, succeeded, kind)
- [x] Successful and failed sign-ins are both recorded, including for
      nonexistent usernames
- [x] A completed reset records a "password reset" attempt
- [x] My account shows the 5 most recent attempts for the signed-in user,
      newest first
- [x] `prune_signin_attempts` deletes attempts older than 90 days and keeps
      newer ones
- [x] Tests cover recording, the activity list, and the prune command

---

## Phase 7: Sign-in lockout

**User stories**: 28, 29, 30, 31, 32

### What to build

After 5 failed sign-ins for a username within 15 minutes, sign-in for that
username is refused, even with the correct password, until the window
passes. Only failures after the latest successful sign-in or password reset
count. The rule lives on the attempt manager/queryset and is checked in
`SignInForm`. The message is the same whether or not the username exists,
and the rule applies to staff and admins too.

### Acceptance criteria

- [ ] The 5th failure within 15 minutes locks the username, and a correct
      password is still refused
- [ ] The message reads "too many failed attempts — try again in a few
      minutes, or reset your password."
- [ ] Unknown usernames lock out identically
- [ ] Failures older than 15 minutes don't count
- [ ] A successful sign-in or password reset clears the count
- [ ] Staff and superuser accounts are protected the same way
- [ ] Tests cover each rule above

---

## Phase 8: Sign out of all other devices

**User stories**: 34

### What to build

Adds `session_salt` to the user and mixes it into `get_session_auth_hash`.
A "Sign out of all other devices" page asks for the current password,
changes the salt, and keeps the current session with
`update_session_auth_hash`. Shipping this signs everyone out once, which is
expected.

### Acceptance criteria

- [ ] `session_salt` field and migration exist, and `get_session_auth_hash`
      includes it
- [ ] The action is a POST that requires the current password, and a wrong
      password changes nothing
- [ ] The current session stays signed in, and another session is signed
      out
- [ ] It returns to My account with a flash message
- [ ] Tests use two clients to show one stays and one is signed out

---

## Phase 9: Delete account

**User stories**: 37, 38, 39, 40, 41

### What to build

A delete-account confirmation page that requires the current password and
an explicit confirmation. Accounts with Placed or Shipped orders are
refused, and those order numbers are listed. Staff and superusers can't use
it. On success, `deactivate()` wipes the personal data but keeps the row,
the user is signed out, and a farewell message is shown. Past orders stay
attached.

### Acceptance criteria

- [ ] `has_open_orders()` is true only for Placed or Shipped orders
- [ ] `deactivate()` sets `is_active=False`; clears the email, pending
      email, and verification; renames the username to `deleted-user-<pk>`;
      makes the password unusable; deletes saved addresses; and changes
      `session_salt`
- [ ] A wrong password or a missing confirmation refuses the deletion
- [ ] Open orders block deletion and are listed by number
- [ ] Staff and superusers are refused
- [ ] On success the user is signed out with a farewell message, the orders
      still exist, and the dashboard totals are unchanged
- [ ] Tests cover each case above

---

## Phase 10: Checkout email pre-fill

**User stories**: 36

### What to build

The checkout email field starts filled with the account's email (verified
or not), alongside the existing saved-address pre-fill. The customer can
still edit it, and the order copies whatever is submitted.

### Acceptance criteria

- [ ] Checkout's initial data includes the account email when one exists
- [ ] An account without an email gets an empty field
- [ ] A submitted, edited email is what the order stores
- [ ] Tests cover all three

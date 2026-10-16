# PRD — Account Security Center

## Problem Statement

ThoughtTronix customers have very little control over the security of their
accounts. Signing up asks only for a username and password, so the store has
no way to reach a customer, and a customer who forgets their password is
locked out for good, with no way to recover the account. Once signed in,
customers can't change their password, can't see whether anyone has been
trying to get into their account, can't sign out a lost or shared device,
and can't close their account. Separately, the sign-in page lets anyone guess
passwords forever, which undercuts every other protection.

## Solution

A "Sign-in & security" section on the My account page, where customers
manage everything that protects their account:

- Every new account gives an email address at signup. The store confirms
  that the customer owns it by sending a verification link.
- Customers can change their email. The change requires their current
  password and only takes effect once the new address is confirmed, and the
  old address is told about it.
- Customers can change their password. Other devices get signed out, and a
  notice email is sent.
- Customers who forget their password can reset it through a link sent to
  their verified email.
- Repeated wrong passwords temporarily pause sign-in for that username.
- Customers can see their recent sign-in activity, sign out every other
  device, and delete their account.
- Checkout pre-fills the customer's email to save typing.

Emails print to the terminal by default and can be switched to real
delivery through environment settings.

## User Stories

### Signing up and email

1. As a new customer, I want to give my email address when I create an
   account, so that I can recover the account if I forget my password.
2. As a new customer, I want to receive a link that confirms my email
   address, so that the store knows the address really belongs to me.
3. As a new customer, I want to be told when an email address is already in
   use, so that I don't accidentally create a second account or claim
   someone else's address.
4. As a customer, I want email addresses that differ only in capitalization
   to be treated as the same address, so that "Casey@Example.com" and
   "casey@example.com" can't become two accounts.
5. As a customer whose email is unverified, I want to keep shopping and
   checking out normally, so that verification never gets in the way of a
   purchase.
6. As a customer whose account was created before emails were required, I
   want a clear reminder on My account to add an email, so that I understand
   I can't recover my account without one.
7. As a customer without an email on file, I want to add one from My account,
   so that I can make my account recoverable.

### The security section

8. As a signed-in customer, I want a "Sign-in & security" section on My
   account, so that every security setting is in one place.
9. As a customer, I want to see my email address and whether it is verified,
   unverified, or has a change pending, so that I know whether I can recover
   my account.
10. As a customer with an unverified or pending email, I want a "Resend
    verification email" button, so that I can get a new link if the old one
    expired or got lost.

### Changing email

11. As a customer, I want to change my email address, so that my account
    follows me when I switch addresses.
12. As a customer, I want changing my email to require my current password,
    so that someone using my unattended, signed-in computer can't take over
    my account.
13. As a customer, I want my old, verified email to stay in effect until I
    click the confirmation link sent to the new one, so that a typo in the
    new address can't lock me out.
14. As a customer, I want to receive a notice at my old address when my email
    is changed, so that I find out if someone else changed it.

### Changing password

15. As a customer, I want to change my password by entering my current
    password and the new one twice, so that only I can change it and I don't
    mistype it.
16. As a customer, I want my new password checked against the store's
    password rules, so that I don't choose something easy to guess.
17. As a customer, I want to stay signed in on the device where I changed my
    password, so that I'm not interrupted.
18. As a customer, I want every other device to be signed out when my
    password changes, so that anyone using my old password loses access.
19. As a customer, I want a "your password was changed" email, so that I find
    out if someone else changed it and can reset it.

### Forgotten password

20. As a customer who forgot my password, I want to request a reset link by
    entering my email, so that I can get back into my account.
21. As a customer, I want the reset page to show the same message whether or
    not the email matches an account, so that strangers can't use it to find
    out who shops at ThoughtTronix.
22. As a customer, I want reset links sent only to verified addresses, so
    that a typo or a falsely claimed address can't receive the key to my
    account.
23. As a customer, I want the reset link to expire after one hour and stop
    working once used, so that an old link sitting in my inbox can't be used
    against me.
24. As a customer who just reset my password, I want to be sent to the
    sign-in page to sign in with my new password, so that I confirm it works.
25. As a customer, I want a "your password was changed" email after a reset
    too, so that I'm told about every password change, however it happened.

### Verification links

26. As a customer, I want verification links to stay valid for three days,
    so that I can confirm my email even if I check it later.
27. As a customer, I want a verification link to stop working once it has
    been used, so that it can't be replayed.

### Limiting sign-in attempts

28. As a customer, I want sign-in for my username paused for 15 minutes after
    5 wrong passwords within 15 minutes, so that nobody can keep guessing my
    password.
29. As a customer who is locked out, I want a message telling me to wait a
    few minutes or reset my password, so that I know how to get back in.
30. As a customer who is locked out, I want a successful password reset to
    clear the pause right away, so that I'm not stuck waiting.
31. As a customer, I want the lockout to behave the same for usernames that
    don't exist, so that the lockout can't be used to find out which
    usernames are real.
32. As a staff member or admin, I want the same sign-in protection, so that
    back-office accounts can't be guessed either.

### Recent activity and sessions

33. As a customer, I want to see my last 5 sign-in attempts, both successful
    and failed, with their times, so that I can spot activity I don't
    recognize.
34. As a customer, I want a "Sign out of all other devices" button that asks
    for my password, so that I can end sessions on a lost phone or a shared
    computer while staying signed in here.
35. As the store operator, I want sign-in attempts older than 90 days
    deleted by a management command, so that the attempt history doesn't
    grow forever.

### Checkout

36. As a customer, I want checkout's email field pre-filled with my account
    email, so that I don't have to type it every time. I can still edit it
    for an order.

### Deleting an account

37. As a customer, I want to delete my account, so that I can leave the store
    and stop it from keeping my account details.
38. As a customer, I want deletion to require my current password and an
    explicit confirmation, so that it can't happen by accident or be done by
    someone else at my computer.
39. As a customer with orders still Placed or Shipped, I want to be told I
    can delete my account once those orders are delivered or cancelled, and
    see which orders they are, so that I don't lose track of a purchase
    that's still on its way.
40. As the store operator, I want deleted customers' past orders kept, so
    that revenue, the dashboard, and the back office stay accurate.
41. As the store operator, I want staff and admin accounts unable to delete
    themselves through My account, so that the back office can't be locked
    out by accident.

### Demo world

42. As a developer or grader, I want the seeded demo users to have verified
    emails, so that password reset can be tried on them right away.

## Implementation Decisions

### User model (accounts)

- The `email` field is overridden on `accounts.User` to be unique and
  nullable. A data migration turns existing blank emails into `null`, so
  that multiple accounts without an email don't break the unique rule.
- Emails are stored lowercase (normalized on save and in forms), so that
  uniqueness ignores capitalization.
- New fields:
  - `email_verified` (boolean, default false)
  - `pending_email` (nullable): an address waiting for confirmation
  - `session_salt`: a value that is changed to sign out all other sessions
- `get_session_auth_hash` is overridden to mix `session_salt` into Django's
  password-based session fingerprint. Changing the salt invalidates every
  other session, and the current one is kept with
  `update_session_auth_hash`, the same way password change already works.
  This changes the fingerprint for everyone, so every user is signed out
  once when the change is deployed.
- `has_open_orders()`: true when the user has any order that is Placed or
  Shipped.
- `deactivate()` deletes the account's personal data without deleting the
  row. It sets `is_active` to false, clears the email, pending email, and
  verification, changes the username to a placeholder like
  `deleted-user-<pk>`, makes the password unusable, deletes saved addresses,
  and changes `session_salt` so all sessions end. Orders stay attached to the
  deactivated user. `Order.user` keeps `CASCADE`, and no order code changes.

### Sign-in attempts (accounts)

- New `SignInAttempt` model: the username as typed (lowercase), a timestamp,
  whether it succeeded, and a `kind` (sign-in or password reset). It isn't a
  foreign key to `User`, so attempts on usernames that don't exist are still
  recorded. No IP address is stored.
- The lockout rule lives with the model (manager or queryset) and is checked
  in `SignInForm`'s validation. With 5 or more failed sign-ins for a username
  in the last 15 minutes, sign-in is refused, even with the correct password.
  Only failures after the most recent clearing event count. A clearing event
  is a successful sign-in or a password reset. The message says "too many failed attempts — try
  again in a few minutes, or reset your password." The message is the same
  whether or not the username exists.
- A successful password reset records an attempt of kind "password reset",
  which clears the pause for that user. Recent activity labels it "Password
  reset", so it never looks like a sign-in that didn't happen.
- Every attempt is recorded, successful or failed.
- New management command `prune_signin_attempts` deletes attempts older than
  90 days.
- Built by hand on purpose instead of with `django-axes`, so the code stays
  visible and follows the "forms own their validation" rule.

### Forms (accounts)

- `SignupForm` adds a required email field and rejects emails that are
  already in use, ignoring capitalization.
- New change-email form: the current password plus the new email. It rejects
  emails already used by another account or matching the current email.
- Password change and reset use Django's built-in forms, styled with DaisyUI
  the same way the existing forms are.
- New confirm-with-password forms for "sign out other devices" and "delete my
  account".

### Views and URLs (accounts namespace)

- My account gets a "Sign-in & security" section above the address book. It
  shows:
  - the email and its status (verified, unverified, or pending change to …)
  - the add-email reminder when there's no email
  - a resend-verification button
  - links to change email, change password, sign out other devices, and
    delete account
  - the recent-activity list of the last 5 attempts
- Each action is its own small form page that returns to My account with a
  flash message, following the pattern the address book already uses.
- Signup sends a verification email after creating the account. It still
  redirects to sign-in, with no automatic sign-in.
- Verify-email view: accepts a signed, time-limited token. On success it
  either marks the current email verified, or moves `pending_email` into
  `email` and marks it verified. Used or expired tokens show a clear error
  with a way to resend.
- The verification token is tied to the address being confirmed, so a link
  stops working once that address is confirmed or replaced. It is built with
  Django's own signing or token tools; no new dependency.
- Change-email view: saves `pending_email`, sends the verification link to
  the new address, and sends the "email changed" notice to the old address
  once the change is confirmed.
- Change-password view: Django's `PasswordChangeView`. It keeps the current
  session, other sessions end automatically, and the "password changed"
  notice is sent to the verified email.
- Password reset: Django's four built-in reset views (request, done,
  confirm, complete), with the "Forgot password?" link on the sign-in page.
  - The request page always shows the same generic message.
  - Mail goes only to active users with a verified email. A small customized
    reset form limits who receives mail.
  - After the reset, the customer goes to the sign-in page; there's no
    automatic sign-in.
  - The "password changed" notice is sent, and the lockout is cleared.
- Sign-out-other-devices view: POST with the current password. It changes
  `session_salt` and keeps the current session.
- Delete-account view: a confirmation page that needs the current password.
  - If the account has open orders, it's refused, and those order numbers are
    listed.
  - Staff and superusers can't use it.
  - On success, it calls `deactivate()`, signs the user out, and shows a
    farewell message.
- Every security view requires sign-in, except signup, the reset flow, and
  email verification.

### Orders

- The checkout view's initial data adds the account's email, whether
  verified or not, to the existing saved-address pre-fill. The order still
  copies whatever email is submitted.

### Email

- Settings read `EMAIL_BACKEND`, host, port, user, password, and TLS from the
  environment with environs. With no `.env`, the backend defaults to the
  console backend. The new keys are documented in the example env file.
- `DEFAULT_FROM_EMAIL` is set to a store-branded no-reply address.
- `PASSWORD_RESET_TIMEOUT` is one hour. A separate setting gives verification
  links three days.
- Every email is plain text, with one template per email: verify email,
  email-changed notice, password-changed notice, and password reset.
  Templates live with the other accounts templates in an emails folder.

### Seed

- Demo and background users are created with `email_verified` set to true.
  Their existing emails are already unique and lowercase.

### Architecture

- Account deletion and the lockout rule live on the model and manager, not
  in a new service module. CLAUDE.md's two deliberate deep modules stay two.
- Views stay thin and follow Django's built-in auth views wherever one
  exists.

## Out of Scope

- Signing in with an email address instead of a username.
- Two-factor authentication.
- Editing first and last name, or other profile fields.
- HTML or branded emails.
- Order confirmation or shipping emails.
- Blocking unverified customers from checkout or sign-in.
- Forcing customers without an email to add one before using the site.
- Back-office tools to view or unlock locked accounts, resend
  verification, or manage customers' security settings.
- Rate limiting by IP address, or recording IP addresses on sign-in attempts.
- Truly deleting user rows, or anonymizing the names and addresses already
  copied onto past orders.
- Automatically cancelling orders when an account is deleted.
- A third-party lockout package such as `django-axes`.
- A separate security page or tabbed My account layout.

## Further Notes

- Everyone gets signed out once when this ships, because of the session
  fingerprint change. That's expected and harmless.
- A customer who has forgotten their password *and* never verified their
  email cannot recover the account through the store. This was accepted in
  exchange for keeping the reset page from revealing who has an account.
- The per-username lockout can be triggered on purpose by someone else.
  Its effect is limited to 15 minutes, and a password reset clears it.
- Because emails go to the console by default, every email flow can be
  tested locally by copying the link from the terminal running the dev
  server, and in tests through Django's in-memory outbox.
- If the security section grows much larger later, it can move to its own
  page.

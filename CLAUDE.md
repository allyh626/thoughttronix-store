# CLAUDE.md — The ThoughtTronix Store

A server-rendered Django 6 storefront and back office. The PRD (`prd/core-platform.md`) and the plan (`plans/core-platform.md`) record how the core platform was designed and built.

## Commands

- `uv sync` — install dependencies (Python 3.13, managed by uv)
- `uv run python manage.py migrate` — apply migrations
- `uv run python manage.py seed` — reset the database to the demo world
  (destructive, idempotent)
- `uv run python manage.py tailwind runserver` — dev server + Tailwind watch
- `uv run python manage.py tailwind build` — compile production CSS
- `uv run pytest` — run the test suite
- `uv run ruff check .` and `uv run ruff format .` — lint and format

## Project layout

- `config/` — the project package (settings, root urls)
- `accounts/` — custom user model (`accounts.User`, `AbstractUser` + nullable
  `job_title`). Roles are Django's own vocabulary: customers are plain users,
  employees are `is_staff`, the admin is `is_superuser`. No role field, no Groups.
  Also owns `Address` (the customer address book, with default
  shipping/billing flags), the My account page, and `accounts/validators.py`
  (`US_STATES`, `zip_validator` — shared with checkout).
- `products/` — catalog (`Category`, `Product`, `Tag`), its back-office CRUD,
  and the `seed` command
- `orders/` — cart, checkout, orders, back-office order management, and
  discount codes (`Coupon`, the back-office Coupons tab). Orders copy a
  coupon's code and savings on; `Order.total` is what the customer paid.
- `dashboard/` — the staff analytics dashboard
- `PROMPTS.md` — the AI-usage log; append entries, never rewrite history
- `templates/` — project-level templates (`base.html`); app templates live in
  `templates/<app>/`
- `assets/` — static sources; `assets/css/source.css` is the Tailwind input,
  `assets/css/tailwind.css` is compiled output (gitignored, never edit)

## Architecture convention

Logic lives in models and managers; cross-model workflows get a service
module; views stay thin.

Exactly two deliberate deep modules, docstrings and type hints on every
public function: `orders/services.py` (`place_order` and `quote` — the
single source of coupon math) and `dashboard/queries.py` (the dashboard's
aggregations).

Idiomatic Django throughout: class-based views, model methods, custom
managers/querysets, forms own their validation. Settings read from `.env`
via environs with working defaults — the app must run with no `.env` present.

## Reference docs — read the one that matches your task

- `docs/CONVENTIONS.md` — before editing templates, styling, HTMX partials,
  views, or URLs
- `docs/TESTING.md` — before writing or changing tests
# KLB website

A complete website for the Kenya Literature Bureau: a public catalogue and
content site, plus a staff dashboard for editing every public page, book, news
item, tender, career, resource and global setting.

| Part | Technology | Location |
| --- | --- | --- |
| Public site and dashboard | React 18 + Vite 6 | `frontend/` |
| API, authentication, SEO files | Django 5 + Django REST Framework | `backend/` |
| Database | PostgreSQL 16 (or newer) | `DATABASE_URL` |
| Static and uploaded files | WhiteNoise + Django media | `backend/staticfiles/`, `backend/media/` |

The design keeps the official KLB artwork and the blue `#0875B9` palette with
red `#C92A36`, yellow `#F3E5AB` and green `#4F9B55` accents.

## What is included

- Public pages for home, about, services, digital, resources, careers, tenders,
  news, contact, privacy and terms. Every page is made of editable sections.
- A catalogue with 128 seeded titles, collection filters, search, sorting and
  paginated "show more" loading.
- Book, news, career, tender and resource detail views.
- Contact and newsletter forms with server-side validation, CSRF protection and
  throttling.
- A custom staff dashboard at `/admin` for pages, the catalogue, news, careers,
  tenders, resources, enquiries, subscribers, users and site settings.
- Three staff roles enforced by both the interface and the API:
  - **Super Administrator** has full access, including critical site settings,
    user management, activity records and restricted code-level content.
  - **Administrator** manages content, Editors and day-to-day settings, but
    cannot change critical or security configuration.
  - **Editor** works only within the content modules and actions granted to the
    account. Delete, publish and system modules are opt-in.
- A **Users and permissions** screen for creating accounts, assigning roles,
  resetting passwords, suspending access and granting per-module View, Create,
  Edit, Delete and Publish permissions.
- An immutable **activity log** recording who created, edited, published or
  deleted content, along with account and settings changes.
- Configurable **dropdown options** for news categories, catalogue categories,
  departments, employment types, locations and other classification fields,
  with an **Other** free-text fallback in the content forms.
- Database-driven `sitemap.xml` and `robots.txt`, per-page titles, descriptions,
  canonical links, Open Graph metadata and JSON-LD.
- A one-command content seed with verified KLB copy and book records.

## Quick start (Windows)

Requirements: Python 3.11 or newer, Node.js 20 or newer, PostgreSQL 16 or newer
and PowerShell.

1. Create the database and user once in PostgreSQL (see
   [docs/SETUP.md](docs/SETUP.md) step 3).
2. Copy the environment template and edit it:

   ```powershell
   cd "C:\Users\Admin IT\Documents\Default Project\klb-platform"
   Copy-Item backend\.env.example backend\.env
   notepad backend\.env
   ```

   Set `DATABASE_URL`, `DJANGO_SECRET_KEY`, `SEED_ADMIN_EMAIL` and
   `SEED_ADMIN_PASSWORD`.

3. Run the setup script:

   ```powershell
   .\scripts\setup-windows.ps1
   ```

Then start the two development servers in separate terminals:

```powershell
.\scripts\dev-backend.ps1
```

```powershell
.\scripts\dev-frontend.ps1
```

Open <http://localhost:5173>. The staff dashboard is at
<http://localhost:5173/admin>. The administrator account is the one you set in
`backend/.env` before running the seed.

For a manual setup, PostgreSQL commands for Windows/macOS/Linux and
troubleshooting, see [docs/SETUP.md](docs/SETUP.md). For a no-Docker walkthrough
with a frontend-to-backend test checklist, see
[docs/LOCAL-WITHOUT-DOCKER.md](docs/LOCAL-WITHOUT-DOCKER.md).

## Production preview (one server)

Build the React app, then let Django serve it:

```powershell
cd frontend
npm run build
cd ..\backend
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Open <http://127.0.0.1:8000>. Do not use the Django development server in
production; use Gunicorn behind nginx as described in
[docs/DEPLOYMENT-HOSTAFRICA.md](docs/DEPLOYMENT-HOSTAFRICA.md).

## Documentation

- [docs/SETUP.md](docs/SETUP.md) - local setup for Windows, macOS and Linux.
- [docs/LOCAL-WITHOUT-DOCKER.md](docs/LOCAL-WITHOUT-DOCKER.md) - local
  PostgreSQL setup, how the frontend and backend communicate, and configuration
  tests.
- [docs/CONTENT-GUIDE.md](docs/CONTENT-GUIDE.md) - how staff edit the site.
- [docs/DEPLOYMENT-HOSTAFRICA.md](docs/DEPLOYMENT-HOSTAFRICA.md) - production
  deployment on a HostAfrica VPS with Ubuntu, PostgreSQL, Gunicorn, nginx and
  HTTPS. Confirm the exact plan features with HostAfrica before ordering.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - how the pieces fit together.
- [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - common errors and fixes.

## Project layout

```text
klb-platform/
  backend/            Django project and REST API
    apps/             accounts, catalogue, content, enquiries
    config/           settings, URLs, sitemap and SPA serving
    seed/             verified page content (cms-seed.json, books.json)
    templates/        SPA shell served by Django
  frontend/           React single-page application
    public/assets/    official KLB artwork, covers, documents
    src/              public site, dashboard, styles and API client
  docs/               setup, content, architecture and deployment guides
  scripts/            Windows setup and development helpers
```

## Security notes

- Never commit `backend/.env`, production secrets or a production database dump.
- Set a long random `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, the real
  `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` in production.
- Serve the site over HTTPS and keep `DJANGO_SECURE_SSL=True` and
  `DJANGO_SECURE_COOKIES=True`.
- Uploaded images and PDFs are limited to 8 MB and to approved file extensions.
- Rich HTML is sanitised on the server before it is stored.
- Permissions are checked again on the API for every request. Hiding a menu item
  is never the only protection, so direct URLs and API calls are refused as well.
- The last active Super Administrator cannot be demoted, deactivated or deleted,
  and no account can change its own role or suspend itself.
- Change the seeded administrator password immediately after the first sign-in.

## Seeded content

`python manage.py seed_content` reads `backend/seed/cms-seed.json` and
`backend/seed/books.json`. It creates missing records and leaves existing ones
alone; use `--reset` only when you intentionally want to replace pages, the
catalogue and site settings. The command never deletes administrator accounts.

The seed contains 12 pages, 128 book records, 21 news items, 1 vacancy, 9 tenders
and 19 resources. All copy, prices and contact details come from the supplied
KLB material; nothing is generated.

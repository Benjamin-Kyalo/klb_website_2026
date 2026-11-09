# Architecture

## Overview

```text
Browser
  |
  |  React single-page application (public site + /admin dashboard)
  v
Django + Django REST Framework
  |         |               |
  |         |               +--> PostgreSQL (content, users, enquiries)
  |         +------------------> backend/media (uploads)
  +----------------------------> frontend/dist (built SPA, served by Django)
```

In development, Vite runs on port 5173 and proxies API, media and SEO requests to
Django on port 8000. In production, nginx sends requests to Gunicorn and serves
`/static/` and `/media/` directly. Django serves `frontend/dist` for every
non-API route so the React router can take over.

## Main directories

```text
backend/
  apps/accounts/       custom user, roles, login/logout, password change, users API
  apps/catalogue/      books, filters, pagination, cover handling
  apps/content/        pages, sections, news, careers, tenders, resources,
                       settings, sitemap data, uploads and HTML sanitising
  apps/enquiries/      public contact form and newsletter subscribers
  config/              settings, URLs, SPA shell, sitemap, robots, health
  seed/                content and catalogue JSON used by seed_content
  templates/           SPA shell with default metadata
frontend/
  src/components/      public layout, header, footer, cards and section renderer
  src/pages/           public pages and detail views
  src/admin/           dashboard screens and reusable form components
  src/lib/             API client, formatting, SEO helpers
  src/styles/          public and dashboard CSS
  public/assets/       official artwork, book covers and documents
```

## Public request flow

1. The browser requests a route such as `/about/`.
2. Django's catch-all returns the SPA shell unless the request targets `api/`,
   `static/`, `media/`, `sitemap.xml`, `robots.txt` or `health/`.
3. React mounts and loads global data from `/api/site/`.
4. `PageView` loads `/api/pages/about/`, then renders each section:
   - rich HTML sections through `dangerouslySetInnerHTML` after server-side
     sanitising;
   - automatic sections through React components that fetch live data.
5. `Seo` updates the title, description, canonical, robots and social tags.

The catalogue, book detail, news detail, 404 and dashboard routes work the same
way with their own API calls.

## API shape

| Area | Endpoint |
| --- | --- |
| Global settings, navigation, page index | `GET /api/site/` |
| Page by slug | `GET /api/pages/<slug>/` |
| Books | `GET /api/books/` with `q`, `collection`, `level`, `subject`, `language`, `featured`, `new`, `ordering`, `page`, `page_size` |
| Book detail | `GET /api/books/<slug>/` |
| Catalogue filters | `GET /api/catalogue/filters/` |
| News | `GET /api/news/` and `GET /api/news/<slug>/` |
| Careers, tenders, resources | `GET /api/careers/`, `/api/tenders/`, `/api/resources/` |
| Contact form | `POST /api/enquiries/` |
| Newsletter | `POST /api/newsletter/` |
| CSRF token | `GET /api/auth/csrf/` |
| Sign in, sign out, current user | `POST /api/auth/login/`, `POST /api/auth/logout/`, `GET /api/auth/me/` |
| Password change | `POST /api/auth/password/` |
| Dashboard CRUD | `/api/admin/pages/`, `/api/admin/books/`, `/api/admin/news/`, `/api/admin/careers/`, `/api/admin/tenders/`, `/api/admin/resources/`, `/api/admin/enquiries/`, `/api/admin/subscribers/`, `/api/admin/users/` |
| Dashboard stats and settings | `GET /api/admin/stats/`, `GET/PATCH /api/admin/settings/` |
| Upload | `POST /api/admin/upload/` as multipart form data with a `file` field |
| Health | `GET /health/` |

Public reads are allowed anonymously. Dashboard endpoints require a signed-in
editor; settings changes and user administration require an administrator.

## Authentication and CSRF

- Session cookies, not JWT. The session cookie is `klb_session` and is HttpOnly.
- The CSRF cookie is readable by JavaScript so the React client can send the
  `X-CSRFToken` header. CSRF remains enforced on every unsafe request.
- Sign-in is rate-limited by DRF's anonymous throttle. The contact form has its
  own stricter scope.
- Editors can read site settings but cannot change them.
- You cannot delete the account currently signed in.

## Content model

- `Page` has many `Section` rows ordered by `sort_order`.
- `Section.kind` selects either rich HTML or an automatic list.
- `News`, `Career`, `Tender` and `Resource` are independent lists.
- `SiteSetting` is a singleton row (`pk=1`) holding contact details, social links,
  SEO defaults, navigation and footer columns.
- `Book` belongs to the catalogue app and supports a cover path or an upload.

Rich text is cleaned by `apps/content/sanitize.py` using Bleach on every save.
The allow-list covers normal content tags, tables, forms with the dashboard's
public form hooks, ARIA attributes and safe inline styles.

## Search engine behaviour

- Django builds `sitemap.xml` from published pages, published news, books and the
  main list pages.
- `robots.txt` disallows `/admin/` and `/api/` and points at the sitemap.
- The SPA shell contains default metadata for crawlers that do not execute
  JavaScript.
- React updates metadata per route after load.
- Missing custom pages render the React 404 page with `noindex, follow`.

### Known limitation: soft 404s

Django returns HTTP 200 for the SPA shell even when the route does not exist,
because the server cannot know which React routes are valid without duplicating
the route table. The browser correctly shows the 404 page and sets
`noindex, follow`, but an HTTP client will see 200. Search engines generally
execute JavaScript, but this is not equivalent to server-side rendering.

The project deliberately does not implement React SSR. If strict HTTP status
codes or full first-paint SEO become requirements, options are:

1. Add a small Django view that checks the slug against published pages and book
   slugs and returns a 404 status while still serving the shell.
2. Introduce a Node SSR layer, which adds a second runtime and more deployment
   complexity.

## Contact and newsletter behaviour

Both forms are intercepted by React and posted as JSON to DRF.

- Contact enquiries are stored in the database and shown in the dashboard. The
  project does **not** include an outbound email provider, so staff must monitor
  **Enquiries**. Adding email would mean configuring Django's email backend and
  calling it from `PublicEnquiryView`.
- Newsletter addresses are stored for export from the dashboard. The project
  does not send campaigns. Connect a mailing provider if bulk mail is required.
- Duplicate newsletter sign-ups return a successful "already on the list"
  response instead of an error.

These are operational facts to plan for, not hidden features.

## Static files, media and the SPA shell

- `frontend/dist` is built by Vite. Django reads it from `FRONTEND_DIST`.
- `backend/staticfiles` holds Django's collected static files, served by
  WhiteNoise and preferably by nginx in production.
- `backend/media` holds uploads. In development Django serves it; in production
  nginx serves it.
- The SPA catch-all excludes `api/`, `static/`, `media/` and the explicit SEO
  routes so missing files return a real 404.

## Design system

The public CSS is split into the supplied KLB styles and a React compatibility
layer. The dashboard uses `body.admin-body` scoping so its classes cannot collide
with public classes. Components reuse the established typography, spacing,
buttons, cards and blue `#0875B9` palette.

## Testing performed

The build was verified locally with:

- Django system checks and migrations.
- A content seed and API smoke tests.
- Public route, catalogue, search, contact and newsletter checks in a browser.
- Dashboard sign-in, page create/update/delete, role restrictions and uploads.
- Production bundle build and SPA asset loading with no browser console errors.

No automated test suite is included. If the project grows, start with Django
tests for permissions, form validation and seed idempotency, and Vitest or
Playwright for the catalogue and dashboard flows.

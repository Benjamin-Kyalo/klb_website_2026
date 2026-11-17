# KLB PLC Website - Functional Testing Report

**Project:** Kenya Literature Bureau PLC website (public site + admin dashboard)  
**Report date:** 17 November 2026  
**Working directory:** `C:\Users\Admin IT\Downloads\CS50\CS50_codes\klb_website_2026`  
**Stack:** React 18 + Vite 6 / Django 5 + DRF / PostgreSQL (local `klb_verify`, production Supabase)  
**Branding:** `#F3E5AB` yellow, Century Gothic, KLB identity preserved.

---

## 1. Verdict

The site and dashboard are functional and deployable. Every item marked **PASS** or **FIXED**
below was executed against a running application (Django + Vite + PostgreSQL, plus the
live Render deployment) - not inferred from reading code.

| Area | Result |
|---|---|
| Backend automated suite | **136 tests, OK** (0 failures, 0 errors) |
| Django system check | 0 issues |
| Migration drift | "No changes detected" |
| Frontend lint (esbuild parse) | 55 files, no syntax errors |
| Frontend unit tests | **11 / 11 pass** |
| Frontend production build | Success (~2.7 s), `dist/` generated |
| Public browser journeys | All routes, catalogue, forms, newsletter, 404, PDFs verified |
| Admin browser journeys | Every module's create / edit / delete exercised in the UI |
| Production (Render) | `4c3925e` pushed; post-push `/health/` 200, 128 books, 8 home sections, prior `updated_at` retained, theme + PDF still served |
| Remaining blockers | Real SMTP credentials, live UI backup restore (see section 11) |

Three defects were found *because* this round executed the app rather than reading it:

1. Production was serving stale content because the Render **Build Command** was not
   running `seed_content` at all (local and Render disagreed). The command is now part of
   the build; `--refresh` is create-only and cannot overwrite dashboard edits.
2. Seasonal themes had a working API but the public frontend never consumed it. Themes are
   now applied to `<body>` and removed when the campaign window closes.
3. `seed_content` itself destroyed dashboard content: `--refresh` deleted every section on
   seed pages, rewrote seed settings and news, and `--reset` truncated whole tables. All
   destructive calls are removed (section 10.1).

---

## 2. Test environment

| Item | Value |
|---|---|
| Backend interpreter | `backend\.venv\Scripts\python.exe` (Python 3.13) |
| Django settings (tests) | `config.test_settings` (SQLite in memory, temp media/backups) |
| Django settings (local dev) | `config.dev_settings` (refuses to run against Supabase) |
| Local database | `postgres://postgres:1234@127.0.0.1:5432/klb_verify` |
| Local backend | `http://127.0.0.1:8000` |
| Local frontend | `http://127.0.0.1:5173` (Vite proxy for `/api`, `/media`, `/assets` is served from `public/`) |
| Local admin | `admin@klb.com` / `Klb@2026` (super administrator) |
| Local DB state | 1 user, 128 books, 12 pages, 21 news items, 19 resources, 9 tenders, 1 career, 0 enquiries, 0 subscribers |
| Local migration | `content.0017_section_seed_key` applied |
| Seed revision applied | `c8e02fdec79007028bf7dd4523e0fc32` |
| Production URL | `https://klb-website.onrender.com` |

Audit artefacts were removed afterwards: no audit book, career, tender, resource, theme,
partner, page or enquiry rows remain in the local database.

---

## 3. Automated test evidence (executed)

| Check | Command | Observed result |
|---|---|---|
| Django system check | `manage.py check --settings=config.test_settings` | `System check identified no issues (0 silenced).` |
| Migration drift | `manage.py makemigrations --check --dry-run --settings=config.test_settings` | `No changes detected` |
| Full backend suite | `manage.py test --settings=config.test_settings` | `Ran 136 tests in 12.935s` -> `OK` |
| Accounts app | `manage.py test apps.accounts --settings=config.test_settings` | `Ran 32 tests ... OK` |
| Content app | `manage.py test apps.content --settings=config.test_settings` | `Ran 104 tests ... OK` |
| Endpoint/permission audit | `manage.py test apps.content.test_audit --settings=config.test_settings` | `Ran 54 tests ... OK` |
| Seed release gate | `manage.py test apps.content.test_seed_content --settings=config.test_settings` | `Ran 12 tests ... OK` |
| Frontend lint | `npm run lint` | `Parsed 55 source files with esbuild. No syntax errors.` |
| Frontend unit tests | `npm test` | `tests 11 / pass 11 / fail 0` |
| Frontend build | `npm run build` | `built in 3.44s` |

The 136 backend tests cover: public content and status filtering, catalogue search /
filters / pagination / sorting, book detail, careers and tender expiry windows, resources,
digital partners, active theme window, sitemap / robots / health / SPA shell, media
traversal, public forms (validation, honeypot, rate limits, email recipients),
authentication (CSRF, login, `me`, logout, suspended and inactive accounts, password
change), every dashboard CRUD surface, editor permission clamping, activity log filtering
and CSV/XLSX/PDF export, backup lifecycle and restore, upload signature validation, dropdown
options, site settings, test-inquiry email, AI draft (success and upstream failure), and
security boundaries.

---

## 4. Public site journeys (executed in the browser)

| Journey | Observed |
|---|---|
| `/` | Renders with title, hero, newsletter; no console errors |
| Hero animation, local | Sampled every 50 ms: `180+ / 45+ / 350` -> `270+ / 68+ / 527` -> ... -> `1,000+ / 250+ / 1947` |
| Catalogue `/books/` | 128 titles; 24 cards per page; "Show more" loads page 2 |
| Search `Mathematics` | 9 results |
| Collection `CBE` | 19 results (`CBE Grade 1..4` matched by prefix) |
| Price sort (descending) | Highest prices first |
| Book detail | Title, price, ISBN, collection, description, buy link, related titles |
| Contact form with `?book=` | Message prefilled with the book title; submit -> `201`; enquiry persisted; email written to console backend |
| Newsletter subscribe | `201`; subscriber active; UI confirms |
| Newsletter unsubscribe | `200`; subscriber inactive; UI confirms |
| Routes `/about/ /services/ /digital/ /news/ /careers/ /tenders/ /resources/ /privacy/ /terms/` | Correct H1/title, no error state |
| News detail | Title, category, date, body |
| `/does-not-exist/` | 404 page |
| `/books/no-such-book-xyz/` | "We could not find that book." |
| Expired career (created in the UI) | Badge `EXPIRED`; public card has no href, `pointer-events:none`, "This vacancy has closed." |
| Expired tender (created in the UI) | Badge `EXPIRED`; public card closed; backslash document path rejected `400`; corrected path created `201`; editing closing date to 2027 flipped badge to `OPEN` and restored the public download link |
| Resource document | `/assets/docs/klb-price-list-2026.pdf` -> `200`, `application/pdf`, 32,835,061 bytes, header `%PDF-1.7` |
| Digital partner | Created in dashboard -> visible on `/api/digital-partners/` -> deleted -> gone from the public API |
| Seasonal theme | Created -> `/api/themes/active/` returns it -> `<body class="theme-audit">`; end date moved into the past -> status `DRAFT`, endpoint returns `{active:false}`, body class removed |
| Sitemap / robots / health | `200`, valid XML / text / `{"status":"ok"}` |

---

## 5. Admin dashboard journeys (executed in the browser)

| Module | Observed |
|---|---|
| Login / logout | `POST /api/auth/login/` 200; `/api/auth/me/` role `super_admin`, 14 permission modules |
| Dashboard | Counts match the database (128 books, 12 pages, 21 news) |
| Pages | Meta description `PATCH` 200 reflected on `/api/pages/privacy/`; status `draft` -> public 404; republished + meta reverted -> 200 |
| Books | Create 201 -> public 200 -> search count 1 -> edit price `PATCH` 200 (550 -> 750) -> delete 204 -> public 404 |
| News | Create 201 -> public list 22 items -> delete 204 |
| Careers | Create expired vacancy 201 -> badge `EXPIRED` -> public closed -> delete 204 |
| Tenders | Create 201 -> unknown/expired handling -> edit 2027 `PATCH` 200 -> `OPEN` -> delete 204 |
| Resources | Create 201 -> public API contains it -> delete 204 |
| Digital partners | Create 201 -> public API contains it -> delete 204 -> removed publicly |
| Themes | Create 201 -> active endpoint + body class -> expiry 200 -> inactive -> delete 204 |
| Dropdown options | Create 201 (blank value generated), edit 200, delete 204 |
| Settings | Tagline/meta saved and reverted; public `/api/site/` reflects edits immediately |
| Test inquiry email | `POST /api/admin/settings/test-inquiry-email/` 200 with honest console-backend message |
| Enquiries | List, filter, status `PATCH` 200, internal note `PATCH` 200, delete 204 |
| Subscribers | List, search, delete 204; badge shows `UNSUBSCRIBED` |
| Users & permissions | Create user 201, delete 204; editor sees only permitted navigation; restricted endpoints return 403 |
| Activity log | Filter `module=users&action=user` returns 2 entries; CSV/XLSX/PDF exports 200 with correct MIME |
| Backups | Create `klb_backup_*.zip` 490.4 KB SUCCESSFUL; download 502,193 bytes `application/zip`; delete 204 (row + file gone) |
| Uploads | Team photo upload 201 and served; renamed text file with `.png` extension rejected 400 by signature check |

---

## 6. Functional testing table

| Feature | Expected Result | Actual Result | Status | Fix Applied |
|---|---|---|---|---|
| Home page render | Hero, navigation, footer, newsletter | All render; no console errors | PASS | None |
| Hero counters - attributes | `data-count`, `data-suffix`, `data-final` survive CMS sanitising | Present in `/api/pages/home/` HTML | FIXED | Sanitizer allow-list |
| Hero counters - local animation | Numbers animate to final values | Sampled 50 ms: 180+ -> ... -> 1,000+ / 250+ / 1947 | FIXED | `animateCounts.js` + reduced-motion + fallback |
| Hero counters - production | Final values displayed | `1,000+`, `250+`, `1947`; `updated_at` 2026-11-17T08:45; site name includes PLC | FIXED | Render Build Command runs `seed_content --refresh`; verified after deploy `e51995d` |
| Local vs Render content parity | Same content from same seed | Production was stale (Nov 12, no `data-count`); now current | FIXED | Seed runs at build time; revision gate prevents overwrites |
| Catalogue list | Paginated cards | 128 titles; 24 per page; "Show more" works | PASS | None |
| Catalogue search | Filtered, case-insensitive | `Mathematics` -> 9 results | PASS | None |
| Collection filter `CBE` | Match `CBE Grade 1..4` | 19 results | FIXED | `collection__istartswith` |
| Price sort descending | Highest first | Correct order | PASS | None |
| Book detail | Full metadata and CTAs | All render, buy link present | PASS | None |
| Contact form prefill | Message prefilled from `?book=` | Prefill verified; submit 201 | PASS | None |
| Contact form validation | Reject missing/invalid fields | DRF 400 with field errors; honeypot silently accepted | PASS | None |
| Enquiry delivery | Persist row + email to configured inbox | Row saved; email to `inquiry_recipient_email` (fallback `contact_email`); console backend locally | PASS | Recipient setting + fallback |
| Enquiry rate limit | 10/min | 429 after limit (locmem cache) | PASS | None |
| Newsletter subscribe | 201 + active subscriber | Subscriber active, UI confirms | PASS | None |
| Newsletter unsubscribe | 200 + inactive subscriber | Inactive, resubscribe works, UI confirms | PASS | None |
| Newsletter rate limit | 5/min | 429 after limit | PASS | None |
| All public routes | Correct page, no error state | All routes load correctly | PASS | None |
| News detail | Full article | Renders title/category/date/body | PASS | None |
| 404 route | Friendly 404 | Renders correctly | PASS | None |
| Missing book | Friendly error | "We could not find that book." | PASS | None |
| Careers expiry | Expired vacancies visibly closed | `EXPIRED` badge; public card disabled, no href, closed copy | FIXED | `StatusBadge` `open`/`closing_soon`/`expired`; real row status |
| Tenders expiry | Expired tenders visibly closed | `EXPIRED` -> edit date -> `OPEN`; public link appears/disappears | FIXED | Same badge fix |
| Tender/resource document links | Reject backslashes | `400` "Use forward slashes (/)" then `201` with corrected path | FIXED | `validate_document_link` |
| Resource PDFs | 200 `application/pdf` | 19/19 resource documents and 9/9 tender documents return PDF; price list 32,835,061 bytes | FIXED | Lowercase on-disk filename + URL repair |
| Digital partners | Dashboard CRUD reflected publicly | Create visible, delete removed | PASS | None |
| Seasonal themes | Active theme changes the public page | Body class applied; removed on expiry/delete | FIXED | `SiteContext` fetches `/api/themes/active/`; CSP-safe |
| Sitemap / robots / health | 200 and correct content | Verified (XML, Disallow `/admin/`, `status: ok`) | PASS | None |
| SPA deep link | Serves app shell | 200 `text/html` | PASS | None |
| Media traversal | Blocked | `/media/../manage.py` variants -> 400/404 | PASS | None |
| Security headers / CSP | Present and allow the chat widget | `X-Frame-Options: DENY`, `nosniff`, CSP with Tidio font/media/frame sources | FIXED | CSP extended for Tidio webfonts, sound and frame |
| Admin login / logout | Session works; CSRF enforced | Login 200, `me` 200, logout works; missing CSRF -> 403 | PASS | None |
| Session timeout | 30 min sliding | `SESSION_COOKIE_AGE=1800`, `SESSION_SAVE_EVERY_REQUEST=True`; idle logout at 25 min | PASS | Backend + frontend idle timer |
| Editor restrictions | No system modules, no publish/delete | Nav hidden; restricted APIs 403; publish/delete blocked | PASS | Permission clamping |
| Pages CRUD | Create/edit/delete + draft hiding | PATCH 200 reflected publicly; draft 404; republish 200; delete in UI works | PASS | None |
| Books CRUD | Unique slugs, public visibility | Create 201, PATCH 200, delete 204, public 404; duplicate slug rejected | PASS | Unique slug generation + validation |
| News CRUD | Create/edit/delete | Create 201, list count 22, delete 204 | PASS | None |
| Careers CRUD | CRUD + expiry | Create 201, badge `EXPIRED`, delete 204 | PASS | None |
| Tenders CRUD | CRUD + document + expiry | Create 201, PATCH 200, delete 204; invalid document rejected | PASS | `validate_document_link` |
| Resources CRUD | CRUD + category + document | Create 201, public list includes it, delete 204 | PASS | None |
| Digital partners CRUD | CRUD + visible flag | Create/edit/delete verified in UI | PASS | None |
| Themes CRUD | CRUD + active window | Create/patch/delete verified; DRAFT when outside window | PASS | Theme application in frontend |
| Dropdown options | CRUD with auto value | Blank value generated from label; duplicate rejected | FIXED | Serializer `validators=[]` |
| Site settings | Editable, public subset only | Save/revert works; `/api/site/` exposes display settings only | FIXED | `PublicSiteSettingSerializer` |
| Test-inquiry email | Administrators can send | 200; message states console backend when SMTP is not configured | FIXED | `permission_action = "edit"`; honest response |
| Enquiries admin | List/filter/status/note/delete | All verified; editor cannot delete | PASS | Delete permission added |
| Subscribers admin | List/search/delete + status | Search works; badge `SUBSCRIBED` / `UNSUBSCRIBED` | FIXED | `StatusBadge` mapping |
| Users & permissions | Admin-only management | Create/delete verified; editor blocked with 403 | PASS | None |
| Activity log | Filter + CSV/XLSX/PDF | Filters correct; exports 200 with correct MIME | PASS | None |
| Backup create/download/delete | Row + real archive | 490.4 KB archive, 502,193 byte download, delete removes row and file | PASS | Unique filenames, atomic writes |
| Backup restore | Safety backup + file restore | Automated tests: restore JSON + media, safety backup created, invalid JSON rejected | PASS | Automated coverage only (see 11.3) |
| Uploads | Validate real file content | PNG accepted; mismatched signature rejected 400 | FIXED | Signature check in `uploads.py` |
| Team photos | Upload, list, attach | Upload 201, public About page shows photo | PASS | None |
| AI draft | Key + topic required; upstream errors handled | Automated tests cover success and failure paths | PASS | None |
| Maintenance mode | Soft public notice, admin accessible | Toggles notice; dashboard unaffected | PASS | None |
| Accessibility preferences | Persist across reloads | `localStorage` key `klb-accessibility-preferences` | PASS | None |
| Seed refresh gate | Deploy can never erase dashboard content | `--refresh` is create-only on every deploy; a new seed revision still keeps dashboard edits; `--force-refresh` rewrites only seed-origin pages/sections/news in place; `--reset` is rejected without `--confirm-reset`; UI-created pages, sections, books, news, careers, tenders, resources, partners and settings survive every mode | FIXED | Removed all `.delete()` calls; `Section.seed_key` ownership marker (migration `0017`); automatic JSON safety dump before restore modes; 12 seed tests |
| Public settings exposure | No operational secrets | Public JSON contains only display fields; staff-only fields absent | FIXED | `PublicSiteSettingSerializer` |

---

## 7. API endpoints verified

**Public**

- `GET /api/site/`, `GET /api/pages/<slug>/`, `GET /api/pages/home/`
- `GET /api/books/`, `GET /api/books/<slug>/`, `GET /api/catalogue/filters/`
- `GET /api/news/`, `GET /api/news/<slug>/`
- `GET /api/careers/`, `GET /api/tenders/`, `GET /api/resources/`, `GET /api/digital-partners/`
- `GET /api/themes/active/`
- `POST /api/enquiries/`, `POST /api/newsletter/`, `POST /api/newsletter/unsubscribe/`
- `GET /health/`, `GET /sitemap.xml`, `GET /robots.txt`

**Admin (session authenticated)**

- `GET/POST/PATCH/PUT/DELETE /api/admin/pages/` (+ duplicate)
- `GET/POST/PATCH/DELETE /api/admin/books/`, `/news/`, `/careers/`, `/tenders/`, `/resources/`,
  `/digital-partners/`, `/themes/`, `/options/`
- `GET/PATCH/DELETE /api/admin/enquiries/<id>/`, `GET/DELETE /api/admin/subscribers/<id>/`
- `GET/POST/PATCH/DELETE /api/admin/users/` (+ reset-password)
- `GET/PATCH /api/admin/settings/`, `POST /api/admin/settings/test-inquiry-email/`
- `GET/POST /api/admin/backup/`, `GET .../download/`, `POST .../restore/`, `DELETE .../<id>/`
- `POST /api/admin/upload/`, `GET/PATCH /api/admin/team-photos/`
- `GET /api/admin/activity/`, `GET /api/admin/activity/export/`
- `POST /api/admin/ai-draft/`

Every endpoint was exercised with valid data, and the write endpoints with invalid data to
confirm `400` + `{"detail": "...", "errors": {...}}`.

---

## 8. Security verification

- Anonymous `GET`/`POST` to every `/api/admin/*` route -> 401/403; no dashboard data leaks.
- Editor role: system modules (settings, backup, users, activity, options) hidden and
  API-blocked; publish/delete clamped even if the payload asks for it.
- CSRF enforced for session-authenticated writes; `/api/auth/csrf/` sets the cookie.
- Login throttled at 5/min, enquiry 10/min, newsletter 5/min; throttling verified with 429.
- Uploaded files validated by magic bytes, not extension (mismatched `.png` rejected).
- Public settings serializer excludes operational values; no secrets in `/api/site/`.
- `.env` is not committed; `config.dev_settings` refuses a Supabase `DATABASE_URL`.
- Media traversal paths (`..`, encoded variants) rejected.
- Security headers set: `X-Frame-Options: DENY`, `nosniff`, Referrer-Policy,
  Permissions-Policy, CSP with `frame-ancestors 'none'`.
- Suspended and inactive accounts cannot sign in.

---

## 9. Production (Render) verification

Commit `e51995d` was pushed to `main`; Render built and deployed it automatically. Verified
against `https://klb-website.onrender.com` after the deploy:

| Check | Observed |
|---|---|
| `/health/` | 200, `{"status":"ok"}` |
| `/api/pages/home/` | `updated_at = 2026-11-17T08:45:21.745034+03:00`, 8 sections, contains `data-count` |
| `/api/site/` | `site_name = "Kenya Literature Bureau PLC"` |
| `/api/themes/active/` | 200; active theme `theme-christmas` (`2026-11-13` to `2026-11-25`) |
| Seasonal theme in the DOM | `<body class="theme-christmas">` after the load |
| Hero counters | 3 elements; final text `1,000+`, `250+`, `1947` |
| Served bundle | `/assets/index-DlE9K2Cy.js` contains `/themes/active/` (theme fix deployed) |
| CSP | includes `font-src ... code.tidio.co`, `media-src ... code.tidio.co`, `frame-src ... code.tidio.co` |
| Browser console | **0 errors**; the previous Tidio CSP font/media errors are gone |
| Price list PDF | `/assets/docs/klb-price-list-2026.pdf` -> `200`, `application/pdf`, 32,835,061 bytes |

**Note on the counter animation in automated production tabs:** in the remote inspection
tab, `requestAnimationFrame` did not fire at all (0 frames in 2.5 s), so the numbers jumped
from `0` to the final values at ~2.3 s via the `setTimeout` safety net. A local foreground
tab animated with intermediate values as designed. This is Chromium background/remote-tab
throttling, not a site defect; the final values are always rendered, and the live production
page displays them correctly.

### 9.1 Data-safety commit `4c3925e` - post-push production checks

After pushing the non-destructive seed commit, the live service was checked again:

| Check | Observed after the push |
|---|---|
| `/health/` | 200, `{"status":"ok"}` |
| `/api/pages/home/` | 8 sections, `updated_at` still `2026-11-17T08:45:21.745034+03:00`, `data-count` present |
| `/api/books/?page_size=1` | `count = 128` (no catalogue rows lost) |
| `/api/site/` | Site name, navigation, footer and statistics returned unchanged |
| `/api/themes/active/` | `theme-christmas` still active |
| Price-list PDF | 200, `application/pdf`, 32,835,061 bytes |

The unchanged `updated_at` and counts are the expected result of a create-only deploy: the
Build Command runs `migrate` then `seed_content --refresh`, which added nothing because all
seed rows already exist.

**Verification limit:** this environment has no Render API token or Shell access, so the
deploy's build log cannot be read back. The seed behaviour itself was executed in the full
136-test suite, in targeted tests (section 10.1) and against the local PostgreSQL database;
production runs the same pushed commit. If the Render dashboard shows the build failed,
open **Logs** and re-run **Manual Deploy -> Clear build cache & deploy**.

---

## 10. Root causes and fixes applied

1. **Stale production content (local vs Render mismatch).** The Render service is a manual
   service, so `render.yaml` was not applied and its Build Command never ran
   `seed_content`. Local and production therefore used different data.
   - Fix: Build Command now runs `python manage.py seed_content --refresh` after migrate;
     documented below for the dashboard.
   - Follow-on risk: refreshing on every deploy would overwrite dashboard edits. Added a
     SHA-256 fingerprint of `cms-seed.json` + `books.json` stored in
     `SiteSetting.seed_revision` (`migration 0016`). A release applies once; later deploys
     print "Seed revision already applied; keeping dashboard edits." `--force-refresh`
     deliberately restores the seed copy.
   - Data-loss follow-up: the original `--refresh` still deleted every section on a seed
     page and rewrote seed settings, and `--reset` deleted whole tables. All destructive
     calls are gone (see 10.1).
   - Evidence: 12 tests (`test_seed_content.py`) prove create-only deploys, edit retention,
     in-place restore, confirmation gating, safety dumps and UI-content preservation.
2. **Seasonal themes were never applied publicly.** `/api/themes/active/` worked but the
   frontend never called it.
   - Fix: `SiteContext` fetches the active theme and adds its `css_class` to `<body>`,
     removing it on expiry, deletion, or theme change.
   - Evidence: body class `theme-audit` while active; endpoint `{active:false}` and no class
     once the end date passed.
3. **Expired careers/tenders looked open in the dashboard.** The badge mapped expired to
   `DRAFT` and closing-soon to `new`.
   - Fix: `StatusBadge` handles `open`, `closing_soon`, `expired`; columns pass the real row
     status; careers lead copy corrected.
4. **Price-list download returned the SPA HTML shell.** The seed used backslashes and the
   file on disk was `KLB-PRICE-LIST-2026.pdf`.
   - Fix: renamed file to lowercase; `validate_document_link()` rejects backslashes and
     requires a root-relative or `http(s)` URL for `Resource.file_url` and
     `Tender.document_url`; seed command repairs existing backslash URLs.
   - Evidence: `/assets/docs/klb-price-list-2026.pdf` -> 200, `application/pdf`,
     32,835,061 bytes, `%PDF-1.7`.
5. **Public `/api/site/` exposed operational settings.** Fix: `PublicSiteSettingSerializer`.
6. **Enquiries had no delete permission in the frontend RBAC map.** Fix: added `delete`.
7. **Book slugs could collide.** Fix: unique slug generation and duplicate-slug validation.
8. **Upload validation trusted the extension.** Fix: file-signature checks.
9. **Dropdown options rejected blank `value`.** Fix: disable the auto unique-together
   validator; generate `value` from the label, then run the custom duplicate check.
10. **Test-inquiry email was blocked for administrators.** Fix: `permission_action = "edit"`;
    the response is honest about the console backend when SMTP is absent.
11. **Subscriber badge reused `published`/`draft`.** Fix: `subscribed`/`unsubscribed`.
12. **Hero counter attributes were stripped by the sanitizer.** Fix: allow `data-count`,
    `data-suffix`, `data-final`; `animateCounts.js` handles reduced motion and a throttled
    `requestAnimationFrame`.
13. **Catalogue `CBE` filter missed `CBE Grade 1..4`.** Fix: `collection__istartswith`
    with vendor-aware handling.
14. **Dev scripts could target Supabase.** Fix: `config.dev_settings` guard.
15. **Tidio chat widget produced CSP console errors** for its webfonts, notification sound
    and frame. Fix: CSP `font-src`, `media-src`, `frame-src` allow `code.tidio.co` /
    `*.tidio.co`; regression test added.

### 10.1 Dashboard content is never deleted or overwritten by seeding

The user reported that content created through the dashboard disappeared after code
changes and deploys. Root causes found in `seed_content.py`:

| Root cause | Previous effect | Fix |
|---|---|---|
| `seed_pages(refresh=True)` ran `page.sections.all().delete()` | Every dashboard section on a seed page was destroyed on each refresh | Sections are matched by `seed_key` and refreshed in place; nothing is deleted |
| `seed_pages(refresh=True)` recreated all seed sections | Dashboard HTML under a seed label was replaced | `--refresh` is create-only; only `--force-refresh` rewrites seed-origin sections |
| `seed_news(refresh=True)` rewrote seed articles | Edited seed articles were reverted | Only the explicit restore modes rewrite seed news |
| `seed_settings` refresh rewrote `navigation`, `footer_columns`, `statistics` and SEO copy | Dashboard settings reverted | Existing settings are never overwritten; only blank values are filled |
| `--reset` deleted `Section`, `Page`, `Book`, `News`, `Career`, `Tender`, `Resource`, `SiteSetting` | Entire site content wiped | All `.delete()` calls removed; `--reset` now restores in place and requires `--confirm-reset` |
| No recovery point before a forced rewrite | A mistaken command was unrecoverable | A JSON `dumpdata` safety file is written to `BACKUP_ROOT` before every restore mode |

Current seed contract:

- Plain `seed_content` and `seed_content --refresh`: create missing rows only. Existing
  pages, sections, books, news, careers, tenders, resources, partners, settings and
  administrator accounts are left exactly as they are. This is what Render runs on every
  deploy.
- `seed_content --force-refresh`: restores the seed copy of seed-origin pages, sections and
  news in place. It creates missing rows, updates rows whose `seed_key` matches the seed
  file, keeps dashboard-added sections (blank `seed_key`), keeps every other dashboard row,
  and keeps every non-blank setting. A safety dump is written first.
- `seed_content --reset`: rejected unless `--confirm-reset` is also passed. With both flags
  it behaves like `--force-refresh`; it never truncates tables.
- No command deletes administrator accounts. `flush` is no longer recommended anywhere;
  `docs/TROUBLESHOOTING.md` now requires a backup and offers non-destructive repairs.

Executed evidence (`.\.venv\Scripts\python.exe manage.py test apps.content.test_seed_content
--settings=config.test_settings`):

```
Found 12 test(s).
Ran 12 tests in 5.796s
OK
```

The 12 tests prove: refresh-once retention, create-only behaviour when the fingerprint
changes, plain-seed retention, backslash repair, forced restore of seed rows,
preservation of dashboard-created pages/sections/news/careers/tenders/resources/partners/
books, confirmation gating, confirmed reset preserving dashboard content, rejection of
combined flags, settings preservation, and the safety dump containing the dashboard page.

Local PostgreSQL verification (`klb_verify`, 2026-11-17), comparing a snapshot before and
after a real `seed_content --refresh --settings=config.dev_settings`:

```
Seed revision already applied; keeping dashboard edits.
  pages: 0  books: 0  news: 0  careers: 0  tenders: 0  resources: 0  digital partners: 0
BEFORE: pages=12 sections=61 books=128 news=21 careers=1 tenders=9 resources=19 partners=6
AFTER : pages=12 sections=61 books=128 news=21 careers=1 tenders=9 resources=19 partners=6
```

Every page `updated_at`, `SiteSetting.updated_at` (`2026-11-16T07:05:22.484529+00:00`),
the section HTML hash (`75b21b343df633b2`) and the news body hash were identical before and
after. All 61 existing sections were adopted under a `seed_key` without changing their
HTML or order; 0 sections remain unowned, so a later forced restore cannot touch content
an editor adds (new sections stay blank-keyed).

---

## 11. Blocked items and remaining external steps

### 11.1 Real SMTP delivery - BLOCKED (credentials)

Emails currently use Django's console backend (visible in server logs) because `EMAIL_HOST`
is blank. To switch to real delivery, set these in the Render dashboard
(Environment -> Add Environment Variable) and redeploy:

```
EMAIL_HOST=<smtp host>
EMAIL_PORT=587
EMAIL_HOST_USER=<smtp user>
EMAIL_HOST_PASSWORD=<smtp password>
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=<verified sender address>
```

Then use **Admin -> Settings -> Send test email** and confirm the message arrives.

### 11.2 Deploying these newest fixes - DONE

Commit `e51995d` was pushed to `origin/main` and Render's automatic deploy picked it up.
The production checks in section 9 confirm the backend and frontend fixes are live (new
bundle `index-DlE9K2Cy.js`, theme class applied, new CSP, price-list PDF).

The later data-safety commit `4c3925e` (migration `0017`, non-destructive `seed_content`)
was pushed on top; section 9.1 records the post-push checks. If automatic deploys are ever
disabled, use **Manual Deploy -> Clear build cache & deploy** with the Build Command in 12.7.

### 11.3 Live UI backup restore - not executed in the browser

Create/download/delete were executed in the UI. Restore is covered by automated tests:
`test_restore_media_creates_safety_backup_and_restores_files` and the invalid-JSON
rejection test. To exercise it manually, upload one of the downloaded archives in
**Admin -> Backups -> Upload & restore** and confirm the safety backup row appears.

### 11.4 Cosmetic items

- The subscribers search empty-state text still reads "No subscribers yet" when a filter
  matches nothing. Cosmetic only.
- Supabase may still hold legacy rows whose `file_url` used backslashes. Running
  `seed_content` (plain or `--refresh`) repairs them; the validator blocks new ones.

---

## 12. Exact PowerShell commands

Run each block from the directory shown. Do not commit or print `.env` contents.

### 12.1 Backend virtual environment and dependencies

```powershell
cd "C:\Users\Admin IT\Downloads\CS50\CS50_codes\klb_website_2026\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 12.2 Django checks, migrations and tests

```powershell
cd "C:\Users\Admin IT\Downloads\CS50\CS50_codes\klb_website_2026\backend"
.\.venv\Scripts\python.exe manage.py check --settings=config.test_settings
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=config.test_settings
.\.venv\Scripts\python.exe manage.py test --settings=config.test_settings
.\.venv\Scripts\python.exe manage.py test apps.content.test_audit --settings=config.test_settings
.\.venv\Scripts\python.exe manage.py test apps.content.test_seed_content --settings=config.test_settings
```

### 12.3 Local database: migrate and seed

```powershell
cd "C:\Users\Admin IT\Downloads\CS50\CS50_codes\klb_website_2026\backend"
$env:DATABASE_URL = "postgres://postgres:1234@127.0.0.1:5432/klb_verify"
.\.venv\Scripts\python.exe manage.py migrate --settings=config.dev_settings
.\.venv\Scripts\python.exe manage.py seed_content --refresh --settings=config.dev_settings
```

`--refresh` is create-only and runs on every deploy; it never overwrites dashboard
content. Use `--force-refresh` only when you deliberately want to restore the seed copy of
seed-origin pages, sections and news. It keeps dashboard-created rows and edited settings
and writes a JSON safety dump to `backend\backups` first. `--reset` requires
`--confirm-reset` and performs the same in-place restore; it never truncates tables.

### 12.4 Frontend dependencies, lint, tests and build

```powershell
cd "C:\Users\Admin IT\Downloads\CS50\CS50_codes\klb_website_2026\frontend"
npm ci
npm run lint
npm test
npm run build
```

### 12.5 Run the local site (two terminals)

```powershell
# Terminal 1 - backend (dev settings refuse to run against Supabase)
cd "C:\Users\Admin IT\Downloads\CS50\CS50_codes\klb_website_2026\backend"
$env:DATABASE_URL = "postgres://postgres:1234@127.0.0.1:5432/klb_verify"
$env:DJANGO_DEBUG = "True"
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --settings=config.dev_settings
```

```powershell
# Terminal 2 - frontend
cd "C:\Users\Admin IT\Downloads\CS50\CS50_codes\klb_website_2026\frontend"
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:5173/` and `http://127.0.0.1:5173/admin/login`.

### 12.6 Review and push the fixes

```powershell
cd "C:\Users\Admin IT\Downloads\CS50\CS50_codes\klb_website_2026"
git status --short
git diff --check
git add -A
git commit -m "fix: gate seed refresh per release, apply seasonal themes, correct expiry badges and CSP"
git push origin main
```

### 12.7 Render deployment

The Render service is a **manual service**, so `render.yaml` is reference only. Set the
Build Command in the Render dashboard:

```
cd frontend && npm ci && npm run build && cd ../backend && pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py seed_content --refresh
```

Start Command:

```
cd backend && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120
```

Confirm these environment variables exist (values never committed):

```
PYTHON_VERSION=3.12.6
NODE_VERSION=20.11.1
DJANGO_DEBUG=False
DJANGO_SECURE_SSL=True
DJANGO_SECURE_COOKIES=True
DJANGO_ALLOWED_HOSTS=klb-website.onrender.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://klb-website.onrender.com
DATABASE_URL=<from the Render PostgreSQL instance>
MEDIA_DIR=/opt/render/project/src/data/media
BACKUP_DIR=/opt/render/project/src/data/backups
SEED_ADMIN_EMAIL=<production admin email>
SEED_ADMIN_PASSWORD=<set in dashboard only>
SESSION_TIMEOUT_SECONDS=1800
EMAIL_HOST / EMAIL_HOST_USER / EMAIL_HOST_PASSWORD / DEFAULT_FROM_EMAIL (see 11.1)
```

Then click **Manual Deploy -> Clear build cache & deploy**. If you use the Render CLI
instead:

```powershell
cd "C:\Users\Admin IT\Downloads\CS50\CS50_codes\klb_website_2026"
render deploys create <service-id> --wait
```

### 12.8 Post-deploy verification

```powershell
$base = "https://klb-website.onrender.com"
(Invoke-WebRequest -UseBasicParsing "$base/health/").Content
$home = (Invoke-WebRequest -UseBasicParsing "$base/api/pages/home/").Content | ConvertFrom-Json
"data-count present: " + ($home.sections.html -join " ").Contains("data-count")
"updated_at: " + $home.updated_at
$site = (Invoke-WebRequest -UseBasicParsing "$base/api/site/").Content | ConvertFrom-Json
"site_name: " + $site.settings.site_name
(Invoke-WebRequest -UseBasicParsing "$base/api/themes/active/").StatusCode
$pdf = Invoke-WebRequest -UseBasicParsing "$base/assets/docs/klb-price-list-2026.pdf" -Method Head
"price list: $($pdf.StatusCode) $($pdf.Headers['Content-Type'])"
```

Then, in a normal browser tab (not a background tab), confirm the hero counters animate
from small numbers to `1,000+`, `250+`, `1947`; confirm an expired career/tender shows the
`EXPIRED` badge and a closed public card; create a theme dated today and confirm the body
class appears, then delete it.

---

## 13. Repeatable verification checklist

1. `manage.py check` -> 0 issues.
2. `makemigrations --check` -> no changes.
3. `manage.py test` -> 136 tests OK.
4. `npm run lint` -> 0 syntax errors.
5. `npm test` -> 11/11.
6. `npm run build` -> success.
7. Local browser: home counters, catalogue search/filter/sort, contact form, newsletter,
   one admin create/edit/delete.
8. Push and deploy; run 12.8.
9. Configure SMTP (11.1) and send the test email.

---

## 14. Test artefact map

| File | Purpose |
|---|---|
| `backend/apps/content/test_audit.py` | 54 executable endpoint/permission/security tests |
| `backend/apps/content/test_seed_content.py` | 12 seed data-safety tests |
| `backend/apps/content/tests.py` | Backup, settings, theme and upload tests |
| `backend/apps/accounts/tests.py` | Authentication, roles, permissions, activity tests |
| `frontend/tests/lib.test.mjs` | 11 RBAC, permission and formatting unit tests |
| `frontend/scripts/check-syntax.mjs` | esbuild parse check used by `npm run lint` |
| `render.yaml` | Reference build/start commands and environment variable names |
| `backend/apps/content/migrations/0016_sitesetting_seed_revision.py` | Adds the seed fingerprint field |

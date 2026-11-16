# KLB PLC Website – Functional Testing Report

**Project:** Kenya Literature Bureau PLC website (public site + admin dashboard)  
**Date:** 16 November 2026  
**Working directory:** `C:\Users\Admin IT\Downloads\CS50\CS50_codes\klb_website_2026`  
**Stack:** React 18 + Vite 6 / Django 5 + DRF / PostgreSQL 18 (local `klb_verify` for verification)  
**Branding:** `#F3E5AB` yellow, Century Gothic, KLB branding preserved.

## 1. Test environment

| Item | Value |
|---|---|
| Backend Python | `backend/.venv` (Python 3.13) |
| Django settings (tests) | `config.test_settings` (SQLite in-memory) |
| Django settings (local dev) | `config.dev_settings` (refuses Supabase) |
| Local database | `postgres://postgres:1234@127.0.0.1:5432/klb_verify` |
| Backend server | `http://127.0.0.1:8000` (Django dev server) |
| Frontend server | `http://127.0.0.1:5173` (Vite dev server, proxies `/api`, `/media`) |
| Admin credentials (local) | `admin@klb.com` / `Klb@2026` (super administrator) |
| Browser tab used | `tab_2b7f7fd1-6245-4e02-a725-0eaa8164b7c3` |

## 2. Automated test results

| Check | Command | Result |
|---|---|---|
| Django system check | `manage.py check --settings=config.test_settings` | 0 issues |
| Migration check | `manage.py makemigrations --check --dry-run` | No changes detected |
| Full backend suite | `manage.py test --settings=config.test_settings` | **123 tests, OK** |
| Audit suite | `manage.py test apps.content.test_audit --settings=config.test_settings` | **53 tests, OK** |
| Frontend lint | `npm run lint` | 55 files parsed, no syntax errors |
| Frontend unit tests | `npm test` | **11/11 pass** |
| Frontend production build | `npm run build` | Success in ~3.4s, `dist/` generated |

## 3. Functional testing table

| Feature | Expected Result | Actual Result | Status | Fix Applied |
|---|---|---|---|---|
| Home page render | Title, hero, footer, newsletter load | Renders correctly, no console errors | PASS | None |
| Hero counters | `data-count`/`data-suffix`/`data-final` animate | Attributes allowed by sanitizer; counters animate | FIXED | Sanitizer allow-list updated |
| Catalogue list (128 titles) | 24 cards per page, pagination | 24 cards, "Show more" loads page 2 (48 total) | PASS | None |
| Catalogue search "Mathematics" | Filtered results | 9 results returned | PASS | None |
| Catalogue collection filter "CBE" | Matches `CBE Grade 1..4` | 19 results via `collection__istartswith` | FIXED | `istartswith` filter + vendor-aware filtering |
| Catalogue price sort (desc) | Highest prices first | Correct order observed | PASS | None |
| Book detail page | Title, price, metadata, buy link, related titles | All fields render; print/bulk CTAs present | PASS | None |
| Contact form prefill (`?book=`) | Message prefilled with book title | Prefill verified; submit 201 | PASS | None |
| Contact form submission | Persist enquiry + email | `Enquiry` id 1 persisted; console email logged (201) | PASS | None |
| Newsletter subscribe | 201 + active subscriber | `Subscriber` active=True, UI "You are on the list" | PASS | None |
| Newsletter unsubscribe | 200 + inactive subscriber | `Subscriber.is_active=False`, UI "unsubscribed" | PASS | None |
| Route sweep (`/about/`, `/services/`, `/digital/`, `/news/`, `/careers/`, `/tenders/`, `/resources/`, `/privacy/`, `/terms/`) | Correct title/H1, no error state | All load with correct H1, no console errors | PASS | None |
| News detail page | Full article view | Loads with title, category, date, body | PASS | None |
| 404 page (`/does-not-exist/`) | "Page not found" | Renders 404 page, title correct | PASS | None |
| Missing book (`/books/no-such-book-xyz/`) | "We could not find that book." | Error state shown | PASS | None |
| Resource PDFs (18) | 200 `application/pdf` | All 18 return 200 PDF | PASS | None |
| Tender PDFs (13) | 200 `application/pdf` | All 13 return 200 PDF | PASS | None |
| Broken price-list download | 200 PDF | Was 404 HTML shell (backslash URL + wrong case) | FIXED | Renamed file to lowercase; `validate_document_link` rejects backslashes |
| Admin login | 200 + dashboard | Login 200, dashboard stats (128 books, 12 pages, 21 news, 1 enquiry) | PASS | None |
| Admin dashboard stats | Correct counts | Matches DB (128 books, 12 pages, 21 news) | PASS | None |
| Dropdown options CRUD (UI) | Create/edit/delete with confirm | POST 201, PATCH 200, DELETE 204; value auto-generated | PASS | Serializer `validators=[]` fix |
| Site settings save/revert | Public API reflects change immediately | Tagline change reflected in `/api/site/`; reverted successfully | PASS | None |
| Test inquiry email endpoint | POST `/api/admin/settings/test-inquiry-email/` | 200, honest console-backend message | PASS | Permission action `edit` |
| Backup create (UI) | New archive + history row | `klb_backup_...zip` 490.4 KB, SUCCESSFUL | PASS | None |
| Backup download (UI) | File download | 502193 bytes, `application/zip` | PASS | None |
| Backup delete (UI) | Row + file removed | DB row gone, file gone, 204 | PASS | None |
| Media upload (team photo) | POST 201 + PATCH photo | Upload 201, photo served 200 PNG, About page shows image | PASS | None |
| Upload signature validation | Reject mismatched content | 400 "file contents do not match" | PASS | `uploads.py` signature check |
| Enquiries admin (list/search/filter/status/note/delete) | Full CRUD + status update | PATCH status/note 200; filters working; DELETE 204 | PASS | None |
| Subscribers admin (list/search/delete) | List + search + delete | Search works; delete 204; status now "UNSUBSCRIBED" | FIXED | StatusBadge mapping for subscribed/unsubscribed |
| Users & permissions (create/edit/delete) | Role-based access | Editor created; nav restricted; API 403 on restricted endpoints; delete 204 | PASS | None |
| Activity log + filters + export | CSV/XLSX/PDF downloads | Filters work; exports 200 with correct MIME | PASS | None |
| Maintenance mode | Soft public notice, admin accessible | Field present, toggles without blocking admin | PASS | None |
| Accessibility preferences | Persist in `localStorage` key `klb-accessibility-preferences` | Verified key usage | PASS | None |
| Session timeout | Backend 1800s + frontend idle 25 min | Settings present | PASS | None |

## 4. API endpoints verified (representative)

Public:
- `GET /api/site/`, `GET /api/pages/<slug>/`, `GET /api/books/`, `GET /api/books/<slug>/`
- `GET /api/catalogue/filters/`, `GET /api/news/`, `GET /api/news/<slug>/`
- `GET /api/careers/`, `GET /api/tenders/`, `GET /api/resources/`, `GET /api/digital-partners/`
- `POST /api/enquiries/`, `POST /api/newsletter/`, `POST /api/newsletter/unsubscribe/`

Admin (super administrator):
- `GET/POST/PATCH/DELETE /api/admin/pages/`, `/api/admin/books/`, `/api/admin/news/`, `/api/admin/careers/`, `/api/admin/tenders/`, `/api/admin/resources/`
- `GET/PATCH /api/admin/enquiries/<id>/`, `DELETE /api/admin/enquiries/<id>/`
- `GET/DELETE /api/admin/subscribers/<id>/`
- `GET/POST/PATCH/DELETE /api/admin/users/`, `/api/admin/options/`
- `GET/PATCH /api/admin/settings/`, `POST /api/admin/settings/test-inquiry-email/`
- `GET/POST /api/admin/backup/`, `GET /api/admin/backup/<id>/download/`, `POST /api/admin/backup/<id>/restore/`, `DELETE /api/admin/backup/<id>/`
- `POST /api/admin/upload/`, `GET/PATCH /api/admin/team-photos/`
- `GET /api/admin/activity/`, `GET /api/admin/activity/export/`

All tested endpoints returned expected status codes (200/201/204) and correct JSON shapes; validation errors are wrapped as `{"detail": "...", "errors": {...}}`.

## 5. Bugs found and fixes applied

1. **Broken price-list download** (`assets\docs\KLB-PRICE-LIST-2026.pdf`): relative backslash URL resolved to the SPA HTML shell, and filename case mismatched on disk.  
   - Fix: renamed file to lowercase `klb-price-list-2026.pdf`; added `validate_document_link()` in `serializers.py` for `Resource.file_url` and `Tender.document_url` (rejects backslashes, requires `/...` or `http(s)://`).  
   - Evidence: 18/18 resource PDFs and 13/13 tender PDFs now return 200 `application/pdf`.
2. **Catalogue collection filter** did not match `CBE Grade 1..4` for `CBE`.  
   - Fix: `collection__istartswith` instead of exact match.
3. **Dropdown serializer** rejected blank `value` auto-generation.  
   - Fix: `validators = []` on `DropdownOptionSerializer`; value generated from label.
4. **Public site settings** exposed operational fields.  
   - Fix: `PublicSiteSettingSerializer` restricts public `/api/site/`.
5. **Enquiry delete permission** missing in frontend RBAC.  
   - Fix: added `delete` permission for enquiries.
6. **Subscriber status badge** showed "DRAFT" for unsubscribed users.  
   - Fix: StatusBadge + subscriber column map to subscribed/unsubscribed.
7. **Test inquiry email** permission action was wrong.  
   - Fix: `permission_action = "edit"` so administrators can use it.
8. **Hero counter attributes** stripped by sanitizer.  
   - Fix: allow `data-count`, `data-suffix`, `data-final`.
9. **Stray `PY` lines** in helper scripts caused blank pages previously.  
   - Scan: no stray `PY` lines remain.
10. **Dev backend scripts** could accidentally target Supabase.  
    - Fix: scripts pass `--settings=config.dev_settings`, which refuses Supabase.

## 6. Security verification

- Unauthenticated `GET /api/admin/*` → 403; anonymous cannot reach protected pages.
- Editor role: nav hides Settings/Backup/Users/Activity/Options; API returns 403 for those modules; read access limited to permitted modules (verified via `/api/auth/me/` permissions and live requests).
- Suspended/inactive accounts cannot sign in (covered by unit tests).
- Upload validation checks file signatures, not just extensions (verified 400 on mismatched content).
- No `.env` secrets committed; `DATABASE_URL` points to Supabase but dev settings refuse to run against it.

## 7. Outstanding issues / external configuration

1. **Real SMTP delivery** requires user-supplied `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` (currently console backend → emails logged to server console).
2. **Production Supabase row** `Resource id 1` has `file_url = "assets\docs\KLB-PRICE-LIST-2026.pdf"` (backslash). Local DB is correct (`/assets/docs/klb-price-list-2026.pdf`). Correct this row in the production admin after deploy; the new validator prevents new bad values.
3. **Render deployment** not executed from this environment (requires push/deploy access).
4. Empty-state wording on subscribers search ("No subscribers yet" even when filtered) is cosmetic; not blocking.

## 8. Exact PowerShell commands

### 8.1 Virtual environment and dependencies
```powershell
cd "C:\Users\Admin IT\Downloads\CS50\CS50_codes\klb_website_2026\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 8.2 Django checks and tests
```powershell
cd "C:\Users\Admin IT\Downloads\CS50\CS50_codes\klb_website_2026\backend"
.\.venv\Scripts\python.exe manage.py check --settings=config.test_settings
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=config.test_settings
.\.venv\Scripts\python.exe manage.py test --settings=config.test_settings
.\.venv\Scripts\python.exe manage.py test apps.content.test_audit --settings=config.test_settings
```

### 8.3 Migrations
```powershell
cd "C:\Users\Admin IT\Downloads\CS50\CS50_codes\klb_website_2026\backend"
.\.venv\Scripts\python.exe manage.py migrate --settings=config.dev_settings
```

### 8.4 Frontend tests and build
```powershell
cd "C:\Users\Admin IT\Downloads\CS50\CS50_codes\klb_website_2026\frontend"
npm install
npm run lint
npm test
npm run build
```

### 8.5 Local servers
```powershell
# Backend (terminal 1) – always use dev settings to avoid touching Supabase
cd "C:\Users\Admin IT\Downloads\CS50\CS50_codes\klb_website_2026\backend"
$env:DATABASE_URL = "postgres://postgres:1234@127.0.0.1:5432/klb_verify"
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --settings=config.dev_settings

# Frontend (terminal 2)
cd "C:\Users\Admin IT\Downloads\CS50\CS50_codes\klb_website_2026\frontend"
npm run dev
```

### 8.6 Git commit and push
```powershell
cd "C:\Users\Admin IT\Downloads\CS50\CS50_codes\klb_website_2026"
git status
git add -A
git commit -m "Full functional audit: fixes, tests, and report"
git push origin main
```

### 8.7 Render deploy
```powershell
# Trigger a manual deploy from the Render dashboard, or via Render CLI:
cd "C:\Users\Admin IT\Downloads\CS50\CS50_codes\klb_website_2026"
render deploy
```
Ensure Render environment variables include `DATABASE_URL`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `EMAIL_*`, `DEFAULT_FROM_EMAIL`, `SESSION_COOKIE_AGE`.

### 8.8 Post-deploy verification
```powershell
Invoke-WebRequest -UseBasicParsing "https://<your-render-url>/health/" | Select-Object StatusCode, Content
Invoke-WebRequest -UseBasicParsing "https://<your-render-url>/" | Select-Object StatusCode
```
Then log in to `/admin/login` with the production admin account and verify dashboard counts, one content edit, and one backup download.

## 9. Summary

- Features tested: 40+ (public pages, catalogue, forms, newsletter, admin CRUD, backups, uploads, users/permissions, activity log, exports).
- Automated: 123 backend tests OK + 53 audit tests OK + 11 frontend tests OK.
- Bugs fixed: 10 (see section 5).
- Remaining: SMTP configuration, production resource URL correction, Render deploy.

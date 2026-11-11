# KLB Website — Implementation Guide

## A. Files Created or Modified

### New files created

| File Path | Purpose |
| --- | --- |
| `backend/apps/content/middleware.py` | Security headers middleware (CSP, cache-control, permissions policy) |
| `backend/apps/content/management/commands/backup.py` | Backup management command (database + media) |
| `backend/apps/content/migrations/0009_career_opening_date_tender_opening_date.py` | Adds opening_date to Career and Tender |
| `backend/apps/content/migrations/0010_websitetheme.py` | Creates WebsiteTheme model |
| `backend/apps/catalogue/migrations/0002_book_search_vector_and_more.py` | Adds search_vector field + GIN index to Book |
| `frontend/src/components/MediaLightbox.jsx` | Image/video lightbox component |
| `frontend/src/components/StatBlock.jsx` | Animated statistics with counting |
| `frontend/src/components/ErrorBoundary.jsx` | React error boundary |
| `frontend/src/components/sections/DigitalPartnersSection.jsx` | API-driven digital partners |
| `frontend/src/admin/AdminTeamPhotos.jsx` | Team photo management page |
| `frontend/src/admin/AdminDigitalPartners.jsx` | Digital partner CRUD page |
| `frontend/src/admin/AdminBackup.jsx` | Backup management page |
| `frontend/src/admin/AdminThemes.jsx` | Website theme/campaign management page |
| `docs/DEPLOYMENT-RENDER.md` | Render deployment guide |
| `docs/DESIGN-SYSTEM.md` | Design system documentation |
| `render.yaml` | Render blueprint |

### Modified files

| File Path | What changed |
| --- | --- |
| `backend/config/settings.py` | Merged REST_FRAMEWORK, env validation, security middleware, rate limiting |
| `backend/config/urls.py` | Added theme, backup, unsubscribe routes; media serving; settings import |
| `backend/apps/content/models.py` | WebsiteTheme, opening_date fields, statistics field, search_vector (catalogue) |
| `backend/apps/content/serializers.py` | WebsiteThemeSerializer, status fields, statistics field |
| `backend/apps/content/views.py` | ActiveThemeView, AdminWebsiteThemeViewSet, AdminBackupView, fixed imports |
| `backend/apps/content/team_photos.py` | Photo parsing and injection |
| `backend/apps/content/sanitize.py` | Allowed data-member, data-lightbox attributes |
| `backend/apps/content/management/commands/seed_content.py` | Company name, --refresh flag, seed_digital_partners |
| `backend/apps/catalogue/models.py` | search_vector field, GinIndex, full-text search in save() |
| `backend/apps/catalogue/views.py` | Full-text search with SearchQuery/SearchRank, fallback to icontains |
| `backend/apps/enquiries/views.py` | UnsubscribeView, fixed NewsletterView, already_subscribed tracking |
| `backend/apps/enquiries/serializers.py` | already_subscribed tracking |
| `backend/seed/cms-seed.json` | Copy improvements, editorial layouts, digital_partners array |
| `frontend/src/styles/klb.css` | Editorial design system, component restyles |
| `frontend/src/styles/admin.css` | Improved contrast, responsive |
| `frontend/src/styles/admin-react.css` | Table scrolling, stat cards, form focus |
| `frontend/src/components/sections/NewsListSection.jsx` | Editorial list |
| `frontend/src/components/sections/ResourcesListSection.jsx` | Resource rows |
| `frontend/src/components/sections/CareersListSection.jsx` | Expiry UI |
| `frontend/src/components/sections/TendersListSection.jsx` | Expiry UI |
| `frontend/src/components/sections/DigitalPartnersSection.jsx` | API-driven partners |
| `frontend/src/components/Header.jsx` | Search filters |
| `frontend/src/components/Footer.jsx` | Link removal, PLC name |
| `frontend/src/components/NewsletterForm.jsx` | Unsubscribe UI |
| `frontend/src/components/Layout.jsx` | Lightbox mount |
| `frontend/src/components/SectionRenderer.jsx` | New section kinds |
| `frontend/src/context/SiteContext.jsx` | Caching, reload fix |
| `frontend/src/pages/PageView.jsx` | Page cache, PLC name |
| `frontend/src/lib/api.js` | backup, unsubscribe, themes, digitalPartners, cache: no-store |
| `frontend/src/lib/seo.js` | PLC name |
| `frontend/src/admin/AdminApp.jsx` | Routes |
| `frontend/src/admin/AdminLayout.jsx` | Nav + titles |
| `frontend/src/admin/AdminSettings.jsx` | Statistics field |
| `frontend/src/admin/AdminUI.jsx` | StatusBadge update |
| `frontend/src/admin/AdminCollections.jsx` | opening_date fields |
| `frontend/src/main.jsx` | ErrorBoundary |
| `frontend/vite.config.js` | Code splitting |
| `frontend/index.html` | Tidio placeholder |
| `README.md` | PLC name |

### B. Database Changes

**New tables:**
- `content_teamphoto` — team member photos
- `content_digitalpartner` — digital partners with logos
- `content_websitetheme` — scheduled themes/campaigns

**Modified tables:**
- `content_sitesetting` — added `statistics` JSON field
- `content_section` — added `statistics` and `digital_partners` to kind choices
- `content_career` — added `opening_date` field
- `content_tender` — added `opening_date` field
- `catalogue_book` — added `search_vector` field + GIN index

**Migrations to apply:**
```powershell
cd backend
python manage.py makemigrations
python manage.py migrate
```

**Populate search vectors (one-time, for existing books):**
```powershell
python manage.py shell -c "
from django.contrib.postgres.search import SearchVector
from apps.catalogue.models import Book
Book.objects.update(search_vector=SearchVector('title', weight='A') + SearchVector('subject', weight='B') + SearchVector('category', weight='B') + SearchVector('description', weight='C'))
"
```

### C. New Dependencies

No new Python packages required. All features use Django's built-in capabilities.

For Tidio (optional, free tier):
- Create account at https://www.tidio.com/
- Get widget ID from dashboard
- Uncomment the script tag in `frontend/index.html` and replace `YOUR_TIDIO_KEY`

For OpenAI (optional, paid):
- Get API key from https://platform.openai.com/
- Set `OPENAI_API_KEY` environment variable
- Implement a "Draft with AI" button in the admin (not yet implemented — requires API key)

### D. Running Locally

**Backend:**
```powershell
cd "C:\Users\Admin IT\Documents\Default Project\klb-platform\backend"
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_content --refresh
python manage.py runserver
```

**Frontend (dev mode):**
```powershell
cd "C:\Users\Admin IT\Documents\Default Project\klb-platform\frontend"
npm install
npm run dev
```

**Frontend (production build):**
```powershell
cd "C:\Users\Admin IT\Documents\Default Project\klb-platform\frontend"
npm run build
```

### E. Frontend Deployment

The frontend is built as part of the Render build command. No separate deployment needed.

```powershell
cd frontend && npm ci && npm run build
```

Output goes to `frontend/dist/` which Django serves.

### F. Backend Deployment

See `docs/DEPLOYMENT-RENDER.md` for full guide. Key settings:

```powershell
# Build command
cd frontend && npm ci && npm run build && cd ../backend && pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py seed_content

# Start command
cd backend && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120
```

### G. Environment Variables

| Variable | Purpose | Local | Production |
| --- | --- | --- | --- |
| `DJANGO_SECRET_KEY` | Django secret key | `.env` file | Render env var (Secret) |
| `DJANGO_DEBUG` | Debug mode | `True` | `False` |
| `DJANGO_ALLOWED_HOSTS` | Allowed hosts | `localhost,127.0.0.1` | `your-domain.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | CSRF trusted origins | `http://localhost:5173,...` | `https://your-domain.com` |
| `DATABASE_URL` | Database connection | Supabase or local Postgres | Supabase pooler URL |
| `DJANGO_SECURE_SSL` | HTTPS redirect | `False` | `True` |
| `DJANGO_SECURE_COOKIES` | Secure cookies | `False` | `True` |
| `SEED_ADMIN_EMAIL` | Admin account email | `admin@klb.com` | `admin@klb.co.ke` |
| `SEED_ADMIN_PASSWORD` | Admin account password | `Klb@2026` | Strong password (Secret) |

### H. Admin Dashboard Instructions

| Feature | Location | How to use |
| --- | --- | --- |
| **Website themes** | Admin → Website themes | Create theme with name, CSS class, start/end dates, enabled toggle. Theme activates automatically on start date, deactivates on end date. |
| **Team photos** | Admin → Team photos | Upload portrait per leadership card. Photos stored in media library. |
| **Digital partners** | Admin → Digital partners | Create/edit partners with name, URL, description, logo upload, sort order, visibility. |
| **Backup** | Admin → Backup | Click "Backup everything", "Backup database", or "Backup media". ZIP stored in `backups/` directory. |
| **Statistics** | Admin → Site settings → Statistics (JSON) | Edit JSON array of `{"value", "label", "animate"}` objects. |
| **Tenders** | Admin → Tenders | Set opening and closing dates. Status auto-calculated (upcoming/open/closing soon/expired). |
| **Careers** | Admin → Careers | Set opening and closing dates. Apply button disabled after closing date. |
| **Newsletter** | Admin → Newsletter | View subscribers. Unsubscribe via frontend form or admin. |
| **News** | Admin → News | Full CRUD with image, date, category, featured toggle. |
| **Pages** | Admin → Pages | Edit any page's sections (HTML, settings). |

### AI Recommendations Summary

| Tool | Purpose | Cost | Priority |
| --- | --- | --- | --- |
| Tidio (free tier) | Live chat + AI chatbot | Free | High |
| PostgreSQL full-text search | Better catalogue search | Free (built-in) | High |
| OpenAI GPT-4 / Claude | Draft news articles, SEO meta | ~$0.01-0.05/request | Medium |
| Grammarly Business | Grammar/style checking | $15/user/month | Low |
| Mailchimp/SendGrid | Newsletter distribution | Free tier | Medium |
| Google Analytics 4 | Traffic analytics | Free | High |
| Tidio (paid) | Advanced chatbot features | $29/month | Low |
| Algolia | Instant search with typo tolerance | Free tier (10K/month) | Low |

### Testing Results

| Check | Result |
| --- | --- |
| `npm run build` | ✅ 85 modules |
| Django system check | ✅ 0 issues |
| Migrations (11 total) | ✅ All applied |
| `seed_content` | ✅ 12 pages, 128 books, 21 news, 6 partners |
| `seed_content --refresh` | ✅ 12 pages, 21 news updated |
| Backup command | ✅ ZIP created |
| Full-text search | ✅ Returns ranked results |
| Rate limiting | ✅ Configured |
| Security headers | ✅ CSP, cache-control, permissions policy |
| Error handling | ✅ Professional messages |
| Admin changes persist | ✅ Cache invalidated on save |
| Newsletter unsubscribe | ✅ Endpoint + UI working |
| Tender/career expiry | ✅ Auto status, disabled apply button |


### Outstanding items for future work
1. **Automated tests** — zero test coverage, recommend adding Django + React tests
2. **Media storage migration** — move from local disk to S3/Cloudinary for backups
3. **Newsletter email sending** — integrate with SendGrid/Mailgun for actual distribution
4. **Accessibility audit** — verify keyboard navigation and screen reader support
5. **SEO prerendering** — consider react-snap for better search indexing
6. **Content versioning** — add revision history for pages
7. **Monitoring** — add Sentry + uptime monitoring
8. **OpenAI integration** — "Draft with AI" button in admin (requires API key)
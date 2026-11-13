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
8. **OpenAI integration** — "Draft with AI" button in admin (requires API key)# #   I .   R e c e n t   W o r k   ( A c c e s s i b i l i t y ,   B a c k u p   H a r d e n i n g ,   S e t t i n g s ,   A c t i v i t y   E x p o r t s ) 
 
 # # #   N e w / m o d i f i e d   f i l e s 
 
 |   F i l e   |   P u r p o s e   | 
 |   - - -   |   - - -   | 
 |   ` f r o n t e n d / s r c / l i b / a c c e s s i b i l i t y . j s `   |   P r e f e r e n c e   m o d e l ,   n o r m a l i s a t i o n ,   p e r s i s t e n c e ,   C S S   c l a s s   a p p l i c a t i o n   | 
 |   ` f r o n t e n d / s r c / c o m p o n e n t s / A c c e s s i b i l i t y M e n u . j s x `   |   A c c e s s i b l e   a c c e s s i b i l i t y   d i a l o g   ( k e y b o a r d ,   f o c u s   t r a p ,   A R I A )   | 
 |   ` f r o n t e n d / s r c / s t y l e s / a c c e s s i b i l i t y . c s s `   |   A l l   a c c e s s i b i l i t y   o p t i o n   s t y l e s   | 
 |   ` f r o n t e n d / s r c / m a i n . j s x `   |   A p p l i e s   s a v e d   p r e f e r e n c e s   b e f o r e   f i r s t   r e n d e r   | 
 |   ` b a c k e n d / a p p s / c o n t e n t / m i g r a t i o n s / 0 0 1 3 _ u n i q u e _ b a c k u p _ f i l e n a m e s . p y `   |   D e d u p e s   a n d   u n i q u e l y   c o n s t r a i n s   b a c k u p   f i l e n a m e s   | 
 |   ` b a c k e n d / c o n f i g / t e s t _ s e t t i n g s . p y `   |   I s o l a t e d   S Q L i t e   s e t t i n g s   f o r   a u t o m a t e d   t e s t s   | 
 |   ` b a c k e n d / c o n f i g / d e v _ s e t t i n g s . p y `   |   L o c a l   P o s t g r e S Q L   s e t t i n g s   w i t h   S u p a b a s e   g u a r d   | 
 |   ` b a c k e n d / a p p s / c o n t e n t / t e s t s . p y `   |   3 0   b a c k u p / s e t t i n g s / t h e m e   A P I   t e s t s   | 
 |   ` b a c k e n d / a p p s / a c c o u n t s / t e s t s . p y `   |   P e r m i s s i o n ,   a c t i v i t y   e x p o r t   a n d   a c t o r   t e s t s   | 
 
 # # #   A c c e s s i b i l i t y 
 
 -   F l o a t i n g   " A c c e s s i b i l i t y "   t r i g g e r   ( b o t t o m - l e f t )   o p e n s   a   d i a l o g   w i t h   t e x t   s i z e ,   h i g h   c o n t r a s t ,   d a r k   d i s p l a y ,   d y s l e x i a - f r i e n d l y   t e x t ,   s p a c i n g ,   u n d e r l i n e   l i n k s ,   g r a y s c a l e ,   r e d u c e d   m o t i o n ,   a n d   r e s e t . 
 -   D a r k   d i s p l a y   a n d   h i g h   c o n t r a s t   a r e   m u t u a l l y   e x c l u s i v e . 
 -   P r e f e r e n c e s   p e r s i s t   i n   ` l o c a l S t o r a g e `   u n d e r   ` k l b - a c c e s s i b i l i t y - p r e f e r e n c e s `   a n d   a r e   a p p l i e d   a s   c l a s s e s   o n   ` < h t m l > `   b e f o r e   f i r s t   r e n d e r ,   s o   t h e r e   i s   n o   f l a s h . 
 -   T h r e e   s k i p   l i n k s   ( m a i n   c o n t e n t ,   n a v i g a t i o n ,   f o o t e r ) ,   ` s i t e F o o t e r `   i d ,   i m p r o v e d   f o c u s   r i n g s . 
 -   K e y b o a r d   a c c e s s i b l e :   f o c u s   t r a p ,   E s c a p e   c l o s e s   a n d   r e t u r n s   f o c u s   t o   t r i g g e r ,   T a b / S h i f t + T a b   c y c l e . 
 -   W C A G   2 . 2   A A   t a r g e t ;   r e s p o n s i v e . 
 
 # # #   B a c k u p   a n d   r e s t o r e 
 
 -   ` B a c k u p R e c o r d `   m o d e l   t r a c k s   e v e r y   a t t e m p t   ( s u c c e s s / f a i l e d )   w i t h   w h o ,   w h e n ,   t y p e ,   c o m p o n e n t s ,   s i z e ,   s t a t u s ,   s t o r a g e . 
 -   C r e a t e :   f u l l ,   d a t a b a s e - o n l y ,   m e d i a - o n l y ,   s e l e c t i v e   c o m p o n e n t s   ( r e a l   f l a g s ,   n o t   d e c o r a t i v e ) . 
 -   U p l o a d   v a l i d a t e s   z i p   a n d   c o n t e n t s ;   s a n i t i s e s   f i l e n a m e ;   s t o r e s   o u t s i d e   ` M E D I A _ R O O T `   i n   ` B A C K U P _ R O O T ` . 
 -   R e s t o r e   v a l i d a t e s   a r c h i v e   b e f o r e   t o u c h i n g   d a t a ,   c r e a t e s   a u t o m a t i c   s a f e t y   b a c k u p ,   a u d i t   l o g s ;   r e j e c t s   c o r r u p t / t r a v e r s a l / o v e r s i z e d   a r c h i v e s . 
 -   R e t e n t i o n   a p p l i e d   a f t e r   e a c h   s u c c e s s f u l   c r e a t e . 
 -   ` B A C K U P _ D I R `   e n v   o v e r r i d e s   s t o r a g e   l o c a t i o n   ( R e n d e r   p e r s i s t e n t   d i s k ) . 
 
 # # #   A c t i v i t y   l o g   e x p o r t s 
 
 -   F i l t e r s   b y   u s e r ,   m o d u l e ,   a c t i o n ,   d a t e   r a n g e ,   s e a r c h . 
 -   C S V ,   E x c e l   ( o p e n p y x l ) ,   P D F   ( r e p o r t l a b )   e x p o r t s   r e f l e c t   f i l t e r s . 
 -   E x p o r t s   a r e   t h e m s e l v e s   a u d i t - l o g g e d   ( ` E X P O R T `   a c t i o n ) . 
 -   F o r m u l a   i n j e c t i o n   g u a r d e d . 
 
 # # #   C e n t r a l   s e t t i n g s 
 
 -   ` / a d m i n / s e t t i n g s `   g r o u p e d   i n t o   9   s e c t i o n s   w i t h   a n c h o r   n a v i g a t i o n . 
 -   M a i n t e n a n c e   m o d e   i s   a   s o f t   p u b l i c   n o t i c e ;   a d m i n   s t a y s   a c c e s s i b l e . 
 -   ` b a c k u p _ r e t e n t i o n ` ,   ` m a i n t e n a n c e _ m o d e ` ,   ` m a i n t e n a n c e _ m e s s a g e `   p e r s i s t e d   a n d   v a l i d a t e d . 
 
 # # #   A u t o m a t e d   t e s t s 
 
 R u n   w i t h : 
 ` ` ` p o w e r s h e l l 
 c d   b a c k e n d 
 p y t h o n   m a n a g e . p y   t e s t   - - s e t t i n g s = c o n f i g . t e s t _ s e t t i n g s 
 ` ` ` 
 6 0   t e s t s   p a s s   ( c o n t e n t   +   a c c o u n t s ) .   T e s t s   u s e   i n - m e m o r y   S Q L i t e   a n d   t e m p   m e d i a / b a c k u p   d i r s ;   t h e y   n e v e r   t o u c h   S u p a b a s e / p r o d u c t i o n . 
 
 # # #   L o c a l   v e r i f i c a t i o n 
 
 ` ` ` p o w e r s h e l l 
 $ e n v : D A T A B A S E _ U R L   =   " p o s t g r e s : / / p o s t g r e s : 1 2 3 4 @ 1 2 7 . 0 . 0 . 1 : 5 4 3 2 / k l b _ v e r i f y " 
 p y t h o n   m a n a g e . p y   m i g r a t e   - - s e t t i n g s = c o n f i g . d e v _ s e t t i n g s 
 p y t h o n   m a n a g e . p y   s e e d _ c o n t e n t   - - s e t t i n g s = c o n f i g . d e v _ s e t t i n g s 
 p y t h o n   m a n a g e . p y   r u n s e r v e r   - - s e t t i n g s = c o n f i g . d e v _ s e t t i n g s 
 ` ` ` 
 ` c o n f i g . d e v _ s e t t i n g s `   r e f u s e s   t o   r u n   a g a i n s t   S u p a b a s e . 
 
 # # #   N e w   d e p e n d e n c i e s 
 
 -   ` o p e n p y x l = = 3 . 1 . 5 `   ( E x c e l   e x p o r t ) 
 -   ` r e p o r t l a b = = 4 . 5 . 1 `   ( P D F   e x p o r t ) 
 
 B o t h   a r e   i n   ` b a c k e n d / r e q u i r e m e n t s . t x t ` .  
 
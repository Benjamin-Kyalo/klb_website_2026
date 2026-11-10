# Deploying on Render.com

This guide deploys the **actual** KLB website stack:

| Part | Technology | Location |
| --- | --- | --- |
| Public site and dashboard | React 18 + Vite 6 | `frontend/` |
| API, authentication, SEO files | Django 5 + Django REST Framework | `backend/` |
| Database | PostgreSQL | `DATABASE_URL` |
| Static and uploaded files | WhiteNoise + Django media | `backend/staticfiles/`, `backend/media/` |

It replaces the older Node/Express/EJS deployment notes. The application is shipped as **one Render web service**:
Django serves the built React application, the API, the sitemap and the SPA fallback.

## 0. Before you start

Render builds from a Git repository. `klb-platform` is **not** a Git repository yet, so create one first:

```bash
cd "C:\Users\Admin IT\Documents\Default Project\klb-platform"
git init
git add .
git commit -m "Initial KLB platform commit"
```

Create an empty repository on GitHub, GitLab or Bitbucket and push it:

```bash
git remote add origin https://github.com/<your-account>/klb-platform.git
git branch -M main
git push -u origin main
```

Confirm that these files are committed and **not** ignored:

- `backend/.env.example`
- `backend/requirements.txt`
- `backend/seed/cms-seed.json`
- `backend/seed/books.json`
- `backend/media/.gitkeep`
- `frontend/package-lock.json`
- `frontend/vite.config.js`

Confirm that these are ignored (they must never be committed):

- `backend/.env`
- `backend/.venv/`
- `backend/staticfiles/`
- `backend/media/uploads/`
- `frontend/node_modules/`
- `frontend/dist/`

## 1. Choose a plan

| Use case | Render web service | Render Postgres | Persistent disk |
| --- | --- | --- | --- |
| Free testing | Free | Free | Not available |
| Production | Starter or higher | Basic-256MB or higher | Required for uploads |

Important Render limits that affect this project:

- Free web services spin down after 15 minutes of inactivity and have no Shell.
- Free Postgres databases expire 30 days after creation.
- Free web services have no persistent disk, so anything written to `backend/media/` (team photos, covers, PDFs uploaded through the dashboard) is lost on the next deploy or restart.
- Production needs a paid web service with a persistent disk mounted at `MEDIA_ROOT`.

## 2. Create the PostgreSQL database

1. In the Render dashboard, click **New +** -> **PostgreSQL**.
2. Use these values:

   | Field | Value |
   | --- | --- |
   | Name | `klb-postgres` |
   | Database | `klb` |
   | User | `klb_user` |
   | Region | the region closest to your users (for example Frankfurt or Oregon) |
   | Plan | `Free` for testing, `Basic-256MB` for production |
   | PostgreSQL version | `16` |

3. Click **Create Database**.
4. Open the database page and copy the **Internal Database URL**. It looks like:

   ```text
   postgres://klb_user:...@dpg-...-a.frankfurt-postgres.render.com/klb
   ```

   Use the **Internal** URL, not the External one. The web service and the database are in the same Render network.

## 3. Create the web service

1. Click **New +** -> **Web Service**.
2. Connect your Git repository and select the `klb-platform` repository.
3. Use these values:

   | Field | Value |
   | --- | --- |
   | Name | `klb-website` |
   | Region | the same region as the database |
   | Branch | `main` |
   | Root Directory | (leave empty) |
   | Runtime | `Python 3` |
   | Build Command | see below |
   | Start Command | see below |
   | Plan | `Free` for testing, `Starter` for production |

4. Build command (paste exactly):

   ```bash
   cd frontend && npm ci && npm run build && cd ../backend && pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py seed_content
   ```

5. Start command (paste exactly):

   ```bash
   cd backend && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120
   ```

6. Health check path:

   ```text
   /health/
   ```

7. Auto-Deploy: **Yes** (rebuilds on every push to `main`).

## 4. Environment variables

Add these in the web service's **Environment** tab before the first deploy. Mark secret values as **Secret**.

| Key | Value | Notes |
| --- | --- | --- |
| `PYTHON_VERSION` | `3.12.6` | Render uses this to select the Python runtime. |
| `NODE_VERSION` | `20.11.1` | Render uses this to select the Node runtime. |
| `DJANGO_SECRET_KEY` | a long random string | Generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"`. Mark as Secret. |
| `DJANGO_DEBUG` | `False` | |
| `DJANGO_ALLOWED_HOSTS` | `klb-website.onrender.com` | Add your custom domain later, comma-separated. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://klb-website.onrender.com` | Must include the scheme. Add the custom domain later. |
| `DJANGO_SECURE_SSL` | `True` | Enables HTTPS redirect and HSTS. |
| `DJANGO_SECURE_COOKIES` | `True` | Marks session and CSRF cookies as secure. |
| `DATABASE_URL` | the Internal Database URL from step 2 | Mark as Secret. |
| `SEED_ADMIN_EMAIL` | `admin@klb.co.ke` | Used only when the administrator account does not yet exist. |
| `SEED_ADMIN_PASSWORD` | a strong password | Mark as Secret. Change it after first sign-in. |
| `DJANGO_LOG_LEVEL` | `INFO` | |

Optional, useful on the Free plan:

| Key | Value | Notes |
| --- | --- | --- |
| `NODE_OPTIONS` | `--max-old-space-size=512` | Prevents Vite from running out of memory during the build. |

Notes about the seed command:

- `seed_content` is idempotent. It creates pages, books, news, careers, tenders, resources and the administrator account only when they are missing.
- On later deploys it will not overwrite content that an editor has changed.
- If you change `backend/seed/cms-seed.json` and want to push those copy changes to an already deployed database, run `python manage.py seed_content --refresh` from the Render Shell (paid plans only) or locally against the production database.
- `--reset` deletes content tables. Never run it against a production database.

## 5. Persistent disk for uploads (production only)

On a paid web service:

1. Open the web service -> **Disks** -> **Add Disk**.
2. Use these values:

   | Field | Value |
   | --- | --- |
   | Name | `klb-media` |
   | Mount Path | `/opt/render/project/src/backend/media` |
   | Size | `1 GB` (increase later if needed) |

3. Save and redeploy.

Why this path: Render checks out the repository at `/opt/render/project/src`, so `backend/media` is exactly `/opt/render/project/src/backend/media`, which is the value of `MEDIA_ROOT`. The `.gitkeep` file keeps the directory in Git so the mount point exists on the first deploy.

On the Free plan there is no disk. Uploads still work during a session but disappear on the next deploy or restart. Use the Free plan for testing only.

## 6. First deploy

1. Click **Create Web Service** (or **Manual Deploy** -> **Deploy latest commit**).
2. Watch the build log. A successful build ends with:

   ```text
   Seed complete:
     settings: Kenya Literature Bureau
     pages: 12
     books: 128
     news: 21
     careers: 1
     tenders: 9
     resources: 19
   ```

3. When the service shows **Live**, open:

   ```text
   https://klb-website.onrender.com/health/
   ```

   Expected response:

   ```json
   {"status":"ok","time":"...","date":"..."}
   ```

4. Open the public site:

   ```text
   https://klb-website.onrender.com/
   ```

## 7. First sign-in and security

1. Open:

   ```text
   https://klb-website.onrender.com/admin/login
   ```

2. Sign in with `SEED_ADMIN_EMAIL` and `SEED_ADMIN_PASSWORD`.
3. Immediately change the password under **Your account**.
4. Create or adjust staff accounts under **Users and permissions** and assign only the modules each person needs.
5. Upload a team photo under **Team photos** to confirm that media uploads and the persistent disk work:

   - Upload a portrait for one leadership card.
   - Open `/about/` and confirm the photo appears.
   - Redeploy the service and confirm the photo is still there. If it disappears, the disk is not mounted correctly.

## 8. Custom domain (optional)

1. In the web service, open **Settings** -> **Custom Domains** and add your domain, for example `www.kenyaliteraturebureau.co.ke`.
2. Follow Render's DNS instructions (a CNAME for `www`, an A record for the apex).
3. Wait for the certificate to be issued (usually a few minutes).
4. Update the environment variables:

   ```text
   DJANGO_ALLOWED_HOSTS=klb-website.onrender.com,www.kenyaliteraturebureau.co.ke
   DJANGO_CSRF_TRUSTED_ORIGINS=https://klb-website.onrender.com,https://www.kenyaliteraturebureau.co.ke
   ```

5. Redeploy.

## 9. Post-deploy verification checklist

- [ ] `https://<host>/health/` returns `{"status":"ok"}`.
- [ ] Home page renders and the announcement bar, navigation and footer appear.
- [ ] Footer no longer shows **Sitemap** or **Staff login**.
- [ ] `/books/` loads and filtering by collection, level and subject works.
- [ ] The header search opens, shows **Filter before searching**, and searches with filters only.
- [ ] `/about/` shows the 12 leadership cards and uploaded team photos.
- [ ] `/digital/` shows the aligned partner logo cards.
- [ ] News page has no **News archive** note and no **Contact media team** link.
- [ ] `/sitemap.xml` and `/robots.txt` return valid XML/text.
- [ ] A content image opens in the media lightbox and closes with `Esc`.
- [ ] Admin login works and the dashboard loads.
- [ ] Uploading a file through the dashboard returns a `/media/...` URL that opens.
- [ ] `https://<host>/admin/team-photos/` lists all 12 members.

## 10. Free vs. paid summary

| Capability | Free | Paid (Starter + disk + Basic Postgres) |
| --- | --- | --- |
| Web service always on | No (spins down) | Yes |
| Render Shell | No | Yes |
| Persistent media uploads | No | Yes |
| Postgres lifetime | 30 days | No expiry |
| Custom domain + TLS | Yes | Yes |
| Suitable for | Testing and demos | Production |

## 11. Troubleshooting

**Build fails at `npm ci`**
- Confirm `frontend/package-lock.json` is committed.
- If memory runs out, set `NODE_OPTIONS=--max-old-space-size=512`.

**Build fails at `collectstatic`**
- The most common cause is a missing static file referenced by CSS. Run `python manage.py collectstatic --noinput` locally first.
- Confirm `frontend/dist/` was created by the build before `collectstatic` runs. The build command order in step 3 already does this.

**`DisallowedHost` / 400 on every page**
- `DJANGO_ALLOWED_HOSTS` does not include the host you are using. Add it and redeploy.

**Admin login returns 403 or the page never loads**
- `DJANGO_CSRF_TRUSTED_ORIGINS` must include the full origin with scheme, for example `https://klb-website.onrender.com`.
- Cookies require HTTPS in production; confirm `DJANGO_SECURE_COOKIES=True` and that you are using `https://`.

**`/health/` returns 503**
- The database is unreachable. Confirm `DATABASE_URL` is the **Internal** URL and that the database is in the same region.
- Free Postgres databases pause; open the database page and confirm it is available.

**Uploaded images return 404 after a redeploy**
- The persistent disk is not mounted, or the mount path is wrong. It must be exactly `/opt/render/project/src/backend/media`.
- On the Free plan this is expected: there is no disk.

**Content changes from `cms-seed.json` do not appear**
- `seed_content` never overwrites existing rows. Use `python manage.py seed_content --refresh` to apply copy changes, or `--reset` only on a non-production database.

**The React app shows a blank page but `/health/` works**
- The frontend was not built. Check the build log for a Vite error and confirm `frontend/dist/index.html` exists after the build.

**Gunicorn times out on first request**
- Free services wake up slowly. Wait 30-60 seconds and retry, or upgrade to a paid plan.

## 12. Backups

- Render Postgres (paid plans) supports manual and scheduled backups from the database page. Enable at least daily backups for production.
- Media files on a persistent disk are **not** backed up by Render. Periodically copy `backend/media/` to object storage or download it through the Render Shell.
- Keep the Git repository as the source of truth for code and seed data. A database restore plus the repository is enough to rebuild the site.

## 13. Optional: one-click blueprint

Save this as `render.yaml` in the repository root if you want Render to create the service and database from a single file. Adjust names, regions and plans to taste.

```yaml
services:
  - type: web
    name: klb-website
    runtime: python
    plan: starter
    buildCommand: cd frontend && npm ci && npm run build && cd ../backend && pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py seed_content
    startCommand: cd backend && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120
    healthCheckPath: /health/
    envVars:
      - key: PYTHON_VERSION
        value: 3.12.6
      - key: NODE_VERSION
        value: 20.11.1
      - key: DJANGO_DEBUG
        value: "False"
      - key: DJANGO_SECURE_SSL
        value: "True"
      - key: DJANGO_SECURE_COOKIES
        value: "True"
      - key: DJANGO_SECRET_KEY
        generateValue: true
      - key: DJANGO_ALLOWED_HOSTS
        value: klb-website.onrender.com
      - key: DJANGO_CSRF_TRUSTED_ORIGINS
        value: https://klb-website.onrender.com
      - key: DATABASE_URL
        fromDatabase:
          name: klb-postgres
          property: connectionString
      - key: SEED_ADMIN_EMAIL
        value: admin@klb.co.ke
      - key: SEED_ADMIN_PASSWORD
        sync: false
      - key: DJANGO_LOG_LEVEL
        value: INFO
    disk:
      name: klb-media
      mountPath: /opt/render/project/src/backend/media
      sizeGB: 1
databases:
  - name: klb-postgres
    plan: basic-256mb
    postgresMajorVersion: 16
```

Render reads `render.yaml` only when you create the service from the **Blueprints** flow, not from a normal "New Web Service" form.

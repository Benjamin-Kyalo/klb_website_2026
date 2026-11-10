# Local setup

This guide takes a new Windows, macOS or Linux machine to a running KLB website.
The application uses PostgreSQL. It does not fall back to SQLite, so create a
database first.

## 1. Software to install

| Software | Minimum | Notes |
| --- | --- | --- |
| Python | 3.11 | 3.12 or 3.13 also work. Add Python to `PATH` on Windows. |
| Node.js | 20 | Includes npm. Node 22 LTS is a good choice. |
| PostgreSQL | 14 | 16 or newer is recommended. Install the server and pgAdmin. |
| Git | current | Optional, for version control. |

VS Code is a convenient editor. Install the Python and ESLint extensions if you
want inline checks.

## 2. Get the project

Unzip the package, or clone your repository, then open a terminal in the folder
that contains `backend/`, `frontend/` and `README.md`.

All commands below assume that folder is the current directory.

## 3. Create the database

The website needs one PostgreSQL user and one empty database. You do this once,
using the `postgres` superuser password chosen when PostgreSQL was installed.

### Windows - pgAdmin (graphical)

1. Open **pgAdmin 4** and connect to the local PostgreSQL server. Enter the
   `postgres` password if prompted.
2. Right-click **Login/Group Roles** > **Create** > **Login/Group Role**.
   - **General** tab: name `klb`.
   - **Definition** tab: password `klb_dev_password` (or your own).
   - **Privileges** tab: enable **Can login?**.
   - Save.
3. Right-click **Databases** > **Create** > **Database**.
   - **Database** name: `klb`.
   - **Owner**: `klb`.
   - Save.

### Windows - psql (command line)

Open **SQL Shell (psql)** from the Start menu, or run:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h 127.0.0.1 -p 5432
```

Enter the `postgres` password, then run:

```sql
CREATE USER klb WITH PASSWORD 'klb_dev_password';
CREATE DATABASE klb OWNER klb;
\q
```

`klb_dev_password` is a local example. If you choose another password, use the
same password in `DATABASE_URL`. Never reuse a local password in production.

### macOS or Linux

```bash
# macOS (Homebrew)
psql -U postgres

# Ubuntu/Debian
sudo -u postgres psql
```

Then run the same `CREATE USER` and `CREATE DATABASE` statements above, and quit
with `\q`.

### Test the connection

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" "postgres://klb:klb_dev_password@127.0.0.1:5432/klb" -c "select 1;"
```

A result of `1` means the user, database and password are correct. On macOS or
Linux use `psql "postgres://..." -c "select 1;"`.

### Managed PostgreSQL

If you use HostAfrica or another managed PostgreSQL service, create the database
in the hosting control panel and use the connection details supplied by the host.
Add `?sslmode=require` if the provider requires TLS.

## 4. Configure the backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

On macOS or Linux:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env`:

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Long random string. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(50))"`. |
| `DJANGO_DEBUG` | `True` locally, `False` in production. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated host names, for example `localhost,127.0.0.1`. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated full origins, including scheme, for example `http://localhost:5173,http://127.0.0.1:8000`. |
| `DATABASE_URL` | PostgreSQL connection string. The example uses `postgres://klb:klb_dev_password@127.0.0.1:5432/klb`; change the password if you used another one. |
| `SEED_ADMIN_EMAIL` | Email for the first administrator account. |
| `SEED_ADMIN_PASSWORD` | Password for that account. At least 10 characters. |
| `SEED_ADMIN_NAME` | Display name for the account. |
| `DJANGO_SECURE_SSL` | `True` behind HTTPS in production. |
| `DJANGO_SECURE_COOKIES` | `True` behind HTTPS in production. |

`backend/.env` is ignored by Git and must not be included in a public archive.

## 5. Create the tables and seed content

```powershell
python manage.py migrate
python manage.py seed_content
```

The seed command is safe to run again: it creates missing records and leaves
existing records alone. It never deletes administrator accounts.

If you need to replace pages, catalogue records and site settings with the
supplied content, run:

```powershell
python manage.py seed_content --reset
```

`--reset` is destructive for content. It is not part of a normal deployment.

## 6. Install the frontend

Return to the project root:

```powershell
cd ..\frontend
npm install
```

## 7. Run the development servers

Terminal 1, backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py runserver 127.0.0.1:8000
```

Terminal 2, frontend:

```powershell
cd frontend
npm run dev
```

Open:

- Public site: <http://localhost:5173>
- Staff dashboard: <http://localhost:5173/admin>

Vite proxies `/api`, `/media`, `/sitemap.xml`, `/robots.txt` and `/health` to
Django, so the browser sees one origin during development.

Sign in with the `SEED_ADMIN_EMAIL` and `SEED_ADMIN_PASSWORD` values from
`backend/.env`, then change the password under **Your account**.

## 8. Build and preview the production bundle

Django serves the built React files, so you can test the real deployment shape
on one port:

```powershell
cd frontend
npm run build
cd ..\backend
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Open <http://127.0.0.1:8000>.

The `runserver` command is for local checks only. Use Gunicorn behind nginx in
production; see [DEPLOYMENT-HOSTAFRICA.md](DEPLOYMENT-HOSTAFRICA.md).

## Useful commands

Run these from `backend/` with the virtual environment active:

| Command | Purpose |
| --- | --- |
| `python manage.py check` | Check Django configuration. |
| `python manage.py check --deploy` | Review production security hints. |
| `python manage.py makemigrations` | Create migrations after model changes. |
| `python manage.py migrate` | Apply migrations. |
| `python manage.py seed_content` | Add missing seeded content. |
| `python manage.py collectstatic --noinput` | Collect Django static files. |
| `python manage.py createsuperuser` | Create another staff account. Django's built-in admin is not mounted, so use the custom dashboard or create an editor in **Users**. |
| `python manage.py shell` | Open a Django shell. |

Frontend commands, from `frontend/`:

| Command | Purpose |
| --- | --- |
| `npm run dev` | Development server with hot reload. |
| `npm run build` | Production build in `frontend/dist`. |
| `npm run preview` | Preview the built files on a local port. |
| `npm run lint` | Lint JavaScript and JSX. |

## Optional frontend environment

Create `frontend/.env` only when you need to override defaults:

| Variable | Default | Purpose |
| --- | --- | --- |
| `VITE_API_BASE` | `/api` | API base path or absolute URL. |
| `VITE_SITE_URL` | `https://klb.co.ke` | Absolute site URL used in canonical links and social metadata. |

Rebuild after changing a `VITE_*` value; Vite embeds these values at build time.

## Checklist before handing the site over

- [ ] `backend/.env` has a unique secret key and a strong administrator password.
- [ ] The seeded administrator password has been changed.
- [ ] The site is served over HTTPS.
- [ ] `DJANGO_DEBUG=False`, `DJANGO_SECURE_SSL=True`, `DJANGO_SECURE_COOKIES=True`.
- [ ] `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` list the real domain.
- [ ] A PostgreSQL backup schedule exists.
- [ ] `backend/media/` is backed up and served by nginx.
- [ ] `npm run build` and `python manage.py collectstatic --noinput` were rerun after the last frontend change.

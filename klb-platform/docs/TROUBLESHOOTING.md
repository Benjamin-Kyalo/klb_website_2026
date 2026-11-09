# Troubleshooting

## First checks

From `backend/` with the virtual environment active:

```powershell
.\.venv\Scripts\python.exe manage.py check
```

From the project root, check that PostgreSQL is running:

```powershell
Get-Service postgresql*
& "C:\Program Files\PostgreSQL\18\bin\pg_isready.exe" -h 127.0.0.1 -p 5432
```

Check the API directly:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/
Invoke-RestMethod http://127.0.0.1:8000/api/site/
```

## Setup problems

### `python` or `npm` is not recognised

Install Python 3.11+ and Node.js 20+ and reopen the terminal. On Windows, ensure
the Python installer option **Add Python to PATH** was enabled. Check:

```powershell
python --version
node --version
npm --version
```

### PowerShell blocks the virtual environment

If `Activate.ps1` is blocked, allow local scripts for your account:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Or call the interpreter directly without activating:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

### `pip install` fails on `psycopg`

Use the binary wheel included in `requirements.txt`:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If the wheel is unavailable for your Python version, install PostgreSQL client
libraries or use a supported Python release.

## Database problems

### `connection refused` on port 5432

PostgreSQL is not running, or it is listening on another port. Start the Windows
service (name may differ, for example `postgresql-x64-18`):

```powershell
Get-Service postgresql*
Start-Service postgresql-x64-18
```

Check it accepts connections:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\pg_isready.exe" -h 127.0.0.1 -p 5432
```

If the server runs on a different port, change the port in `DATABASE_URL` in
`backend/.env`.

### `password authentication failed for user "klb"`

The password in `DATABASE_URL` is wrong, or the `klb` user has not been created
yet. Test the exact string with `psql`:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" "postgres://klb:klb_dev_password@127.0.0.1:5432/klb" -c "select 1;"
```

If the role does not exist, connect as the `postgres` superuser and create it
(see [SETUP.md](SETUP.md#3-create-the-database)):

```sql
CREATE USER klb WITH PASSWORD 'klb_dev_password';
CREATE DATABASE klb OWNER klb;
```

`klb_dev_password` is only an example local password.

### `relation "..." does not exist`

Migrations are missing:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

### Start over with the local database

The fastest option keeps the database and clears its data, then reseeds:

```powershell
.\.venv\Scripts\python.exe manage.py flush --noinput
.\.venv\Scripts\python.exe manage.py seed_content
```

`flush` deletes every record, including staff accounts. The seed recreates the
administrator from the `SEED_ADMIN_*` values in `backend/.env`.

To recreate the database itself, stop Django, then connect as the `postgres`
superuser:

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h 127.0.0.1 -p 5432
```

```sql
DROP DATABASE klb;
CREATE DATABASE klb OWNER klb;
\q
```

Then apply migrations and seed again:

```powershell
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_content
```

Both options delete local data. Only do this when you are sure.

## Backend problems

### The development server does not pick up changes

The project is often run with `--noreload`. Stop the process and start it again.
On Windows, find and stop leftover servers:

```powershell
Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -like '*manage.py runserver*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

### `That port is already in use`

Choose another port, or stop the process holding 8000:

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen
```

If you change the backend port, update the Vite proxy in
`frontend/vite.config.js`.

### CSRF verification failed

- Confirm the frontend origin is listed in `DJANGO_CSRF_TRUSTED_ORIGINS` with the
  full scheme, for example `http://localhost:5173`.
- Clear cookies for the site and reload.
- Behind nginx, confirm `X-Forwarded-Proto` is sent and that HTTPS is configured.
- Do not set `DJANGO_SECURE_COOKIES=True` while testing over plain HTTP.

### CORS or cross-origin errors

In development, use the Vite URL (`http://localhost:5173`) rather than opening the
frontend from a `file://` path. In production, serve the SPA from the same domain
as the API. The project does not enable permissive CORS because it does not need
it.

### Admin sign-in fails

- Confirm the account exists in **Users**.
- The seeded account is only created when `SEED_ADMIN_*` values were present when
  `seed_content` ran.
- Create or reset an account from the dashboard, or use the Django shell:

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from apps.accounts.models import User; u=User.objects.get(email='admin@example.com'); u.set_password('new-password-at-least-10'); u.save(); print('updated')"
```

Never put a real password in documentation or source control.

### Uploads fail

- Allowed extensions: JPG, JPEG, PNG, WebP, GIF and PDF.
- Maximum size: 8 MB.
- The request must be multipart form data with the field name `file`.
- In production, `backend/media/` must be writable by the service account.

## Frontend problems

### Blank page after a build

Check the browser console and the Django server log. Common causes:

- `frontend/dist` is missing; run `npm run build` from `frontend/`.
- The browser cached an old asset name; hard-refresh.
- A JavaScript error; run `npm run build` again and read the terminal output.

### Styles look wrong in the dashboard

The dashboard stylesheet is scoped to `body.admin-body`. Keep that class on the
body while the dashboard is mounted. Do not import the dashboard CSS into public
components.

### Catalogue filters do not work

- Confirm `/api/catalogue/filters/` returns JSON.
- Check the network tab for the `/api/books/` request and its query string.
- Filter values are case-sensitive at the API level and are sent from the
  supplied filter definitions.

### Images return the HTML page instead of an image

A missing asset falls through to the SPA shell, so the response is HTML. Confirm
the file exists under `frontend/public/assets` or `backend/media`. Rebuild the
frontend after adding files to `public/assets`.

### Old content after saving in the dashboard

Global settings and pages reload through the API. If a change does not appear,
refresh once. If the production site still shows old JavaScript, rebuild the
frontend, rerun `collectstatic`, and reload nginx.

## SEO problems

### Sitemap shows `127.0.0.1` or the wrong domain

The sitemap uses the incoming request host. In production, make sure nginx sends
the real `Host` header and that the public host is the one users visit.

### Page source has default metadata

The app is a client-rendered single-page application. Django serves default
metadata in the shell, then React updates it after the page loads. This is a
known limitation described in [ARCHITECTURE.md](ARCHITECTURE.md). Use a crawler
that executes JavaScript, or implement server-side rendering if source-level
metadata is mandatory.

### Missing pages return HTTP 200

This is the soft-404 limitation. The browser shows the 404 page and sets
`noindex, follow`. See [ARCHITECTURE.md](ARCHITECTURE.md) for options.

## Deployment problems

See the troubleshooting table in
[DEPLOYMENT-HOSTAFRICA.md](DEPLOYMENT-HOSTAFRICA.md#13-troubleshooting-the-deployment).

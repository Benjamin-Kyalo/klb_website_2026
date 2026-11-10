# Run locally without Docker

This guide assumes PostgreSQL is already installed on the computer. The project
does not use Docker and does not fall back to SQLite.

## 1. What to install

| Software | Minimum | Check |
| --- | --- | --- |
| Python | 3.11 | `python --version` |
| Node.js | 20 | `node --version` |
| PostgreSQL | 14 (16+ recommended) | `Get-Service postgresql*` |

The PostgreSQL Windows installer also installs psql and pgAdmin. Keep the
`postgres` superuser password you chose during installation.

## 2. Create the database once

Open **SQL Shell (psql)** or pgAdmin and connect as the `postgres` superuser.
Then create a user and a database:

```sql
CREATE USER klb WITH PASSWORD 'klb_dev_password';
CREATE DATABASE klb OWNER klb;
```

`klb_dev_password` is only an example local password. If you use another
password, use the same one in `backend/.env`.

Confirm the server is running and the database exists:

```powershell
Get-Service postgresql*
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" "postgres://klb:klb_dev_password@127.0.0.1:5432/klb" -c "select 1;"
```

A result of `1` means the user, password, database and port are correct. Change
`18` in the path if you installed another PostgreSQL version.

If you prefer to use the existing `postgres` superuser, that also works:

```text
DATABASE_URL=postgres://postgres:YOUR_POSTGRES_PASSWORD@127.0.0.1:5432/klb
```

## 3. Configure `backend/.env`

From the project root:

```powershell
Copy-Item backend\.env.example backend\.env
notepad backend\.env
```

Set at least these values:

```dotenv
DJANGO_SECRET_KEY=replace-with-a-long-random-string
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000
DATABASE_URL=postgres://klb:klb_dev_password@127.0.0.1:5432/klb
SEED_ADMIN_EMAIL=your-admin@example.com
SEED_ADMIN_PASSWORD=choose-a-strong-password
SEED_ADMIN_NAME=KLB Administrator
```

`backend/.env` is ignored by Git and must never be added to the ZIP or a
repository.

## 4. Install dependencies and seed the database

```powershell
cd "C:\Users\Admin IT\Documents\Default Project\klb-platform"
.\scripts\setup-windows.ps1
```

The script creates `backend/.venv`, installs the Python and Node packages,
checks the PostgreSQL connection, runs migrations and seeds the content. On
macOS or Linux use `./scripts/setup-unix.sh`.

For a manual install:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_content
cd ..\frontend
npm install
```

## 5. Start both servers

Use two PowerShell terminals in the project root.

Terminal 1 - Django API on port 8000:

```powershell
.\scripts\dev-backend.ps1
```

Terminal 2 - React site on port 5173:

```powershell
.\scripts\dev-frontend.ps1
```

Open <http://localhost:5173>. The dashboard is at
<http://localhost:5173/admin>.

## How the frontend and backend communicate

```text
Browser
  |
  |  http://localhost:5173
  v
Vite development server  --- /api, /media, /sitemap.xml, /robots.txt, /health --->  Django + DRF
                                                                                     |
                                                                                     v
                                                                              PostgreSQL 5432
```

- The browser only talks to port `5173`. This keeps cookies and CSRF on one
  origin.
- Vite forwards requests that start with `/api`, `/media`, `/sitemap.xml`,
  `/robots.txt` or `/health` to `http://127.0.0.1:8000`.
- Django handles the API, authentication, uploads, SEO files and the database.
- React never connects to PostgreSQL directly.
- In production there is no Vite server: `npm run build` creates
  `frontend/dist`, and Django serves that build and the API from one origin.

The proxy is configured in `frontend/vite.config.js`. The API routes are in
`backend/config/urls.py`.

## 6. Test the configuration

Run these checks in order. Stop at the first failure; the troubleshooting
section below explains what to fix.

### Check 1 - PostgreSQL is running

```powershell
Get-Service postgresql*
& "C:\Program Files\PostgreSQL\18\bin\pg_isready.exe" -h 127.0.0.1 -p 5432
```

Expected: the service is `Running` and pg_isready prints
`127.0.0.1:5432 - accepting connections`.

### Check 2 - Django is running

With the backend terminal open:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/
```

Expected:

```text
status time                     date
------ ----                     ----
ok     2026-11-05T09:01:28...  2026-11-05
```

### Check 3 - Django can read the database

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/site/
Invoke-RestMethod "http://127.0.0.1:8000/api/books/?page_size=2"
Invoke-RestMethod http://127.0.0.1:8000/api/pages/home/
```

Expected: the site name, a `count` of `128` books, and a page object with a
`sections` list. A `500` error here usually means the database is empty or
migrations were not run.

### Check 4 - the Vite proxy reaches Django

Use the frontend address instead of the backend address:

```powershell
Invoke-RestMethod http://127.0.0.1:5173/api/site/
Invoke-RestMethod "http://127.0.0.1:5173/api/books/?page_size=2"
Invoke-RestMethod http://127.0.0.1:5173/health/
```

Expected: the same data as Check 3. This proves the browser path works. If Check
3 works but Check 4 fails, Django is fine and only the proxy or the Vite server
is wrong.

### Check 5 - sign in through the proxy

In a browser, open <http://localhost:5173/admin> and sign in with
`SEED_ADMIN_EMAIL` and `SEED_ADMIN_PASSWORD` from `backend/.env`. The dashboard
should load the catalogue.

To test the same login from PowerShell, replace the two values in the snippet:

```powershell
$base = 'http://127.0.0.1:5173'
$email = 'your-admin@example.com'
$password = 'the-password-from-backend-env'

$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
$csrf = (Invoke-RestMethod "$base/api/auth/csrf/" -WebSession $session).csrfToken
$headers = @{ 'X-CSRFToken' = $csrf; 'Referer' = "$base/admin" }
$body = @{ email = $email; password = $password } | ConvertTo-Json

$login = Invoke-RestMethod "$base/api/auth/login/" -Method Post `
    -WebSession $session -Headers $headers `
    -ContentType 'application/json' -Body $body
$login.user.email

$me = Invoke-RestMethod "$base/api/auth/me/" -WebSession $session
$me.user.email

Invoke-RestMethod "$base/api/admin/books/?page_size=1" -WebSession $session
```

Expected: your e-mail twice, then `count: 128`. A `400` means the e-mail or
password is wrong. A `403` with "CSRF verification failed" means the CSRF token
or `Referer` header is missing.

### Check 6 - production build

```powershell
cd frontend
npm run build
cd ..\backend
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Open <http://127.0.0.1:8000>. One server now serves the React build, the API,
the sitemap and uploaded files.

## Common failures

| Symptom | Cause | Fix |
| --- | --- | --- |
| `connection refused` on port 5432 | PostgreSQL is stopped or on another port | Start the service and check `DATABASE_URL` |
| `password authentication failed` | Wrong password or user | Test the exact URL with `psql` |
| `relation "content_page" does not exist` | Migrations not applied | `manage.py migrate` |
| `EADDRINUSE` on 8000 or 5173 | An old server is still running | Close it, or stop the process on that port |
| Page loads but API calls fail | Django is not running, or the proxy target changed | Start Django and check `vite.config.js` |
| `403 CSRF verification failed` | Wrong origin or missing token | Check `DJANGO_CSRF_TRUSTED_ORIGINS` and reload the page |
| Login says "email or password is incorrect" | Seed used different values | Reseed, or reset the password in the Django shell |
| Dashboard is empty | The API returned an error | Open DevTools > Network and inspect the failed request |

To find a process holding a port:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 8000,5173 |
    Select-Object LocalPort, OwningProcess
Get-Process -Id <OwningProcess>
```

To reset local content completely, see
[TROUBLESHOOTING.md](TROUBLESHOOTING.md#start-over-with-the-local-database).

# Deploying on HostAfrica

This guide targets a HostAfrica **VPS** running Ubuntu 24.04 LTS with SSH access.
The application needs Python 3.11+, PostgreSQL, Node.js for the frontend build,
and the ability to run a long-lived Gunicorn process behind nginx. Those
requirements are not available on every shared-hosting plan. Confirm the
features of the plan you order with HostAfrica; if the plan only supports PHP,
choose a VPS or a Python-capable managed platform instead.

The example domain `klb.example` stands for your real domain. Replace it
everywhere. DNS, TLS, firewall and backup settings must be configured on your
account; this document does not assume they already exist.

## 1. Server packages

Sign in over SSH as a user with sudo rights:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip postgresql postgresql-contrib \
  nginx git curl ufw certbot python3-certbot-nginx
```

Check the versions:

```bash
python3 --version
psql --version
nginx -v
```

If the distribution Python is older than 3.11, install a newer Python from the
distribution's supported repositories before continuing.

## 2. Create the database

```bash
sudo -u postgres psql
```

Inside `psql`, using a strong password of your own:

```sql
CREATE USER klb_user WITH PASSWORD 'replace-with-a-long-random-password';
CREATE DATABASE klb_prod OWNER klb_user;
ALTER ROLE klb_user SET client_encoding TO 'utf8';
ALTER ROLE klb_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE klb_user SET timezone TO 'Africa/Nairobi';
\q
```

Test the login:

```bash
psql "postgres://klb_user:replace-with-a-long-random-password@127.0.0.1:5432/klb_prod" -c "select 1;"
```

Keep PostgreSQL listening on localhost only unless you have a specific reason to
expose it. The application and the database run on the same VPS in this setup.

## 3. Put the code on the server

Create an application directory owned by the deployment user:

```bash
sudo mkdir -p /var/www/klb-platform
sudo chown "$USER":"$USER" /var/www/klb-platform
```

Upload the project (rsync, SFTP or Git). The final server layout should contain:

```text
/var/www/klb-platform/
  backend/
  frontend/
  docs/
  scripts/
  README.md
```

Do **not** upload `backend/.env`, `backend/.venv`, `frontend/node_modules`,
`backend/staticfiles`, `backend/media`, local database dumps or QA test data.

You can build the frontend on your own computer and upload `frontend/dist`, or
install Node.js on the server and build there. Building locally is simpler and
avoids running Node in production:

```powershell
cd frontend
npm ci
npm run build
```

Then upload the `frontend/dist` folder with the rest of the project.

## 4. Backend environment

```bash
cd /var/www/klb-platform/backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
nano .env
```

Set production values:

```dotenv
DJANGO_SECRET_KEY=replace-with-a-long-random-string
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=klb.example,www.klb.example
DJANGO_CSRF_TRUSTED_ORIGINS=https://klb.example,https://www.klb.example

DATABASE_URL=postgres://klb_user:replace-with-a-long-random-password@127.0.0.1:5432/klb_prod

SEED_ADMIN_EMAIL=replace-with-the-real-administrator-email
SEED_ADMIN_PASSWORD=replace-with-a-strong-password
SEED_ADMIN_NAME=KLB Administrator

DJANGO_SECURE_SSL=True
DJANGO_SECURE_COOKIES=True
```

Generate the secret key on the server:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Rules:

- `DJANGO_ALLOWED_HOSTS` contains host names only, without `https://`.
- `DJANGO_CSRF_TRUSTED_ORIGINS` contains full origins, including `https://`.
- If you use `www` and the bare domain, list both.
- Protect the file: `chmod 600 .env`.

## 5. Database tables, content and static files

```bash
source .venv/bin/activate
python manage.py migrate
python manage.py seed_content
python manage.py collectstatic --noinput
python manage.py check --deploy
```

`seed_content` is safe to rerun. On a brand-new database it creates the pages,
128 books, news, tenders, careers, resources and the first administrator from
the `SEED_ADMIN_*` values.

Create the media directory if it does not exist:

```bash
mkdir -p media
```

The `check --deploy` output may still mention items that do not apply, such as
HSTS preload policy. Review every warning rather than ignoring it.

### Frontend build URL

The canonical URL and social metadata come from `VITE_SITE_URL` at build time.
Create `frontend/.env.production` before building:

```dotenv
VITE_SITE_URL=https://klb.example
```

Then rebuild:

```bash
cd /var/www/klb-platform/frontend
npm ci
npm run build
```

If you built on another machine, set the same value there before building.

## 6. Run Gunicorn with systemd

Create `/etc/systemd/system/klb.service`:

```ini
[Unit]
Description=KLB website (Gunicorn)
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/klb-platform/backend
EnvironmentFile=/var/www/klb-platform/backend/.env
ExecStart=/var/www/klb-platform/backend/.venv/bin/gunicorn \
    config.wsgi:application \
    --bind 127.0.0.1:8001 \
    --workers 3 \
    --timeout 60 \
    --access-logfile - \
    --error-logfile -
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Give the service account access to the files it needs:

```bash
sudo chown -R www-data:www-data /var/www/klb-platform/backend/media
sudo chown -R www-data:www-data /var/www/klb-platform/backend/staticfiles
sudo chmod 600 /var/www/klb-platform/backend/.env
sudo chown root:www-data /var/www/klb-platform/backend/.env
```

The code itself can stay read-only for `www-data`; only `media/` must be writable.
If uploads fail, check the ownership of `media/` and the service logs.

Start and check the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now klb
sudo systemctl status klb
sudo journalctl -u klb -n 50 --no-pager
```

Test locally on the server:

```bash
curl -I http://127.0.0.1:8001/
curl -s http://127.0.0.1:8001/health/
```

## 7. nginx

Create `/etc/nginx/sites-available/klb`:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name klb.example www.klb.example;

    client_max_body_size 10m;

    location /static/ {
        alias /var/www/klb-platform/backend/staticfiles/;
        access_log off;
        expires 30d;
        add_header Cache-Control "public";
    }

    location /media/ {
        alias /var/www/klb-platform/backend/media/;
        access_log off;
        expires 7d;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }
}
```

Enable it and test:

```bash
sudo ln -s /etc/nginx/sites-available/klb /etc/nginx/sites-enabled/klb
sudo nginx -t
sudo systemctl reload nginx
```

Disable the default site if it conflicts:

```bash
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx
```

The Django settings already trust `X-Forwarded-Proto` when `DJANGO_DEBUG=False`,
so HTTPS is detected correctly behind this proxy.

## 8. HTTPS

Only run this after the domain resolves to the server and port 80 is reachable:

```bash
sudo certbot --nginx -d klb.example -d www.klb.example
```

Certbot edits the nginx configuration and installs a renewal timer. Test renewal:

```bash
sudo certbot renew --dry-run
```

After HTTPS works, confirm that `http://` redirects to `https://`, that sign-in
works, and that the browser does not report mixed content.

## 9. Firewall and basic hardening

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

If you use a HostAfrica firewall or security group, allow SSH, HTTP and HTTPS
there as well. Do not open PostgreSQL port 5432 to the internet.

Disable password SSH login only after you have confirmed key-based login works.

## 10. First sign-in and handover

1. Open `https://klb.example/admin`.
2. Sign in with `SEED_ADMIN_EMAIL` and `SEED_ADMIN_PASSWORD`.
3. Change the password under **Your account**.
4. Create editor accounts under **Users** if staff should manage content without
   access to settings or user administration.
5. Add a real book or page, publish it, and check it on the public site.
6. Submit the contact form and confirm the enquiry appears under **Enquiries**.
7. Subscribe to the newsletter and confirm the address appears under
   **Newsletter**.
8. Check `https://klb.example/sitemap.xml` and `https://klb.example/robots.txt`.

Delete any QA or test records before handover.

## 11. Backups

Back up both the database and the uploads.

Database:

```bash
pg_dump "postgres://klb_user:PASSWORD@127.0.0.1:5432/klb_prod" \
  --format=custom --file="/var/backups/klb-$(date +%F).dump"
```

Uploads:

```bash
tar -czf "/var/backups/klb-media-$(date +%F).tar.gz" \
  -C /var/www/klb-platform/backend media
```

Store copies off the server and test a restore occasionally. A backup that has
never been restored is only a hope.

Restore example into an empty database:

```bash
pg_restore --clean --no-owner --dbname="postgres://klb_user:PASSWORD@127.0.0.1:5432/klb_prod" \
  /var/backups/klb-2026-01-01.dump
```

## 12. Updating the site

```bash
cd /var/www/klb-platform
# upload or pull the new code first
source backend/.venv/bin/activate
pip install -r backend/requirements.txt
python backend/manage.py migrate
python backend/manage.py collectstatic --noinput
cd frontend && npm ci && npm run build && cd ..
sudo systemctl restart klb
sudo systemctl reload nginx
```

If migrations are not part of the release, do not run them. Take a database
backup before any release that changes models.

## 13. Troubleshooting the deployment

| Symptom | Check |
| --- | --- |
| `502 Bad Gateway` | `sudo systemctl status klb` and `sudo journalctl -u klb -n 100`. Gunicorn is probably not running or the port is wrong. |
| `DisallowedHost` | Add the exact host name to `DJANGO_ALLOWED_HOSTS` and restart the service. |
| CSRF error when signing in or saving | Add the full `https://` origin to `DJANGO_CSRF_TRUSTED_ORIGINS`; make sure nginx sends `X-Forwarded-Proto`. |
| Sign-in appears to succeed but the session is lost | Confirm `DJANGO_SECURE_COOKIES=True` only when the site is actually served over HTTPS, and that the domain matches. |
| Uploads return 500 or 403 | Check ownership and permissions on `backend/media/`. |
| Static CSS or JavaScript missing | Run `collectstatic`; check the nginx `/static/` alias and `backend/staticfiles/`. |
| Old page content after a deploy | Rebuild the frontend, rerun `collectstatic`, then hard-refresh. Vite asset names change on each build. |
| `relation ... does not exist` | Run `python manage.py migrate`. |
| Database connection refused | Check PostgreSQL is running, the port and password in `DATABASE_URL`, and `pg_hba.conf`. |
| Sitemap shows the wrong domain | The sitemap uses the request host. Make sure nginx forwards `Host` and that the canonical public host is used. |

## 14. What this guide does not claim

This document does not assert that DNS, mail, backups or TLS are already set up
on any HostAfrica account. Those are steps you perform in the HostAfrica control
panel and on the server. The KLB contact addresses and social links shown on the
site are content that staff can edit in **Site settings**, not deployment
settings.

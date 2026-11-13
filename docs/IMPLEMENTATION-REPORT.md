# KLB Website — Final Implementation Report

Date: 2026-11-13

## Summary

This report covers the work completed in this round: fixing the themes API 400 error,
hardening backup/restore, fixing the media backup encoding bug, adding activity log
exports, centralising admin settings, implementing the accessibility menu, and
adding automated tests and documentation.

## Fixes

- Themes API 400 "This field may not be blank." — WebsiteThemeSerializer now accepts a
  blank slug and the model generates one from the name; duplicate slugs return a clear
  field-level error.
- Media backup "cannot access local variable 'db_url'" — db_url is read once at the top
  of handle() so media-only backups no longer reference an unbound variable.
- Half-finished archives — archives are written to a .part file and atomically renamed.
- Empty components silently became a full backup — the API now requires at least one
  component.
- Restore could overwrite with a corrupt archive — restore validates the zip, entry
  count and uncompressed size before touching data, and creates an automatic safety
  backup first.
- Duplicate history rows — _sync_disk_records uses get_or_create plus a unique filename
  constraint. Migration 0013 dedupes existing rows.
- DRF format query override 404 — URL_FORMAT_OVERRIDE is None so the activity export
  endpoint can use ?format=csv|xlsx|pdf.
- Windows encoding — dumpdata is captured to a text buffer and written as UTF-8.

## Features added

- Backup and restore management at /admin/backup: full, database-only, media-only and
  selective component creation; history with who/when/type/components/size/status/
  storage/actions; search, type and status filters; download, upload with validation,
  restore with safeguards, delete, retention.
- Activity log exports at /admin/activity: filters by user, module, action, date range
  and search; CSV, Excel and PDF exports reflecting the filters; exports are
  audit-logged.
- Central admin settings at /admin/settings: 9 grouped sections with anchor navigation;
  maintenance mode soft notice; backup retention; validated and permission-controlled.
- Accessibility menu: floating trigger, dialog with text size, contrast, dark display,
  dyslexia font, spacing, underline links, grayscale, reduced motion and reset;
  persisted preferences; keyboard accessible with focus trap.

## Storage

- Backups live outside MEDIA_ROOT. BACKUP_ROOT comes from BACKUP_DIR (default
  BASE_DIR/backups).
- On Render, one disk is mounted at /opt/render/project/src/data; MEDIA_DIR and
  BACKUP_DIR point at .../data/media and .../data/backups, so uploads and backups
  survive redeploys.

## Security

- Backend permission enforcement for every admin endpoint; restore requires the delete
  permission on the backup module.
- Upload validation, path-traversal protection, non-public backup directory, CSRF on
  state-changing requests, no secrets in backup metadata.

## Tests

- 60 automated tests (30 content + 30 accounts) pass under config.test_settings
  (in-memory SQLite, temp media/backups).
- Covers backup create/download/upload/restore/delete, retention, permissions,
  settings, themes, activity filters and exports.

## Deployment

- render.yaml uses a single klb-data disk with MEDIA_DIR and BACKUP_DIR.
- New dependencies: openpyxl==3.1.5, reportlab==4.5.1.
- Local development: config.dev_settings refuses Supabase URLs.

## Documentation

- docs/DEPLOYMENT-RENDER.md updated for disk layout and backup storage.
- docs/IMPLEMENTATION-GUIDE.md updated with accessibility, backup, settings, exports,
  tests, dependencies and local verification.

import { useCallback, useEffect, useRef, useState } from "react";
import { admin } from "../lib/api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { formatDateTime } from "../lib/format.js";
import { Alert, Card, EmptyState, PageHead } from "./AdminUI.jsx";

const TYPE_LABELS = {
  full: "Full backup",
  database: "Database only",
  media: "Media only",
  selective: "Selected components",
};

const STATUS_LABELS = {
  success: "Successful",
  failed: "Failed",
  in_progress: "In progress",
};

const COMPONENT_LABELS = {
  database: "Database",
  media: "Media files",
};

function typeLabel(record) {
  return TYPE_LABELS[record.backup_type] || record.backup_type || "Backup";
}

function componentList(record) {
  if (Array.isArray(record.components) && record.components.length) {
    return record.components;
  }
  if (record.backup_type === "database") return ["database"];
  if (record.backup_type === "media") return ["media"];
  return ["database", "media"];
}

function formatSize(bytes) {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function statusClass(status) {
  if (status === "failed") return "backup-status backup-status--failed";
  if (status === "in_progress") return "backup-status backup-status--progress";
  return "backup-status backup-status--success";
}

export default function AdminBackup() {
  const { can } = useAuth();
  const canView = can("backup", "view");
  const canCreate = can("backup", "create");
  const canDelete = can("backup", "delete");

  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [components, setComponents] = useState({ database: true, media: true });
  const [expanded, setExpanded] = useState(null);
  const [restoreTarget, setRestoreTarget] = useState(null);
  const [filters, setFilters] = useState({ search: "", type: "", status: "" });
  const [appliedFilters, setAppliedFilters] = useState({ search: "", type: "", status: "" });
  const fileRef = useRef(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await admin.backups.list(appliedFilters);
      setRows(Array.isArray(data) ? data : data.results || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [appliedFilters]);

  useEffect(() => {
    if (canView) load();
  }, [canView, load]);

  const selectedComponents = Object.keys(components).filter((key) => components[key]);

  async function createBackup(event) {
    event.preventDefault();
    if (!selectedComponents.length) {
      setError("Choose the database, media files, or both before creating a backup.");
      return;
    }
    setBusy("create");
    setError("");
    setNotice("");
    try {
      const data = await admin.backups.create({ components: selectedComponents });
      setNotice(
        data.detail
          ? `${data.detail} File: ${data.filename || "created"}.`
          : "Backup created successfully."
      );
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function downloadBackup(record) {
    setBusy(`download:${record.id}`);
    setError("");
    setNotice("");
    try {
      await admin.backups.download(record.id, record.filename);
      setNotice("Download started. Check your browser's downloads folder.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function confirmRestore() {
    const record = restoreTarget;
    if (!record) return;
    setBusy(`restore:${record.id}`);
    setError("");
    setNotice("");
    try {
      const data = await admin.backups.restore(record.id);
      setNotice(data.detail || "Backup restored successfully.");
      setRestoreTarget(null);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function deleteBackup(record) {
    const confirmed = window.confirm(
      `Delete "${record.filename || "this failed backup record"}"?\n\n` +
        "The archive is removed from the server and this history entry is deleted. " +
        "This cannot be undone."
    );
    if (!confirmed) return;

    setBusy(`delete:${record.id}`);
    setError("");
    setNotice("");
    try {
      await admin.backups.remove(record.id);
      if (expanded === record.id) setExpanded(null);
      setNotice("Backup deleted.");
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function uploadBackup(event) {
    event.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError("Choose a .zip backup file to upload first.");
      return;
    }
    if (!file.name.toLowerCase().endsWith(".zip")) {
      setError("Only .zip backup files can be uploaded.");
      return;
    }

    setBusy("upload");
    setError("");
    setNotice("");
    try {
      const data = await admin.backups.upload(file);
      setNotice(data.detail || "Backup uploaded successfully.");
      if (fileRef.current) fileRef.current.value = "";
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  function applyFilters(event) {
    event.preventDefault();
    setAppliedFilters({ ...filters, search: filters.search.trim() });
  }

  function clearFilters() {
    const empty = { search: "", type: "", status: "" };
    setFilters(empty);
    setAppliedFilters(empty);
  }

  const isBusy = Boolean(busy);
  const hasFilters = Boolean(
    appliedFilters.search || appliedFilters.type || appliedFilters.status
  );

  if (!canView) {
    return (
      <>
        <PageHead title="Backup & restore" />
        <Alert kind="warn">Your account does not have permission to manage backups.</Alert>
      </>
    );
  }

  return (
    <>
      <PageHead
        title="Backup & restore"
        lead="Create archives of the database and media library, keep copies off the server, and restore an earlier state when needed. Every operation is recorded in the activity log."
        actions={
          <button
            className="btn btn--secondary btn--sm"
            type="button"
            onClick={load}
            disabled={loading || isBusy}
          >
            {loading ? "Refreshing…" : "Refresh list"}
          </button>
        }
      />

      <Alert kind="error" onClose={() => setError("")}>
        {error}
      </Alert>
      <Alert onClose={() => setNotice("")}>{notice}</Alert>

      <div className="admin-split">
        <Card title="Create a backup">
          <form onSubmit={createBackup}>
            <p className="admin-lead backup-intro">
              Select the parts of the site to include. The choice below controls exactly what is
              written into the archive.
            </p>
            <fieldset className="backup-components">
              <legend className="sr-only">Backup components</legend>
              <label className="backup-component">
                <input
                  type="checkbox"
                  checked={components.database}
                  onChange={(event) =>
                    setComponents((current) => ({ ...current, database: event.target.checked }))
                  }
                  disabled={!canCreate || isBusy}
                />
                <span>
                  <strong>Database</strong>
                  <span>
                    Pages, catalogue, news, careers, tenders, resources, enquiries, user accounts
                    and site settings.
                  </span>
                </span>
              </label>
              <label className="backup-component">
                <input
                  type="checkbox"
                  checked={components.media}
                  onChange={(event) =>
                    setComponents((current) => ({ ...current, media: event.target.checked }))
                  }
                  disabled={!canCreate || isBusy}
                />
                <span>
                  <strong>Media files</strong>
                  <span>
                    Uploaded images, book covers, team photographs and PDF documents in the media
                    library.
                  </span>
                </span>
              </label>
            </fieldset>
            <div className="form-actions">
              <button className="btn btn--primary" type="submit" disabled={!canCreate || isBusy}>
                {busy === "create" ? "Creating backup…" : "Create backup"}
              </button>
              <button
                className="btn btn--secondary"
                type="button"
                onClick={() => setComponents({ database: true, media: true })}
                disabled={!canCreate || isBusy}
              >
                Select everything
              </button>
            </div>
          </form>
          <p className="muted-meta backup-footnote">
            Both options selected produces a full backup. A database-only or media-only archive is
            also valid and can be restored on its own. Archives are written to the private backup
            directory on the server; they are never served as public media.
          </p>
        </Card>

        <Card title="Upload an archive">
          <form onSubmit={uploadBackup}>
            <div className="field">
              <label htmlFor="backup-file">Backup file (.zip)</label>
              <input
                id="backup-file"
                ref={fileRef}
                type="file"
                accept=".zip,application/zip"
                disabled={!canCreate || isBusy}
              />
              <span className="hint">
                Upload a backup previously downloaded from this site. The archive is checked for a
                valid database dump or media folder before it is accepted.
              </span>
            </div>
            <div className="form-actions">
              <button className="btn btn--secondary" type="submit" disabled={!canCreate || isBusy}>
                {busy === "upload" ? "Uploading…" : "Upload backup"}
              </button>
            </div>
          </form>
          <p className="muted-meta backup-footnote">
            Uploaded archives appear in the history below. Inspect the details before restoring
            one.
          </p>
        </Card>
      </div>

      <Card
        title={`Backup history${rows.length ? ` · ${rows.length}` : ""}`}
        style={{ marginTop: "1.25rem" }}
      >
        <form className="activity-filters" onSubmit={applyFilters}>
          <label className="sr-only" htmlFor="backup-search">
            Search backups
          </label>
          <input
            id="backup-search"
            type="search"
            value={filters.search}
            placeholder="Search file name or administrator…"
            onChange={(event) =>
              setFilters((current) => ({ ...current, search: event.target.value }))
            }
          />
          <select
            aria-label="Filter by backup type"
            value={filters.type}
            onChange={(event) =>
              setFilters((current) => ({ ...current, type: event.target.value }))
            }
          >
            <option value="">All types</option>
            <option value="full">Full backup</option>
            <option value="database">Database only</option>
            <option value="media">Media only</option>
            <option value="selective">Selected components</option>
          </select>
          <select
            aria-label="Filter by status"
            value={filters.status}
            onChange={(event) =>
              setFilters((current) => ({ ...current, status: event.target.value }))
            }
          >
            <option value="">All statuses</option>
            <option value="success">Successful</option>
            <option value="failed">Failed</option>
            <option value="in_progress">In progress</option>
          </select>
          <button className="btn btn--primary" type="submit">
            Apply filters
          </button>
          {hasFilters ? (
            <button className="btn btn--secondary" type="button" onClick={clearFilters}>
              Clear
            </button>
          ) : null}
        </form>

        {restoreTarget ? (
          <div className="backup-restore" role="alert" aria-live="assertive">
            <h3>Restore {restoreTarget.filename}?</h3>
            <p>
              The archive will overwrite current records and media files with the contents of this
              backup. Anything created after the backup was taken will be replaced or merged.
            </p>
            <ul>
              <li>A safety backup of the current site is created automatically before restoring.</li>
              <li>
                Included components:{" "}
                {componentList(restoreTarget)
                  .map((key) => COMPONENT_LABELS[key] || key)
                  .join(" and ")}
                .
              </li>
              <li>The archive is validated before any data is changed.</li>
              <li>The restore and its outcome are recorded in the activity log.</li>
            </ul>
            <div className="form-actions">
              <button
                className="btn btn--danger"
                type="button"
                onClick={confirmRestore}
                disabled={isBusy}
              >
                {busy === `restore:${restoreTarget.id}`
                  ? "Restoring…"
                  : "Create safety backup and restore"}
              </button>
              <button
                className="btn btn--secondary"
                type="button"
                onClick={() => setRestoreTarget(null)}
                disabled={isBusy}
              >
                Cancel
              </button>
            </div>
          </div>
        ) : null}

        {loading ? (
          <p className="muted-meta">Loading backups…</p>
        ) : rows.length ? (
          <div className="table-wrap">
            <table className="admin-table backup-table">
              <thead>
                <tr>
                  <th>Backup</th>
                  <th>Created</th>
                  <th>Size</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((record) => {
                  const failed = record.status === "failed";
                  return (
                    <FragmentRow
                      key={record.id}
                      record={record}
                      failed={failed}
                      expanded={expanded === record.id}
                      toggleExpanded={() =>
                        setExpanded((current) => (current === record.id ? null : record.id))
                      }
                      busy={busy}
                      isBusy={isBusy}
                      canDelete={canDelete}
                      onDownload={() => downloadBackup(record)}
                      onRestore={() => {
                        setError("");
                        setNotice("");
                        setRestoreTarget(record);
                      }}
                      onDelete={() => deleteBackup(record)}
                    />
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title={hasFilters ? "No backups match these filters." : "No backups yet."}>
            {hasFilters
              ? "Clear the filters to see the full history."
              : "Create a backup above, or upload an existing .zip backup file."}
          </EmptyState>
        )}

        <p className="muted-meta backup-retention">
          Older archives are removed automatically according to the retention limit in Site
          settings (10 backups by default; 0 keeps every backup). Failed attempts remain in the
          history so they can be investigated.
        </p>
      </Card>
    </>
  );
}

function FragmentRow({
  record,
  failed,
  expanded,
  toggleExpanded,
  busy,
  isBusy,
  canDelete,
  onDownload,
  onRestore,
  onDelete,
}) {
  const usable = !failed && Boolean(record.filename);
  return (
    <>
      <tr>
        <td className="admin-table__title backup-table__name">
          <span className="mono">{record.filename || "No archive produced"}</span>
          <small>
            {typeLabel(record)} ·{" "}
            {componentList(record)
              .map((key) => COMPONENT_LABELS[key] || key)
              .join(" + ")}
          </small>
        </td>
        <td className="activity-table__time">
          {formatDateTime(record.created_at) || "—"}
          <br />
          <small>by {record.created_by_name || "System / unknown"}</small>
        </td>
        <td>{record.size ? formatSize(record.size) : "—"}</td>
        <td>
          <span className={statusClass(record.status)}>
            {STATUS_LABELS[record.status] || record.status || "Successful"}
          </span>
          {record.restored_at ? (
            <>
              <br />
              <small className="muted-meta">
                Restored {formatDateTime(record.restored_at)}
              </small>
            </>
          ) : null}
        </td>
        <td>
          <div className="admin-table__actions">
            <button
              className="btn btn--secondary btn--sm"
              type="button"
              onClick={onDownload}
              disabled={!usable || isBusy}
            >
              {busy === `download:${record.id}` ? "Downloading…" : "Download"}
            </button>
            <button
              className="btn btn--secondary btn--sm"
              type="button"
              onClick={onRestore}
              disabled={!usable || !canDelete || isBusy}
            >
              Restore
            </button>
            <button
              className="btn btn--secondary btn--sm"
              type="button"
              onClick={toggleExpanded}
              aria-expanded={expanded}
            >
              {expanded ? "Hide details" : "Details"}
            </button>
            <button
              className="btn btn--danger btn--sm"
              type="button"
              onClick={onDelete}
              disabled={!canDelete || isBusy}
            >
              {busy === `delete:${record.id}` ? "Deleting…" : "Delete"}
            </button>
          </div>
        </td>
      </tr>
      {expanded ? (
        <tr className="backup-detail-row">
          <td colSpan={5}>
            <div className="backup-detail">
              <dl>
                <div>
                  <dt>Archive</dt>
                  <dd className="mono">{record.filename || "None"}</dd>
                </div>
                <div>
                  <dt>Type</dt>
                  <dd>{typeLabel(record)}</dd>
                </div>
                <div>
                  <dt>Components</dt>
                  <dd>
                    {componentList(record)
                      .map((key) => COMPONENT_LABELS[key] || key)
                      .join(", ")}
                  </dd>
                </div>
                <div>
                  <dt>Storage</dt>
                  <dd>Private server backup directory (not publicly accessible)</dd>
                </div>
                <div>
                  <dt>Created by</dt>
                  <dd>{record.created_by_name || "System / unknown"}</dd>
                </div>
                <div>
                  <dt>Last restored</dt>
                  <dd>
                    {record.restored_at
                      ? `${formatDateTime(record.restored_at)}${
                          record.restored_by_name ? ` by ${record.restored_by_name}` : ""
                        }`
                      : "Never"}
                  </dd>
                </div>
              </dl>
              {record.error ? (
                <div className="backup-detail__error">
                  <strong>Failure reason</strong>
                  <p>{record.error}</p>
                </div>
              ) : null}
            </div>
          </td>
        </tr>
      ) : null}
    </>
  );
}

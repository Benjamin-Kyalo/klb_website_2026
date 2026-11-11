import { useState } from "react";
import { admin } from "../lib/api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { Alert, Card, EmptyState, PageHead } from "./AdminUI.jsx";

export default function AdminBackup() {
  const { can } = useAuth();
  const canBackup = can("pages", "view");
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [lastBackup, setLastBackup] = useState(null);

  async function runBackup(type) {
    setBusy(type);
    setError("");
    setNotice("");
    try {
      const data = await admin.backup(type);
      setLastBackup(data);
      setNotice(data.detail || "Backup created successfully.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  return (
    <>
      <PageHead
        title="Backup"
        lead="Create a backup of the database and media files. Backups are stored on the server in the backups/ directory."
      />

      <Alert kind="error" onClose={() => setError("")}>{error}</Alert>
      <Alert onClose={() => setNotice("")}>{notice}</Alert>

      {!canBackup ? (
        <Alert kind="warn">Your account does not have permission to create backups.</Alert>
      ) : null}

      <div className="admin-grid admin-grid--3" style={{ marginBottom: "1.5rem" }}>
        <Card title="Full backup">
          <p className="admin-lead" style={{ marginBottom: "1rem" }}>
            Database + all media files (team photos, uploaded documents, covers).
          </p>
          <button
            className="btn btn--primary"
            type="button"
            onClick={() => runBackup("full")}
            disabled={Boolean(busy)}
          >
            {busy === "full" ? "Creating…" : "Backup everything"}
          </button>
        </Card>

        <Card title="Database only">
          <p className="admin-lead" style={{ marginBottom: "1rem" }}>
            All content, settings, and user accounts. No media files.
          </p>
          <button
            className="btn btn--secondary"
            type="button"
            onClick={() => runBackup("database")}
            disabled={Boolean(busy)}
          >
            {busy === "database" ? "Creating…" : "Backup database"}
          </button>
        </Card>

        <Card title="Media only">
          <p className="admin-lead" style={{ marginBottom: "1rem" }}>
            Uploaded files: team photos, covers, PDFs, and documents.
          </p>
          <button
            className="btn btn--secondary"
            type="button"
            onClick={() => runBackup("media")}
            disabled={Boolean(busy)}
          >
            {busy === "media" ? "Creating…" : "Backup media"}
          </button>
        </Card>
      </div>

      {lastBackup ? (
        <Card title="Last backup">
          <dl className="admin-facts">
            <div>
              <dt>File</dt>
              <dd>{lastBackup.filename}</dd>
            </div>
            <div>
              <dt>Size</dt>
              <dd>{(lastBackup.size / 1024).toFixed(1)} KB</dd>
            </div>
          </dl>
          <p className="muted-meta" style={{ marginTop: "0.75rem" }}>
            The backup file is stored on the server in the <code>backups/</code> directory.
            Download it via Render Shell or your hosting provider's file manager.
          </p>
        </Card>
      ) : (
        <EmptyState title="No backup created yet.">
          Choose an option above to create your first backup.
        </EmptyState>
      )}

      <Card title="Important notes" style={{ marginTop: "1.5rem" }}>
        <ul style={{ margin: 0, paddingLeft: "1.2rem", color: "var(--muted, #4a5c64)", fontSize: "0.85rem", lineHeight: 1.7 }}>
          <li>Backups are stored on the server. On Render, use the Shell to download them, or mount a persistent disk for the <code>backups/</code> directory.</li>
          <li>Render's PostgreSQL has built-in backups on paid plans. Enable them in the database settings.</li>
          <li>Media files on a Render disk are <strong>not</strong> backed up by Render. Use this tool or set up external storage (S3).</li>
          <li>For automated backups, use a cron job or Render's scheduled jobs (paid plans).</li>
        </ul>
      </Card>
    </>
  );
}

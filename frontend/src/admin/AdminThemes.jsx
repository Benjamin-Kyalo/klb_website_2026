import { useEffect, useState } from "react";
import { admin } from "../lib/api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { Alert, Card, EmptyState, PageHead, StatusBadge } from "./AdminUI.jsx";
import RecordForm from "./RecordForm.jsx";

const THEME_FIELDS = [
  { name: "name", label: "Theme name", required: true },
  { name: "slug", label: "URL slug", hint: "Leave blank to generate from the name." },
  { name: "description", label: "Description", type: "textarea", rows: 2, full: true },
  { name: "css_class", label: "CSS class", hint: "Class applied to the body when this theme is active. e.g. theme-christmas" },
  { name: "start_date", label: "Start date", type: "date" },
  { name: "end_date", label: "End date", type: "date" },
  { name: "is_active", label: "Enabled", type: "checkbox", defaultValue: true },
];

export default function AdminThemes() {
  const { can } = useAuth();
  const editable = can("pages", "edit");
  const [themes, setThemes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [editing, setEditing] = useState(null);

  useEffect(() => {
    load();
  }, []);

  async function load() {
    setLoading(true);
    try {
      const data = await admin.themes.list();
      setThemes(Array.isArray(data) ? data : data.results || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSave(payload) {
    try {
      if (editing?.id) {
        await admin.themes.update(editing.id, payload);
        setNotice("Theme updated.");
      } else {
        await admin.themes.create(payload);
        setNotice("Theme created.");
      }
      setEditing(null);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete(id) {
    if (!window.confirm("Delete this theme?")) return;
    try {
      await admin.themes.remove(id);
      setNotice("Theme deleted.");
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <>
      <PageHead
        title="Website themes"
        lead="Schedule seasonal themes and campaigns. The active theme is applied automatically based on start and end dates."
        actions={
          editable && !editing ? (
            <button className="btn btn--primary" type="button" onClick={() => setEditing({})}>
              New theme
            </button>
          ) : null
        }
      />

      <Alert kind="error" onClose={() => setError("")}>{error}</Alert>
      <Alert onClose={() => setNotice("")}>{notice}</Alert>

      {editing ? (
        <Card title={editing.id ? "Edit theme" : "New theme"}>
          <RecordForm
            fields={THEME_FIELDS}
            initial={editing}
            onSubmit={handleSave}
            onCancel={() => setEditing(null)}
            submitLabel={editing.id ? "Save changes" : "Create theme"}
          />
        </Card>
      ) : null}

      {loading ? (
        <p className="muted-meta">Loading themes…</p>
      ) : themes.length ? (
        <Card title={`${themes.length} theme${themes.length === 1 ? "" : "s"}`}>
          <div className="table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>CSS class</th>
                  <th>Start</th>
                  <th>End</th>
                  <th>Status</th>
                  <th>Enabled</th>
                  <th className="admin-table__actions">Actions</th>
                </tr>
              </thead>
              <tbody>
                {themes.map((t) => (
                  <tr key={t.id}>
                    <td className="admin-table__title">{t.name}</td>
                    <td><code>{t.css_class || "—"}</code></td>
                    <td>{t.start_date || "—"}</td>
                    <td>{t.end_date || "—"}</td>
                    <td><StatusBadge status={t.status === "active" ? "published" : t.status === "scheduled" ? "new" : "draft"} /></td>
                    <td>{t.is_active ? "Yes" : "No"}</td>
                    <td className="admin-table__actions">
                      {editable ? (
                        <>
                          <button className="btn btn--secondary btn--sm" type="button" onClick={() => setEditing(t)}>
                            Edit
                          </button>
                          <button className="btn btn--danger btn--sm" type="button" onClick={() => handleDelete(t.id)}>
                            Delete
                          </button>
                        </>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        <EmptyState title="No themes yet.">
          {editable ? "Use the “New theme” button to create your first campaign." : null}
        </EmptyState>
      )}

      <Card title="How themes work" style={{ marginTop: "1.5rem" }}>
        <ul style={{ margin: 0, paddingLeft: "1.2rem", color: "var(--muted, #4a5c64)", fontSize: "0.85rem", lineHeight: 1.7 }}>
          <li>A theme activates automatically when its start date arrives.</li>
          <li>It deactivates automatically when its end date passes.</li>
          <li>The site reverts to the default theme when no theme is active.</li>
          <li>Add CSS rules targeting the theme's CSS class (e.g. <code>.theme-christmas</code>) in <code>klb.css</code>.</li>
          <li>Only one theme should be active at a time. If multiple overlap, the most recently started one wins.</li>
        </ul>
      </Card>
    </>
  );
}

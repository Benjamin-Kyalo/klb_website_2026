import { useCallback, useEffect, useState } from "react";
import { admin } from "../lib/api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { Alert, Card, EmptyState, PageHead } from "./AdminUI.jsx";
import RecordForm from "./RecordForm.jsx";

export default function AdminCrudPage({
  resource,
  module,
  title,
  lead,
  singular,
  columns,
  fields,
  defaults = {},
  searchPlaceholder = "Search…",
  lookupField = "id",
  canCreate = true,
  canDelete = true,
  canEdit = true,
  extraActions = null,
  listParams = {},
}) {
  const { can } = useAuth();
  const allowCreate = canCreate && (!module || can(module, "create"));
  const allowEdit = canEdit && (!module || can(module, "edit"));
  const allowDelete = canDelete && (!module || can(module, "delete"));
  const allowPublish = !module || can(module, "publish");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [editing, setEditing] = useState(null);

  // Serialise the extra filters so inline objects passed by callers do not
  // trigger a fresh request on every render.
  const listParamsKey = JSON.stringify(listParams || {});

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = JSON.parse(listParamsKey);
      const data = await admin.all(resource, { ...params, search: appliedSearch });
      setRows(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [resource, appliedSearch, listParamsKey]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleSave(payload) {
    const lookup = editing?.[lookupField];
    if (lookup !== undefined && lookup !== null && lookup !== "") {
      await admin.update(resource, lookup, payload);
      setNotice(`${singular} updated.`);
    } else {
      await admin.create(resource, payload);
      setNotice(`${singular} created.`);
    }
    setEditing(null);
    await load();
  }

  async function handleDelete(row) {
    const label = row.title || row.name || row.email || singular;
    if (!window.confirm(`Delete “${label}”? This cannot be undone.`)) return;
    try {
      await admin.remove(resource, row[lookupField]);
      setNotice(`${singular} deleted.`);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  const isEditing = editing !== null;

  return (
    <>
      <PageHead
        title={title}
        lead={lead}
        actions={
          <>
            {extraActions}
            {allowCreate && !isEditing ? (
              <button className="btn btn--primary" type="button" onClick={() => setEditing({ ...defaults })}>
                New {singular.toLowerCase()}
              </button>
            ) : null}
          </>
        }
      />

      <Alert kind="success" onClose={() => setNotice("")}>
        {notice}
      </Alert>
      <Alert kind="error" onClose={() => setError("")}>
        {error}
      </Alert>

      {isEditing ? (
        <Card title={`${editing?.[lookupField] ? `Edit ${singular.toLowerCase()}` : `New ${singular.toLowerCase()}`}`}>
          <RecordForm
            fields={fields}
            initial={editing}
            onSubmit={handleSave}
            onCancel={() => setEditing(null)}
            canPublish={allowPublish}
            submitLabel={editing?.[lookupField] ? "Save changes" : `Create ${singular.toLowerCase()}`}
          />
        </Card>
      ) : (
        <Card
          title={`${rows.length} ${rows.length === 1 ? singular.toLowerCase() : `${singular.toLowerCase()}s`}`}
          actions={
            <form
              className="admin-search"
              onSubmit={(event) => {
                event.preventDefault();
                setAppliedSearch(search.trim());
              }}
            >
              <label className="sr-only" htmlFor={`${resource}-search`}>
                {searchPlaceholder}
              </label>
              <input
                id={`${resource}-search`}
                type="search"
                value={search}
                placeholder={searchPlaceholder}
                onChange={(event) => setSearch(event.target.value)}
              />
              <button className="btn btn--secondary btn--sm" type="submit">
                Search
              </button>
            </form>
          }
        >
          {loading ? (
            <p className="muted-meta">Loading…</p>
          ) : rows.length ? (
            <div className="table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    {columns.map((column) => (
                      <th key={column.key}>{column.label}</th>
                    ))}
                    <th className="admin-table__actions">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.id}>
                      {columns.map((column) => (
                        <td key={column.key} className={column.className}>
                          {column.render ? column.render(row) : row[column.key] ?? "—"}
                        </td>
                      ))}
                      <td className="admin-table__actions">
                        {allowEdit ? (
                          <button className="btn btn--secondary btn--sm" type="button" onClick={() => setEditing(row)}>
                            Edit
                          </button>
                        ) : null}
                        {allowDelete ? (
                          <button className="btn btn--danger btn--sm" type="button" onClick={() => handleDelete(row)}>
                            Delete
                          </button>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState title={`No ${singular.toLowerCase()}s yet.`}>
              {allowCreate ? `Use the “New ${singular.toLowerCase()}” button to add the first one.` : null}
            </EmptyState>
          )}
        </Card>
      )}
    </>
  );
}

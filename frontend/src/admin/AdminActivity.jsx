import { useCallback, useEffect, useState } from "react";
import { admin } from "../lib/api.js";
import { MODULES } from "../lib/permissions.js";
import { formatDateTime } from "../lib/format.js";
import { Alert, Card, EmptyState, PageHead } from "./AdminUI.jsx";

const ACTIONS = [
  { value: "create", label: "Created" },
  { value: "update", label: "Updated" },
  { value: "delete", label: "Deleted" },
  { value: "publish", label: "Published" },
  { value: "unpublish", label: "Unpublished" },
  { value: "settings", label: "Settings" },
  { value: "user", label: "Account change" },
  { value: "password", label: "Password reset" },
];

const MODULE_OPTIONS = [...MODULES, { key: "media", label: "File uploads" }].filter(
  (module, index, list) => list.findIndex((item) => item.key === module.key) === index
);

function moduleLabel(key) {
  return MODULE_OPTIONS.find((module) => module.key === key)?.label || key;
}

export default function AdminActivity() {
  const [rows, setRows] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [module, setModule] = useState("");
  const [action, setAction] = useState("");
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const pageSize = 40;

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await admin.list("activity", {
        page,
        page_size: pageSize,
        module,
        action,
        search: appliedSearch,
      });
      setRows(data.results || []);
      setCount(data.count || 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [page, module, action, appliedSearch]);

  useEffect(() => {
    load();
  }, [load]);

  const pages = Math.max(1, Math.ceil(count / pageSize));

  function applyFilters(event) {
    event.preventDefault();
    setPage(1);
    setAppliedSearch(search.trim());
  }

  function resetFilters() {
    setModule("");
    setAction("");
    setSearch("");
    setAppliedSearch("");
    setPage(1);
  }

  const hasFilters = Boolean(module || action || appliedSearch);

  return (
    <>
      <PageHead
        title="Activity log"
        lead="A record of who created, edited, deleted or published content, and when. Entries cannot be changed or removed."
      />

      <Alert kind="error" onClose={() => setError("")}>
        {error}
      </Alert>

      <Card title="Filter the log">
        <form className="activity-filters" onSubmit={applyFilters}>
          <label className="sr-only" htmlFor="activity-search">
            Search activity
          </label>
          <input
            id="activity-search"
            type="search"
            value={search}
            placeholder="Search person, record or detail…"
            onChange={(event) => setSearch(event.target.value)}
          />
          <select
            aria-label="Filter by module"
            value={module}
            onChange={(event) => {
              setModule(event.target.value);
              setPage(1);
            }}
          >
            <option value="">All modules</option>
            {MODULE_OPTIONS.map((item) => (
              <option value={item.key} key={item.key}>
                {item.label}
              </option>
            ))}
          </select>
          <select
            aria-label="Filter by action"
            value={action}
            onChange={(event) => {
              setAction(event.target.value);
              setPage(1);
            }}
          >
            <option value="">All actions</option>
            {ACTIONS.map((item) => (
              <option value={item.value} key={item.value}>
                {item.label}
              </option>
            ))}
          </select>
          <button className="btn btn--primary" type="submit">
            Apply filters
          </button>
          {hasFilters ? (
            <button className="btn btn--secondary" type="button" onClick={resetFilters}>
              Clear
            </button>
          ) : null}
        </form>
      </Card>

      <Card
        title={`${count} ${count === 1 ? "entry" : "entries"}`}
        actions={
          pages > 1 ? (
            <div className="pager">
              <button
                className="btn btn--secondary btn--sm"
                type="button"
                disabled={page <= 1 || loading}
                onClick={() => setPage((value) => Math.max(1, value - 1))}
              >
                Previous
              </button>
              <span>
                Page {page} of {pages}
              </span>
              <button
                className="btn btn--secondary btn--sm"
                type="button"
                disabled={page >= pages || loading}
                onClick={() => setPage((value) => Math.min(pages, value + 1))}
              >
                Next
              </button>
            </div>
          ) : null
        }
      >
        {loading ? (
          <p className="muted-meta">Loading activity…</p>
        ) : rows.length ? (
          <div className="table-wrap">
            <table className="admin-table activity-table">
              <thead>
                <tr>
                  <th>When</th>
                  <th>Who</th>
                  <th>Action</th>
                  <th>Module</th>
                  <th>Record</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((entry) => (
                  <tr key={entry.id}>
                    <td className="activity-table__time">
                      {formatDateTime(entry.created_at)}
                    </td>
                    <td>
                      <strong>{entry.actor_name || "System"}</strong>
                      {entry.actor_email ? (
                        <>
                          <br />
                          <small className="mono">{entry.actor_email}</small>
                        </>
                      ) : null}
                    </td>
                    <td>
                      <span className={`activity-action activity-action--${entry.action}`}>
                        {entry.action_label}
                      </span>
                    </td>
                    <td>{moduleLabel(entry.module)}</td>
                    <td className="admin-table__title">{entry.object_label || "—"}</td>
                    <td>
                      {entry.detail || "—"}
                      {entry.ip_address ? (
                        <>
                          <br />
                          <small className="mono">IP {entry.ip_address}</small>
                        </>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No activity matches these filters.">
            Changes made in the content manager will appear here.
          </EmptyState>
        )}
      </Card>
    </>
  );
}

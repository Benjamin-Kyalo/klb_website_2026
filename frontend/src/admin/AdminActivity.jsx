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
  { value: "settings", label: "Settings updated" },
  { value: "user", label: "Account change" },
  { value: "password", label: "Password reset" },
  { value: "backup", label: "Backup operation" },
  { value: "export", label: "Report exported" },
];

const MODULE_OPTIONS = [...MODULES, { key: "media", label: "File uploads" }].filter(
  (module, index, list) => list.findIndex((item) => item.key === module.key) === index
);

const EMPTY_FILTERS = {
  search: "",
  actor: "",
  module: "",
  action: "",
  dateFrom: "",
  dateTo: "",
};

function moduleLabel(key) {
  return MODULE_OPTIONS.find((module) => module.key === key)?.label || key;
}

export default function AdminActivity() {
  const [rows, setRows] = useState([]);
  const [actors, setActors] = useState([]);
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [draft, setDraft] = useState(EMPTY_FILTERS);
  const [applied, setApplied] = useState(EMPTY_FILTERS);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const pageSize = 40;

  const params = {
    page,
    page_size: pageSize,
    actor: applied.actor,
    module: applied.module,
    action: applied.action,
    search: applied.search,
    date_from: applied.dateFrom,
    date_to: applied.dateTo,
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await admin.list("activity", params);
      setRows(data.results || []);
      setCount(data.count || 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, applied]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    let active = true;
    admin
      .activityActors()
      .then((data) => {
        if (active) setActors(Array.isArray(data) ? data : data.results || []);
      })
      .catch(() => {
        /* The filter simply stays empty if the lookup fails. */
      });
    return () => {
      active = false;
    };
  }, []);

  const pages = Math.max(1, Math.ceil(count / pageSize));

  function applyFilters(event) {
    event.preventDefault();
    if (draft.dateFrom && draft.dateTo && draft.dateFrom > draft.dateTo) {
      setError("The start date must be on or before the end date.");
      return;
    }
    setError("");
    setPage(1);
    setApplied({ ...draft, search: draft.search.trim() });
  }

  function resetFilters() {
    setDraft(EMPTY_FILTERS);
    setApplied(EMPTY_FILTERS);
    setPage(1);
  }

  const hasFilters = Boolean(
    applied.search ||
      applied.actor ||
      applied.module ||
      applied.action ||
      applied.dateFrom ||
      applied.dateTo
  );

  async function downloadLog(format) {
    setExporting(format);
    setError("");
    setNotice("");
    try {
      const filename = await admin.activityExport({
        format,
        actor: applied.actor,
        module: applied.module,
        action: applied.action,
        search: applied.search,
        date_from: applied.dateFrom,
        date_to: applied.dateTo,
      });
      setNotice(
        `${format === "xlsx" ? "Excel workbook" : format.toUpperCase()} exported${
          filename ? ` as ${filename}` : ""
        }. It reflects the filters currently applied.`
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setExporting("");
    }
  }

  return (
    <>
      <PageHead
        title="Activity log"
        lead="An audit record of content changes, settings updates, user administration, backups and exports. Entries cannot be edited or deleted."
      />

      <Alert kind="error" onClose={() => setError("")}>
        {error}
      </Alert>
      <Alert onClose={() => setNotice("")}>{notice}</Alert>

      <Card title="Filter the log">
        <form className="log-filters" onSubmit={applyFilters}>
          <div className="field log-filters__search">
            <label htmlFor="activity-search">Search</label>
            <input
              id="activity-search"
              type="search"
              value={draft.search}
              placeholder="Person, record, detail or IP…"
              onChange={(event) =>
                setDraft((current) => ({ ...current, search: event.target.value }))
              }
            />
          </div>
          <div className="field">
            <label htmlFor="activity-user">User</label>
            <select
              id="activity-user"
              value={draft.actor}
              onChange={(event) =>
                setDraft((current) => ({ ...current, actor: event.target.value }))
              }
            >
              <option value="">All users</option>
              {actors.map((person) => (
                <option value={person.id} key={person.id}>
                  {person.name}
                  {person.email && person.email !== person.name ? ` (${person.email})` : ""}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="activity-module">Module</label>
            <select
              id="activity-module"
              value={draft.module}
              onChange={(event) =>
                setDraft((current) => ({ ...current, module: event.target.value }))
              }
            >
              <option value="">All modules</option>
              {MODULE_OPTIONS.map((item) => (
                <option value={item.key} key={item.key}>
                  {item.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="activity-action">Action</label>
            <select
              id="activity-action"
              value={draft.action}
              onChange={(event) =>
                setDraft((current) => ({ ...current, action: event.target.value }))
              }
            >
              <option value="">All actions</option>
              {ACTIONS.map((item) => (
                <option value={item.value} key={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="activity-from">From date</label>
            <input
              id="activity-from"
              type="date"
              value={draft.dateFrom}
              max={draft.dateTo || undefined}
              onChange={(event) =>
                setDraft((current) => ({ ...current, dateFrom: event.target.value }))
              }
            />
          </div>
          <div className="field">
            <label htmlFor="activity-to">To date</label>
            <input
              id="activity-to"
              type="date"
              value={draft.dateTo}
              min={draft.dateFrom || undefined}
              onChange={(event) =>
                setDraft((current) => ({ ...current, dateTo: event.target.value }))
              }
            />
          </div>
          <div className="log-filters__actions">
            <button className="btn btn--primary" type="submit">
              Apply filters
            </button>
            {hasFilters ? (
              <button className="btn btn--secondary" type="button" onClick={resetFilters}>
                Clear
              </button>
            ) : null}
          </div>
        </form>
      </Card>

      <Card
        title={`${count} ${count === 1 ? "entry" : "entries"}`}
        actions={
          <div className="log-export">
            <span className="muted-meta">Download filtered records:</span>
            <button
              className="btn btn--secondary btn--sm"
              type="button"
              onClick={() => downloadLog("csv")}
              disabled={Boolean(exporting) || loading || !count}
            >
              {exporting === "csv" ? "Preparing…" : "CSV"}
            </button>
            <button
              className="btn btn--secondary btn--sm"
              type="button"
              onClick={() => downloadLog("xlsx")}
              disabled={Boolean(exporting) || loading || !count}
            >
              {exporting === "xlsx" ? "Preparing…" : "Excel"}
            </button>
            <button
              className="btn btn--secondary btn--sm"
              type="button"
              onClick={() => downloadLog("pdf")}
              disabled={Boolean(exporting) || loading || !count}
            >
              {exporting === "pdf" ? "Preparing…" : "PDF"}
            </button>
          </div>
        }
      >
        {loading ? (
          <p className="muted-meta">Loading activity…</p>
        ) : rows.length ? (
          <>
            <div className="log-summary">
              Showing entries for the selected filters. Newest first.
            </div>
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
            {pages > 1 ? (
              <div className="pager log-pager">
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
            ) : null}
          </>
        ) : (
          <EmptyState title="No activity matches these filters.">
            {hasFilters
              ? "Adjust the filters or clear them to see the full audit history."
              : "Changes made in the content manager will appear here."}
          </EmptyState>
        )}
      </Card>
    </>
  );
}

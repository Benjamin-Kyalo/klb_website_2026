import { useCallback, useEffect, useState } from "react";
import { admin } from "../lib/api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { formatDate } from "../lib/format.js";
import { Alert, Card, EmptyState, Field, PageHead } from "./AdminUI.jsx";

const TABS = [
  { key: "all", label: "All" },
  { key: "new", label: "New" },
  { key: "in_progress", label: "In progress" },
  { key: "closed", label: "Closed" },
];

const TYPE_LABELS = {
  general: "General enquiry",
  bulk: "Bulk order",
  order: "Order or delivery",
  quote: "Printing, design or branding quote",
  publishing: "Publishing a manuscript",
  translation: "Translation services",
  printing: "Printing services",
  branding: "Branding services",
  digital: "Digital editions",
  media: "Media enquiry",
  events: "Events and school visits",
  procurement: "Tender or procurement",
  access: "Access to information",
  complaints: "Complaint or feedback",
  careers: "Recruitment",
};

function EnquiryCard({ enquiry, onSaved, onDeleted }) {
  const { can } = useAuth();
  const canEdit = can("enquiries", "edit");
  const canDelete = can("enquiries", "delete");
  const [status, setStatus] = useState(enquiry.status);
  const [note, setNote] = useState(enquiry.internal_note || "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function save() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const updated = await admin.update("enquiries", enquiry.id, { status, internal_note: note });
      setNotice("Saved.");
      onSaved(updated);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!window.confirm(`Delete the enquiry from ${enquiry.name}? This cannot be undone.`)) return;
    try {
      await admin.remove("enquiries", enquiry.id);
      onDeleted();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <article className={`enquiry${enquiry.status === "closed" ? " enquiry--handled" : ""}`}>
      <div className="enquiry__head">
        <div>
          <h3 style={{ marginBottom: ".15rem" }}>{enquiry.subject}</h3>
          <p className="enquiry__meta">
            {enquiry.name}
            {enquiry.organisation ? ` · ${enquiry.organisation}` : ""} · {TYPE_LABELS[enquiry.enquiry_type] || enquiry.enquiry_type} ·{" "}
            {formatDate(enquiry.created_at)}
          </p>
        </div>
        <span className={`badge badge--${enquiry.status === "new" ? "new" : enquiry.status === "closed" ? "muted" : "draft"}`}>
          {enquiry.status.replace("_", " ")}
        </span>
      </div>

      <p className="enquiry__msg">{enquiry.message}</p>

      <p className="enquiry__meta">
        <a href={`mailto:${enquiry.email}`}>{enquiry.email}</a>
        {enquiry.phone ? (
          <>
            {" · "}
            <a href={`tel:${enquiry.phone.replace(/[^\d+]/g, "")}`}>{enquiry.phone}</a>
          </>
        ) : null}
      </p>

      <div className="enquiry__actions admin-enquiry__controls">
        <Field label="Status" htmlFor={`status-${enquiry.id}`}>
          <select
            id={`status-${enquiry.id}`}
            value={status}
            disabled={!canEdit}
            onChange={(event) => setStatus(event.target.value)}
          >
            <option value="new">New</option>
            <option value="in_progress">In progress</option>
            <option value="closed">Closed</option>
          </select>
        </Field>
        <Field label="Internal note" htmlFor={`note-${enquiry.id}`} className="enquiry__note">
          <textarea
            id={`note-${enquiry.id}`}
            rows={2}
            value={note}
            placeholder="Notes are only visible to staff."
            disabled={!canEdit}
            onChange={(event) => setNote(event.target.value)}
          />
        </Field>
        <div className="enquiry__buttons">
          {canEdit ? (
            <button className="btn btn--primary btn--sm" type="button" onClick={save} disabled={busy}>
              {busy ? "Saving…" : "Save"}
            </button>
          ) : null}
          <a className="btn btn--secondary btn--sm" href={`mailto:${enquiry.email}?subject=${encodeURIComponent(`Re: ${enquiry.subject}`)}`}>
            Reply by email
          </a>
          {canDelete ? (
            <button className="btn btn--danger btn--sm" type="button" onClick={remove}>
              Delete
            </button>
          ) : null}
        </div>
      </div>

      {!canEdit ? (
        <p className="muted-meta">Your account has read-only access to enquiries.</p>
      ) : null}

      {notice ? <p className="muted-meta">{notice}</p> : null}
      {error ? <p className="field-error">{error}</p> : null}
    </article>
  );
}

export default function AdminEnquiries() {
  const [tab, setTab] = useState("all");
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = { search: appliedSearch };
      if (tab !== "all") params.status = tab;
      setRows(await admin.all("enquiries", params));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [tab, appliedSearch]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <>
      <PageHead
        title="Enquiries"
        lead="Messages sent through the website contact form. Update the status as you respond; notes are for staff only."
      />

      <Alert kind="success" onClose={() => setNotice("")}>
        {notice}
      </Alert>
      <Alert kind="error" onClose={() => setError("")}>
        {error}
      </Alert>

      <div className="admin-toolbar">
        <div className="admin-tabs" role="tablist" aria-label="Filter enquiries">
          {TABS.map((item) => (
            <button
              key={item.key}
              type="button"
              role="tab"
              aria-selected={tab === item.key}
              className={tab === item.key ? "is-active" : undefined}
              onClick={() => setTab(item.key)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <form
          className="admin-search"
          onSubmit={(event) => {
            event.preventDefault();
            setAppliedSearch(search.trim());
          }}
        >
          <label className="sr-only" htmlFor="enquiry-search">
            Search enquiries
          </label>
          <input
            id="enquiry-search"
            type="search"
            value={search}
            placeholder="Search name, email or subject…"
            onChange={(event) => setSearch(event.target.value)}
          />
          <button className="btn btn--secondary btn--sm" type="submit">
            Search
          </button>
        </form>
      </div>

      <Card title={`${rows.length} ${rows.length === 1 ? "enquiry" : "enquiries"}`}>
        {loading ? (
          <p className="muted-meta">Loading enquiries…</p>
        ) : rows.length ? (
          rows.map((enquiry) => (
            <EnquiryCard
              key={enquiry.id}
              enquiry={enquiry}
              onSaved={(updated) => {
                setRows((current) => current.map((row) => (row.id === updated.id ? updated : row)));
                setNotice("Enquiry updated.");
              }}
              onDeleted={() => {
                setRows((current) => current.filter((row) => row.id !== enquiry.id));
                setNotice("Enquiry deleted.");
              }}
            />
          ))
        ) : (
          <EmptyState title="No enquiries in this view.">
            New messages from the contact form will appear here.
          </EmptyState>
        )}
      </Card>
    </>
  );
}

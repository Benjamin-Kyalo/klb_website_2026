import { useCallback, useEffect, useMemo, useState } from "react";
import { admin } from "../lib/api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useOptions } from "../context/OptionsContext.jsx";
import { Alert, Card, EmptyState, Field, PageHead } from "./AdminUI.jsx";

const GROUPS = [
  { value: "news_category", label: "News category" },
  { value: "publication_category", label: "Catalogue category" },
  { value: "collection", label: "Catalogue collection" },
  { value: "department", label: "Department" },
  { value: "job_location", label: "Job location" },
  { value: "employment_type", label: "Employment type" },
  { value: "tender_category", label: "Tender category" },
  { value: "resource_category", label: "Resource category" },
  { value: "event_category", label: "Event category" },
];

const GROUP_LABELS = Object.fromEntries(GROUPS.map((group) => [group.value, group.label]));

function OptionForm({ option, defaultGroup, onSave, onCancel }) {
  const [values, setValues] = useState({
    group: option?.group || defaultGroup || "news_category",
    value: option?.value || "",
    label: option?.label || "",
    sort_order: option?.sort_order ?? 0,
    is_active: option?.is_active ?? true,
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function setValue(name, value) {
    setValues((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    if (!values.label.trim()) {
      setError("Enter a label for this option.");
      return;
    }
    setBusy(true);
    try {
      await onSave({
        group: values.group,
        value: values.value.trim(),
        label: values.label.trim(),
        sort_order: Number(values.sort_order) || 0,
        is_active: Boolean(values.is_active),
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="record-form" onSubmit={handleSubmit} noValidate>
      {error ? (
        <div className="admin-flash admin-flash--error" role="alert">
          {error}
        </div>
      ) : null}
      <div className="field-row">
        <Field label="List" htmlFor="option-group" required hint="The form field this option belongs to.">
          <select
            id="option-group"
            value={values.group}
            disabled={Boolean(option)}
            onChange={(event) => setValue("group", event.target.value)}
          >
            {GROUPS.map((group) => (
              <option value={group.value} key={group.value}>
                {group.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Label" htmlFor="option-label" required hint="What editors see in the dropdown.">
          <input
            id="option-label"
            type="text"
            value={values.label}
            onChange={(event) => setValue("label", event.target.value)}
          />
        </Field>
        <Field
          label="Stored value"
          htmlFor="option-value"
          hint="Leave blank to generate one from the label. Changing this can affect existing records."
        >
          <input
            id="option-value"
            type="text"
            value={values.value}
            onChange={(event) => setValue("value", event.target.value)}
          />
        </Field>
        <Field label="Sort order" htmlFor="option-sort" hint="Lower numbers appear first.">
          <input
            id="option-sort"
            type="number"
            min="0"
            value={values.sort_order}
            onChange={(event) => setValue("sort_order", event.target.value)}
          />
        </Field>
      </div>
      <label className="check" htmlFor="option-active">
        <input
          id="option-active"
          type="checkbox"
          checked={values.is_active}
          onChange={(event) => setValue("is_active", event.target.checked)}
        />
        <span>Available in dashboard dropdowns</span>
      </label>
      <div className="form-actions">
        <button className="btn btn--primary" type="submit" disabled={busy}>
          {busy ? "Saving…" : option ? "Save option" : "Add option"}
        </button>
        <button className="btn btn--secondary" type="button" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
      </div>
    </form>
  );
}

export default function AdminOptions() {
  const { can } = useAuth();
  const { reload: reloadOptions } = useOptions();
  const [options, setOptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [editing, setEditing] = useState(null);
  const [filter, setFilter] = useState("");

  const canCreate = can("options", "create");
  const canEdit = can("options", "edit");
  const canDelete = can("options", "delete");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setOptions(await admin.all("options"));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function refreshOptions() {
    await load();
    await reloadOptions();
  }

  async function handleSave(payload) {
    if (editing?.id) {
      await admin.options.update(editing.id, payload);
      setNotice("Option updated.");
    } else {
      await admin.options.create(payload);
      setNotice("Option added.");
    }
    setEditing(null);
    await refreshOptions();
  }

  async function handleDelete(option) {
    if (!window.confirm(`Remove “${option.label}” from ${GROUP_LABELS[option.group] || option.group}?`)) return;
    try {
      await admin.options.remove(option.id);
      setNotice("Option removed.");
      await refreshOptions();
    } catch (err) {
      setError(err.message);
    }
  }

  const groups = useMemo(() => {
    const visible = filter ? options.filter((option) => option.group === filter) : options;
    return GROUPS.map((group) => ({
      ...group,
      options: visible
        .filter((option) => option.group === group.value)
        .sort((a, b) => a.sort_order - b.sort_order || a.label.localeCompare(b.label)),
    })).filter((group) => group.options.length || group.value === filter);
  }, [options, filter]);

  return (
    <>
      <PageHead
        title="Dropdown options"
        lead="Manage the standard choices offered in forms. Keeping these lists tidy makes content consistent across the website."
        actions={
          canCreate ? (
            <button className="btn btn--primary" type="button" onClick={() => setEditing({})}>
              New option
            </button>
          ) : null
        }
      />

      <Alert kind="success" onClose={() => setNotice("")}>
        {notice}
      </Alert>
      <Alert kind="error" onClose={() => setError("")}>
        {error}
      </Alert>

      {editing ? (
        <Card title={editing.id ? `Edit ${editing.label}` : "New option"}>
          <OptionForm
            option={editing.id ? editing : null}
            defaultGroup={filter || "news_category"}
            onSave={handleSave}
            onCancel={() => setEditing(null)}
          />
        </Card>
      ) : null}

      {!canCreate && !canEdit ? (
        <Alert kind="warn">
          Your account can use these options but cannot add or change them. Ask an administrator if a
          new choice is needed.
        </Alert>
      ) : null}

      <Card title="Standard choices">
        <div className="admin-toolbar options-toolbar">
          <label className="inline-field" htmlFor="option-filter">
            <span>Show</span>
            <select id="option-filter" value={filter} onChange={(event) => setFilter(event.target.value)}>
              <option value="">All lists</option>
              {GROUPS.map((group) => (
                <option value={group.value} key={group.value}>
                  {group.label}
                </option>
              ))}
            </select>
          </label>
          <p className="muted-meta">{options.length} options across {GROUPS.length} lists</p>
        </div>

        {loading ? (
          <p className="muted-meta">Loading options…</p>
        ) : groups.length ? (
          groups.map((group) => (
            <section className="option-group" key={group.value}>
              <div className="option-group__head">
                <h3>{group.label}</h3>
                <span className="muted-meta">{group.options.length} options</span>
              </div>
              <div className="table-wrap">
                <table className="admin-table admin-table--compact">
                  <thead>
                    <tr>
                      <th>Label</th>
                      <th>Stored value</th>
                      <th>Order</th>
                      <th>Status</th>
                      {(canEdit || canDelete) && <th className="admin-table__actions">Actions</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {group.options.map((option) => (
                      <tr key={option.id}>
                        <td className="admin-table__title">{option.label}</td>
                        <td className="mono">{option.value || "—"}</td>
                        <td>{option.sort_order}</td>
                        <td>
                          {option.is_active ? (
                            <span className="badge badge--published">Available</span>
                          ) : (
                            <span className="badge badge--muted">Hidden</span>
                          )}
                        </td>
                        {(canEdit || canDelete) && (
                          <td className="admin-table__actions">
                            {canEdit ? (
                              <button
                                className="btn btn--secondary btn--sm"
                                type="button"
                                onClick={() => setEditing(option)}
                              >
                                Edit
                              </button>
                            ) : null}
                            {canDelete ? (
                              <button
                                className="btn btn--danger btn--sm"
                                type="button"
                                onClick={() => handleDelete(option)}
                              >
                                Remove
                              </button>
                            ) : null}
                          </td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          ))
        ) : (
          <EmptyState title="No options in this list yet.">
            Add a choice so it appears in the matching dashboard form.
          </EmptyState>
        )}
      </Card>
    </>
  );
}

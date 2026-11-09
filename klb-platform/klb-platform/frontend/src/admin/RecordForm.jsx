import { useEffect, useRef, useState } from "react";
import { admin } from "../lib/api.js";
import { safeImagePath } from "../lib/format.js";
import { useOptions } from "../context/OptionsContext.jsx";
import { Field } from "./AdminUI.jsx";

const OTHER = "__other__";

function toFormValue(field, value) {
  if (field.type === "tags") return Array.isArray(value) ? value.join(", ") : value || "";
  if (field.type === "json") return value ? JSON.stringify(value, null, 2) : "";
  if (value === null || value === undefined) return field.type === "checkbox" ? false : "";
  return value;
}

function fromFormValue(field, value) {
  if (field.type === "checkbox") return Boolean(value);
  if (field.type === "number") return value === "" ? null : Number(value);
  if (field.type === "tags")
    return String(value)
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);
  if (field.type === "json") {
    if (!String(value).trim()) return field.name === "settings" ? {} : [];
    return JSON.parse(value);
  }
  return value;
}

export function RichTextEditor({ id, value, onChange, rows = 10 }) {
  const ref = useRef(null);

  useEffect(() => {
    if (ref.current && ref.current.innerHTML !== value && document.activeElement !== ref.current) {
      ref.current.innerHTML = value || "";
    }
  }, [value]);

  function run(command, argument = null) {
    const editor = ref.current;
    if (!editor) return;
    editor.focus();
    document.execCommand(command, false, argument);
    onChange(editor.innerHTML);
  }

  function addLink() {
    const url = window.prompt("Link address (https://…)");
    if (url) run("createLink", url);
  }

  return (
    <div className="rich-editor" style={{ "--editor-rows": rows }}>
      <div className="rich-editor__toolbar" role="toolbar" aria-label="Text formatting">
        <button type="button" onClick={() => run("bold")} title="Bold" aria-label="Bold">
          <strong>B</strong>
        </button>
        <button type="button" onClick={() => run("italic")} title="Italic" aria-label="Italic">
          <em>I</em>
        </button>
        <button type="button" onClick={() => run("formatBlock", "<h2>")} title="Heading 2">
          H2
        </button>
        <button type="button" onClick={() => run("formatBlock", "<h3>")} title="Heading 3">
          H3
        </button>
        <button type="button" onClick={() => run("formatBlock", "<p>")} title="Paragraph">
          P
        </button>
        <button type="button" onClick={() => run("insertUnorderedList")} title="Bulleted list" aria-label="Bulleted list">
          • List
        </button>
        <button type="button" onClick={() => run("insertOrderedList")} title="Numbered list" aria-label="Numbered list">
          1. List
        </button>
        <button type="button" onClick={addLink} title="Add link">
          Link
        </button>
        <button type="button" onClick={() => run("removeFormat")} title="Clear formatting">
          Clear
        </button>
      </div>
      <div
        id={id}
        ref={ref}
        className="rich-editor__surface"
        contentEditable
        role="textbox"
        aria-multiline="true"
        suppressContentEditableWarning
        onInput={(event) => onChange(event.currentTarget.innerHTML)}
        onBlur={(event) => onChange(event.currentTarget.innerHTML)}
      />
      <p className="hint">
        Use the toolbar to format text. Unsafe markup is removed automatically when the record is saved.
      </p>
    </div>
  );
}

function HtmlField({ id, value, onChange, rows = 10 }) {
  const [preview, setPreview] = useState(false);
  return (
    <>
      <textarea
        id={id}
        className="source-editor__textarea"
        rows={rows}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        spellCheck="false"
      />
      <div className="html-field__actions">
        <button type="button" className="btn btn--secondary btn--sm" onClick={() => setPreview((open) => !open)}>
          {preview ? "Hide preview" : "Preview HTML"}
        </button>
        <span className="hint">Scripts are removed automatically when you save.</span>
      </div>
      {preview ? (
        <div className="admin-html-preview" dangerouslySetInnerHTML={{ __html: value }} />
      ) : null}
    </>
  );
}

function FileField({ id, value, onChange, accept = "image/*,.pdf", label = "Upload file" }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function handleFile(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const data = await admin.upload(file);
      onChange(data.url);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
      event.target.value = "";
    }
  }

  const isImage = value && !/\.pdf(\?|$)/i.test(value);

  return (
    <div className="upload-field">
      <div className="upload-field__row">
        <label className="sr-only" htmlFor={id}>
          {label}
        </label>
        <input id={id} type="file" accept={accept} onChange={handleFile} disabled={busy} />
        {busy ? <span className="hint">Uploading…</span> : null}
      </div>
      {error ? <span className="field-error">{error}</span> : null}
      {isImage ? <img className="upload-preview" src={safeImagePath(value)} alt="" /> : null}
    </div>
  );
}

export default function RecordForm({
  fields,
  initial,
  onSubmit,
  onCancel,
  submitLabel = "Save changes",
  canPublish = true,
}) {
  const { optionsFor } = useOptions();

  const fieldOptions = (field) => {
    const source = field.optionsGroup ? optionsFor(field.optionsGroup) : field.options || [];
    return Array.isArray(source) ? source : [];
  };

  const [values, setValues] = useState(() => {
    const output = {};
    fields.forEach((field) => {
      const raw = initial?.[field.name] ?? field.defaultValue;
      if (field.allowOther) {
        const options = field.optionsGroup ? optionsFor(field.optionsGroup) : field.options || [];
        const matches = options.some((option) => String(option.value) === String(raw));
        output[field.name] = raw === "" || raw === null || raw === undefined || matches ? raw ?? "" : OTHER;
        output[`${field.name}__other`] = matches || raw === undefined || raw === null ? "" : raw;
      } else {
        output[field.name] = toFormValue(field, raw);
      }
    });
    return output;
  });
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  // Options are bundled with the app and then refreshed from the API. When the
  // refreshed lists arrive, an existing custom value may turn out to be one of
  // the configured choices, so move it back from the "Other" input.
  const optionSignature = fields
    .filter((field) => field.optionsGroup)
    .map((field) => `${field.name}:${fieldOptions(field).map((option) => option.value).join("|")}`)
    .join(";");

  useEffect(() => {
    setValues((current) => {
      let changed = false;
      const next = { ...current };
      fields.forEach((field) => {
        if (!field.allowOther || current[field.name] !== OTHER) return;
        const custom = current[`${field.name}__other`];
        const match = fieldOptions(field).find(
          (option) => String(option.value) === String(custom)
        );
        if (match) {
          next[field.name] = match.value;
          next[`${field.name}__other`] = "";
          changed = true;
        }
      });
      return changed ? next : current;
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [optionSignature]);

  function setValue(name, value) {
    setValues((current) => ({ ...current, [name]: value }));
  }

  function resolvedValue(field) {
    const raw = values[field.name];
    if (field.allowOther && raw === OTHER) return String(values[`${field.name}__other`] ?? "").trim();
    return raw;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setErrors({});
    setMessage("");

    const validation = {};
    fields.forEach((field) => {
      if (field.readOnly || !field.required) return;
      const value = resolvedValue(field);
      if (value === "" || value === null || value === undefined) {
        validation[field.name] = "This field is required.";
      }
    });

    const payload = {};
    try {
      fields.forEach((field) => {
        if (field.readOnly) return;
        payload[field.name] = fromFormValue(field, resolvedValue(field));
      });
    } catch {
      setMessage("One of the JSON fields is not valid JSON. Check the brackets and quotes.");
      return;
    }

    if (Object.keys(validation).length) {
      setErrors(validation);
      setMessage("Please complete the required fields highlighted below.");
      return;
    }

    setBusy(true);
    try {
      await onSubmit(payload);
    } catch (err) {
      setMessage(err.message || "The record could not be saved.");
      if (err.fields) setErrors(err.fields);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="record-form" noValidate>
      {message ? (
        <div className="admin-flash admin-flash--error" role="alert">
          {message}
        </div>
      ) : null}

      <div className="field-row">
        {fields.map((field) => {
          const id = `field-${field.name}`;
          const raw = values[field.name];
          const rawError = errors[field.name];
          const fieldError = Array.isArray(rawError) ? rawError[0] : rawError;
          const wrapperClass = field.full ? "field--full" : "";
          const options = fieldOptions(field);
          const publishLocked = field.publish && !canPublish;
          const lockedHint = publishLocked
            ? "Your account does not have permission to change publication status."
            : "";

          if (field.type === "checkbox") {
            return (
              <Field key={field.name} className={wrapperClass}>
                <label className="check" htmlFor={id}>
                  <input
                    id={id}
                    type="checkbox"
                    checked={Boolean(raw)}
                    disabled={publishLocked || busy}
                    onChange={(event) => setValue(field.name, event.target.checked)}
                  />
                  <span>{field.label}</span>
                </label>
                {field.hint ? <span className="hint">{field.hint}</span> : null}
                {lockedHint ? <span className="hint hint--warn">{lockedHint}</span> : null}
                {fieldError ? <span className="field-error">{fieldError}</span> : null}
              </Field>
            );
          }

          if (field.type === "select") {
            const hasCurrent = options.some((option) => String(option.value) === String(raw));
            return (
              <Field
                key={field.name}
                label={field.label}
                htmlFor={id}
                hint={field.hint}
                error={fieldError}
                className={wrapperClass}
                required={field.required}
              >
                <select
                  id={id}
                  value={raw}
                  required={field.required}
                  disabled={publishLocked || busy}
                  onChange={(event) => setValue(field.name, event.target.value)}
                >
                  <option value="">Choose…</option>
                  {raw && !hasCurrent ? <option value={raw}>{raw}</option> : null}
                  {options.map((option) => (
                    <option value={option.value} key={option.value}>
                      {option.label}
                    </option>
                  ))}
                  {field.allowOther ? <option value={OTHER}>Other (enter below)</option> : null}
                </select>
                {field.allowOther && raw === OTHER ? (
                  <input
                    className="select-other"
                    type="text"
                    value={values[`${field.name}__other`] || ""}
                    placeholder={field.otherPlaceholder || "Enter a new value"}
                    aria-label={`${field.label} other value`}
                    onChange={(event) => setValue(`${field.name}__other`, event.target.value)}
                  />
                ) : null}
                {lockedHint ? <span className="hint hint--warn">{lockedHint}</span> : null}
              </Field>
            );
          }

          return (
            <Field
              key={field.name}
              label={field.label}
              htmlFor={id}
              hint={field.hint}
              error={fieldError}
              className={wrapperClass}
              required={field.required}
            >
              {field.type === "richtext" ? (
                <RichTextEditor
                  id={id}
                  value={raw}
                  onChange={(value) => setValue(field.name, value)}
                  rows={field.rows || 12}
                />
              ) : field.type === "textarea" || field.type === "html" || field.type === "json" ? (
                field.type === "html" ? (
                  <HtmlField id={id} value={raw} onChange={(value) => setValue(field.name, value)} rows={field.rows || 12} />
                ) : (
                  <textarea
                    id={id}
                    rows={field.rows || (field.type === "json" ? 8 : 4)}
                    value={raw}
                    placeholder={field.placeholder}
                    className={field.type === "json" ? "mono" : undefined}
                    onChange={(event) => setValue(field.name, event.target.value)}
                    spellCheck={field.type !== "json"}
                  />
                )
              ) : field.type === "file" ? (
                <>
                  <input
                    id={id}
                    type="text"
                    value={raw}
                    placeholder={field.placeholder || "Upload a file or paste a path"}
                    onChange={(event) => setValue(field.name, event.target.value)}
                  />
                  <FileField
                    id={`${id}-upload`}
                    value={raw}
                    label={`Upload ${field.label}`}
                    onChange={(url) => setValue(field.name, url)}
                    accept={field.accept}
                  />
                </>
              ) : (
                <input
                  id={id}
                  type={
                    field.type === "password"
                      ? "password"
                      : field.type === "number"
                        ? "number"
                        : field.type === "date"
                          ? "date"
                          : field.type === "email"
                            ? "email"
                            : field.type === "url"
                              ? "url"
                              : "text"
                  }
                  value={raw}
                  placeholder={field.placeholder}
                  step={field.step}
                  min={field.min}
                  required={field.required}
                  autoComplete={field.autoComplete}
                  onChange={(event) => setValue(field.name, event.target.value)}
                />
              )}
            </Field>
          );
        })}
      </div>

      <div className="form-actions">
        <button className="btn btn--primary" type="submit" disabled={busy}>
          {busy ? "Saving…" : submitLabel}
        </button>
        {onCancel ? (
          <button className="btn btn--secondary" type="button" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
        ) : null}
      </div>
    </form>
  );
}

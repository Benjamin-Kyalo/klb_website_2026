import { Link } from "react-router-dom";

export function PageHead({ title, lead, actions }) {
  return (
    <div className="admin-pagehead">
      <div>
        <h1>{title}</h1>
        {lead ? <p className="admin-lead">{lead}</p> : null}
      </div>
      {actions ? <div className="admin-pagehead__actions">{actions}</div> : null}
    </div>
  );
}

export function Card({ title, actions, children, className = "" }) {
  return (
    <section className={`admin-card ${className}`.trim()}>
      {title || actions ? (
        <div className="admin-card__head">
          {title ? <h2>{title}</h2> : <span />}
          {actions}
        </div>
      ) : null}
      {children}
    </section>
  );
}

export function Alert({ kind = "success", children, onClose }) {
  if (!children) return null;
  const cls =
    kind === "error" ? "admin-flash admin-flash--error" : kind === "warn" ? "admin-flash admin-flash--warn" : "admin-flash";
  return (
    <div className={cls} role={kind === "error" ? "alert" : "status"}>
      {children}
      {onClose ? (
        <button type="button" className="admin-flash__close" onClick={onClose} aria-label="Dismiss">
          ×
        </button>
      ) : null}
    </div>
  );
}

export function Field({ label, htmlFor, hint, error, children, className = "", required = false }) {
  return (
    <div className={`field${required ? " field--required" : ""} ${className}`.trim()}>
      {label ? (
        <label htmlFor={htmlFor}>
          {label}
          {required ? (
            <span className="field__required" aria-hidden="true">
              {" "}
              *
            </span>
          ) : null}
        </label>
      ) : null}
      {children}
      {hint ? <span className="hint">{hint}</span> : null}
      {error ? <span className="field-error">{error}</span> : null}
    </div>
  );
}

export function EmptyState({ title, children, action }) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      {children ? <p>{children}</p> : null}
      {action}
    </div>
  );
}

export function BackLink({ to, children = "Back" }) {
  return (
    <Link className="admin-backlink" to={to}>
      ← {children}
    </Link>
  );
}

export function StatusBadge({ status }) {
  const label = status === "published" ? "published" : status === "draft" ? "draft" : status === "new" ? "closing soon" : status === "expired" ? "expired" : status;
  const cls = status === "published" ? "published" : status === "draft" ? "draft" : status === "new" ? "warn" : status === "expired" ? "muted" : "muted";
  return <span className={`badge badge--${cls}`}>{label}</span>;
}

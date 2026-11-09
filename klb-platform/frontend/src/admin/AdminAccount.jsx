import { useState } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import { auth } from "../lib/api.js";
import { formatDate } from "../lib/format.js";
import { ACTION_LABELS, MODULES } from "../lib/permissions.js";
import { Alert, Card, Field, PageHead } from "./AdminUI.jsx";

export default function AdminAccount() {
  const { user, refresh, permissions, roleLabel, isSuperAdministrator } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setNotice("");

    if (next.length < 10) {
      setError("Choose a password with at least 10 characters.");
      return;
    }
    if (next !== confirm) {
      setError("The new passwords do not match.");
      return;
    }

    setBusy(true);
    try {
      const data = await auth.changePassword(current, next);
      setNotice(data.detail || "Password updated.");
      setCurrent("");
      setNext("");
      setConfirm("");
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHead
        title="Your account"
        lead="Details of the account you are signed in with, and the password used to access the dashboard."
      />

      <Alert kind="success" onClose={() => setNotice("")}>
        {notice}
      </Alert>
      <Alert kind="error" onClose={() => setError("")}>
        {error}
      </Alert>

      <div className="admin-split">
        <Card title="Change password">
          <form onSubmit={handleSubmit} className="record-form">
            <Field label="Current password" htmlFor="current-password">
              <input
                id="current-password"
                type="password"
                value={current}
                onChange={(event) => setCurrent(event.target.value)}
                autoComplete="current-password"
                required
              />
            </Field>
            <Field label="New password" htmlFor="new-password" hint="At least 10 characters.">
              <input
                id="new-password"
                type="password"
                value={next}
                onChange={(event) => setNext(event.target.value)}
                autoComplete="new-password"
                required
              />
            </Field>
            <Field label="Confirm new password" htmlFor="confirm-password">
              <input
                id="confirm-password"
                type="password"
                value={confirm}
                onChange={(event) => setConfirm(event.target.value)}
                autoComplete="new-password"
                required
              />
            </Field>
            <div className="form-actions">
              <button className="btn btn--primary" type="submit" disabled={busy}>
                {busy ? "Updating…" : "Update password"}
              </button>
            </div>
          </form>
        </Card>

        <Card title="Account details">
          <dl className="admin-facts admin-facts--stacked">
            <div>
              <dt>Name</dt>
              <dd>{user?.display_name || "—"}</dd>
            </div>
            <div>
              <dt>Email</dt>
              <dd>{user?.email || "—"}</dd>
            </div>
            <div>
              <dt>Username</dt>
              <dd>{user?.username || "—"}</dd>
            </div>
            <div>
              <dt>Role</dt>
              <dd>
                <span className={`role-badge role-badge--${user?.role || "editor"}`}>{roleLabel}</span>
              </dd>
            </div>
            <div>
              <dt>Last signed in</dt>
              <dd>{user?.last_login ? formatDate(user.last_login) : "—"}</dd>
            </div>
          </dl>
          <p className="muted-meta" style={{ marginTop: "1rem" }}>
            Ask an administrator to change your name, email address or role.
          </p>
        </Card>
      </div>

      <Card title="Your access">
        {isSuperAdministrator ? (
          <p className="muted-meta">
            As a Super Administrator you have full access to every module, including user
            management, site settings and the activity log.
          </p>
        ) : (
          <p className="muted-meta">
            These are the actions your account can perform. Contact an administrator if you need more
            access.
          </p>
        )}
        <ul className="access-list">
          {MODULES.map((module) => {
            const granted = permissions?.[module.key] || [];
            return (
              <li key={module.key}>
                <span className="access-list__module">{module.label}</span>
                <span className="access-list__actions">
                  {granted.length
                    ? granted.map((action) => (
                        <span className="permission-chip" key={action}>
                          {ACTION_LABELS[action] || action}
                        </span>
                      ))
                    : <span className="muted-meta">No access</span>}
                </span>
              </li>
            );
          })}
        </ul>
      </Card>
    </>
  );
}

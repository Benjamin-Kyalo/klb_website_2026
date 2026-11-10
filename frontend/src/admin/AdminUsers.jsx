import { useCallback, useEffect, useMemo, useState } from "react";
import { admin } from "../lib/api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { formatDate } from "../lib/format.js";
import { ACTION_LABELS, ROLE_LABELS } from "../lib/permissions.js";
import { Alert, Card, EmptyState, Field, PageHead } from "./AdminUI.jsx";

const EMPTY_USER = {
  full_name: "",
  username: "",
  email: "",
  role: "editor",
  is_active: true,
  is_suspended: false,
};

function samePermissions(a, b) {
  const keys = new Set([...Object.keys(a || {}), ...Object.keys(b || {})]);
  for (const key of keys) {
    const left = [...(a?.[key] || [])].sort().join(",");
    const right = [...(b?.[key] || [])].sort().join(",");
    if (left !== right) return false;
  }
  return true;
}

function defaultMatrix(defaults, role) {
  return JSON.parse(JSON.stringify(defaults?.[role] || defaults?.editor || {}));
}

function errorText(value) {
  return Array.isArray(value) ? value[0] : value;
}

function PermissionMatrix({ modules, value, onChange, disabled, lockedModules = [] }) {
  const locked = useMemo(() => new Set(lockedModules), [lockedModules]);
  const groups = useMemo(() => {
    const output = [];
    modules.forEach((module) => {
      let group = output.find((item) => item.label === module.group);
      if (!group) {
        group = { label: module.group, modules: [] };
        output.push(group);
      }
      group.modules.push(module);
    });
    return output;
  }, [modules]);

  function toggle(module, action) {
    if (disabled) return;
    const current = value?.[module] || [];
    const next = current.includes(action)
      ? current.filter((item) => item !== action)
      : [...current, action];
    onChange({ ...value, [module]: next });
  }

  return (
    <div className="permission-matrix">
      {groups.map((group) => (
        <section className="permission-matrix__group" key={group.label}>
          <h3>{group.label}</h3>
          <div className="permission-matrix__scroll">
            <table className="permission-table">
              <thead>
                <tr>
                  <th scope="col">Module</th>
                  {["view", "create", "edit", "delete", "publish"].map((action) => (
                    <th scope="col" key={action}>
                      {ACTION_LABELS[action]}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {group.modules.map((module) => (
                  <tr key={module.key}>
                    <th scope="row">{module.label}</th>
                    {["view", "create", "edit", "delete", "publish"].map((action) => {
                      const available = module.actions.includes(action);
                      const checked = (value?.[module.key] || []).includes(action);
                      const blocked = locked.has(module.key);
                      return (
                        <td key={action}>
                          {available ? (
                            <label className={`permission-check${blocked ? " is-locked" : ""}`}>
                              <input
                                type="checkbox"
                                checked={checked && !blocked}
                                disabled={disabled || blocked}
                                title={blocked ? "This module is not available to Editors." : undefined}
                                onChange={() => toggle(module.key, action)}
                              />
                              <span className="sr-only">
                                {module.label}: {ACTION_LABELS[action]}
                              </span>
                            </label>
                          ) : (
                            <span className="permission-na" aria-hidden="true">
                              ·
                            </span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ))}
    </div>
  );
}

function UserForm({ user, meta, currentUserId, onSave, onCancel }) {
  const isSelf = user?.id === currentUserId;
  const canManageSuperAdmins = Boolean(meta?.canManageSuperAdmins);
  const modules = meta?.modules || [];
  const defaults = meta?.defaults || {};
  const editorModules = meta?.editorModules || [];

  const roleOptions = useMemo(() => {
    const options = [
      { value: "editor", label: "Editor" },
      { value: "admin", label: "Administrator" },
      { value: "super_admin", label: "Super Administrator" },
    ].filter((option) => canManageSuperAdmins || option.value === "editor");
    if (user && !options.some((option) => option.value === user.role)) {
      options.push({ value: user.role, label: ROLE_LABELS[user.role] || user.role });
    }
    return options;
  }, [canManageSuperAdmins, user]);

  const [values, setValues] = useState(() => ({
    ...EMPTY_USER,
    ...(user || {}),
    password: "",
  }));
  const initialRole = user?.role || "editor";
  const [custom, setCustom] = useState(
    Boolean(user?.permissions) && !samePermissions(user.permissions, defaults[initialRole])
  );
  const [matrix, setMatrix] = useState(() =>
    user?.permissions || defaultMatrix(defaults, initialRole)
  );
  const [errors, setErrors] = useState({});
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const roleLocked = isSelf;
  const matrixLocked = values.role === "super_admin";
  const lockedModules =
    values.role === "editor"
      ? modules.filter((module) => !editorModules.includes(module.key)).map((module) => module.key)
      : [];

  function setValue(name, value) {
    setValues((current) => ({ ...current, [name]: value }));
  }

  function handleRole(role) {
    setValue("role", role);
    if (!custom) setMatrix(defaultMatrix(defaults, role));
  }

  function toggleCustom(checked) {
    setCustom(checked);
    if (checked && (!matrix || !Object.keys(matrix).length)) {
      setMatrix(defaultMatrix(defaults, values.role));
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setErrors({});
    setMessage("");

    const validation = {};
    if (!values.full_name.trim()) validation.full_name = "Enter the person's full name.";
    if (!values.email.trim()) validation.email = "Enter an email address.";
    if (!user && (!values.password || values.password.length < 10)) {
      validation.password = "Choose a password with at least 10 characters.";
    }
    if (user && values.password && values.password.length < 10) {
      validation.password = "Choose a password with at least 10 characters.";
    }
    if (Object.keys(validation).length) {
      setErrors(validation);
      setMessage("Please complete the highlighted fields.");
      return;
    }

    const payload = {
      full_name: values.full_name.trim(),
      username: values.username.trim(),
      email: values.email.trim(),
      role: values.role,
      is_active: Boolean(values.is_active),
      is_suspended: Boolean(values.is_suspended),
      permissions: custom ? matrix : defaultMatrix(defaults, values.role),
    };
    if (values.password) payload.password = values.password;

    setBusy(true);
    try {
      await onSave(payload);
    } catch (err) {
      setMessage(err.message || "The account could not be saved.");
      if (err.fields) setErrors(err.fields);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="record-form user-form" onSubmit={handleSubmit} noValidate>
      {message ? (
        <div className="admin-flash admin-flash--error" role="alert">
          {message}
        </div>
      ) : null}

      <div className="field-row">
        <Field label="Full name" htmlFor="user-full-name" required error={errorText(errors.full_name)}>
          <input
            id="user-full-name"
            type="text"
            value={values.full_name}
            autoComplete="name"
            onChange={(event) => setValue("full_name", event.target.value)}
          />
        </Field>
        <Field
          label="Email address"
          htmlFor="user-email"
          required
          error={errorText(errors.email)}
          hint="Used to sign in and to send password resets."
        >
          <input
            id="user-email"
            type="email"
            value={values.email}
            autoComplete="email"
            onChange={(event) => setValue("email", event.target.value)}
          />
        </Field>
        <Field
          label="Username"
          htmlFor="user-username"
          error={errorText(errors.username)}
          hint="Optional. Generated from the email address when left blank."
        >
          <input
            id="user-username"
            type="text"
            value={values.username}
            autoComplete="username"
            onChange={(event) => setValue("username", event.target.value)}
          />
        </Field>
        <Field
          label={user ? "New password (optional)" : "Password"}
          htmlFor="user-password"
          required={!user}
          error={errorText(errors.password)}
          hint="At least 10 characters. Leave blank when editing to keep the current password."
        >
          <input
            id="user-password"
            type="password"
            value={values.password}
            autoComplete="new-password"
            onChange={(event) => setValue("password", event.target.value)}
          />
        </Field>
        <Field
          label="Role"
          htmlFor="user-role"
          hint={
            roleLocked
              ? "You cannot change the role on the account you are signed in with."
              : "Role defaults are applied unless custom permissions are enabled."
          }
        >
          <select
            id="user-role"
            value={values.role}
            disabled={roleLocked}
            onChange={(event) => handleRole(event.target.value)}
          >
            {roleOptions.map((option) => (
              <option value={option.value} key={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>
        <div className="field">
          <span className="label">Account status</span>
          <label className="check" htmlFor="user-active">
            <input
              id="user-active"
              type="checkbox"
              checked={Boolean(values.is_active)}
              disabled={isSelf}
              onChange={(event) => setValue("is_active", event.target.checked)}
            />
            <span>Active — the account can sign in</span>
          </label>
          <label className="check" htmlFor="user-suspended">
            <input
              id="user-suspended"
              type="checkbox"
              checked={Boolean(values.is_suspended)}
              disabled={isSelf}
              onChange={(event) => setValue("is_suspended", event.target.checked)}
            />
            <span>Suspended — sign-in is blocked</span>
          </label>
        </div>
      </div>

      <div className="permission-heading">
        <div>
          <h3>Permissions</h3>
          <p className="muted-meta">
            {values.role === "super_admin"
              ? "Super Administrators always have full access to every module."
              : "Choose the actions this account may perform in each module."}
          </p>
        </div>
        {values.role !== "super_admin" ? (
          <label className="check" htmlFor="user-custom-permissions">
            <input
              id="user-custom-permissions"
              type="checkbox"
              checked={custom}
              onChange={(event) => toggleCustom(event.target.checked)}
            />
            <span>Use custom permissions</span>
          </label>
        ) : null}
      </div>

      <PermissionMatrix
        modules={modules}
        value={custom && values.role !== "super_admin" ? matrix : defaultMatrix(defaults, values.role)}
        onChange={setMatrix}
        disabled={!custom || matrixLocked}
        lockedModules={lockedModules}
      />

      <p className="muted-meta">
        Editors can never be granted system modules such as user management, the activity log, site
        settings or dropdown options, even if those boxes are selected.
      </p>

      <div className="form-actions">
        <button className="btn btn--primary" type="submit" disabled={busy}>
          {busy ? "Saving…" : user ? "Save account" : "Create account"}
        </button>
        <button className="btn btn--secondary" type="button" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
      </div>
    </form>
  );
}

function ResetPasswordForm({ user, onDone, onCancel }) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    if (password.length < 10) {
      setError("Choose a password with at least 10 characters.");
      return;
    }
    if (password !== confirm) {
      setError("The two passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      await admin.resetPassword(user.id, password);
      onDone(`Password reset for ${user.display_name}.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="record-form" onSubmit={handleSubmit}>
      <p className="muted-meta">
        Set a new password for <strong>{user.display_name}</strong> ({user.email}). Share it securely
        and ask them to change it after signing in.
      </p>
      {error ? (
        <div className="admin-flash admin-flash--error" role="alert">
          {error}
        </div>
      ) : null}
      <div className="field-row">
        <Field label="New password" htmlFor="reset-password" required hint="At least 10 characters.">
          <input
            id="reset-password"
            type="password"
            value={password}
            autoComplete="new-password"
            onChange={(event) => setPassword(event.target.value)}
          />
        </Field>
        <Field label="Confirm password" htmlFor="reset-password-confirm" required>
          <input
            id="reset-password-confirm"
            type="password"
            value={confirm}
            autoComplete="new-password"
            onChange={(event) => setConfirm(event.target.value)}
          />
        </Field>
      </div>
      <div className="form-actions">
        <button className="btn btn--primary" type="submit" disabled={busy}>
          {busy ? "Resetting…" : "Reset password"}
        </button>
        <button className="btn btn--secondary" type="button" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
      </div>
    </form>
  );
}

export default function AdminUsers() {
  const { user: currentUser, can } = useAuth();
  const [users, setUsers] = useState([]);
  const [meta, setMeta] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [editing, setEditing] = useState(null);
  const [resetting, setResetting] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [rows, permissions] = await Promise.all([
        admin.all("users", { search: appliedSearch }),
        meta ? Promise.resolve(meta) : admin.permissionsMeta(),
      ]);
      setUsers(rows);
      setMeta(permissions);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [appliedSearch, meta]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleSave(payload) {
    if (editing?.id) {
      await admin.update("users", editing.id, payload);
      setNotice(`${editing.display_name || editing.email} updated.`);
    } else {
      await admin.create("users", payload);
      setNotice("Account created.");
    }
    setEditing(null);
    await load();
  }

  async function toggleField(account, field, label) {
    try {
      await admin.update("users", account.id, { [field]: !account[field] });
      setNotice(`${account.display_name} ${label}.`);
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete(account) {
    if (!window.confirm(`Delete the account for ${account.display_name}? This cannot be undone.`)) return;
    try {
      await admin.remove("users", account.id);
      setNotice("Account deleted.");
      await load();
    } catch (err) {
      setError(err.message);
    }
  }

  const canManage = can("users", "create") || can("users", "edit");
  const canDelete = can("users", "delete");
  const privilegedTotal = users.filter((account) => account.role === "super_admin").length;

  return (
    <>
      <PageHead
        title="Users and permissions"
        lead="Create staff accounts, assign roles and decide exactly which modules each person may use. Changes take effect immediately."
        actions={
          can("users", "create") ? (
            <button className="btn btn--primary" type="button" onClick={() => setEditing({})}>
              New account
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
        <Card title={editing.id ? `Edit ${editing.display_name || editing.email}` : "New account"}>
          <UserForm
            user={editing.id ? editing : null}
            meta={meta}
            currentUserId={currentUser?.id}
            onSave={handleSave}
            onCancel={() => setEditing(null)}
          />
        </Card>
      ) : null}

      {resetting ? (
        <Card title={`Reset password: ${resetting.display_name}`}>
          <ResetPasswordForm
            user={resetting}
            onDone={(message) => {
              setResetting(null);
              setNotice(message);
            }}
            onCancel={() => setResetting(null)}
          />
        </Card>
      ) : null}

      <Card
        title={`${users.length} ${users.length === 1 ? "account" : "accounts"}`}
        actions={
          <form
            className="admin-search"
            onSubmit={(event) => {
              event.preventDefault();
              setAppliedSearch(search.trim());
            }}
          >
            <label className="sr-only" htmlFor="user-search">
              Search accounts
            </label>
            <input
              id="user-search"
              type="search"
              value={search}
              placeholder="Search name, email or username…"
              onChange={(event) => setSearch(event.target.value)}
            />
            <button className="btn btn--secondary btn--sm" type="submit">
              Search
            </button>
          </form>
        }
      >
        {loading ? (
          <p className="muted-meta">Loading accounts…</p>
        ) : users.length ? (
          <div className="table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Account</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Last signed in</th>
                  <th className="admin-table__actions">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((account) => {
                  const isSelf = account.id === currentUser?.id;
                  const isLastSuper =
                    account.role === "super_admin" && privilegedTotal <= 1;
                  return (
                    <tr key={account.id}>
                      <td className="admin-table__title">
                        {account.display_name}
                        <br />
                        <small className="mono">{account.email}</small>
                      </td>
                      <td>
                        <span className={`role-badge role-badge--${account.role}`}>
                          {account.role_label || ROLE_LABELS[account.role]}
                        </span>
                      </td>
                      <td>
                        {!account.is_active ? (
                          <span className="badge badge--muted">Deactivated</span>
                        ) : account.is_suspended ? (
                          <span className="badge badge--new">Suspended</span>
                        ) : (
                          <span className="badge badge--published">Active</span>
                        )}
                      </td>
                      <td>{account.last_login ? formatDate(account.last_login) : "Never"}</td>
                      <td className="admin-table__actions">
                        {can("users", "edit") ? (
                          <button
                            className="btn btn--secondary btn--sm"
                            type="button"
                            onClick={() => setEditing(account)}
                          >
                            Edit
                          </button>
                        ) : null}
                        {can("users", "edit") ? (
                          <button
                            className="btn btn--secondary btn--sm"
                            type="button"
                            onClick={() => setResetting(account)}
                          >
                            Reset password
                          </button>
                        ) : null}
                        {canManage && !isSelf ? (
                          <button
                            className="btn btn--secondary btn--sm"
                            type="button"
                            onClick={() =>
                              toggleField(
                                account,
                                "is_active",
                                account.is_active ? "deactivated" : "activated"
                              )
                            }
                          >
                            {account.is_active ? "Deactivate" : "Activate"}
                          </button>
                        ) : null}
                        {canManage && !isSelf ? (
                          <button
                            className="btn btn--secondary btn--sm"
                            type="button"
                            onClick={() =>
                              toggleField(
                                account,
                                "is_suspended",
                                account.is_suspended ? "reinstated" : "suspended"
                              )
                            }
                          >
                            {account.is_suspended ? "Reinstate" : "Suspend"}
                          </button>
                        ) : null}
                        {canDelete && !isSelf && !isLastSuper ? (
                          <button
                            className="btn btn--danger btn--sm"
                            type="button"
                            onClick={() => handleDelete(account)}
                          >
                            Delete
                          </button>
                        ) : null}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No accounts match this search.">
            Clear the search or create a new account.
          </EmptyState>
        )}
      </Card>
    </>
  );
}

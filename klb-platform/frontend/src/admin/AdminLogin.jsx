import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { Field } from "./AdminUI.jsx";

export default function AdminLogin() {
  const { user, loading, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (!loading && user) {
    return <Navigate to={location.state?.from || "/admin"} replace />;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email.trim(), password);
      navigate(location.state?.from || "/admin", { replace: true });
    } catch (err) {
      setError(err.message || "Could not sign in. Check your email and password.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="admin-login">
      <div className="admin-login__card">
        <div className="admin-login__brand">
          <span className="admin-login__logo">
            <img src="/assets/klb-emblem.png" alt="" width="482" height="482" />
          </span>
          <div>
            <strong>Content manager</strong>
            <small>Kenya Literature Bureau</small>
          </div>
        </div>
        <h1>Staff sign in</h1>
        <p className="admin-lead">Use the email and password issued by your site administrator.</p>

        {error ? (
          <div className="admin-flash admin-flash--error" role="alert">
            {error}
          </div>
        ) : null}

        <form onSubmit={handleSubmit}>
          <Field label="Email address" htmlFor="email">
            <input
              id="email"
              name="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              autoComplete="username"
              autoFocus
            />
          </Field>
          <Field label="Password" htmlFor="password">
            <input
              id="password"
              name="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              autoComplete="current-password"
            />
          </Field>
          <button className="btn btn--primary btn--block" type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="admin-login__note">
          <Link to="/">← Back to klb.co.ke</Link>
        </p>
      </div>
    </main>
  );
}

import { useState } from "react";
import { subscribe, unsubscribe } from "../lib/api.js";

export default function NewsletterForm() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState({ state: "idle", message: "" });
  const [busy, setBusy] = useState(false);

  const [showUnsubscribe, setShowUnsubscribe] = useState(false);
  const [unsubEmail, setUnsubEmail] = useState("");

  async function handleUnsubscribe(event) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    try {
      const data = await unsubscribe(unsubEmail);
      setStatus({ state: "success", message: data.detail });
      setUnsubEmail("");
      setShowUnsubscribe(false);
    } catch (error) {
      setStatus({ state: "error", message: error.message });
    } finally {
      setBusy(false);
    }
  }
  async function handleSubmit(event) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setStatus({ state: "idle", message: "Subscribing…" });
    try {
      const data = await subscribe(email);
      setStatus({ state: "success", message: data.detail });
      setEmail("");
    } catch (error) {
      setStatus({ state: "error", message: error.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <form className="newsletter-form" onSubmit={handleSubmit} noValidate>
        <label className="sr-only" htmlFor="newsletterEmail">
          Email address
        </label>
        <input
          id="newsletterEmail"
          name="email"
          type="email"
          placeholder="you@school.ac.ke"
          required
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          aria-describedby="newsletterStatus"
        />
        <button type="submit" disabled={busy}>
          {busy ? "Sending…" : "Subscribe"}
        </button>
      </form>
      <p
        className="newsletter-note"
        id="newsletterStatus"
        role="status"
        aria-live="polite"
        data-state={status.state === "idle" ? undefined : status.state}
        data-newsletter-status
      >
        {status.message || "Unsubscribe any time."}
      </p>
      <button
        type="button"
        className="newsletter-unsubscribe-toggle"
        onClick={() => setShowUnsubscribe(!showUnsubscribe)}
        style={{ background: "none", border: "none", color: "var(--blue, #0875b9)", cursor: "pointer", fontSize: "0.75rem", textDecoration: "underline", padding: 0, marginTop: "0.5rem" }}
      >
        {showUnsubscribe ? "Cancel" : "Unsubscribe"}
      </button>
      {showUnsubscribe ? (
        <form className="newsletter-form" onSubmit={handleUnsubscribe} noValidate style={{ marginTop: "0.5rem" }}>
          <label className="sr-only" htmlFor="unsubEmail">Email address</label>
          <input
            id="unsubEmail"
            type="email"
            placeholder="you@school.ac.ke"
            required
            value={unsubEmail}
            onChange={(event) => setUnsubEmail(event.target.value)}
          />
          <button type="submit" disabled={busy}>
            {busy ? "Processing…" : "Unsubscribe"}
          </button>
        </form>
      ) : null}
    </>
  );
}

import { useState } from "react";
import { subscribe } from "../lib/api.js";

export default function NewsletterForm() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState({ state: "idle", message: "" });
  const [busy, setBusy] = useState(false);

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
        {status.message || "We only use your email for KLB news. Unsubscribe any time."}
      </p>
    </>
  );
}

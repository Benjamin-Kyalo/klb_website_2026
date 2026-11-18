import { useEffect, useState } from "react";

/**
 * Share, copy-link and print actions for detail pages.
 *
 * Uses the native share sheet where the browser supports it, falls back to
 * copying the current address, and always announces the outcome through a
 * polite live region so keyboard and screen-reader users get feedback.
 */
export default function ShareActions({ title, path = "", label = "Share this page" }) {
  const [status, setStatus] = useState("");

  useEffect(() => {
    if (!status) return undefined;
    const timer = setTimeout(() => setStatus(""), 5000);
    return () => clearTimeout(timer);
  }, [status]);

  function currentUrl() {
    if (typeof window !== "undefined" && window.location) {
      return window.location.href;
    }
    return path;
  }

  async function copyLink() {
    const url = currentUrl();
    let copied = false;
    try {
      if (navigator.clipboard?.writeText) {
        await Promise.race([
          navigator.clipboard.writeText(url).then(() => {
            copied = true;
          }),
          new Promise((_, reject) => setTimeout(() => reject(new Error("Clipboard timeout")), 1500)),
        ]);
      }
    } catch {
      /* fall back to the legacy copy path below */
    }
    if (!copied && typeof document !== "undefined") {
      try {
        const field = document.createElement("textarea");
        field.value = url;
        field.setAttribute("readonly", "");
        field.style.position = "fixed";
        field.style.opacity = "0";
        document.body.appendChild(field);
        field.select();
        copied = document.execCommand("copy");
        field.remove();
      } catch {
        copied = false;
      }
    }
    setStatus(copied ? "Link copied to clipboard." : "Could not copy automatically. Copy the link from your address bar.");
  }

  async function share() {
    const url = currentUrl();
    if (navigator.share) {
      try {
        await navigator.share({ title, url });
        setStatus("Shared.");
        return;
      } catch (error) {
        if (error?.name === "AbortError") return;
      }
    }
    copyLink();
  }

  function print() {
    if (typeof window !== "undefined") window.print();
  }

  return (
    <div className="share-actions no-print" aria-label={label}>
      {typeof navigator !== "undefined" && navigator.share ? (
        <button className="btn btn--secondary btn--sm" type="button" onClick={share}>
          Share
        </button>
      ) : null}
      <button className="btn btn--secondary btn--sm" type="button" onClick={copyLink}>
        Copy link
      </button>
      <button className="btn btn--secondary btn--sm" type="button" onClick={print}>
        Print
      </button>
      <span className="share-actions__status" role="status" aria-live="polite">
        {status}
      </span>
    </div>
  );
}

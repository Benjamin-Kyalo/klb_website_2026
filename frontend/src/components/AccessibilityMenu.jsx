import { useCallback, useEffect, useRef, useState } from "react";
import {
  DEFAULT_A11Y,
  a11yActiveCount,
  applyA11yPrefs,
  loadA11yPrefs,
  resetA11yPrefs,
  saveA11yPrefs,
  stepTextScale,
} from "../lib/accessibility.js";

const TOGGLES = [
  {
    key: "contrast",
    label: "High contrast",
    note: "Stronger text and border contrast.",
  },
  {
    key: "dark",
    label: "Dark display",
    note: "Light text on dark surfaces.",
  },
  {
    key: "dyslexia",
    label: "Dyslexia-friendly text",
    note: "Wider, simpler letterforms.",
  },
  {
    key: "spacing",
    label: "More text spacing",
    note: "Roomier lines, words and paragraphs.",
  },
  {
    key: "underline",
    label: "Underline links",
    note: "Makes links easier to identify.",
  },
  {
    key: "grayscale",
    label: "Grayscale",
    note: "Removes colour distraction.",
  },
  {
    key: "reduceMotion",
    label: "Reduce motion",
    note: "Stops animation and smooth scrolling.",
  },
];

function AccessIcon() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">
      <circle cx="12" cy="4.4" r="2.1" fill="currentColor" />
      <path
        d="M4.3 8.2a1 1 0 0 1 1.2-.75l4.2.9h4.6l4.2-.9a1 1 0 1 1 .42 1.96l-3.62.78v2.2l1.9 6.7a1 1 0 0 1-1.92.56L12.75 13h-1.5l-2.55 6.65a1 1 0 0 1-1.92-.56l1.9-6.7v-2.2l-3.62-.78a1 1 0 0 1-.76-1.2Z"
        fill="currentColor"
      />
    </svg>
  );
}

export default function AccessibilityMenu() {
  const [prefs, setPrefs] = useState(loadA11yPrefs);
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [speaking, setSpeaking] = useState(false);
  const triggerRef = useRef(null);
  const panelRef = useRef(null);

  const update = useCallback((next, announcement) => {
    setPrefs(next);
    applyA11yPrefs(next);
    saveA11yPrefs(next);
    if (announcement) setMessage(announcement);
  }, []);

  const close = useCallback(() => {
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    setSpeaking(false);
    setOpen(false);
    window.setTimeout(() => triggerRef.current?.focus(), 0);
  }, []);

  const openMenu = useCallback(() => setOpen(true), []);

  useEffect(() => {
    const onExternalOpen = () => openMenu();
    window.addEventListener("klb:open-accessibility", onExternalOpen);
    return () => window.removeEventListener("klb:open-accessibility", onExternalOpen);
  }, [openMenu]);

  useEffect(() => {
    applyA11yPrefs(prefs);
  }, []); // Applied once here and immediately in main.jsx to avoid a flash.

  useEffect(() => {
    if (!open) return undefined;
    document.body.classList.add("a11y-panel-open");
    const timer = window.setTimeout(() => {
      const first = panelRef.current?.querySelector("button");
      first?.focus();
    }, 30);

    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        close();
        return;
      }
      if (event.key !== "Tab" || !panelRef.current) return;
      const focusable = Array.from(
        panelRef.current.querySelectorAll(
          'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])'
        )
      ).filter((node) => node.offsetParent !== null);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    return () => {
      window.clearTimeout(timer);
      document.removeEventListener("keydown", onKeyDown);
      document.body.classList.remove("a11y-panel-open");
    };
  }, [open, close]);

  function toggle(key, label) {
    const next = { ...prefs, [key]: !prefs[key] };
    // Dark display and high contrast are alternative colour schemes; turning
    // one on turns the other off so the result is predictable.
    if (key === "contrast" && next.contrast) next.dark = false;
    if (key === "dark" && next.dark) next.contrast = false;
    update(next, `${label} ${next[key] ? "turned on" : "turned off"}.`);
  }

  function changeSize(direction) {
    const next = stepTextScale(prefs, direction);
    if (next.textScale === prefs.textScale) return;
    update(next, `Text size set to ${next.textScale} percent.`);
  }

  function readAloud() {
    if (!("speechSynthesis" in window)) {
      setMessage("Text-to-speech is not supported in this browser.");
      return;
    }
    window.speechSynthesis.cancel();
    const source =
      document.querySelector("main") || document.querySelector("[role='main']") || document.body;
    const text = (source?.innerText || "").replace(/\\s+/g, " ").trim().slice(0, 6000);
    if (!text) {
      setMessage("There is no readable text on this page.");
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.speak(utterance);
    setMessage("Reading this page aloud.");
  }

  function stopReading() {
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    setSpeaking(false);
    setMessage("Stopped reading.");
  }

  function resetAll() {
    update(resetA11yPrefs(), "All accessibility preferences reset.");
  }

  const activeCount = a11yActiveCount(prefs);
  const canGrow = prefs.textScale < 150;
  const canShrink = prefs.textScale > 100;

  return (
    <>
      <button
        type="button"
        ref={triggerRef}
        className="a11y-trigger"
        aria-expanded={open}
        aria-controls="a11y-panel"
        onClick={() => (open ? close() : openMenu())}
      >
        <AccessIcon />
        <span>Accessibility</span>
        {activeCount ? (
          <span className="a11y-trigger__count" aria-label={`${activeCount} preferences on`}>
            {activeCount}
          </span>
        ) : null}
      </button>

      {open ? (
        <button
          type="button"
          className="a11y-scrim"
          aria-label="Close accessibility options"
          onClick={close}
        />
      ) : null}

      <div
        className={`a11y-panel${open ? " is-open" : ""}`}
        id="a11y-panel"
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="a11y-title"
        hidden={!open}
      >
        <div className="a11y-panel__head">
          <div>
            <h2 id="a11y-title">Accessibility options</h2>
            <p>Adjust how the website looks and moves. Preferences are saved on this device.</p>
          </div>
          <button type="button" className="a11y-close" onClick={close} aria-label="Close accessibility options">
            ×
          </button>
        </div>

        <div className="a11y-group">
          <h3>Text size</h3>
          <div className="a11y-size">
            <button
              type="button"
              className="a11y-size__btn"
              onClick={() => changeSize(-1)}
              disabled={!canShrink}
              aria-label="Decrease text size"
            >
              A−
            </button>
            <output className="a11y-size__value" aria-live="polite">
              {prefs.textScale}%
            </output>
            <button
              type="button"
              className="a11y-size__btn"
              onClick={() => changeSize(1)}
              disabled={!canGrow}
              aria-label="Increase text size"
            >
              A+
            </button>
            <button
              type="button"
              className="a11y-linkbtn"
              onClick={() => update({ ...prefs, textScale: DEFAULT_A11Y.textScale }, "Text size reset to 100 percent.")}
              disabled={prefs.textScale === DEFAULT_A11Y.textScale}
            >
              Reset size
            </button>
          </div>
        </div>

        <div className="a11y-group">
          <h3>Reading and display</h3>
          <div className="a11y-toggles">
            {TOGGLES.map((item) => (
              <button
                type="button"
                key={item.key}
                className={`a11y-toggle${prefs[item.key] ? " is-on" : ""}`}
                aria-pressed={prefs[item.key]}
                onClick={() => toggle(item.key, item.label)}
              >
                <span className="a11y-toggle__label">{item.label}</span>
                <span className="a11y-toggle__note">{item.note}</span>
                <span className="a11y-toggle__state" aria-hidden="true">
                  {prefs[item.key] ? "On" : "Off"}
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className="a11y-panel__foot">
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            onClick={speaking ? stopReading : readAloud}
          >
            {speaking ? "Stop reading" : "Read this page aloud"}
          </button>
          <button type="button" className="btn btn--secondary btn--sm" onClick={resetAll}>
            Reset all accessibility settings
          </button>
          <p className="sr-only" aria-live="polite">
            {message}
          </p>
          <p className="a11y-panel__note">
            Keyboard users: press Escape to close this panel. System reduced-motion settings are
            respected even when the option above is off.
          </p>
        </div>
      </div>
    </>
  );
}

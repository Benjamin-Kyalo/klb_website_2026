import { useEffect, useRef, useState } from "react";

/**
 * Enlarges content images and videos in a centred overlay.
 *
 * Clicks are delegated from the document so every CMS section, article and
 * service block is covered without wrapping each image in another component.
 * Images that are links keep their normal navigation unless they opt in with
 * data-lightbox.
 */
const SELECTOR = [
  "[data-lightbox]",
  ".cms-section img",
  ".prose img",
  ".split-media img",
  ".service-detail__media img",
  ".team-card__photo img",
  "main video",
].join(",");

function captionFor(element) {
  const explicit = element.getAttribute("data-caption");
  if (explicit) return explicit.trim();
  const figure = element.closest("figure");
  const caption = figure?.querySelector("figcaption")?.textContent;
  if (caption && caption.trim()) return caption.trim();
  return (element.getAttribute("alt") || "").trim();
}

function mediaFor(element) {
  if (element.tagName === "VIDEO") {
    const source = element.currentSrc || element.getAttribute("src") || element.querySelector("source")?.src;
    if (!source) return null;
    return { kind: "video", src: source, caption: captionFor(element) };
  }
  const src = element.currentSrc || element.getAttribute("src");
  if (!src) return null;
  return { kind: "image", src, caption: captionFor(element) };
}

export default function MediaLightbox() {
  const [media, setMedia] = useState(null);
  const [open, setOpen] = useState(false);
  const triggerRef = useRef(null);
  const closeRef = useRef(null);

  useEffect(() => {
    function handleClick(event) {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey) return;
      const element = event.target.closest(SELECTOR);
      if (!element) return;
      if (element.closest("a") && !element.hasAttribute("data-lightbox")) return;
      if (element.closest(".brand, .brand-mark, .book-grid, .book-detail__cover")) return;
      const next = mediaFor(element);
      if (!next) return;
      event.preventDefault();
      triggerRef.current = element;
      setMedia(next);
      setOpen(true);
    }

    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, []);

  useEffect(() => {
    if (!open) return undefined;

    document.body.classList.add("lightbox-open");
    const focusTimer = window.setTimeout(() => closeRef.current?.focus(), 30);

    function handleKeyDown(event) {
      if (event.key === "Escape") close();
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      window.clearTimeout(focusTimer);
      document.body.classList.remove("lightbox-open");
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  function close() {
    setOpen(false);
    setMedia(null);
    window.setTimeout(() => triggerRef.current?.focus?.(), 30);
  }

  if (!open || !media) return null;

  return (
    <div
      className="lightbox is-open"
      role="dialog"
      aria-modal="true"
      aria-label="Enlarged media viewer"
      onClick={(event) => {
        if (event.target === event.currentTarget) close();
      }}
    >
      <div className="lightbox__stage">
        <button
          type="button"
          className="lightbox__close"
          ref={closeRef}
          onClick={close}
          aria-label="Close enlarged view"
        >
          ×
        </button>
        <div className="lightbox__media">
          {media.kind === "video" ? (
            <video className="lightbox__video" src={media.src} controls autoPlay playsInline>
              Your browser does not support video playback.
            </video>
          ) : (
            <img className="lightbox__image" src={media.src} alt={media.caption || ""} />
          )}
        </div>
        {media.caption ? <p className="lightbox__caption">{media.caption}</p> : null}
      </div>
    </div>
  );
}

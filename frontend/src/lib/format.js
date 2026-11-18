export function formatDate(value, options) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-KE", options || { day: "numeric", month: "long", year: "numeric" });
}

export function formatShortDate(value) {
  return formatDate(value, { day: "numeric", month: "short", year: "numeric" });
}

export function formatDateTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-KE", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function money(price, currency = "KES") {
  if (price === null || price === undefined || price === "") return "Enquire";
  const number = Number(price);
  if (Number.isNaN(number)) return "Enquire";
  return `${currency === "KES" ? "KSh" : currency} ${number.toLocaleString("en-KE", { maximumFractionDigits: 0 })}`;
}

export function pluralise(count, singular, plural) {
  return `${count} ${count === 1 ? singular : plural || `${singular}s`}`;
}

export function safeImagePath(path) {
  if (!path) return "/assets/klb-logo-blue.png";
  if (/^https?:\/\//i.test(path) || path.startsWith("/") || path.startsWith("data:")) return path;
  return `/${path}`;
}

const ABSOLUTE_URL = /^(?:[a-z][a-z0-9+.-]*:)?\/\//i;

/**
 * Turns a site-relative path into a fully qualified URL.
 *
 * Social images and JSON-LD require absolute URLs, but dashboard content can
 * legitimately store either `/assets/cover.webp` or a full `https://` URL.
 * Absolute URLs (including protocol-relative ones) are returned untouched so
 * they are never concatenated onto the site origin.
 */
export function absoluteUrl(path, base = "") {
  if (!path) return "";
  const value = String(path);
  if (ABSOLUTE_URL.test(value) || value.startsWith("data:")) return value;
  const origin = String(base || "").replace(/\/+$/, "");
  const suffix = value.startsWith("/") ? value : `/${value}`;
  return origin ? `${origin}${suffix}` : suffix;
}

export const COLLECTION_LABELS = {
  CBE: "CBE",
  Secondary: "Secondary",
  Revision: "Revision & TopMark",
  Readers: "Readers & literature",
  Tertiary: "Tertiary & reference",
};

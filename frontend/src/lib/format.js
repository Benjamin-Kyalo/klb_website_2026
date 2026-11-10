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

export const COLLECTION_LABELS = {
  CBC: "CBC",
  Secondary: "Secondary",
  Revision: "Revision & TopMark",
  Readers: "Readers & literature",
  Tertiary: "Tertiary & reference",
};

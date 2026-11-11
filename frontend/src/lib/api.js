const API_BASE = (import.meta.env.VITE_API_BASE || "/api").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, status, fields = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fields = fields;
  }
}

export function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : "";
}

let csrfPromise = null;

export async function ensureCsrf() {
  if (getCookie("csrftoken")) return getCookie("csrftoken");
  if (!csrfPromise) {
    csrfPromise = fetch(`${API_BASE}/auth/csrf/`, { credentials: "include" })
      .then((res) => res.json())
      .then((data) => data.csrfToken)
      .finally(() => {
        csrfPromise = null;
      });
  }
  return csrfPromise;
}

export function buildQuery(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "" || value === false) return;
    if (Array.isArray(value)) {
      value.forEach((item) => search.append(key, item));
    } else {
      search.set(key, String(value));
    }
  });
  const text = search.toString();
  return text ? `?${text}` : "";
}

function extractError(data, status) {
  if (!data) return new ApiError(`Request failed (${status}).`, status);
  if (typeof data === "string") {
    // If the response is HTML (e.g., server error page), return a clean message
    if (data.includes("<!doctype") || data.includes("<html")) {
      return new ApiError("An unexpected error occurred. Please try again later.", status);
    }
    return new ApiError(data, status);
  }
  const fields = data.errors || null;
  if (fields) {
    const firstKey = Object.keys(fields)[0];
    const raw = firstKey ? fields[firstKey] : null;
    const first = Array.isArray(raw) ? raw[0] : raw;
    if (first) return new ApiError(String(first), status, fields);
  }
  return new ApiError(data.detail || `Request failed (${status}).`, status, fields);
}

export async function api(path, { method = "GET", body, headers = {}, raw = false } = {}) {
  const options = {
    method,
    credentials: "include",
    headers: { Accept: "application/json", ...headers },
    cache: "no-store",
  };

  if (body !== undefined && body !== null) {
    if (body instanceof FormData) {
      options.body = body;
    } else {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }
  }

  if (!["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase())) {
    await ensureCsrf();
    const token = getCookie("csrftoken");
    if (token) options.headers["X-CSRFToken"] = token;
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, options);
  } catch {
    throw new ApiError("Cannot reach the server. Check your connection and try again.", 0);
  }

  if (response.status === 204) return null;

  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();

  if (!response.ok) throw extractError(data, response.status);
  return data;
}

// ---------------------------------------------------------------------------
// Public endpoints
// ---------------------------------------------------------------------------
export const getSite = () => api("/site/");
export const getPage = (slug) => api(`/pages/${encodeURIComponent(slug)}/`);
export const getBooks = (params) => api(`/books/${buildQuery(params)}`);
export const getBook = (slug) => api(`/books/${encodeURIComponent(slug)}/`);
export const getCatalogueFilters = () => api("/catalogue/filters/");
export const getNews = (params = {}) => api(`/news/${buildQuery(params)}`);
export const getNewsItem = (slug) => api(`/news/${encodeURIComponent(slug)}/`);
export const getCareers = (params = {}) => api(`/careers/${buildQuery(params)}`);
export const getTenders = (params = {}) => api(`/tenders/${buildQuery(params)}`);
export const getResources = (params = {}) => api(`/resources/${buildQuery(params)}`);
export const getDigitalPartners = () => api("/digital-partners/");
export const getActiveTheme = () => api("/themes/active/");
export const sendEnquiry = (payload) => api("/enquiries/", { method: "POST", body: payload });
export const subscribe = (email) => api("/newsletter/", { method: "POST", body: { email } });
export const unsubscribe = (email) => api("/newsletter/unsubscribe/", { method: "POST", body: { email } });

// ---------------------------------------------------------------------------
// Authentication
// ---------------------------------------------------------------------------
export const auth = {
  me: () => api("/auth/me/"),
  login: (email, password) => api("/auth/login/", { method: "POST", body: { email, password } }),
  logout: () => api("/auth/logout/", { method: "POST" }),
  changePassword: (currentPassword, newPassword) =>
    api("/auth/password/", {
      method: "POST",
      body: { current_password: currentPassword, new_password: newPassword },
    }),
};

// ---------------------------------------------------------------------------
// Dashboard endpoints
// ---------------------------------------------------------------------------
const adminUrl = (resource, path = "") =>
  `/admin/${resource}/${path ? `${typeof path === "number" ? path : encodeURIComponent(path)}/` : ""}`;

export const admin = {
  stats: () => api("/admin/stats/"),
  settings: {
    get: () => api("/admin/settings/"),
    update: (payload) => api("/admin/settings/", { method: "PATCH", body: payload }),
  },
  list: (resource, params = {}) => api(adminUrl(resource, "") + buildQuery(params)),
  all: async (resource, params = {}) => {
    // Fetch every page of a dashboard list (used by simple tables).
    let next = adminUrl(resource) + buildQuery({ ...params, page_size: 96 });
    const rows = [];
    while (next) {
      const data = await api(next);
      rows.push(...(Array.isArray(data) ? data : data.results || []));
      if (data.next) {
        const url = new URL(data.next);
        next = `${url.pathname.replace(/^\/api/, "")}${url.search}`;
      } else {
        next = null;
      }
    }
    return rows;
  },
  get: (resource, id) => api(adminUrl(resource, id)),
  create: (resource, payload) => api(adminUrl(resource), { method: "POST", body: payload }),
  update: (resource, id, payload) =>
    api(adminUrl(resource, id), { method: "PATCH", body: payload }),
  replace: (resource, id, payload) =>
    api(adminUrl(resource, id), { method: "PUT", body: payload }),
  remove: (resource, id) => api(adminUrl(resource, id), { method: "DELETE" }),
  duplicatePage: (slug) => api(`/admin/pages/${encodeURIComponent(slug)}/duplicate/`, { method: "POST" }),
  resetPassword: (id, newPassword) =>
    api(`/admin/users/${id}/reset-password/`, {
      method: "POST",
      body: { new_password: newPassword },
    }),
  permissionsMeta: () => api("/admin/users/permissions/"),
  activity: (params = {}) => api(`/admin/activity/${buildQuery(params)}`),
  options: {
    list: (params = {}) => api(`/admin/options/${buildQuery(params)}`),
    groups: (params = {}) => api(`/admin/options/groups/${buildQuery(params)}`),
    create: (payload) => api("/admin/options/", { method: "POST", body: payload }),
    update: (id, payload) => api(`/admin/options/${id}/`, { method: "PATCH", body: payload }),
    remove: (id) => api(`/admin/options/${id}/`, { method: "DELETE" }),
  },
  upload: (file) => {
    const form = new FormData();
    form.append("file", file);
    return api("/admin/upload/", { method: "POST", body: form });
  },
  teamPhotos: {
    list: () => api("/admin/team-photos/"),
    update: (key, payload) =>
      api(`/admin/team-photos/${encodeURIComponent(key)}/`, { method: "PATCH", body: payload }),
  },
  digitalPartners: {
    list: (params = {}) => api(`/admin/digital-partners/${buildQuery(params)}`),
    get: (id) => api(`/admin/digital-partners/${id}/`),
    create: (payload) => api("/admin/digital-partners/", { method: "POST", body: payload }),
    update: (id, payload) => api(`/admin/digital-partners/${id}/`, { method: "PATCH", body: payload }),
    remove: (id) => api(`/admin/digital-partners/${id}/`, { method: "DELETE" }),
  },
  backup: (type = "full") => api("/admin/backup/", { method: "POST", body: { type } }),
  aiDraft: (topic) => api("/admin/ai-draft/", { method: "POST", body: { topic } }),
  themes: {
    list: (params = {}) => api(`/admin/themes/${buildQuery(params)}`),
    get: (id) => api(`/admin/themes/${id}/`),
    create: (payload) => api("/admin/themes/", { method: "POST", body: payload }),
    update: (id, payload) => api(`/admin/themes/${id}/`, { method: "PATCH", body: payload }),
    remove: (id) => api(`/admin/themes/${id}/`, { method: "DELETE" }),
  },
};

export { API_BASE };

import { Link } from "react-router-dom";
import { safeImagePath } from "../lib/format.js";
import AdminCrudPage from "./AdminCrudPage.jsx";
import { StatusBadge } from "./AdminUI.jsx";

function LogoThumb({ src }) {
  return src ? (
    <img className="admin-thumb" src={safeImagePath(src)} alt="" width="48" height="48" loading="lazy" style={{ objectFit: "contain" }} />
  ) : (
    <span className="admin-thumb admin-thumb--empty" aria-hidden="true">—</span>
  );
}

const partnerFields = [
  { name: "key", label: "Key", required: true, hint: "Short unique identifier, e.g. klb, opiq." },
  { name: "name", label: "Partner name", required: true },
  { name: "url", label: "Website URL", type: "url", full: true },
  { name: "description", label: "Description", type: "textarea", rows: 2, full: true },
  { name: "sort_order", label: "Sort order", type: "number", min: "0", defaultValue: 0 },
  { name: "logo", label: "Logo", type: "file", accept: "image/*", full: true, hint: "Upload a square or wide logo. It will be scaled to fit." },
  { name: "is_active", label: "Show on public website", type: "checkbox", defaultValue: true, publish: true },
];

const partnerColumns = [
  {
    key: "logo",
    label: "Logo",
    render: (row) => <LogoThumb src={row.logo} />,
  },
  {
    key: "name",
    label: "Partner",
    className: "admin-table__title",
    render: (row) => (
      <>
        {row.name}
        <br />
        <small className="mono">{row.key}</small>
      </>
    ),
  },
  { key: "url", label: "Website", render: (row) => (row.url ? <a href={row.url} rel="noopener" target="_blank">{row.url}</a> : "—") },
  {
    key: "is_active",
    label: "Visible",
    render: (row) => <StatusBadge status={row.is_active ? "published" : "draft"} />,
  },
];

export function AdminDigitalPartners() {
  return (
    <AdminCrudPage
      resource="digital-partners"
      module="pages"
      title="Digital partners"
      lead="Manage the logos, names and links shown in the Digital partners section. Uploaded logos are stored in the media library."
      singular="Digital partner"
      columns={partnerColumns}
      fields={partnerFields}
      lookupField="id"
      searchPlaceholder="Search partner name…"
      defaults={{ is_active: true, sort_order: 0 }}
    />
  );
}

export default AdminDigitalPartners;

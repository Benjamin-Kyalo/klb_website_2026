import { Link } from "react-router-dom";
import { formatDate, money, safeImagePath } from "../lib/format.js";
import AdminCrudPage from "./AdminCrudPage.jsx";
import { StatusBadge } from "./AdminUI.jsx";

function Thumb({ src }) {
  return <img className="admin-thumb" src={safeImagePath(src)} alt="" width="40" height="60" loading="lazy" />;
}

// ---------------------------------------------------------------------------
// Catalogue
// ---------------------------------------------------------------------------
const bookFields = [
  { name: "title", label: "Title", required: true },
  { name: "slug", label: "URL slug", hint: "Leave blank to generate from the title." },
  {
    name: "collection",
    label: "Collection",
    type: "select",
    optionsGroup: "collection",
    allowOther: true,
    hint: "The main catalogue series this title belongs to.",
  },
  { name: "level", label: "Level", hint: "e.g. Grade 3, Form 2, Secondary." },
  {
    name: "category",
    label: "Category",
    type: "select",
    optionsGroup: "publication_category",
    allowOther: true,
    hint: "Choose the closest classification, or add a new one.",
  },
  { name: "subject", label: "Subject" },
  { name: "language", label: "Language" },
  { name: "price", label: "Price", type: "number", step: "0.01", min: "0" },
  { name: "currency", label: "Currency", defaultValue: "KES" },
  { name: "isbn", label: "ISBN" },
  { name: "publisher", label: "Publisher", defaultValue: "Kenya Literature Bureau PLC" },
  { name: "sort_order", label: "Sort order", type: "number", min: "0", defaultValue: 0 },
  { name: "cover", label: "Cover image", type: "file", accept: "image/*", full: true, hint: "Paste a path such as /assets/covers/title.webp or upload a new image." },
  { name: "description", label: "Description", type: "textarea", rows: 5, full: true },
  { name: "store_url", label: "Ebookstore URL", full: true },
  { name: "source_url", label: "Source URL", full: true },
  { name: "categories", label: "Extra categories", type: "tags", full: true, hint: "Comma-separated; used for extra catalogue filters." },
  { name: "featured", label: "Featured title", type: "checkbox" },
  { name: "new_arrival", label: "New arrival", type: "checkbox" },
  { name: "is_published", label: "Published on the website", type: "checkbox", defaultValue: true, publish: true },
];

const bookColumns = [
  {
    key: "cover",
    label: "",
    render: (row) => <Thumb src={row.cover_url} />,
  },
  {
    key: "title",
    label: "Title",
    className: "admin-table__title",
    render: (row) => (
      <>
        {row.title}
        <br />
        <small className="mono">{row.isbn || row.slug}</small>
      </>
    ),
  },
  { key: "collection", label: "Collection" },
  { key: "level", label: "Level" },
  { key: "price", label: "Price", render: (row) => money(row.price, row.currency) },
  {
    key: "is_published",
    label: "Status",
    render: (row) => <StatusBadge status={row.is_published ? "published" : "draft"} />,
  },
];

export function AdminBooks() {
  return (
    <AdminCrudPage
      resource="books"
      module="books"
      title="Catalogue"
      lead="Every title in the catalogue. Prices are e-book prices from the KLB ebookstore and can be edited here."
      singular="Book"
      columns={bookColumns}
      fields={bookFields}
      lookupField="slug"
      searchPlaceholder="Search title, ISBN, category…"
      defaults={{
        collection: "CBE",
        currency: "KES",
        publisher: "Kenya Literature Bureau PLC",
        is_published: true,
        sort_order: 0,
      }}
      extraActions={
        <Link className="btn btn--secondary" to="/books/" target="_blank" rel="noopener">
          View catalogue ↗
        </Link>
      }
    />
  );
}

// ---------------------------------------------------------------------------
// News
// ---------------------------------------------------------------------------
const newsFields = [
  { name: "title", label: "Headline", required: true },
  { name: "slug", label: "URL slug", hint: "Leave blank for a readable default." },
  {
    name: "category",
    label: "Category",
    type: "select",
    optionsGroup: "news_category",
    allowOther: true,
    hint: "Choose a standard category, or add a new one.",
  },
  { name: "published_at", label: "Published date", type: "date", required: true },
  {
    name: "status",
    label: "Status",
    type: "select",
    options: [
      { value: "published", label: "Published" },
      { value: "draft", label: "Draft" },
    ],
    defaultValue: "published",
    publish: true,
  },
  { name: "image", label: "Image", type: "file", accept: "image/*", full: true },
  { name: "summary", label: "Summary", type: "textarea", rows: 3, full: true },
  { name: "body_html", label: "Article", type: "richtext", full: true },
  { name: "featured", label: "Feature on the home page", type: "checkbox" },
];

const newsColumns = [
  { key: "title", label: "Headline", className: "admin-table__title" },
  { key: "category", label: "Category" },
  { key: "published_at", label: "Published", render: (row) => formatDate(row.published_at) },
  { key: "status", label: "Status", render: (row) => <StatusBadge status={row.status} /> },
  {
    key: "featured",
    label: "Featured",
    render: (row) => (row.featured ? "Yes" : "—"),
  },
];

export function AdminNews() {
  return (
    <AdminCrudPage
      resource="news"
      module="news"
      title="News and announcements"
      lead="Announcements appear on the news page and, when featured, on the home page."
      singular="News item"
      columns={newsColumns}
      fields={newsFields}
      lookupField="slug"
      searchPlaceholder="Search news…"
      enableAIDraft={true}
      defaults={{ status: "published", featured: false }}
    />
  );
}

// ---------------------------------------------------------------------------
// Careers
// ---------------------------------------------------------------------------
const careerFields = [
  { name: "title", label: "Job title", required: true },
  {
    name: "department",
    label: "Department",
    type: "select",
    optionsGroup: "department",
    allowOther: true,
  },
  {
    name: "location",
    label: "Location",
    type: "select",
    optionsGroup: "job_location",
    allowOther: true,
  },
  {
    name: "employment_type",
    label: "Employment type",
    type: "select",
    optionsGroup: "employment_type",
    allowOther: true,
  },
  { name: "opening_date", label: "Opening date", type: "date", hint: "Leave blank to open immediately." },
  { name: "closing_date", label: "Closing date", type: "date" },
  { name: "apply_url", label: "Application URL", full: true, hint: "Link to the KLB e-recruitment portal." },
  { name: "summary", label: "Summary", type: "textarea", rows: 3, full: true },
  { name: "body_html", label: "Full advert", type: "richtext", full: true },
  { name: "is_open", label: "Vacancy is open", type: "checkbox", defaultValue: true, publish: true },
  { name: "sort_order", label: "Sort order", type: "number", min: "0", defaultValue: 0 },
];

const careerColumns = [
  { key: "title", label: "Vacancy", className: "admin-table__title" },
  { key: "department", label: "Department" },
  { key: "location", label: "Location" },
  { key: "closing_date", label: "Closes", render: (row) => (row.closing_date ? formatDate(row.closing_date) : "—") },
  { key: "status", label: "Status", render: (row) => <StatusBadge status={row.status === "expired" ? "draft" : row.status === "closing_soon" ? "new" : "published"} /> },
];

export function AdminCareers() {
  return (
    <AdminCrudPage
      resource="careers"
      module="careers"
      title="Careers"
      lead="Vacancies appear on the careers page. Closed vacancies stay in the dashboard but are hidden from the public list."
      singular="Vacancy"
      columns={careerColumns}
      fields={careerFields}
      searchPlaceholder="Search vacancies…"
      defaults={{ is_open: true, sort_order: 0 }}
    />
  );
}

// ---------------------------------------------------------------------------
// Tenders
// ---------------------------------------------------------------------------
const tenderFields = [
  { name: "title", label: "Tender title", required: true },
  {
    name: "category",
    label: "Category",
    type: "select",
    optionsGroup: "tender_category",
    allowOther: true,
  },
  { name: "published_on", label: "Published date", type: "date" },
  { name: "opening_date", label: "Opening date", type: "date", hint: "Leave blank to open immediately." },
  { name: "closing_date", label: "Closing date", type: "date" },
  { name: "document_url", label: "Tender document", type: "file", accept: "application/pdf", full: true, hint: "Upload a PDF or paste a path." },
  { name: "summary", label: "Summary", type: "textarea", rows: 3, full: true },
  { name: "body_html", label: "Full notice", type: "richtext", full: true },
  { name: "is_open", label: "Tender is open", type: "checkbox", defaultValue: true, publish: true },
  { name: "sort_order", label: "Sort order", type: "number", min: "0", defaultValue: 0 },
];

const tenderColumns = [
  { key: "title", label: "Tender", className: "admin-table__title" },
  { key: "category", label: "Category" },
  { key: "published_on", label: "Published", render: (row) => (row.published_on ? formatDate(row.published_on) : "—") },
  { key: "closing_date", label: "Closing", render: (row) => (row.closing_date ? formatDate(row.closing_date) : "—") },
  { key: "status", label: "Status", render: (row) => <StatusBadge status={row.status === "expired" ? "draft" : row.status === "closing_soon" ? "new" : "published"} /> },
];

export function AdminTenders() {
  return (
    <AdminCrudPage
      resource="tenders"
      module="tenders"
      title="Tenders"
      lead="Procurement notices and their documents. Closed tenders remain available in the dashboard."
      singular="Tender"
      columns={tenderColumns}
      fields={tenderFields}
      searchPlaceholder="Search tenders…"
      defaults={{ is_open: true, sort_order: 0 }}
    />
  );
}

// ---------------------------------------------------------------------------
// Resources
// ---------------------------------------------------------------------------
const resourceFields = [
  { name: "title", label: "Document title", required: true },
  {
    name: "category",
    label: "Category",
    type: "select",
    optionsGroup: "resource_category",
    allowOther: true,
    required: true,
    hint: "Choose the section this document belongs to, or add a new one.",
  },
  { name: "file_url", label: "File or link", type: "file", accept: "application/pdf", full: true, required: true },
  { name: "description", label: "Description", type: "textarea", rows: 3, full: true },
  { name: "external", label: "Links to an external website", type: "checkbox" },
  { name: "sort_order", label: "Sort order", type: "number", min: "0", defaultValue: 0 },
];

const resourceColumns = [
  { key: "title", label: "Document", className: "admin-table__title" },
  { key: "category", label: "Category" },
  {
    key: "file_url",
    label: "File",
    render: (row) => (
      <a href={row.file_url} target="_blank" rel="noopener">
        {row.external ? "External link ↗" : "Open document"}
      </a>
    ),
  },
  { key: "sort_order", label: "Order" },
];

export function AdminResources() {
  return (
    <AdminCrudPage
      resource="resources"
      module="resources"
      title="Resources"
      lead="Price lists, annual reports, governance documents and customer forms shown on the resources page."
      singular="Resource"
      columns={resourceColumns}
      fields={resourceFields}
      searchPlaceholder="Search resources…"
      defaults={{ category: "price-lists", external: false, sort_order: 0 }}
    />
  );
}

// ---------------------------------------------------------------------------
// Newsletter subscribers
// ---------------------------------------------------------------------------
const subscriberColumns = [
  { key: "email", label: "Email address", className: "admin-table__title" },
  { key: "created_at", label: "Subscribed", render: (row) => formatDate(row.created_at) },
  { key: "is_active", label: "Status", render: (row) => <StatusBadge status={row.is_active ? "published" : "draft"} /> },
];

export function AdminSubscribers() {
  return (
    <AdminCrudPage
      resource="subscribers"
      module="subscribers"
      title="Newsletter"
      lead="People who subscribed through the website footer. Remove an address to unsubscribe it."
      singular="Subscriber"
      columns={subscriberColumns}
      fields={[]}
      canCreate={false}
      canEdit={false}
      searchPlaceholder="Search email addresses…"
    />
  );
}

import { useEffect, useState } from "react";
import { admin } from "../lib/api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useSite } from "../context/SiteContext.jsx";
import { Alert, Card, PageHead } from "./AdminUI.jsx";
import RecordForm from "./RecordForm.jsx";

const FIELDS = [
  { name: "site_name", label: "Site name", required: true },
  { name: "tagline", label: "Tagline" },
  { name: "phone", label: "Main phone" },
  { name: "phone_alt", label: "Other phone numbers", hint: "Free text; shown under the main number." },
  { name: "contact_email", label: "General email", type: "email" },
  { name: "customer_email", label: "Customer care email", type: "email" },
  {
    name: "address",
    label: "Postal address",
    full: true,
    hint: "Shown in the footer and on the contact page.",
  },
  { name: "facebook", label: "Facebook URL", type: "url" },
  { name: "twitter", label: "X / Twitter URL", type: "url" },
  { name: "instagram", label: "Instagram URL", type: "url" },
  { name: "linkedin", label: "LinkedIn URL", type: "url" },
  { name: "ebookstore", label: "KLB ebookstore URL", type: "url" },
  {
    name: "announcement",
    label: "Announcement bar",
    full: true,
    hint: "Leave blank to hide the bar at the top of every page.",
  },
  {
    name: "footer_blurb",
    label: "Footer description",
    type: "textarea",
    rows: 3,
    full: true,
  },
  { name: "seo_default_title", label: "Default browser title", full: true },
  {
    name: "seo_default_description",
    label: "Default meta description",
    type: "textarea",
    rows: 3,
    full: true,
  },
  {
    name: "og_image",
    label: "Social sharing image",
    type: "file",
    accept: "image/*",
    full: true,
    hint: "Used when a page has no image of its own. Recommended size 1200 × 630 pixels.",
  },
  {
    name: "navigation",
    label: "Main navigation (JSON)",
    type: "json",
    rows: 18,
    full: true,
    superOnly: true,
    hint: "Each item needs a label and href. Items may include a panel with intro text and link columns.",
  },
  {
    name: "footer_columns",
    label: "Footer columns (JSON)",
    type: "json",
    rows: 14,
    full: true,
    superOnly: true,
    hint: "A list of columns. Each column has a title and a list of [label, href] link pairs.",
  },
];

export default function AdminSettings() {
  const { isSuperAdministrator } = useAuth();
  const { reload: reloadSite } = useSite();
  const [settings, setSettings] = useState(null);
  const [formKey, setFormKey] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const fields = FIELDS.filter((field) => !field.superOnly || isSuperAdministrator);

  useEffect(() => {
    let cancelled = false;
    admin.settings
      .get()
      .then((data) => {
        if (!cancelled) setSettings(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSave(payload) {
    const updated = await admin.settings.update(payload);
    setSettings(updated);
    setNotice("Site settings saved. Changes are live on the website.");
    await reloadSite();
  }

  return (
    <>
      <PageHead
        title="Site settings"
        lead="Contact details, social links and search defaults shown across the public website."
      />

      <Alert kind="success" onClose={() => setNotice("")}>
        {notice}
      </Alert>
      <Alert kind="error" onClose={() => setError("")}>
        {error}
      </Alert>

      {!isSuperAdministrator ? (
        <Alert kind="warn">
          Navigation structure and footer columns are managed by a Super Administrator. Everything
          else on this page can be changed by an Administrator.
        </Alert>
      ) : null}

      {loading ? (
        <p className="muted-meta">Loading settings…</p>
      ) : settings ? (
        <Card title="Global details">
          <RecordForm
            key={formKey}
            fields={fields}
            initial={settings}
            onSubmit={handleSave}
            onCancel={() => setFormKey((value) => value + 1)}
            submitLabel="Save settings"
          />
        </Card>
      ) : null}
    </>
  );
}

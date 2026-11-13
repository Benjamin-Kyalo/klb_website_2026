import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { admin } from "../lib/api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useSite } from "../context/SiteContext.jsx";
import { Alert, Card, PageHead } from "./AdminUI.jsx";
import RecordForm from "./RecordForm.jsx";

const ORGANISATION_FIELDS = [
  { name: "site_name", label: "Website name", required: true },
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
];

const LINK_FIELDS = [
  { name: "facebook", label: "Facebook URL", type: "url" },
  { name: "twitter", label: "X / Twitter URL", type: "url" },
  { name: "instagram", label: "Instagram URL", type: "url" },
  { name: "linkedin", label: "LinkedIn URL", type: "url" },
  { name: "ebookstore", label: "KLB ebookstore URL", type: "url" },
];

const PUBLISHING_FIELDS = [
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
    hint: "A short description of the Bureau, shown at the bottom of every page.",
  },
];

const SHARING_FIELDS = [
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
];

const STATISTICS_FIELDS = [
  {
    name: "statistics",
    label: "Homepage statistics",
    type: "json",
    rows: 8,
    full: true,
    hint: 'A list of {"value": "1947", "label": "Year established", "animate": false}. Use a "+" suffix for counts (for example "1000+").',
  },
];

const SYSTEM_FIELDS = [
  {
    name: "maintenance_mode",
    label: "Show a maintenance notice on the public website",
    type: "checkbox",
    hint: "Displays a clear notice to visitors. The public site and the administration area remain available, so you can finish the work and switch it off here.",
  },
  {
    name: "maintenance_message",
    label: "Maintenance notice text",
    type: "textarea",
    rows: 3,
    full: true,
    hint: "Explain what is happening and when normal service is expected. Leave blank to use the default wording.",
  },
  {
    name: "backup_retention",
    label: "Backups to keep",
    type: "number",
    min: 0,
    step: 1,
    hint: "Successful backups kept on the server. Oldest archives are removed first. Use 0 to keep every backup.",
  },
];

const STRUCTURE_FIELDS = [
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

function SettingsSection({ title, description, children }) {
  return (
    <section className="settings-section">
      <div className="settings-section__head">
        <h2>{title}</h2>
        {description ? <p>{description}</p> : null}
      </div>
      {children}
    </section>
  );
}

export default function AdminSettings() {
  const { isSuperAdministrator } = useAuth();
  const { reload: reloadSite } = useSite();
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

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

  function saveGroup(label) {
    return async (payload) => {
      const updated = await admin.settings.update(payload);
      setSettings(updated);
      setNotice(`${label} saved. The public website now uses these values.`);
      await reloadSite();
    };
  }

  return (
    <>
      <PageHead
        title="Admin settings"
        lead="Configuration for the public website and the content manager. Changes are applied immediately and recorded in the activity log."
      />

      <Alert kind="success" onClose={() => setNotice("")}>
        {notice}
      </Alert>
      <Alert kind="error" onClose={() => setError("")}>
        {error}
      </Alert>

      {!isSuperAdministrator ? (
        <Alert kind="warn">
          Navigation structure and footer columns are managed by a Super Administrator. Every
          other setting on this page can be changed by an Administrator.
        </Alert>
      ) : null}

      {loading ? (
        <p className="muted-meta">Loading settings…</p>
      ) : settings ? (
        <div className="settings-layout">
          <nav className="settings-nav" aria-label="Settings sections">
            <a href="#organisation">Organisation and contact</a>
            <a href="#links">Social and public links</a>
            <a href="#publishing">Announcement and footer</a>
            <a href="#sharing">Search and sharing</a>
            <a href="#statistics">Homepage statistics</a>
            <a href="#system">System and backups</a>
            <a href="#appearance">Appearance and themes</a>
            <a href="#access">Users, roles and audit</a>
            {isSuperAdministrator ? <a href="#structure">Navigation and footer</a> : null}
          </nav>

          <div className="settings-panels">
            <Card>
              <SettingsSection
                title="Organisation and contact"
                description="Identity and contact details shown in the header, footer, contact page and email templates."
              >
                <RecordForm
                  fields={ORGANISATION_FIELDS}
                  initial={settings}
                  onSubmit={saveGroup("Organisation and contact details")}
                  submitLabel="Save organisation details"
                />
              </SettingsSection>
            </Card>

            <Card>
              <SettingsSection
                title="Social and public links"
                description="Destinations used by the footer icons and the ebookstore button. Leave a field blank to hide that link."
              >
                <RecordForm
                  fields={LINK_FIELDS}
                  initial={settings}
                  onSubmit={saveGroup("Social links")}
                  submitLabel="Save links"
                />
              </SettingsSection>
            </Card>

            <Card>
              <SettingsSection
                title="Announcement and footer"
                description="Short messages that appear across the public site. Keep the announcement concise; it is not a substitute for a news article."
              >
                <RecordForm
                  fields={PUBLISHING_FIELDS}
                  initial={settings}
                  onSubmit={saveGroup("Announcement and footer")}
                  submitLabel="Save publishing details"
                />
              </SettingsSection>
            </Card>

            <Card>
              <SettingsSection
                title="Search and sharing"
                description="Defaults used when a page does not provide its own title, description or sharing image."
              >
                <RecordForm
                  fields={SHARING_FIELDS}
                  initial={settings}
                  onSubmit={saveGroup("Search and sharing defaults")}
                  submitLabel="Save search defaults"
                />
              </SettingsSection>
            </Card>

            <Card>
              <SettingsSection
                title="Homepage statistics"
                description="Figures shown in the homepage statistics band. Use only verified figures; decorative or invented numbers should not be published."
              >
                <RecordForm
                  fields={STATISTICS_FIELDS}
                  initial={settings}
                  onSubmit={saveGroup("Homepage statistics")}
                  submitLabel="Save statistics"
                />
              </SettingsSection>
            </Card>

            <Card>
              <SettingsSection
                title="System and backups"
                description="Operational preferences for the public site and the backup history."
              >
                <RecordForm
                  fields={SYSTEM_FIELDS}
                  initial={settings}
                  onSubmit={saveGroup("System settings")}
                  submitLabel="Save system settings"
                />
              </SettingsSection>
            </Card>

            <Card>
              <SettingsSection
                title="Appearance and themes"
                description="Seasonal and campaign themes change the banner treatment without altering the permanent KLB identity."
              >
                <p className="settings-inline-note">
                  Themes are managed separately so their start and end dates, activation state and
                  styling can be reviewed together.
                </p>
                <Link className="btn btn--secondary" to="/admin/themes">
                  Manage website themes
                </Link>
              </SettingsSection>
            </Card>

            <Card>
              <SettingsSection
                title="Users, roles and audit"
                description="Account administration and the record of changes are kept in dedicated sections because they contain personal and audit data."
              >
                <div className="settings-links">
                  <Link to="/admin/users">Users and permissions</Link>
                  <Link to="/admin/activity">Activity log and exports</Link>
                  <Link to="/admin/backup">Backup and restore</Link>
                  <Link to="/admin/options">Dropdown options</Link>
                </div>
              </SettingsSection>
            </Card>

            {isSuperAdministrator ? (
              <Card>
                <SettingsSection
                  title="Navigation and footer structure"
                  description="These structures control the main menu and the footer link columns. Invalid JSON is rejected; keep a copy of the current value before large edits."
                >
                  <RecordForm
                    fields={STRUCTURE_FIELDS.filter((field) => !field.superOnly || isSuperAdministrator)}
                    initial={settings}
                    onSubmit={saveGroup("Navigation and footer structure")}
                    submitLabel="Save structure"
                  />
                </SettingsSection>
              </Card>
            ) : null}
          </div>
        </div>
      ) : null}
    </>
  );
}

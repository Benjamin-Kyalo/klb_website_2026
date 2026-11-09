import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { admin } from "../lib/api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useSite } from "../context/SiteContext.jsx";
import { Alert, BackLink, Card, Field, PageHead } from "./AdminUI.jsx";
import { RichTextEditor } from "./RecordForm.jsx";

const KIND_OPTIONS = [
  { value: "html", label: "Rich HTML block" },
  { value: "book_grid", label: "Book grid" },
  { value: "news_list", label: "News list" },
  { value: "careers_list", label: "Careers list" },
  { value: "tenders_list", label: "Tenders list" },
  { value: "resources_list", label: "Resources list" },
];

const KIND_LABELS = Object.fromEntries(KIND_OPTIONS.map((option) => [option.value, option.label]));

let sectionKey = 0;
const nextKey = () => `section-${++sectionKey}`;

function slugify(value) {
  return value
    .toLowerCase()
    .replace(/['’]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 120);
}

function sectionHint(kind) {
  switch (kind) {
    case "book_grid":
      return "Settings keys: kicker, heading, lede, actionLabel, actionUrl, limit, tabs (true or false), mode (featured or new).";
    case "news_list":
      return "Settings keys: kicker, heading, lede, actionLabel, actionUrl, limit, introHtml.";
    case "careers_list":
      return "Settings keys: kicker, heading, lede, actionLabel, actionUrl, introHtml.";
    case "tenders_list":
      return "Settings keys: kicker, heading, lede, introHtml.";
    case "resources_list":
      return "Settings keys: kicker, heading, lede, category (leave blank for all).";
    default:
      return "Settings keys: sectionClass, sectionId. The HTML below is rendered as written; scripts are removed when saving.";
  }
}

export default function PageEditor() {
  const { slug: routeSlug } = useParams();
  const isNew = !routeSlug;
  const navigate = useNavigate();
  const { reload: reloadSite } = useSite();
  const { can, isSuperAdministrator } = useAuth();
  const canPublish = can("pages", "publish");

  const [meta, setMeta] = useState({
    title: "",
    slug: "",
    meta_title: "",
    meta_description: "",
    template: "page",
    status: "published",
    sort_order: 0,
  });
  const [sections, setSections] = useState([]);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [slugTouched, setSlugTouched] = useState(!isNew);

  useEffect(() => {
    if (isNew) {
      setLoading(false);
      return undefined;
    }
    let cancelled = false;
    setLoading(true);
    admin
      .get("pages", routeSlug)
      .then((data) => {
        if (cancelled) return;
        setMeta({
          title: data.title || "",
          slug: data.slug || "",
          meta_title: data.meta_title || "",
          meta_description: data.meta_description || "",
          template: data.template || "page",
          status: data.status || "published",
          sort_order: data.sort_order ?? 0,
        });
        setSections(
          (data.sections || []).map((section) => ({
            key: nextKey(),
            id: section.id,
            label: section.label || "",
            kind: section.kind || "html",
            html: section.html || "",
            settingsText: JSON.stringify(section.settings || {}, null, 2),
            preview: false,
          }))
        );
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
  }, [isNew, routeSlug]);

  function setMetaValue(name, value) {
    setMeta((current) => {
      const next = { ...current, [name]: value };
      if (name === "title" && !slugTouched) next.slug = slugify(value);
      return next;
    });
  }

  function updateSection(key, changes) {
    setSections((current) => current.map((section) => (section.key === key ? { ...section, ...changes } : section)));
  }

  function moveSection(index, direction) {
    setSections((current) => {
      const target = index + direction;
      if (target < 0 || target >= current.length) return current;
      const next = [...current];
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  function addSection(kind = "html") {
    setSections((current) => [
      ...current,
      {
        key: nextKey(),
        label: kind === "html" ? "New section" : `New ${kind.replace(/_/g, " ")}`,
        kind,
        html:
          kind === "html"
            ? '<section class="section">\n  <div class="container">\n    <h2>Section heading</h2>\n    <p>Write your content here.</p>\n  </div>\n</section>'
            : "",
        settingsText: "{}",
        preview: false,
      },
    ]);
  }

  function removeSection(key) {
    if (!window.confirm("Remove this section from the page?")) return;
    setSections((current) => current.filter((section) => section.key !== key));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setNotice("");

    if (!meta.title.trim()) {
      setError("Give the page a title.");
      return;
    }
    if (!meta.slug.trim()) {
      setError("Give the page a URL slug, for example about-us.");
      return;
    }

    let parsedSections;
    try {
      parsedSections = sections.map((section, index) => ({
        ...(section.id ? { id: section.id } : {}),
        label: section.label.trim() || `Section ${index + 1}`,
        kind: section.kind,
        html: section.html,
        settings: section.settingsText.trim() ? JSON.parse(section.settingsText) : {},
        sort_order: index,
      }));
    } catch {
      setError("One of the section settings contains invalid JSON. Check the brackets, quotes and commas.");
      return;
    }

    const payload = {
      title: meta.title.trim(),
      slug: meta.slug.trim(),
      meta_title: meta.meta_title.trim(),
      meta_description: meta.meta_description.trim(),
      template: meta.template,
      status: meta.status,
      sort_order: Number(meta.sort_order) || 0,
      sections: parsedSections,
    };

    setSaving(true);
    try {
      if (isNew) {
        await admin.create("pages", payload);
        setNotice("Page created.");
      } else {
        await admin.update("pages", routeSlug, payload);
        setNotice("Page saved.");
      }
      await reloadSite();
      navigate("/admin/pages");
    } catch (err) {
      setError(err.message || "The page could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  const canMove = (section) => isSuperAdministrator || section.kind === "html";
  const canRemove = (section) => isSuperAdministrator || section.kind === "html";

  return (
    <>
      <BackLink to="/admin/pages">Back to pages</BackLink>
      <PageHead
        title={isNew ? "New page" : `Edit: ${meta.title || routeSlug}`}
        lead="Change the page details and its sections. Formatting is cleaned automatically when the page is saved."
        actions={
          !isNew && meta.slug ? (
            <a
              className="btn btn--secondary"
              href={meta.slug === "home" ? "/" : `/${meta.slug}/`}
              target="_blank"
              rel="noopener"
            >
              View page ↗
            </a>
          ) : null
        }
      />

      <Alert kind="success" onClose={() => setNotice("")}>
        {notice}
      </Alert>
      <Alert kind="error" onClose={() => setError("")}>
        {error}
      </Alert>

      {!isSuperAdministrator ? (
        <Alert kind="warn">
          Your account can edit page content. Page layout, section type and advanced settings are
          managed by a Super Administrator.
        </Alert>
      ) : null}

      {loading ? (
        <p className="muted-meta">Loading page…</p>
      ) : (
        <form onSubmit={handleSubmit} className="record-form">
          <Card title="Page details">
            <div className="field-row">
              <Field label="Title" htmlFor="page-title" required>
                <input
                  id="page-title"
                  type="text"
                  value={meta.title}
                  onChange={(event) => setMetaValue("title", event.target.value)}
                  required
                />
              </Field>
              <Field label="URL slug" htmlFor="page-slug" required hint="Lowercase words separated by hyphens. Use “home” for the front page.">
                <input
                  id="page-slug"
                  type="text"
                  value={meta.slug}
                  onChange={(event) => {
                    setSlugTouched(true);
                    setMetaValue("slug", event.target.value);
                  }}
                  required
                />
              </Field>
              <Field label="Browser title" htmlFor="page-meta-title" hint="Shown in search results and browser tabs. Leave blank to use the page title.">
                <input
                  id="page-meta-title"
                  type="text"
                  value={meta.meta_title}
                  onChange={(event) => setMetaValue("meta_title", event.target.value)}
                />
              </Field>
              <Field
                label="Status"
                htmlFor="page-status"
                hint={
                  canPublish
                    ? "Drafts are hidden from the public site and the sitemap."
                    : "Your account does not have permission to publish pages. An editor with publishing rights can do this."
                }
              >
                <select
                  id="page-status"
                  value={meta.status}
                  disabled={!canPublish}
                  onChange={(event) => setMetaValue("status", event.target.value)}
                >
                  <option value="published">Published</option>
                  <option value="draft">Draft</option>
                </select>
              </Field>
              {isSuperAdministrator ? (
                <Field label="Template" htmlFor="page-template" hint="Catalogue pages use a fixed catalogue layout; standard pages render their sections.">
                  <select id="page-template" value={meta.template} onChange={(event) => setMetaValue("template", event.target.value)}>
                    <option value="page">Standard page</option>
                    <option value="catalogue">Catalogue page</option>
                  </select>
                </Field>
              ) : null}
              <Field label="Sort order" htmlFor="page-sort" hint="Used for ordering in lists. Lower numbers appear first.">
                <input
                  id="page-sort"
                  type="number"
                  min="0"
                  value={meta.sort_order}
                  onChange={(event) => setMetaValue("sort_order", event.target.value)}
                />
              </Field>
              <Field label="Meta description" htmlFor="page-meta-description" className="field--full" hint="One or two sentences for search engines (about 150 characters).">
                <textarea
                  id="page-meta-description"
                  rows={3}
                  value={meta.meta_description}
                  onChange={(event) => setMetaValue("meta_description", event.target.value)}
                />
              </Field>
            </div>
          </Card>

          <Card
            title={`Sections (${sections.length})`}
            actions={
              <div className="btn-row">
                <button className="btn btn--secondary btn--sm" type="button" onClick={() => addSection("html")}>
                  Add HTML section
                </button>
                {isSuperAdministrator ? (
                  <>
                    <button className="btn btn--secondary btn--sm" type="button" onClick={() => addSection("book_grid")}>
                      Add book grid
                    </button>
                    <button className="btn btn--secondary btn--sm" type="button" onClick={() => addSection("news_list")}>
                      Add news list
                    </button>
                  </>
                ) : null}
              </div>
            }
          >
            <p className="muted-meta">
              Sections render in this order. Automatic list sections fetch live data from the
              catalogue, news, careers, tenders and resources.
            </p>

            {sections.length ? (
              sections.map((section, index) => (
                <div className="admin-section" key={section.key}>
                  <div className="admin-section__head">
                    <span className="kind-tag">{index + 1}</span>
                    <div className="admin-section__title">
                      <Field label="Section label" htmlFor={`section-label-${section.key}`}>
                        <input
                          id={`section-label-${section.key}`}
                          type="text"
                          value={section.label}
                          onChange={(event) => updateSection(section.key, { label: event.target.value })}
                        />
                      </Field>
                    </div>
                    {isSuperAdministrator ? (
                      <div className="admin-section__kind">
                        <Field label="Type" htmlFor={`section-kind-${section.key}`}>
                          <select
                            id={`section-kind-${section.key}`}
                            value={section.kind}
                            onChange={(event) => updateSection(section.key, { kind: event.target.value })}
                          >
                            {KIND_OPTIONS.map((option) => (
                              <option value={option.value} key={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        </Field>
                      </div>
                    ) : (
                      <p className="kind-note">{KIND_LABELS[section.kind] || section.kind}</p>
                    )}
                    <div className="admin-section__actions">
                      {canMove(section) ? (
                        <>
                          <button
                            className="btn btn--secondary btn--sm"
                            type="button"
                            onClick={() => moveSection(index, -1)}
                            disabled={index === 0}
                            aria-label="Move section up"
                          >
                            ↑
                          </button>
                          <button
                            className="btn btn--secondary btn--sm"
                            type="button"
                            onClick={() => moveSection(index, 1)}
                            disabled={index === sections.length - 1}
                            aria-label="Move section down"
                          >
                            ↓
                          </button>
                        </>
                      ) : null}
                      {canRemove(section) ? (
                        <button className="btn btn--danger btn--sm" type="button" onClick={() => removeSection(section.key)}>
                          Remove
                        </button>
                      ) : null}
                    </div>
                  </div>

                  <div className="admin-section__body">
                    {section.kind === "html" ? (
                      <Field
                        label={isSuperAdministrator ? "HTML content" : "Content"}
                        htmlFor={`section-html-${section.key}`}
                        hint={
                          isSuperAdministrator
                            ? "Paste or edit the section markup. Scripts, event handlers and unsafe CSS are removed automatically."
                            : "Use the toolbar to format this section. Unsafe markup is removed automatically when you save."
                        }
                      >
                        {isSuperAdministrator ? (
                          <>
                            <textarea
                              id={`section-html-${section.key}`}
                              className="source-editor__textarea"
                              rows={12}
                              value={section.html}
                              onChange={(event) => updateSection(section.key, { html: event.target.value })}
                              spellCheck="false"
                            />
                            <div className="html-field__actions">
                              <button
                                className="btn btn--secondary btn--sm"
                                type="button"
                                onClick={() => updateSection(section.key, { preview: !section.preview })}
                              >
                                {section.preview ? "Hide preview" : "Preview HTML"}
                              </button>
                            </div>
                            {section.preview ? (
                              <div className="admin-html-preview" dangerouslySetInnerHTML={{ __html: section.html }} />
                            ) : null}
                          </>
                        ) : (
                          <RichTextEditor
                            id={`section-html-${section.key}`}
                            value={section.html}
                            onChange={(value) => updateSection(section.key, { html: value })}
                            rows={14}
                          />
                        )}
                      </Field>
                    ) : (
                      <div className="admin-section__readonly">
                        <p>
                          This is an automatic <strong>{KIND_LABELS[section.kind] || section.kind}</strong>{" "}
                          section. Its content is pulled from the live website, so there is nothing
                          to edit here.
                        </p>
                      </div>
                    )}

                    {isSuperAdministrator ? (
                      <Field
                        label="Settings (JSON)"
                        htmlFor={`section-settings-${section.key}`}
                        hint={sectionHint(section.kind)}
                      >
                        <textarea
                          id={`section-settings-${section.key}`}
                          className="mono"
                          rows={6}
                          value={section.settingsText}
                          onChange={(event) => updateSection(section.key, { settingsText: event.target.value })}
                          spellCheck="false"
                        />
                      </Field>
                    ) : null}
                  </div>
                </div>
              ))
            ) : (
              <p className="muted-meta">This page has no sections yet. Add an HTML section to begin.</p>
            )}
          </Card>

          <div className="form-actions">
            <button className="btn btn--primary" type="submit" disabled={saving}>
              {saving ? "Saving…" : isNew ? "Create page" : "Save changes"}
            </button>
            <Link className="btn btn--secondary" to="/admin/pages">
              Cancel
            </Link>
          </div>
        </form>
      )}
    </>
  );
}

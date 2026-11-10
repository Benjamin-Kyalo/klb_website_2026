import { useEffect, useState } from "react";
import { getResources } from "../../lib/api.js";
import { Arrow } from "../Icons.jsx";

const CATEGORY_LABELS = {
  "price-lists": "Price list",
  "annual-reports": "Annual report",
  governance: "Governance",
  "customer-forms": "Form",
};

function typeLabel(item) {
  const isPdf = /\.pdf(\?|$)/i.test(item.file_url || "");
  const base = isPdf ? "PDF" : "Link";
  const suffix = CATEGORY_LABELS[item.category];
  return suffix ? `${base} · ${suffix}` : base;
}

export default function ResourcesListSection({ section }) {
  const settings = section.settings || {};
  const [resources, setResources] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getResources({ category: settings.category })
      .then((data) => {
        if (!cancelled) setResources(data || []);
      })
      .catch(() => {
        if (!cancelled) setResources([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [settings.category]);

  return (
    <section className={settings.sectionClass || "section"} id={settings.sectionId || undefined}>
      <div className="container">
        <div className="section-head reveal">
          <div className="section-head__text">
            <p className="kicker">{settings.kicker || "Resources"}</p>
            <h2>{settings.heading || "Documents and downloads."}</h2>
            {settings.lede ? <p>{settings.lede}</p> : null}
          </div>
        </div>

        {loading ? (
          <p className="muted-meta">Loading documents…</p>
        ) : resources.length ? (
          <div className="resource-list reveal">
            {resources.map((item) => (
              <div className="resource-row" key={item.id}>
                <div className="resource-row__main">
                  <span className="resource-row__type">{typeLabel(item)}</span>
                  <h3>{item.title}</h3>
                  {item.description ? <p>{item.description}</p> : null}
                </div>
                <a
                  className="resource-row__action link-arrow"
                  href={item.file_url}
                  rel={item.external ? "noopener" : undefined}
                >
                  Open {item.external ? "↗" : ""} <Arrow />
                </a>
              </div>
            ))}
          </div>
        ) : (
          <div className="callout">
            <strong>No documents in this section yet.</strong>
            <p>Add resources in the admin panel and they will appear here.</p>
          </div>
        )}
      </div>
    </section>
  );
}

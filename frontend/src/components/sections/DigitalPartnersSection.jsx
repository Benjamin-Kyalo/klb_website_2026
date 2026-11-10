import { useEffect, useState } from "react";

export default function DigitalPartnersSection({ section }) {
  const settings = section.settings || {};
  const [partners, setPartners] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/digital-partners/")
      .then((res) => res.json())
      .then((data) => {
        if (!cancelled) setPartners(Array.isArray(data) ? data : data.results || []);
      })
      .catch(() => {
        if (!cancelled) setPartners([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className={settings.sectionClass || "section section--paper-2"} id={settings.sectionId || undefined}>
      <div className="container">
        {settings.introHtml ? <div dangerouslySetInnerHTML={{ __html: settings.introHtml }} /> : null}
        <div className="section-head reveal">
          <div className="section-head__text">
            <p className="kicker">{settings.kicker || "Where to find KLB e-books"}</p>
            <h2>{settings.heading || "Digital partners."}</h2>
            {settings.lede ? <p>{settings.lede}</p> : null}
          </div>
        </div>

        {loading ? (
          <p className="muted-meta">Loading partners…</p>
        ) : partners.length ? (
          <div className="partner-logo-grid reveal">
            {partners.map((partner) => (
              <a
                className="partner-logo"
                href={partner.url || "#"}
                key={partner.id || partner.key}
                rel="noopener"
              >
                {partner.logo ? (
                  <img src={partner.logo} alt={partner.name} loading="lazy" />
                ) : (
                  <span className="partner-logo__mark" aria-hidden="true">
                    {partner.name
                      .split(/\s+/)
                      .slice(0, 2)
                      .map((w) => w[0])
                      .join("")
                      .toUpperCase()}
                  </span>
                )}
                <strong>{partner.name}</strong>
                {partner.description ? <span>{partner.description}</span> : null}
              </a>
            ))}
          </div>
        ) : (
          <div className="callout">
            <strong>No digital partners listed yet.</strong>
            <p>Add partners in the admin dashboard and they will appear here.</p>
          </div>
        )}
      </div>
    </section>
  );
}

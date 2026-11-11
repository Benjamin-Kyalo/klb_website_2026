import { useEffect, useState } from "react";
import { getTenders } from "../../lib/api.js";
import { formatDate } from "../../lib/format.js";
import { Arrow } from "../Icons.jsx";

export default function TendersListSection({ section }) {
  const settings = section.settings || {};
  const [tenders, setTenders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getTenders()
      .then((data) => {
        if (!cancelled) setTenders(data || []);
      })
      .catch(() => {
        if (!cancelled) setTenders([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className={settings.sectionClass || "section"} id={settings.sectionId || undefined}>
      <div className="container">
        {settings.introHtml ? <div dangerouslySetInnerHTML={{ __html: settings.introHtml }} /> : null}
        <div className="section-head reveal">
          <div className="section-head__text">
            <p className="kicker">{settings.kicker || "Open opportunities"}</p>
            <h2>{settings.heading || "Current tenders."}</h2>
            {settings.lede ? <p>{settings.lede}</p> : null}
          </div>
        </div>

        {loading ? (
          <p className="muted-meta">Loading tenders…</p>
        ) : tenders.length ? (
          <div className="tender-list reveal">
            {tenders.map((tender) => {
              const expired = tender.status === "expired";
              const closingSoon = tender.status === "closing_soon";
              return (
                <a className={`tender${expired ? " tender--expired" : ""}`} href={expired ? undefined : (tender.document_url || "#")} key={tender.id} onClick={expired ? (e) => e.preventDefault() : undefined} style={expired ? { pointerEvents: "none", opacity: 0.7 } : undefined}>
                  <div>
                    <span className="tender__tag">{tender.category || "Tender"}</span>
                    <h3>{tender.title}</h3>
                    <p>{tender.summary || "Download the tender document for requirements, submission details and deadlines."}</p>
                    {tender.published_on ? <p className="muted-meta">Published: {formatDate(tender.published_on)}</p> : null}
                    {tender.closing_date ? <p className="muted-meta">Closing date: {formatDate(tender.closing_date)}</p> : null}
                    {expired ? (
                      <p className="muted-meta" style={{ color: "var(--red, #b32632)", fontWeight: 600 }}>
                        This tender has closed.
                      </p>
                    ) : closingSoon ? (
                      <p className="muted-meta" style={{ color: "var(--yellow, #7b5a10)", fontWeight: 600 }}>
                        Closing soon — submit before {formatDate(tender.closing_date)}.
                      </p>
                    ) : null}
                  </div>
                  <span className="link-arrow">
                    {expired ? "Closed" : (tender.document_url ? "Download PDF" : "View details")} <Arrow />
                  </span>
                </a>
              );
            })}
          </div>
        ) : (
          <div className="callout">
            <strong>No tenders are open right now.</strong>
            <p>New procurement notices will appear here when they are published.</p>
          </div>
        )}
      </div>
    </section>
  );
}

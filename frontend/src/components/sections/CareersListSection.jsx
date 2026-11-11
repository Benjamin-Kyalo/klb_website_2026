import { useEffect, useState } from "react";
import { getCareers } from "../../lib/api.js";
import { formatDate } from "../../lib/format.js";
import { Arrow } from "../Icons.jsx";

export default function CareersListSection({ section }) {
  const settings = section.settings || {};
  const [careers, setCareers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getCareers()
      .then((data) => {
        if (!cancelled) setCareers(data || []);
      })
      .catch(() => {
        if (!cancelled) setCareers([]);
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
        <div className="section-head reveal">
          <div className="section-head__text">
            <p className="kicker">{settings.kicker || "Opportunities"}</p>
            <h2>{settings.heading || "Current vacancies."}</h2>
            {settings.lede ? <p>{settings.lede}</p> : null}
          </div>
          {settings.actionLabel ? (
            <div className="section-head__action">
              <a
                className="btn btn--primary"
                href={settings.actionUrl || "https://recruitment.klb.co.ke"}
                rel="noopener"
              >
                {settings.actionLabel} ↗
              </a>
            </div>
          ) : null}
        </div>

        {loading ? (
          <p className="muted-meta">Loading vacancies…</p>
        ) : careers.length ? (
          <div className="tender-list reveal">
            {careers.map((job) => {
              const meta = [job.location, job.employment_type, job.closing_date ? `Closes ${formatDate(job.closing_date)}` : ""]
                .filter(Boolean)
                .join(" · ");
              const expired = job.status === "expired";
              const closingSoon = job.status === "closing_soon";
              return (
                <a className={`job${expired ? " job--expired" : ""}`} href={expired ? undefined : (job.apply_url || "https://recruitment.klb.co.ke")} rel="noopener" key={job.id} onClick={expired ? (e) => e.preventDefault() : undefined} style={expired ? { pointerEvents: "none", opacity: 0.7 } : undefined}>
                  <div>
                    <span className="tender__tag">{job.department || "Opportunity"}</span>
                    <h3>{job.title}</h3>
                    <p>{job.summary}</p>
                    {meta ? <p className="muted-meta">{meta}</p> : null}
                    {expired ? (
                      <p className="muted-meta" style={{ color: "var(--red, #b32632)", fontWeight: 600 }}>
                        This vacancy has closed.
                      </p>
                    ) : closingSoon ? (
                      <p className="muted-meta" style={{ color: "var(--yellow, #7b5a10)", fontWeight: 600 }}>
                        Closing soon — apply before {formatDate(job.closing_date)}.
                      </p>
                    ) : null}
                  </div>
                  <span className="link-arrow">
                    {expired ? "Closed" : "Apply online"} <Arrow />
                  </span>
                </a>
              );
            })}
          </div>
        ) : (
          <div className="callout">
            <strong>No vacancies are open right now.</strong>
            <p>Check the official KLB e-recruitment portal for new opportunities.</p>
          </div>
        )}

        {settings.introHtml ? <div dangerouslySetInnerHTML={{ __html: settings.introHtml }} /> : null}
      </div>
    </section>
  );
}

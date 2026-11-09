import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getNews } from "../../lib/api.js";
import { formatDate } from "../../lib/format.js";
import { Arrow } from "../Icons.jsx";

export default function NewsListSection({ section }) {
  const settings = section.settings || {};
  const [news, setNews] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const params = settings.limit ? { limit: settings.limit } : {};
    getNews(params)
      .then((data) => {
        if (!cancelled) setNews(Array.isArray(data) ? data : data.results || []);
      })
      .catch(() => {
        if (!cancelled) setNews([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [settings.limit]);

  return (
    <section className={settings.sectionClass || "section"} id={settings.sectionId || undefined}>
      <div className="container">
        {settings.introHtml ? <div dangerouslySetInnerHTML={{ __html: settings.introHtml }} /> : null}
        <div className="section-head reveal">
          <div className="section-head__text">
            <p className="kicker">{settings.kicker || "News & announcements"}</p>
            <h2>{settings.heading || "From the Bureau."}</h2>
            {settings.lede ? <p>{settings.lede}</p> : null}
          </div>
          {settings.actionLabel ? (
            <div className="section-head__action">
              <Link className="link-arrow" to={settings.actionUrl || "/news/"}>
                {settings.actionLabel} <Arrow />
              </Link>
            </div>
          ) : null}
        </div>

        {loading ? (
          <p className="muted-meta">Loading announcements…</p>
        ) : news.length ? (
          <div className="news-grid reveal">
            {news.map((item) => (
              <Link className="news-card" to={`/news/${item.slug}/`} key={item.id}>
                <div className="news-card__meta">
                  <span className="news-card__tag">{item.category}</span>
                  <span>{formatDate(item.published_at)}</span>
                </div>
                <h3>{item.title}</h3>
                <p>{item.summary || "Announcement from Kenya Literature Bureau."}</p>
                <span className="link-arrow">
                  Read announcement <Arrow />
                </span>
              </Link>
            ))}
          </div>
        ) : (
          <div className="callout">
            <strong>No announcements yet.</strong>
            <p>New KLB announcements will appear here as they are published in the admin panel.</p>
          </div>
        )}
      </div>
    </section>
  );
}

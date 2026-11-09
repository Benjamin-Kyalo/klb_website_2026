import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getNewsItem } from "../lib/api.js";
import { formatDate, safeImagePath } from "../lib/format.js";
import Seo, { SITE_URL } from "../lib/seo.js";
import { useSite } from "../context/SiteContext.jsx";
import Loading, { ErrorState } from "../components/Loading.jsx";

export default function NewsDetailPage() {
  const { slug } = useParams();
  const { settings } = useSite();
  const [article, setArticle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setArticle(null);
    getNewsItem(slug)
      .then((data) => {
        if (!cancelled) setArticle(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (loading) {
    return (
      <div className="container page-loading">
        <Loading label="Loading announcement…" />
      </div>
    );
  }

  if (error || !article) {
    return (
      <div className="container page-loading">
        <Seo
          title="News item not found | Kenya Literature Bureau"
          description="That announcement could not be found."
          path={`/news/${slug}/`}
          noindex
        />
        <ErrorState error={error} title="We could not find that announcement." />
        <p style={{ textAlign: "center", marginTop: "1rem" }}>
          <Link className="btn btn--secondary" to="/news/">
            Back to news
          </Link>
        </p>
      </div>
    );
  }

  const description = article.summary || article.title;
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    headline: article.title,
    datePublished: article.published_at,
    dateModified: article.updated_at,
    description,
    articleSection: article.category || undefined,
    image: article.image ? `${SITE_URL}${safeImagePath(article.image)}` : `${SITE_URL}/assets/og-klb.jpg`,
    author: { "@type": "Organization", name: "Kenya Literature Bureau" },
    publisher: { "@type": "Organization", name: "Kenya Literature Bureau" },
    mainEntityOfPage: `${SITE_URL}/news/${article.slug}/`,
  };

  return (
    <>
      <Seo title={`${article.title} | Kenya Literature Bureau`} description={description} path={`/news/${article.slug}/`} type="article" jsonLd={jsonLd} />

      <section className="page-hero page-hero--compact">
        <div className="container">
          <nav className="breadcrumbs" aria-label="Breadcrumb">
            <Link to="/">Home</Link>
            <span aria-hidden="true">/</span>
            <Link to="/news/">News &amp; media</Link>
            <span aria-hidden="true">/</span>
            <span aria-current="page">{article.title}</span>
          </nav>
          <div className="page-hero__inner">
            <div>
              <p className="kicker">
                {article.category} · {formatDate(article.published_at)}
              </p>
              <h1>{article.title}</h1>
              <p>{article.summary}</p>
            </div>
          </div>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <div className="split">
            <div className="prose reveal is-visible">
              {article.body_html ? (
                <div dangerouslySetInnerHTML={{ __html: article.body_html }} />
              ) : (
                <>
                  <p>{article.summary || "Announcement from Kenya Literature Bureau."}</p>
                  <p>
                    Full article text and photography are being recovered from the previous site and will be added. For
                    comment or verification, contact Corporate Communications.
                  </p>
                </>
              )}
              <div className="callout" style={{ marginTop: "1.6rem" }}>
                <strong>Media enquiries</strong>
                <p>
                  Corporate Communications
                  <br />
                  <a href={`mailto:${settings.contact_email}`}>{settings.contact_email}</a>
                </p>
              </div>
              <div className="btn-row" style={{ marginTop: "1.4rem" }}>
                <Link className="btn btn--secondary" to="/news/">
                  Back to news
                </Link>
              </div>
            </div>
            {article.image ? (
              <div className="split-media reveal is-visible">
                <img src={safeImagePath(article.image)} alt={article.title} width="1600" height="1067" loading="lazy" />
              </div>
            ) : null}
          </div>
        </div>
      </section>
    </>
  );
}

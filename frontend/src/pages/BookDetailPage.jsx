import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getBook, getBooks } from "../lib/api.js";
import { COLLECTION_LABELS, money, safeImagePath } from "../lib/format.js";
import Seo, { SITE_URL } from "../lib/seo.js";
import { useSite } from "../context/SiteContext.jsx";
import BookCard from "../components/BookCard.jsx";
import Loading, { ErrorState } from "../components/Loading.jsx";
import { Arrow } from "../components/Icons.jsx";

export default function BookDetailPage() {
  const { slug } = useParams();
  const { settings } = useSite();
  const [book, setBook] = useState(null);
  const [related, setRelated] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setBook(null);
    setRelated([]);

    getBook(slug)
      .then(async (data) => {
        if (cancelled) return;
        setBook(data);
        if (data.collection) {
          try {
            const list = await getBooks({ collection: data.collection, page_size: 5 });
            if (!cancelled) {
              setRelated((list.results || []).filter((item) => item.slug !== data.slug).slice(0, 4));
            }
          } catch {
            /* related titles are optional */
          }
        }
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
        <Loading label="Loading book details…" />
      </div>
    );
  }

  if (error || !book) {
    return (
      <div className="container page-loading">
        <Seo
          title="Book not found | Kenya Literature Bureau"
          description="That book could not be found in the KLB catalogue."
          path={`/books/${slug}/`}
          noindex
        />
        <ErrorState error={error} title="We could not find that book." />
        <p style={{ textAlign: "center", marginTop: "1rem" }}>
          <Link className="btn btn--secondary" to="/books/">
            Back to the catalogue
          </Link>
        </p>
      </div>
    );
  }

  const collectionLabel = COLLECTION_LABELS[book.collection] || book.collection;
  const description = `${book.title} — ${book.subject || collectionLabel} for ${book.level || "learners"}, published by Kenya Literature Bureau. View details, price and buying options.`;
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Book",
    name: book.title,
    url: `${SITE_URL}/books/${book.slug}/`,
    image: `${SITE_URL}${safeImagePath(book.cover_url)}`,
    description: (book.description || "").slice(0, 500),
    isbn: book.isbn || undefined,
    inLanguage: book.language || undefined,
    publisher: { "@type": "Organization", name: "Kenya Literature Bureau" },
    offers: book.price
      ? {
          "@type": "Offer",
          price: book.price,
          priceCurrency: book.currency || "KES",
          url: book.store_url || `${SITE_URL}/books/${book.slug}/`,
          availability: "https://schema.org/InStock",
        }
      : undefined,
  };

  return (
    <>
      <Seo title={`${book.title} | Kenya Literature Bureau`} description={description} path={`/books/${book.slug}/`} jsonLd={jsonLd} />

      <div className="container">
        <nav className="breadcrumbs" aria-label="Breadcrumb" style={{ paddingTop: "1.6rem" }}>
          <Link to="/">Home</Link>
          <span aria-hidden="true">/</span>
          <Link to="/books/">Books</Link>
          <span aria-hidden="true">/</span>
          <Link to={`/books/?collection=${encodeURIComponent(book.collection)}`}>{collectionLabel}</Link>
          <span aria-hidden="true">/</span>
          <span aria-current="page">{book.title}</span>
        </nav>

        <div className="book-detail">
          <div className="book-detail__cover">
            <img
              className="book-cover"
              src={safeImagePath(book.cover_url)}
              alt={`Cover of ${book.title}`}
              width="600"
              height="900"
              loading="eager"
              decoding="async"
            />
            <p className="book-detail__cover-note">Cover image from the KLB ebookstore. Actual edition may differ.</p>
          </div>
          <div>
            <p className="book-detail__eyebrow">
              {book.collection} · {book.level}
            </p>
            <h1>{book.title}</h1>
            <p className="book-detail__sub">{book.subject} · Published by Kenya Literature Bureau</p>

            <div className="book-detail__price">
              {book.price ? (
                <>
                  <strong>{money(book.price, book.currency)}</strong>
                  <span>E-book price where listed · print prices vary</span>
                </>
              ) : (
                <>
                  <strong>Enquire</strong>
                  <span>Price on request</span>
                </>
              )}
            </div>

            <div className="book-detail__actions">
              <a
                className="btn btn--primary btn--lg"
                href={book.store_url || settings.ebookstore || "https://klbbooks.com/"}
                rel="noopener"
              >
                Buy the e-book ↗
              </a>
              <Link className="btn btn--secondary btn--lg" to={`/contact/?type=order&book=${book.slug}`}>
                Enquire about a print copy
              </Link>
            </div>

            <dl className="meta-list">
              <div>
                <dt>Publisher</dt>
                <dd>Kenya Literature Bureau</dd>
              </div>
              <div>
                <dt>Collection</dt>
                <dd>{collectionLabel}</dd>
              </div>
              <div>
                <dt>Level</dt>
                <dd>{book.level || "—"}</dd>
              </div>
              <div>
                <dt>Subject</dt>
                <dd>{book.subject || "—"}</dd>
              </div>
              <div>
                <dt>Language</dt>
                <dd>{book.language || "—"}</dd>
              </div>
              <div>
                <dt>ISBN</dt>
                <dd>{book.isbn || "Available on request"}</dd>
              </div>
              <div>
                <dt>Publication date</dt>
                <dd>Available on request</dd>
              </div>
              <div>
                <dt>Format</dt>
                <dd>Print; e-book where available</dd>
              </div>
            </dl>

            <div className="book-description">
              <h2>About this book</h2>
              <p>{book.description || "Description available from the KLB ebookstore listing."}</p>
            </div>

            <div className="book-note">
              <strong>Before you order</strong>
              <p>
                This page is compiled from KLB&apos;s public ebookstore listing. Prices are e-book prices where shown
                and may change. Confirm the current print price, edition and availability with customer service on{" "}
                {settings.phone} or <a href={`mailto:${settings.customer_email}`}>{settings.customer_email}</a>.
              </p>
            </div>

            <div className="btn-row" style={{ marginTop: "1.4rem" }}>
              <Link className="btn btn--secondary" to={`/contact/?type=bulk&book=${book.slug}`}>
                Order for a school
              </Link>
              <Link className="btn btn--secondary" to="/resources/#price-lists">
                Price lists
              </Link>
            </div>
          </div>
        </div>
      </div>

      {related.length ? (
        <section className="section section--paper-2">
          <div className="container">
            <div className="section-head reveal is-visible">
              <div className="section-head__text">
                <p className="kicker">Related titles</p>
                <h2>More from this collection.</h2>
              </div>
              <div className="section-head__action">
                <Link className="link-arrow" to={`/books/?collection=${encodeURIComponent(book.collection)}`}>
                  See all {collectionLabel} <Arrow />
                </Link>
              </div>
            </div>
            <div className="book-grid">
              {related.map((item) => (
                <BookCard book={item} key={item.id} />
              ))}
            </div>
          </div>
        </section>
      ) : null}
    </>
  );
}

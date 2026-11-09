import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getBooks } from "../../lib/api.js";
import BookCard from "../BookCard.jsx";
import { Arrow } from "../Icons.jsx";

const TABS = [
  { key: "featured", label: "Featured" },
  { key: "CBC", label: "CBC" },
  { key: "Secondary", label: "Secondary" },
  { key: "Readers", label: "Readers" },
];

export default function BookGridSection({ section }) {
  const settings = section.settings || {};
  const limit = Number(settings.limit) || 16;
  const [tab, setTab] = useState(settings.mode === "new" ? "new" : "featured");
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const params = { page_size: limit };
    if (tab === "featured") params.featured = 1;
    else if (tab === "new") params.new = 1;
    else params.collection = tab;

    getBooks(params)
      .then((data) => {
        if (!cancelled) setBooks(data.results || []);
      })
      .catch(() => {
        if (!cancelled) setBooks([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [tab, limit]);

  return (
    <section className={settings.sectionClass || "section"} id={settings.sectionId || undefined}>
      <div className="container">
        <div className="section-head reveal">
          <div className="section-head__text">
            <p className="kicker">{settings.kicker || "Selected titles"}</p>
            <h2>{settings.heading || "Books for the classroom, the library and the shelf at home."}</h2>
            {settings.lede ? <p>{settings.lede}</p> : null}
          </div>
          {settings.tabs ? (
            <div className="section-head__action">
              <div className="tabs" role="tablist" aria-label="Filter featured books">
                {TABS.map((item) => (
                  <button
                    className="tab"
                    key={item.key}
                    type="button"
                    role="tab"
                    aria-selected={tab === item.key}
                    onClick={() => setTab(item.key)}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>
          ) : null}
        </div>

        {loading ? (
          <div className="book-grid" aria-busy="true">
            {Array.from({ length: Math.min(limit, 8) }).map((_, index) => (
              <div className="book-card book-card--skeleton" key={index} aria-hidden="true" />
            ))}
          </div>
        ) : books.length ? (
          <div className="book-grid reveal">
            {books.map((book, index) => (
              <BookCard
                book={book}
                eager={index < 4}
                key={book.id}
                badge={index < 4 && book.featured ? "Featured" : book.new_arrival ? "New" : ""}
              />
            ))}
          </div>
        ) : (
          <div className="callout">
            <strong>No titles to show here yet.</strong>
            <p>Browse the full catalogue to find a title.</p>
          </div>
        )}

        <div className="load-more">
          <Link className="btn btn--secondary" to={settings.actionUrl || "/books/"}>
            {settings.actionLabel || "See the full catalogue"} <Arrow />
          </Link>
        </div>
      </div>
    </section>
  );
}

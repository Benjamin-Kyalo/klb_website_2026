import { Link } from "react-router-dom";
import { money, safeImagePath } from "../lib/format.js";

export default function BookCard({ book, eager = false, badge = "" }) {
  const label = badge || (book.new_arrival ? "New" : book.featured ? "Featured" : "");
  return (
    <article className="book-card">
      <Link className="book-card__link" to={`/books/${book.slug}/`}>
        <div className="book-card__media">
          <img
            className="book-cover"
            src={safeImagePath(book.cover_url || book.cover)}
            alt={`Cover of ${book.title}`}
            width="324"
            height="486"
            loading={eager ? "eager" : "lazy"}
            decoding="async"
          />
          {label ? (
            <span className={`book-card__badge${label === "New" ? " book-card__badge--new" : ""}`}>{label}</span>
          ) : null}
          <span className="book-card__quick">View book</span>
        </div>
        <div className="book-card__body">
          <p className="book-card__eyebrow">
            {book.collection}
            {book.level ? ` · ${book.level}` : ""}
          </p>
          <h3 className="book-card__title">{book.title}</h3>
          <div className="book-card__meta">
            <span>{book.subject}</span>
            <span className="book-card__price">{money(book.price, book.currency)}</span>
          </div>
        </div>
      </Link>
    </article>
  );
}

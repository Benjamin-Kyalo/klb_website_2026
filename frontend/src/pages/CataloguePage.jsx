import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getBooks, getCatalogueFilters } from "../lib/api.js";
import { COLLECTION_LABELS, pluralise } from "../lib/format.js";
import Seo, { SITE_URL } from "../lib/seo.js";
import { useSite } from "../context/SiteContext.jsx";
import BookCard from "../components/BookCard.jsx";
import Loading from "../components/Loading.jsx";
import { CloseIcon, SearchIcon } from "../components/Icons.jsx";

const SORT_OPTIONS = [
  { value: "", label: "Catalogue order" },
  { value: "title", label: "Title A–Z" },
  { value: "price", label: "Price: low to high" },
  { value: "-price", label: "Price: high to low" },
  { value: "-new_arrival", label: "New arrivals first" },
];

export default function CataloguePage() {
  const { settings } = useSite();
  const [searchParams, setSearchParams] = useSearchParams();
  const [filters, setFilters] = useState(null);
  const [books, setBooks] = useState([]);
  const [count, setCount] = useState(0);
  const [nextUrl, setNextUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [searchText, setSearchText] = useState(searchParams.get("q") || "");

  const query = useMemo(
    () => ({
      q: searchParams.get("q") || "",
      collection: searchParams.get("collection") || "",
      level: searchParams.get("level") || "",
      subject: searchParams.get("subject") || "",
      sort: searchParams.get("sort") || "",
    }),
    [searchParams]
  );

  useEffect(() => {
    setSearchText(query.q);
  }, [query.q]);

  useEffect(() => {
    getCatalogueFilters()
      .then(setFilters)
      .catch(() => setFilters({ collections: [], levels: [], subjects: [] }));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setBooks([]);
    setCount(0);
    setNextUrl(null);

    const params = { page_size: 24 };
    if (query.q) params.q = query.q;
    if (query.collection) params.collection = query.collection;
    if (query.level) params.level = query.level;
    if (query.subject) params.subject = query.subject;
    if (query.sort) params.ordering = query.sort;

    getBooks(params)
      .then((data) => {
        if (cancelled) return;
        setBooks(data.results || []);
        setCount(data.count || 0);
        setNextUrl(data.next);
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
  }, [query]);

  function updateParam(key, value) {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    setSearchParams(next, { replace: true });
  }

  function clearAll() {
    setSearchParams({}, { replace: true });
    setFiltersOpen(false);
  }

  function submitSearch(event) {
    event.preventDefault();
    updateParam("q", searchText.trim());
  }

  async function loadMore() {
    if (!nextUrl || loadingMore) return;
    setLoadingMore(true);
    try {
      const url = new URL(nextUrl);
      const params = Object.fromEntries(url.searchParams.entries());
      const pageData = await getBooks(params);
      setBooks((current) => [...current, ...(pageData.results || [])]);
      setNextUrl(pageData.next);
    } catch (err) {
      setError(err);
    } finally {
      setLoadingMore(false);
    }
  }

  const activeFilters = [
    query.collection && ["collection", COLLECTION_LABELS[query.collection] || query.collection],
    query.level && ["level", query.level],
    query.subject && ["subject", query.subject],
    query.q && ["q", `“${query.q}”`],
  ].filter(Boolean);

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: "KLB catalogue",
    numberOfItems: count,
    itemListElement: books.slice(0, 20).map((book, index) => ({
      "@type": "ListItem",
      position: index + 1,
      url: `${SITE_URL}/books/${book.slug}/`,
      name: book.title,
    })),
  };

  return (
    <>
      <Seo
        title="Books & catalogue | Kenya Literature Bureau PLC"
        description="Search the KLB catalogue of CBC, secondary, revision and readers titles. Filter by collection, level and subject, and view prices and buying options."
        path="/books/"
        jsonLd={jsonLd}
      />

      <section className="catalogue-hero">
        <div className="container">
          <nav className="breadcrumbs" aria-label="Breadcrumb">
            <a href="/">Home</a>
            <span aria-hidden="true">/</span>
            <span aria-current="page">Books</span>
          </nav>
          <div className="catalogue-hero__row">
            <div>
              <p className="kicker">The KLB catalogue</p>
              <h1>Find your next book.</h1>
              <p>
                Every title we can currently verify from the KLB ebookstore — curriculum course books, revision
                guides, readers and reference. Search by title, subject or level.
              </p>
            </div>
            <form className="catalogue-search" onSubmit={submitSearch} role="search">
              <SearchIcon />
              <label className="sr-only" htmlFor="catalogueSearch">
                Search the catalogue
              </label>
              <input
                id="catalogueSearch"
                name="q"
                type="search"
                placeholder="Search titles, subjects or levels"
                autoComplete="off"
                value={searchText}
                onChange={(event) => setSearchText(event.target.value)}
              />
              <button type="submit">Search</button>
            </form>
          </div>
          <div className="active-filters catalogue-chips">
            {(filters?.collections || []).map((collection) => (
              <a
                className={`filter-chip${query.collection === collection ? " is-active" : ""}`}
                href={`/books/?collection=${encodeURIComponent(collection)}`}
                key={collection}
                onClick={(event) => {
                  event.preventDefault();
                  updateParam("collection", query.collection === collection ? "" : collection);
                }}
              >
                {COLLECTION_LABELS[collection] || collection}
              </a>
            ))}
          </div>
        </div>
      </section>

      <div className="container catalogue-layout">
        <aside className={`filters${filtersOpen ? " is-open" : ""}`} aria-label="Catalogue filters">
          <div className="filters__head">
            <strong>Filter</strong>
            <button className="filters__clear" type="button" onClick={clearAll}>
              Clear all
            </button>
            <button
              className="icon-btn filters-close-mobile"
              type="button"
              onClick={() => setFiltersOpen(false)}
              aria-label="Close filters"
            >
              <CloseIcon />
            </button>
          </div>

          <FilterGroup
            title="Collection"
            field="collection"
            values={filters?.collections}
            selected={query.collection}
            labels={COLLECTION_LABELS}
            onChange={updateParam}
          />
          <FilterGroup
            title="Level"
            field="level"
            values={filters?.levels}
            selected={query.level}
            onChange={updateParam}
          />
          <FilterGroup
            title="Subject"
            field="subject"
            values={filters?.subjects}
            selected={query.subject}
            onChange={updateParam}
            collapsed
          />
          <div className="btn-row" style={{ marginTop: "1.2rem" }}>
            <button className="btn btn--primary btn--full filters-toggle" type="button" onClick={() => setFiltersOpen(false)}>
              Show results
            </button>
          </div>
        </aside>

        <div>
          <div className="catalogue-toolbar">
            <p className="result-count">
              <strong>{count}</strong> {count === 1 ? "title" : "titles"}{" "}
              {activeFilters.length ? <span>matching your filters</span> : null}
            </p>
            <div className="catalogue-toolbar__actions">
              <button className="btn btn--secondary btn--sm filters-open" type="button" onClick={() => setFiltersOpen(true)}>
                Filters
              </button>
              <label className="sort-select">
                Sort by
                <select
                  value={query.sort}
                  onChange={(event) => updateParam("sort", event.target.value)}
                  aria-label="Sort catalogue"
                >
                  {SORT_OPTIONS.map((option) => (
                    <option value={option.value} key={option.value || "default"}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>

          {activeFilters.length ? (
            <div className="active-filters">
              {activeFilters.map(([key, label]) => (
                <button className="filter-chip" type="button" key={key} onClick={() => updateParam(key, "")}>
                  {label} <span aria-hidden="true">×</span>
                </button>
              ))}
              <button className="filter-chip filter-chip--clear" type="button" onClick={clearAll}>
                Clear all
              </button>
            </div>
          ) : null}

          <h2 className="sr-only">Catalogue results</h2>

          {loading ? (
            <Loading label="Loading the catalogue…" />
          ) : error ? (
            <div className="catalogue-empty">
              <strong>The catalogue could not be loaded.</strong>
              <p>{error.message}</p>
              <button className="btn btn--secondary" type="button" onClick={() => window.location.reload()}>
                Try again
              </button>
            </div>
          ) : books.length ? (
            <>
              <div className="book-grid catalogue-grid">
                {books.map((book, index) => (
                  <BookCard book={book} eager={index < 8} key={book.id} />
                ))}
              </div>
              {nextUrl ? (
                <div className="load-more">
                  <button className="btn btn--secondary" type="button" onClick={loadMore} disabled={loadingMore}>
                    {loadingMore ? "Loading…" : "Show more titles"}
                  </button>
                </div>
              ) : (
                <p className="catalogue-end muted-meta">
                  Showing all {pluralise(count, "title")} for this search.
                </p>
              )}
            </>
          ) : (
            <div className="catalogue-empty">
              <strong>No titles match those filters.</strong>
              <p>Try removing a filter or searching for a broader term such as “mathematics” or “Grade 3”.</p>
              <button className="btn btn--secondary" type="button" onClick={clearAll}>
                Clear all filters
              </button>
            </div>
          )}

          <div className="callout" style={{ marginTop: "2.5rem" }}>
            <strong>About this catalogue</strong>
            <p>
              Titles, covers and prices are drawn from KLB&apos;s public ebookstore. Prices shown are e-book prices
              where listed and may differ from print prices. ISBNs and publication dates are not published on the
              ebookstore, so they are marked “available on request”. Confirm edition, availability and price with{" "}
              <a href={`mailto:${settings.customer_email}`}>{settings.customer_email}</a> before ordering.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}

function FilterGroup({ title, field, values, selected, labels = {}, onChange, collapsed = false }) {
  if (!values || !values.length) return null;
  return (
    <details className="filter-group" open={!collapsed}>
      <summary>{title}</summary>
      <div className="filter-options">
        {values.map((value) => (
          <label className="check" key={value}>
            <input
              type="checkbox"
              checked={selected === value}
              onChange={() => onChange(field, selected === value ? "" : value)}
            />
            <span>{labels[value] || value}</span>
          </label>
        ))}
      </div>
    </details>
  );
}

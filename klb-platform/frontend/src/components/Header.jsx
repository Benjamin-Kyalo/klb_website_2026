import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { getBooks } from "../lib/api.js";
import { safeImagePath } from "../lib/format.js";
import { useSite } from "../context/SiteContext.jsx";
import { Caret, CloseIcon, MenuIcon, SearchIcon } from "./Icons.jsx";

function isActive(pathname, href) {
  const target = href.split("?")[0].split("#")[0];
  if (target === "/") return pathname === "/";
  return pathname === target || pathname.startsWith(target);
}

function InlineLink({ item, className, onNavigate, children, ...rest }) {
  const external = /^https?:\/\//i.test(item.href);
  if (external || item.href.startsWith("mailto:") || item.href.startsWith("tel:")) {
    return (
      <a className={className} href={item.href} rel="noopener" onClick={onNavigate} {...rest}>
        {children}
      </a>
    );
  }
  return (
    <Link className={className} to={item.href} onClick={onNavigate} {...rest}>
      {children}
    </Link>
  );
}

export default function Header() {
  const { settings, navigation } = useSite();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const searchInputRef = useRef(null);
  const searchButtonRef = useRef(null);

  useEffect(() => {
    setMobileOpen(false);
    setSearchOpen(false);
  }, [pathname]);

  useEffect(() => {
    document.body.classList.toggle("is-locked", mobileOpen || searchOpen);
    return () => document.body.classList.remove("is-locked");
  }, [mobileOpen, searchOpen]);

  useEffect(() => {
    if (!searchOpen) return undefined;
    const timer = window.setTimeout(() => searchInputRef.current?.focus(), 60);
    return () => window.clearTimeout(timer);
  }, [searchOpen]);

  useEffect(() => {
    if (!searchOpen) return undefined;
    const onKeyDown = (event) => {
      if (event.key === "Escape") setSearchOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [searchOpen]);

  useEffect(() => {
    const text = query.trim();
    if (!searchOpen || text.length < 2) {
      setResults([]);
      setSearching(false);
      return undefined;
    }
    setSearching(true);
    const timer = window.setTimeout(async () => {
      try {
        const data = await getBooks({ q: text, page_size: 6 });
        setResults(data.results || []);
      } catch {
        setResults([]);
      } finally {
        setSearching(false);
      }
    }, 250);
    return () => window.clearTimeout(timer);
  }, [query, searchOpen]);

  function openSearch() {
    setSearchOpen(true);
    setMobileOpen(false);
  }

  function closeSearch() {
    setSearchOpen(false);
    setQuery("");
    setResults([]);
    searchButtonRef.current?.focus();
  }

  function handleSearchSubmit(event) {
    event.preventDefault();
    const text = query.trim();
    closeSearch();
    navigate(text ? `/books/?q=${encodeURIComponent(text)}` : "/books/");
  }

  return (
    <>
      <div className="site-utility">
        <div className="container utility-inner">
          <p className="utility-tagline">
            <span aria-hidden="true" />
            {settings.tagline}
          </p>
          <div className="utility-links">
            <Link to="/tenders/">Tenders</Link>
            <Link to="/careers/">Careers</Link>
            <a href={settings.ebookstore || "https://klbbooks.com/"} rel="noopener">
              KLB ebookstore ↗
            </a>
          </div>
        </div>
      </div>

      {settings.announcement ? (
        <div className="announcement-bar" role="status">
          <div className="container">{settings.announcement}</div>
        </div>
      ) : null}

      <header className="site-header" id="siteHeader">
        <div className="container header-inner">
          <Link className="brand" to="/">
            <span className="brand-mark">
              <img src="/assets/klb-emblem.png" alt="" width="482" height="482" />
            </span>
            <span className="brand-text">
              <span className="brand-name">{settings.site_name}</span>
              <span className="brand-tagline">Publishers &amp; printers</span>
            </span>
          </Link>

          <nav className="nav-primary" aria-label="Primary">
            <ul className="nav-list">
              {navigation.map((item) => {
                const active = isActive(pathname, item.href);
                const panelId = `nav-${item.label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
                return (
                  <li className={`nav-item${active ? " is-active" : ""}`} key={item.label}>
                    <InlineLink
                      item={item}
                      className="nav-link"
                      aria-current={active ? "page" : undefined}
                    >
                      {item.label} {item.panel ? <Caret /> : null}
                    </InlineLink>
                    {item.panel ? (
                      <div className="nav-panel nav-panel--wide" id={panelId}>
                        <div className="nav-panel-grid">
                          <div className="nav-panel-intro">
                            <strong>{item.label}</strong>
                            <p>{item.panel.intro}</p>
                          </div>
                          {item.panel.columns.map((column) => (
                            <div key={column.title}>
                              <h3>{column.title}</h3>
                              <ul>
                                {column.links.map((link) => {
                                  const [label, href, note] = link;
                                  return (
                                    <li key={`${column.title}-${label}`}>
                                      <InlineLink item={{ href }}>
                                        {label}
                                        {note ? <span>{note}</span> : null}
                                      </InlineLink>
                                    </li>
                                  );
                                })}
                              </ul>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          </nav>

          <div className="header-actions">
            <button
              className="icon-btn search-desktop"
              type="button"
              ref={searchButtonRef}
              onClick={openSearch}
              aria-label="Search books"
            >
              <SearchIcon />
            </button>
            <Link className="btn btn--primary btn--sm btn--header" to="/books/">
              Browse books
            </Link>
            <button
              className="icon-btn menu-toggle"
              type="button"
              onClick={() => setMobileOpen(true)}
              aria-label="Open menu"
              aria-expanded={mobileOpen}
              aria-controls="mobileNav"
            >
              <MenuIcon />
            </button>
          </div>
        </div>
      </header>

      <div
        className={`mobile-nav${mobileOpen ? " is-open" : ""}`}
        id="mobileNav"
        aria-hidden={mobileOpen ? "false" : "true"}
        aria-label="Mobile navigation"
      >
        <div className="mobile-nav-head">
          <Link className="brand" to="/" aria-label="Kenya Literature Bureau home">
            <span className="brand-mark">
              <img src="/assets/klb-emblem.png" alt="" width="482" height="482" />
            </span>
            <span className="brand-text">
              <span className="brand-name">{settings.site_name}</span>
              <span className="brand-tagline">Publishers &amp; printers</span>
            </span>
          </Link>
          <button className="icon-btn" type="button" onClick={() => setMobileOpen(false)} aria-label="Close menu">
            <CloseIcon />
          </button>
        </div>
        <div className="mobile-nav-body">
          <ul className="mobile-nav-list">
            {navigation.map((item) => (
              <li key={item.label}>
                {item.panel ? (
                  <details>
                    <summary>{item.label}</summary>
                    <ul className="mobile-sub">
                      {item.panel.columns.flatMap((column) =>
                        column.links.map((link) => (
                          <li key={`${column.title}-${link[0]}`}>
                            <a href={link[1]} onClick={() => setMobileOpen(false)}>
                              {link[0]}
                            </a>
                          </li>
                        ))
                      )}
                    </ul>
                  </details>
                ) : (
                  <InlineLink
                    item={item}
                    className="mobile-nav-link"
                    onNavigate={() => setMobileOpen(false)}
                    aria-current={isActive(pathname, item.href) ? "page" : undefined}
                  >
                    {item.label} <span aria-hidden="true">→</span>
                  </InlineLink>
                )}
              </li>
            ))}
          </ul>
        </div>
        <div className="mobile-nav-foot">
          <Link className="btn btn--primary btn--full" to="/books/" onClick={() => setMobileOpen(false)}>
            Browse the catalogue
          </Link>
          <div className="mobile-contact">
            <a href={`tel:${(settings.phone || "").replace(/[^\d+]/g, "")}`}>{settings.phone}</a>
            <a href={`mailto:${settings.contact_email}`}>{settings.contact_email}</a>
            <a href={settings.ebookstore || "https://klbbooks.com/"} rel="noopener">
              KLB ebookstore ↗
            </a>
          </div>
        </div>
      </div>

      {searchOpen ? (
        <div
          className="search-dialog is-open"
          role="dialog"
          aria-modal="true"
          aria-labelledby="searchTitle"
          onClick={(event) => {
            if (event.target === event.currentTarget) closeSearch();
          }}
        >
          <div className="search-shell">
            <h2 className="sr-only" id="searchTitle">
              Search KLB books
            </h2>
            <form className="search-form" onSubmit={handleSearchSubmit} role="search">
              <SearchIcon />
              <label className="sr-only" htmlFor="siteSearch">
                Search books, subjects or levels
              </label>
              <input
                id="siteSearch"
                ref={searchInputRef}
                name="q"
                type="search"
                placeholder="Search a title, subject or level…"
                autoComplete="off"
                spellCheck="false"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
              <button type="button" className="icon-btn" onClick={closeSearch} aria-label="Close search">
                <CloseIcon />
              </button>
            </form>
            <div className="search-results" aria-live="polite">
              {query.trim().length < 2 ? (
                <p className="search-hint">
                  Start typing to search more than 1,000 KLB titles, or press <kbd>Enter</kbd> for the full catalogue.
                </p>
              ) : searching ? (
                <p className="search-hint">Searching the catalogue…</p>
              ) : results.length ? (
                results.map((book) => (
                  <Link className="search-result" key={book.id} to={`/books/${book.slug}/`} onClick={closeSearch}>
                    <img src={safeImagePath(book.cover_url)} alt="" width="40" height="60" loading="lazy" />
                    <div>
                      <strong>{book.title}</strong>
                      <span>
                        {book.subject} · {book.level}
                      </span>
                    </div>
                    <span className="arrow" aria-hidden="true">
                      →
                    </span>
                  </Link>
                ))
              ) : (
                <div className="search-empty">
                  <strong>No titles matched “{query.trim()}”.</strong>
                  <p>Try a subject such as mathematics, or a level such as Grade 3.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

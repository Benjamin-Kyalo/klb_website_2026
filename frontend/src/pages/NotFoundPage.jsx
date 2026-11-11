import { Link } from "react-router-dom";
import Seo from "../lib/seo.js";
import { SearchIcon } from "../components/Icons.jsx";

export default function NotFoundPage() {
  return (
    <>
      <Seo
        title="Page not found | Kenya Literature Bureau PLC"
        description="The page you requested could not be found. Browse the KLB catalogue, news, resources or contact the team."
        path="/404/"
        noindex
      />
      <section className="page-hero">
        <div className="container">
          <nav className="breadcrumbs" aria-label="Breadcrumb">
            <Link to="/">Home</Link>
            <span aria-hidden="true">/</span>
            <span aria-current="page">Page not found</span>
          </nav>
          <div className="page-hero__inner">
            <div>
              <p className="kicker">404</p>
              <h1>That page has moved or never existed.</h1>
              <p>
                Check the address, search the catalogue, or use the links below to find what you need.
              </p>
            </div>
          </div>
        </div>
      </section>
      <section className="section">
        <div className="container">
          <form className="catalogue-search" action="/books/" method="get" role="search" style={{ maxWidth: "42rem" }}>
            <SearchIcon />
            <label className="sr-only" htmlFor="notFoundSearch">
              Search the catalogue
            </label>
            <input id="notFoundSearch" name="q" type="search" placeholder="Search titles, subjects or levels" />
            <button type="submit">Search</button>
          </form>
          <div className="btn-row" style={{ marginTop: "1.4rem" }}>
            <Link className="btn btn--primary" to="/">
              Home
            </Link>
            <Link className="btn btn--secondary" to="/books/">
              Catalogue
            </Link>
            <Link className="btn btn--secondary" to="/contact/">
              Contact
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}

import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { admin } from "../lib/api.js";
import { formatDate } from "../lib/format.js";
import { useSite } from "../context/SiteContext.jsx";
import { useAuth } from "../context/AuthContext.jsx";
import { Alert, Card, EmptyState, PageHead, StatusBadge } from "./AdminUI.jsx";

export default function AdminPages() {
  const { reload: reloadSite } = useSite();
  const { can } = useAuth();
  const [pages, setPages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setPages(await admin.all("pages", { search: appliedSearch }));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [appliedSearch]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleDuplicate(page) {
    try {
      const copy = await admin.duplicatePage(page.slug);
      setNotice(`Created “${copy.title}” as a draft.`);
      await load();
      await reloadSite();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDelete(page) {
    if (page.slug === "home") {
      setError("The home page cannot be deleted. Edit it instead, or create another page and change the navigation.");
      return;
    }
    if (!window.confirm(`Delete “${page.title}”? Its sections will be removed. This cannot be undone.`)) return;
    try {
      await admin.remove("pages", page.slug);
      setNotice(`“${page.title}” was deleted.`);
      await load();
      await reloadSite();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <>
      <PageHead
        title="Pages"
        lead="Each page is built from sections. Open a page to edit its text, rich HTML or the automatic lists (books, news, tenders, careers and resources)."
        actions={
          can("pages", "create") ? (
            <Link className="btn btn--primary" to="/admin/pages/new">
              New page
            </Link>
          ) : null
        }
      />

      <Alert kind="success" onClose={() => setNotice("")}>
        {notice}
      </Alert>
      <Alert kind="error" onClose={() => setError("")}>
        {error}
      </Alert>

      <Card
        title={`${pages.length} ${pages.length === 1 ? "page" : "pages"}`}
        actions={
          <form
            className="admin-search"
            onSubmit={(event) => {
              event.preventDefault();
              setAppliedSearch(search.trim());
            }}
          >
            <label className="sr-only" htmlFor="pages-search">
              Search pages
            </label>
            <input
              id="pages-search"
              type="search"
              value={search}
              placeholder="Search pages…"
              onChange={(event) => setSearch(event.target.value)}
            />
            <button className="btn btn--secondary btn--sm" type="submit">
              Search
            </button>
          </form>
        }
      >
        {loading ? (
          <p className="muted-meta">Loading pages…</p>
        ) : pages.length ? (
          <div className="table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>Page</th>
                  <th>Status</th>
                  <th>Sections</th>
                  <th>Updated</th>
                  <th className="admin-table__actions">Actions</th>
                </tr>
              </thead>
              <tbody>
                {pages.map((page) => (
                  <tr key={page.id}>
                    <td className="admin-table__title">
                      {page.title}
                      <br />
                      <small className="mono">/{page.slug === "home" ? "" : `${page.slug}/`}</small>
                    </td>
                    <td>
                      <StatusBadge status={page.status} />
                    </td>
                    <td>{page.section_count}</td>
                    <td>{formatDate(page.updated_at)}</td>
                    <td className="admin-table__actions">
                      {can("pages", "edit") ? (
                        <Link className="btn btn--secondary btn--sm" to={`/admin/pages/${page.slug}/edit`}>
                          Edit
                        </Link>
                      ) : null}
                      <a
                        className="btn btn--secondary btn--sm"
                        href={page.slug === "home" ? "/" : `/${page.slug}/`}
                        target="_blank"
                        rel="noopener"
                      >
                        View
                      </a>
                      {can("pages", "create") ? (
                        <button className="btn btn--secondary btn--sm" type="button" onClick={() => handleDuplicate(page)}>
                          Duplicate
                        </button>
                      ) : null}
                      {can("pages", "delete") ? (
                        <button className="btn btn--danger btn--sm" type="button" onClick={() => handleDelete(page)}>
                          Delete
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No pages found.">
            {appliedSearch ? "Try a different search term." : "Create the first page to get started."}
          </EmptyState>
        )}
      </Card>
    </>
  );
}

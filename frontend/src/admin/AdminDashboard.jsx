import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { admin } from "../lib/api.js";
import { formatDate } from "../lib/format.js";
import { useAuth } from "../context/AuthContext.jsx";
import { Alert, Card, PageHead } from "./AdminUI.jsx";

const QUICK_LINKS = [
  { label: "Manage pages", href: "/admin/pages", note: "Edit any page, section or block of HTML on the site.", module: "pages" },
  { label: "Catalogue", href: "/admin/books", note: "Titles, prices, covers and featured selections.", module: "books" },
  { label: "News", href: "/admin/news", note: "Announcements shown on the home page and news index.", module: "news" },
  { label: "Enquiries", href: "/admin/enquiries", note: "Messages sent through the contact form.", module: "enquiries" },
  { label: "Resources", href: "/admin/resources", note: "Price lists, annual reports and forms.", module: "resources" },
  { label: "Admin settings", href: "/admin/settings", note: "Organisation details, publishing defaults and system preferences.", module: "settings" },
  { label: "Backup & restore", href: "/admin/backup", note: "Create, download, upload and restore site archives.", module: "backup" },
];

export default function AdminDashboard() {
  const { user, can } = useAuth();
  const [stats, setStats] = useState(null);
  const [recent, setRecent] = useState([]);
  const [activity, setActivity] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const jobs = [admin.stats()];
    if (can("enquiries", "view")) jobs.push(admin.list("enquiries", { page_size: 5 }));
    else jobs.push(Promise.resolve({ results: [] }));
    if (can("activity", "view")) jobs.push(admin.activity({ page_size: 6 }));
    else jobs.push(Promise.resolve({ results: [] }));

    Promise.all(jobs)
      .then(([statsData, enquiryData, activityData]) => {
        if (cancelled) return;
        setStats(statsData);
        setRecent(enquiryData.results || []);
        setActivity(activityData.results || []);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [can]);

  const quickLinks = QUICK_LINKS.filter((item) => can(item.module, "view"));
  const canEnquiries = can("enquiries", "view");
  const canSubscribers = can("subscribers", "view");
  const canCatalogue = can("books", "view") || can("pages", "view");
  const canOperations =
    can("careers", "view") || can("tenders", "view") || can("resources", "view");

  return (
    <>
      <PageHead
        title={`Welcome${user?.display_name ? `, ${user.display_name.split(" ")[0]}` : ""}`}
        lead="Everything on the public website is edited here. Changes go live as soon as you save."
        actions={
          can("pages", "edit") ? (
            <Link className="btn btn--primary" to="/admin/pages/home/edit">
              Edit home page
            </Link>
          ) : null
        }
      />

      <Alert kind="error" onClose={() => setError("")}>
        {error}
      </Alert>

      {loading ? (
        <p className="muted-meta">Loading dashboard…</p>
      ) : stats ? (
        <>
          <div className="admin-stats">
            {can("books", "view") ? (
              <div className="admin-stat">
                <strong>{stats.published_books ?? stats.books}</strong>
                <span>Published books</span>
              </div>
            ) : null}
            {can("pages", "view") ? (
              <div className="admin-stat">
                <strong>{stats.published_pages ?? stats.pages}</strong>
                <span>Published pages</span>
              </div>
            ) : null}
            {can("news", "view") ? (
              <div className="admin-stat">
                <strong>{stats.news}</strong>
                <span>News items</span>
              </div>
            ) : null}
            {canEnquiries ? (
              <div className={`admin-stat${stats.new_enquiries > 0 ? " admin-stat--alert" : ""}`}>
                <strong>{stats.new_enquiries}</strong>
                <span>New enquiries</span>
              </div>
            ) : null}
          </div>

          <div className={canEnquiries ? "admin-split" : ""}>
            {canEnquiries ? (
              <Card
                title="Latest enquiries"
                actions={
                  <Link className="btn btn--secondary btn--sm" to="/admin/enquiries">
                    View all
                  </Link>
                }
              >
                {recent.length ? (
                  <div className="table-wrap">
                    <table className="admin-table">
                      <thead>
                        <tr>
                          <th>From</th>
                          <th>Subject</th>
                          <th>Received</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {recent.map((item) => (
                          <tr key={item.id}>
                            <td className="admin-table__title">
                              {item.name}
                              <br />
                              <small>{item.email}</small>
                            </td>
                            <td>{item.subject}</td>
                            <td>{formatDate(item.created_at)}</td>
                            <td>
                              <span className={`badge badge--${item.status === "new" ? "new" : "muted"}`}>
                                {item.status.replace("_", " ")}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="muted-meta">No enquiries have been received yet.</p>
                )}
              </Card>
            ) : null}

            <Card title="Quick actions">
              <ul className="admin-quicklinks">
                {quickLinks.length ? (
                  quickLinks.map((item) => (
                    <li key={item.href}>
                      <Link to={item.href}>{item.label}</Link>
                      <span>{item.note}</span>
                    </li>
                  ))
                ) : (
                  <li className="muted-meta">No sections are available for this account.</li>
                )}
              </ul>
            </Card>
          </div>

          {canCatalogue || canOperations || canSubscribers ? (
            <div className="admin-grid admin-grid--3" style={{ marginTop: "1.2rem" }}>
              {canCatalogue ? (
                <Card title="Catalogue at a glance">
                  <dl className="admin-facts">
                    {can("books", "view") ? (
                      <div>
                        <dt>Books</dt>
                        <dd>{stats.books}</dd>
                      </div>
                    ) : null}
                    {can("books", "view") ? (
                      <div>
                        <dt>Published</dt>
                        <dd>{stats.published_books}</dd>
                      </div>
                    ) : null}
                    {can("pages", "view") ? (
                      <div>
                        <dt>Pages</dt>
                        <dd>{stats.pages}</dd>
                      </div>
                    ) : null}
                  </dl>
                </Card>
              ) : null}
              {canOperations ? (
                <Card title="Careers and tenders">
                  <dl className="admin-facts">
                    {can("careers", "view") ? (
                      <div>
                        <dt>Careers</dt>
                        <dd>{stats.careers}</dd>
                      </div>
                    ) : null}
                    {can("tenders", "view") ? (
                      <div>
                        <dt>Tenders</dt>
                        <dd>{stats.tenders}</dd>
                      </div>
                    ) : null}
                    {can("resources", "view") ? (
                      <div>
                        <dt>Resources</dt>
                        <dd>{stats.resources}</dd>
                      </div>
                    ) : null}
                  </dl>
                </Card>
              ) : null}
              {canSubscribers ? (
                <Card title="Newsletter">
                  <dl className="admin-facts">
                    <div>
                      <dt>Subscribers</dt>
                      <dd>{stats.subscribers}</dd>
                    </div>
                  </dl>
                  <Link className="btn btn--secondary btn--sm" to="/admin/subscribers">
                    View subscribers
                  </Link>
                </Card>
              ) : null}
            </div>
          ) : null}

          {can("activity", "view") ? (
            <Card
              title="Recent activity"
              className="admin-activity-summary"
              actions={
                <Link className="btn btn--secondary btn--sm" to="/admin/activity">
                  Full log
                </Link>
              }
            >
              {activity.length ? (
                <ul className="activity-feed">
                  {activity.map((entry) => (
                    <li key={entry.id}>
                      <span className={`activity-dot activity-dot--${entry.action}`} aria-hidden="true" />
                      <div>
                        <strong>{entry.object_label || entry.module}</strong>
                        <p>
                          {entry.actor_name || "System"} {entry.action_label.toLowerCase()} {entry.module}
                          <span className="activity-time">
                            {formatDate(entry.created_at, {
                              day: "numeric",
                              month: "short",
                              year: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="muted-meta">No activity has been recorded yet.</p>
              )}
            </Card>
          ) : null}
        </>
      ) : null}
    </>
  );
}

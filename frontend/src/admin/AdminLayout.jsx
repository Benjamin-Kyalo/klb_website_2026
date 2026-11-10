import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

const TITLES = [
  ["/admin/pages", "Pages"],
  ["/admin/team-photos", "Team photos"],
  ["/admin/digital-partners", "Digital partners"],
  ["/admin/books", "Catalogue"],
  ["/admin/news", "News"],
  ["/admin/careers", "Careers"],
  ["/admin/tenders", "Tenders"],
  ["/admin/resources", "Resources"],
  ["/admin/enquiries", "Enquiries"],
  ["/admin/subscribers", "Newsletter"],
  ["/admin/settings", "Site settings"],
  ["/admin/users", "Users and permissions"],
  ["/admin/activity", "Activity log"],
  ["/admin/options", "Dropdown options"],
  ["/admin/account", "Your account"],
];

export default function AdminLayout({ children }) {
  const { user, logout, can, roleLabel, isSuperAdministrator } = useAuth();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    document.body.classList.add("admin-body");
    return () => document.body.classList.remove("admin-body");
  }, []);

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  const title = TITLES.find(([path]) => pathname.startsWith(path))?.[1] || "Dashboard";

  async function handleLogout() {
    await logout();
    navigate("/admin/login", { replace: true });
  }

  const contentNav = [
    { to: "/admin/pages", label: "Pages", module: "pages" },
    { to: "/admin/team-photos", label: "Team photos", module: "pages" },
    { to: "/admin/digital-partners", label: "Digital partners", module: "pages" },
    { to: "/admin/books", label: "Catalogue", module: "books" },
    { to: "/admin/news", label: "News", module: "news" },
    { to: "/admin/careers", label: "Careers", module: "careers" },
    { to: "/admin/tenders", label: "Tenders", module: "tenders" },
    { to: "/admin/resources", label: "Resources", module: "resources" },
  ].filter((item) => can(item.module, "view"));

  const audienceNav = [
    { to: "/admin/enquiries", label: "Enquiries", module: "enquiries" },
    { to: "/admin/subscribers", label: "Newsletter", module: "subscribers" },
  ].filter((item) => can(item.module, "view"));

  const systemNav = [
    { to: "/admin/settings", label: "Site settings", module: "settings" },
    { to: "/admin/users", label: "Users and permissions", module: "users" },
    { to: "/admin/activity", label: "Activity log", module: "activity" },
    { to: "/admin/options", label: "Dropdown options", module: "options", manage: true },
  ].filter((item) => (item.manage ? can(item.module, "create") || can(item.module, "edit") : can(item.module, "view")));

  const sections = [
    { label: "Content", items: contentNav },
    { label: "Audience", items: audienceNav },
    { label: "System", items: systemNav },
  ].filter((section) => section.items.length);

  return (
    <>
      <a className="admin-skip" href="#admin-main">
        Skip to content
      </a>
      <div className={`admin-shell${menuOpen ? " admin-shell--menu" : ""}`}>
        <aside className={`admin-sidebar${menuOpen ? " is-open" : ""}`}>
          <Link className="admin-brand" to="/admin">
            <span className="admin-brand__mark">
              <img src="/assets/klb-emblem.png" alt="" width="482" height="482" />
            </span>
            <span>
              <strong>Content manager</strong>
              <small>Kenya Literature Bureau</small>
            </span>
          </Link>

          <div className="admin-rolebar">
            <span className={`role-badge role-badge--${user?.role || "editor"}`}>
              {roleLabel}
            </span>
            {isSuperAdministrator ? <span className="role-note">Full system access</span> : null}
          </div>

          <nav className="admin-nav" aria-label="Admin sections">
            <NavLink to="/admin" end className={({ isActive }) => (isActive ? "is-active" : undefined)}>
              Dashboard
            </NavLink>
            {sections.map((section) => (
              <div className="admin-nav__group" key={section.label}>
                <p className="admin-nav__label">{section.label}</p>
                {section.items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) => (isActive ? "is-active" : undefined)}
                  >
                    {item.label}
                  </NavLink>
                ))}
              </div>
            ))}
            <div className="admin-nav__group">
              <p className="admin-nav__label">Account</p>
              <NavLink
                to="/admin/account"
                className={({ isActive }) => (isActive ? "is-active" : undefined)}
              >
                Your account
              </NavLink>
            </div>
          </nav>

          <div className="admin-sidebar__foot">
            <a href="/" target="_blank" rel="noopener">
              View live site ↗
            </a>
            <button type="button" className="admin-linkbtn" onClick={handleLogout}>
              Sign out
            </button>
            {user ? (
              <p className="admin-userchip">
                <span>{user.display_name}</span>
                <small>{user.email}</small>
              </p>
            ) : null}
          </div>
        </aside>

        {menuOpen ? (
          <button
            className="admin-scrim"
            type="button"
            aria-label="Close menu"
            onClick={() => setMenuOpen(false)}
          />
        ) : null}

        <div className="admin-main" id="admin-main">
          <header className="admin-topbar">
            <button
              className="admin-menutoggle"
              type="button"
              aria-label="Toggle menu"
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((open) => !open)}
            >
              <span />
              <span />
              <span />
            </button>
            <p className="admin-topbar__title">{title}</p>
            <span className={`role-badge role-badge--${user?.role || "editor"} admin-topbar__role`}>
              {roleLabel}
            </span>
            <a className="admin-topbar__site" href="/" target="_blank" rel="noopener">
              Open website ↗
            </a>
          </header>
          <div className="admin-content">{children || <Outlet />}</div>
        </div>
      </div>
    </>
  );
}

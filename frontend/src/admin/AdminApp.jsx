import { lazy, Suspense, useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import Loading from "../components/Loading.jsx";
import AdminLayout from "./AdminLayout.jsx";
import AdminLogin from "./AdminLogin.jsx";
import { AdminBooks, AdminCareers, AdminNews, AdminResources, AdminSubscribers, AdminTenders } from "./AdminCollections.jsx";

const AdminDashboard = lazy(() => import("./AdminDashboard.jsx"));
const AdminPages = lazy(() => import("./AdminPages.jsx"));
const PageEditor = lazy(() => import("./PageEditor.jsx"));
const AdminEnquiries = lazy(() => import("./AdminEnquiries.jsx"));
const AdminSettings = lazy(() => import("./AdminSettings.jsx"));
const AdminUsers = lazy(() => import("./AdminUsers.jsx"));
const AdminActivity = lazy(() => import("./AdminActivity.jsx"));
const AdminOptions = lazy(() => import("./AdminOptions.jsx"));
const AdminAccount = lazy(() => import("./AdminAccount.jsx"));
const AdminTeamPhotos = lazy(() => import("./AdminTeamPhotos.jsx"));
const AdminDigitalPartners = lazy(() => import("./AdminDigitalPartners.jsx"));

function RequireAuth({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="admin-boot">
        <Loading label="Checking your session…" />
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/admin/login" state={{ from: location.pathname }} replace />;
  }
  return children;
}

function RequirePermission({ module, action = "view", children }) {
  const { can } = useAuth();
  if (!can(module, action)) return <Navigate to="/admin" replace />;
  return children;
}

function Page({ module, action, children }) {
  return (
    <RequireAuth>
      <RequirePermission module={module} action={action}>
        <AdminLayout>{children}</AdminLayout>
      </RequirePermission>
    </RequireAuth>
  );
}

function LazyPage({ children }) {
  return (
    <Suspense fallback={<div className="admin-boot"><Loading label="Loading…" /></div>}>
      {children}
    </Suspense>
  );
}

export default function AdminApp() {
  useEffect(() => {
    document.body.classList.add("admin-body");
    return () => document.body.classList.remove("admin-body");
  }, []);

  return (
    <Routes>
      <Route path="login" element={<AdminLogin />} />
      <Route
        index
        element={
          <RequireAuth>
            <AdminLayout>
              <LazyPage><AdminDashboard /></LazyPage>
            </AdminLayout>
          </RequireAuth>
        }
      />
      <Route path="pages" element={<Page module="pages"><LazyPage><AdminPages /></LazyPage></Page>} />
      <Route
        path="pages/new"
        element={
          <Page module="pages" action="create">
            <LazyPage><PageEditor /></LazyPage>
          </Page>
        }
      />
      <Route
        path="pages/:slug/edit"
        element={
          <Page module="pages" action="edit">
            <LazyPage><PageEditor /></LazyPage>
          </Page>
        }
      />
      <Route path="books" element={<Page module="books"><LazyPage><AdminBooks /></LazyPage></Page>} />
      <Route path="news" element={<Page module="news"><LazyPage><AdminNews /></LazyPage></Page>} />
      <Route path="careers" element={<Page module="careers"><LazyPage><AdminCareers /></LazyPage></Page>} />
      <Route path="tenders" element={<Page module="tenders"><LazyPage><AdminTenders /></LazyPage></Page>} />
      <Route path="resources" element={<Page module="resources"><LazyPage><AdminResources /></LazyPage></Page>} />
      <Route path="enquiries" element={<Page module="enquiries"><LazyPage><AdminEnquiries /></LazyPage></Page>} />
      <Route path="subscribers" element={<Page module="subscribers"><LazyPage><AdminSubscribers /></LazyPage></Page>} />
      <Route path="settings" element={<Page module="settings"><LazyPage><AdminSettings /></LazyPage></Page>} />
      <Route path="users" element={<Page module="users"><LazyPage><AdminUsers /></LazyPage></Page>} />
      <Route path="activity" element={<Page module="activity"><LazyPage><AdminActivity /></LazyPage></Page>} />
      <Route path="options" element={<Page module="options"><LazyPage><AdminOptions /></LazyPage></Page>} />
      <Route path="team-photos" element={<Page module="pages"><LazyPage><AdminTeamPhotos /></LazyPage></Page>} />
      <Route path="digital-partners" element={<Page module="pages"><LazyPage><AdminDigitalPartners /></LazyPage></Page>} />
      <Route
        path="account"
        element={
          <RequireAuth>
            <AdminLayout>
              <LazyPage><AdminAccount /></LazyPage>
            </AdminLayout>
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/admin" replace />} />
    </Routes>
  );
}

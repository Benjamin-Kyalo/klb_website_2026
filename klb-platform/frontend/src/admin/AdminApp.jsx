import { useEffect } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import Loading from "../components/Loading.jsx";
import AdminLayout from "./AdminLayout.jsx";
import AdminLogin from "./AdminLogin.jsx";
import AdminDashboard from "./AdminDashboard.jsx";
import AdminPages from "./AdminPages.jsx";
import PageEditor from "./PageEditor.jsx";
import { AdminBooks, AdminCareers, AdminNews, AdminResources, AdminSubscribers, AdminTenders } from "./AdminCollections.jsx";
import AdminEnquiries from "./AdminEnquiries.jsx";
import AdminSettings from "./AdminSettings.jsx";
import AdminUsers from "./AdminUsers.jsx";
import AdminActivity from "./AdminActivity.jsx";
import AdminOptions from "./AdminOptions.jsx";
import AdminAccount from "./AdminAccount.jsx";

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
              <AdminDashboard />
            </AdminLayout>
          </RequireAuth>
        }
      />
      <Route path="pages" element={<Page module="pages"><AdminPages /></Page>} />
      <Route
        path="pages/new"
        element={
          <Page module="pages" action="create">
            <PageEditor />
          </Page>
        }
      />
      <Route
        path="pages/:slug/edit"
        element={
          <Page module="pages" action="edit">
            <PageEditor />
          </Page>
        }
      />
      <Route path="books" element={<Page module="books"><AdminBooks /></Page>} />
      <Route path="news" element={<Page module="news"><AdminNews /></Page>} />
      <Route path="careers" element={<Page module="careers"><AdminCareers /></Page>} />
      <Route path="tenders" element={<Page module="tenders"><AdminTenders /></Page>} />
      <Route path="resources" element={<Page module="resources"><AdminResources /></Page>} />
      <Route path="enquiries" element={<Page module="enquiries"><AdminEnquiries /></Page>} />
      <Route path="subscribers" element={<Page module="subscribers"><AdminSubscribers /></Page>} />
      <Route path="settings" element={<Page module="settings"><AdminSettings /></Page>} />
      <Route path="users" element={<Page module="users"><AdminUsers /></Page>} />
      <Route path="activity" element={<Page module="activity"><AdminActivity /></Page>} />
      <Route path="options" element={<Page module="options"><AdminOptions /></Page>} />
      <Route
        path="account"
        element={
          <RequireAuth>
            <AdminLayout>
              <AdminAccount />
            </AdminLayout>
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/admin" replace />} />
    </Routes>
  );
}

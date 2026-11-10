import { Navigate, Route, Routes, useParams } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import PageView from "./pages/PageView.jsx";
import CataloguePage from "./pages/CataloguePage.jsx";
import BookDetailPage from "./pages/BookDetailPage.jsx";
import NewsDetailPage from "./pages/NewsDetailPage.jsx";
import NotFoundPage from "./pages/NotFoundPage.jsx";
import AdminApp from "./admin/AdminApp.jsx";

function PageRoute() {
  const { slug } = useParams();
  return (
    <Layout>
      <PageView slug={slug} />
    </Layout>
  );
}

export default function App() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <Layout>
            <PageView slug="home" />
          </Layout>
        }
      />
      <Route
        path="/books"
        element={
          <Layout>
            <CataloguePage />
          </Layout>
        }
      />
      <Route
        path="/books/:slug"
        element={
          <Layout>
            <BookDetailPage />
          </Layout>
        }
      />
      <Route
        path="/news/:slug"
        element={
          <Layout>
            <NewsDetailPage />
          </Layout>
        }
      />
      <Route path="/admin/*" element={<AdminApp />} />
      <Route path="/:slug" element={<PageRoute />} />
      <Route
        path="*"
        element={
          <Layout>
            <NotFoundPage />
          </Layout>
        }
      />
    </Routes>
  );
}

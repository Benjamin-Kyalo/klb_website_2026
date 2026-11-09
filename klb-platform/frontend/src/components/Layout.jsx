import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import Header from "./Header.jsx";
import Footer from "./Footer.jsx";
import RevealObserver from "./RevealObserver.jsx";

export default function Layout({ children }) {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return (
    <div className="site-shell">
      <RevealObserver />
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <Header />
      <main id="main" key={pathname} className="page-transition">
        {children}
      </main>
      <Footer />
    </div>
  );
}

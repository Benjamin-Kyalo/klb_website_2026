import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import Header from "./Header.jsx";
import Footer from "./Footer.jsx";
import MediaLightbox from "./MediaLightbox.jsx";
import RevealObserver from "./RevealObserver.jsx";
import AccessibilityMenu from "./AccessibilityMenu.jsx";
import { useSite } from "../context/SiteContext.jsx";

export default function Layout({ children }) {
  const { pathname } = useLocation();
  const { settings } = useSite();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return (
    <div className="site-shell">
      <RevealObserver />
      <div className="skip-links">
        <a href="#main">Skip to main content</a>
        <a href="#siteHeader">Skip to navigation</a>
        <a href="#siteFooter">Skip to footer</a>
      </div>
      {settings?.maintenance_mode ? (
        <div className="maintenance-notice" role="status">
          <strong>Maintenance notice</strong>
          <span>
            {settings.maintenance_message ||
              "Some parts of the website may be unavailable while we carry out maintenance. Please try again shortly."}
          </span>
        </div>
      ) : null}
      <Header />
      <main id="main" tabIndex={-1} key={pathname} className="page-transition">
        {children}
      </main>
      <Footer />
      <MediaLightbox />
      <AccessibilityMenu />
    </div>
  );
}

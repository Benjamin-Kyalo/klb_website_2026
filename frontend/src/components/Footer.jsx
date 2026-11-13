import { Link } from "react-router-dom";
import { useSite } from "../context/SiteContext.jsx";
import NewsletterForm from "./NewsletterForm.jsx";
import { BookIcon, FacebookIcon, XIcon } from "./Icons.jsx";

export default function Footer() {
  const { settings, footerColumns } = useSite();
  const year = new Date().getFullYear();

  return (
    <footer className="site-footer" id="siteFooter">
      <div className="container footer-top">
        <div className="footer-brand">
          <p>{settings.footer_blurb}</p>
          <div className="footer-social">
            <a href={settings.facebook || "https://www.facebook.com/klbkenya/"} rel="noopener" aria-label="KLB on Facebook">
              <FacebookIcon />
            </a>
            <a href={settings.twitter || "https://twitter.com/klb_kenya"} rel="noopener" aria-label="KLB on X">
              <XIcon />
            </a>
            <a
              href={settings.ebookstore || "https://klbbooks.com/"}
              rel="noopener"
              aria-label="KLB ebookstore"
            >
              <BookIcon />
            </a>
          </div>
        </div>

        {footerColumns.map((column) => (
          <div className="footer-col" key={column.title}>
            <h2>{column.title}</h2>
            <ul>
              {column.links.map((link) => {
                const [label, href] = link;
                return (
                  <li key={`${column.title}-${label}`}>
                    <a href={href}>{label}</a>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>

      <div className="container footer-top footer-newsletter-row">
        <div className="footer-newsletter">
          <h3>KLB newsletter</h3>
          <p>New titles, curriculum resources and Bureau news.</p>
          <NewsletterForm />
        </div>
      </div>

      <div className="container footer-bottom">
        <p>© {year} Kenya Literature Bureau PLC. All rights reserved.</p>
        <ul>
          <li>
            <Link to="/about/">About KLB</Link>
          </li>
          <li>
            <Link to="/privacy/">Privacy</Link>
          </li>
          <li>
            <Link to="/terms/">Terms of sale</Link>
          </li>
          <li>
            <Link to="/resources/">Resources</Link>
          </li>
          <li>
            <button
              type="button"
              className="footer-a11y-link"
              onClick={() => window.dispatchEvent(new Event("klb:open-accessibility"))}
            >
              Accessibility options
            </button>
          </li>
        </ul>
      </div>
    </footer>
  );
}

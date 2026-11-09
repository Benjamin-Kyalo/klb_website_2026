import { useEffect, useRef, useState } from "react";
import { useLocation, useSearchParams } from "react-router-dom";
import { getPage, sendEnquiry } from "../lib/api.js";
import { SITE_URL } from "../lib/seo.js";
import { useSite } from "../context/SiteContext.jsx";
import Seo from "../lib/seo.js";
import SectionRenderer from "../components/SectionRenderer.jsx";
import Loading, { ErrorState } from "../components/Loading.jsx";
import NotFoundPage from "./NotFoundPage.jsx";

const TYPE_LABELS = {
  general: "General enquiry",
  bulk: "Bulk order",
  order: "Order or delivery question",
  quote: "Printing, design or branding quote",
  publishing: "Publishing a manuscript",
  translation: "Translation services",
  printing: "Printing services",
  branding: "Branding and merchandise",
  digital: "Digital editions and licences",
  media: "Media enquiry",
  events: "Events and school visits",
  procurement: "Tender or procurement",
  access: "Access to information",
  complaints: "Complaint or feedback",
  careers: "Careers and recruitment",
};

export default function PageView({ slug }) {
  const { settings } = useSite();
  const [page, setPage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const containerRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    setPage(null);

    getPage(slug)
      .then((data) => {
        if (!cancelled) setPage(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [slug]);

  // Scroll to in-page anchors once the CMS sections have rendered.
  useEffect(() => {
    if (!page || !location.hash) return;
    const id = decodeURIComponent(location.hash.slice(1));
    const timer = window.setTimeout(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 120);
    return () => window.clearTimeout(timer);
  }, [page, location.hash]);

  // Pre-fill the contact form from links such as /contact/?type=bulk or ?book=...
  useEffect(() => {
    if (!page || slug !== "contact" || !containerRef.current) return;
    const form = containerRef.current.querySelector("[data-enquiry-form]");
    if (!form) return;

    const type = searchParams.get("type");
    const select = form.querySelector('select[name="type"]');
    if (type && select && Array.from(select.options).some((option) => option.value === type)) {
      select.value = type;
    }

    const book = searchParams.get("book");
    const message = form.querySelector('textarea[name="message"]');
    if (book && message && !message.value) {
      message.value = `I would like to enquire about a print copy of: ${book.replace(/-/g, " ")}.\n\n`;
    }
  }, [page, slug, searchParams]);

  // Intercept the CMS contact form and submit it to the Django API.
  useEffect(() => {
    const container = containerRef.current;
    if (!page || slug !== "contact" || !container) return undefined;

    const controller = new AbortController();

    container.addEventListener(
      "submit",
      async (event) => {
        const form = event.target.closest("[data-enquiry-form]");
        if (!form) return;
        event.preventDefault();

        const status = form.querySelector("[data-form-status]");
        const button = form.querySelector('button[type="submit"]');
        const data = new FormData(form);

        if (!data.get("consent")) {
          if (status) {
            status.dataset.state = "error";
            status.textContent = "Please agree to the privacy notice before sending.";
          }
          return;
        }

        const type = data.get("type") || "general";
        const payload = {
          name: (data.get("name") || "").toString().trim(),
          email: (data.get("email") || "").toString().trim(),
          phone: (data.get("phone") || "").toString().trim(),
          organisation: (data.get("organisation") || "").toString().trim(),
          enquiry_type: type,
          subject: `Website enquiry: ${TYPE_LABELS[type] || "General"}`,
          message: (data.get("message") || "").toString().trim(),
          company_website: (data.get("website") || "").toString().trim(),
        };

        if (status) {
          status.dataset.state = "";
          status.textContent = "Sending your enquiry…";
        }
        if (button) button.disabled = true;

        try {
          const response = await sendEnquiry(payload);
          form.reset();
          if (status) {
            status.dataset.state = "success";
            status.textContent = response.detail;
          }
        } catch (err) {
          if (status) {
            status.dataset.state = "error";
            status.textContent = err.message || "Sorry, the enquiry could not be sent. Please try again.";
          }
        } finally {
          if (button) button.disabled = false;
        }
      },
      { signal: controller.signal }
    );

    return () => controller.abort();
  }, [page, slug]);

  if (loading) {
    return (
      <div className="container page-loading">
        <Loading label="Loading page…" />
      </div>
    );
  }

  if (error) {
    if (error.status === 404) return <NotFoundPage />;
    return (
      <div className="container page-loading">
        <ErrorState error={error} title="We could not load this page." />
      </div>
    );
  }

  if (!page) return null;

  const path = slug === "home" ? "/" : `/${slug}/`;
  const title = page.meta_title || `${page.title} | ${settings.site_name}`;
  const description = page.meta_description || settings.seo_default_description;
  const jsonLd =
    slug === "home"
      ? {
          "@context": "https://schema.org",
          "@type": "Organization",
          name: "Kenya Literature Bureau",
          alternateName: "KLB",
          url: SITE_URL,
          logo: `${SITE_URL}/assets/klb-lockup.png`,
          foundingDate: "1947",
          description:
            "Kenya Literature Bureau is a State corporation that publishes, prints and distributes educational, cultural and scientific books, periodicals and digital materials.",
          address: {
            "@type": "PostalAddress",
            streetAddress: settings.address,
            addressLocality: "Nairobi",
            addressCountry: "KE",
          },
          contactPoint: {
            "@type": "ContactPoint",
            telephone: settings.phone,
            contactType: "customer service",
            email: settings.contact_email,
            areaServed: "KE",
            availableLanguage: ["English", "Kiswahili"],
          },
          sameAs: [settings.ebookstore, settings.facebook, settings.twitter].filter(Boolean),
        }
      : {
          "@context": "https://schema.org",
          "@type": "WebPage",
          name: page.title,
          url: `${SITE_URL}${path}`,
          description,
          isPartOf: { "@type": "WebSite", name: settings.site_name, url: SITE_URL },
        };

  return (
    <>
      <Seo title={title} description={description} path={path} jsonLd={jsonLd} />
      <div ref={containerRef}>
        {page.sections
          .filter((section) => section.kind !== "html" || (section.html || "").trim())
          .map((section) => (
            <SectionRenderer section={section} key={section.id} />
          ))}
      </div>
    </>
  );
}

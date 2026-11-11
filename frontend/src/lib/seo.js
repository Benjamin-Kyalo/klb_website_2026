import { useEffect } from "react";

const SITE_URL = (import.meta.env.VITE_SITE_URL || "https://klb.co.ke").replace(/\/$/, "");

function setMeta(selector, attrs) {
  let element = document.head.querySelector(selector);
  if (!element) {
    element = document.createElement(selector.startsWith("link") ? "link" : "meta");
    document.head.appendChild(element);
  }
  Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, value));
  return element;
}

/**
 * Updates document metadata for each route. React renders in the browser, so
 * these tags are applied after load. Django serves the sitemap and robots.txt,
 * and the server-rendered shell carries default metadata for crawlers.
 */
export default function Seo({
  title,
  description,
  path = "/",
  image = "/assets/og-klb.jpg",
  type = "website",
  jsonLd = null,
  noindex = false,
}) {
  useEffect(() => {
    const fullTitle = title || "Kenya Literature Bureau PLC";
    const url = `${SITE_URL}${path}`;
    document.title = fullTitle;

    if (description) {
      setMeta('meta[name="description"]', { name: "description", content: description });
      setMeta('meta[property="og:description"]', { property: "og:description", content: description });
      setMeta('meta[name="twitter:description"]', { name: "twitter:description", content: description });
    }
    setMeta('meta[property="og:title"]', { property: "og:title", content: fullTitle });
    setMeta('meta[name="twitter:title"]', { name: "twitter:title", content: fullTitle });
    setMeta('meta[property="og:url"]', { property: "og:url", content: url });
    setMeta('meta[property="og:type"]', { property: "og:type", content: type });
    setMeta('meta[property="og:image"]', { property: "og:image", content: image });
    setMeta('meta[name="twitter:image"]', { name: "twitter:image", content: image });
    setMeta('link[rel="canonical"]', { rel: "canonical", href: url });
    setMeta('meta[name="robots"]', {
      name: "robots",
      content: noindex ? "noindex, follow" : "index, follow",
    });

    let script = document.getElementById("page-jsonld");
    if (jsonLd) {
      if (!script) {
        script = document.createElement("script");
        script.type = "application/ld+json";
        script.id = "page-jsonld";
        document.head.appendChild(script);
      }
      script.textContent = JSON.stringify(jsonLd);
    } else if (script) {
      script.remove();
    }
  }, [title, description, path, image, type, jsonLd, noindex]);

  return null;
}

export { SITE_URL };

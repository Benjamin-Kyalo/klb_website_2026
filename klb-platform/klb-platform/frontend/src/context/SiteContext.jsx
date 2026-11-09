import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { getSite } from "../lib/api.js";

const SiteContext = createContext(null);

export const FALLBACK_SETTINGS = {
  site_name: "Kenya Literature Bureau",
  tagline: "Publishing & printing for you since 1947",
  phone: "020 3541196/7",
  phone_alt: "0711 318 188 · 0732 344 599",
  address: "KLB Road, Bellevue Area, off Mombasa Road, P.O. Box 30022-00100, Nairobi",
  contact_email: "info@klb.co.ke",
  customer_email: "customer@klb.co.ke",
  facebook: "https://www.facebook.com/klbkenya/",
  twitter: "https://twitter.com/klb_kenya",
  ebookstore: "https://klbbooks.com/",
  announcement: "",
  footer_blurb:
    "Kenya Literature Bureau is a State corporation established in 1947 to publish, print and distribute educational, cultural and scientific materials for Kenya and the region.",
  seo_default_title: "Kenya Literature Bureau | Books, publishing and printing since 1947",
  seo_default_description:
    "Kenya Literature Bureau publishes and prints CBC, secondary, revision and readers titles. Search KLB books, buy e-books, and enquire about bulk orders or printing services.",
  og_image: "/assets/og-klb.jpg",
};

export function SiteProvider({ children }) {
  const [site, setSite] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const reload = useCallback(async () => {
    try {
      const data = await getSite();
      setSite(data);
      setError(null);
      return data;
    } catch (err) {
      setError(err);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const settings = { ...FALLBACK_SETTINGS, ...(site?.settings || {}) };
  const navigation = site?.navigation?.length ? site.navigation : [];
  const footerColumns = site?.settings?.footer_columns?.length ? site.settings.footer_columns : [];
  const pages = site?.pages || [];

  return (
    <SiteContext.Provider
      value={{ site, settings, navigation, footerColumns, pages, loading, error, reload }}
    >
      {children}
    </SiteContext.Provider>
  );
}

export function useSite() {
  const value = useContext(SiteContext);
  if (!value) throw new Error("useSite must be used inside SiteProvider");
  return value;
}

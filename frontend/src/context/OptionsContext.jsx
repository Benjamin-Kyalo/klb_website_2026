import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { admin } from "../lib/api.js";
import { useAuth } from "./AuthContext.jsx";

const FALLBACK = {
  news_category: [
    "Announcement", "Community", "Events", "Governance", "Leadership",
    "Operations", "Partnerships", "People", "Publishing", "Recognition",
    "Sales", "Schools",
  ].map((value) => ({ value, label: value })),
  publication_category: ["CBE", "Secondary", "Revision", "Readers", "Tertiary", "Reference"].map(
    (value) => ({ value, label: value })
  ),
  collection: ["CBE", "Secondary", "Revision", "Readers", "Tertiary"].map((value) => ({
    value,
    label: value,
  })),
  department: [
    "Editorial", "Publishing", "Sales and Marketing", "Finance", "Human Resources",
    "ICT", "Operations", "Legal", "Procurement",
  ].map((value) => ({ value, label: value })),
  job_location: ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Regional offices"].map(
    (value) => ({ value, label: value })
  ),
  employment_type: ["Permanent", "Contract", "Internship", "Temporary", "Part time"].map(
    (value) => ({ value, label: value })
  ),
  tender_category: [
    "Supply", "Services", "Works", "Framework", "Expression of interest", "Addendum",
  ].map((value) => ({ value, label: value })),
  resource_category: ["price-lists", "annual-reports", "governance", "customer-forms"].map(
    (value) => ({ value, label: value })
  ),
  event_category: ["Event", "Launch", "Partnership", "Community"].map((value) => ({
    value,
    label: value,
  })),
};

const OptionsContext = createContext(null);

export function OptionsProvider({ children }) {
  const { user } = useAuth();
  const [options, setOptions] = useState(FALLBACK);

  const reload = useCallback(async () => {
    if (!user) return;
    try {
      const data = await admin.options.groups();
      setOptions((current) => ({ ...current, ...(data.options || {}) }));
    } catch {
      // Keep the bundled defaults when the network is unavailable.
    }
  }, [user]);

  useEffect(() => {
    if (user) {
      reload();
    }
  }, [user, reload]);

  const value = useMemo(
    () => ({
      options,
      reload,
      optionsFor: (group) => (options[group]?.length ? options[group] : FALLBACK[group] || []),
    }),
    [options, reload]
  );

  return <OptionsContext.Provider value={value}>{children}</OptionsContext.Provider>;
}

export function useOptions() {
  const value = useContext(OptionsContext);
  if (!value) throw new Error("useOptions must be used inside OptionsProvider");
  return value;
}

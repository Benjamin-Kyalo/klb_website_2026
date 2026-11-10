import { useEffect } from "react";

/** Reveals elements with the .reveal class as they enter the viewport. */
export default function RevealObserver() {
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") {
      document.querySelectorAll(".reveal").forEach((element) => element.classList.add("is-visible"));
      return undefined;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.08 }
    );

    const observeAll = () => {
      document.querySelectorAll(".reveal:not(.is-visible)").forEach((element) => observer.observe(element));
    };

    observeAll();
    const mutation = new MutationObserver(observeAll);
    mutation.observe(document.body, { childList: true, subtree: true });

    return () => {
      observer.disconnect();
      mutation.disconnect();
    };
  }, []);

  return null;
}

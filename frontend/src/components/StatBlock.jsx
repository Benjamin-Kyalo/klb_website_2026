import { useEffect, useRef, useState } from "react";
import { useSite } from "../context/SiteContext.jsx";

/**
 * Animated statistics block.
 *
 * Reads statistics from site settings (admin-manageable) and animates
 * numeric values counting up when the block enters the viewport.
 * Respects prefers-reduced-motion.
 */
function parseValue(raw) {
  const text = String(raw || "").trim();
  const match = text.match(/^([\d,]+)(.*)$/);
  if (!match) return { number: null, suffix: text };
  const number = parseInt(match[1].replace(/,/g, ""), 10);
  if (Number.isNaN(number)) return { number: null, suffix: text };
  return { number, suffix: match[2] || "" };
}

function CountUp({ value, suffix, animate }) {
  const [display, setDisplay] = useState(animate ? 0 : value);
  const ref = useRef(null);
  const started = useRef(false);

  useEffect(() => {
    if (!animate) {
      setDisplay(value);
      return undefined;
    }
    const node = ref.current;
    if (!node) return undefined;

    const prefersReduced =
      typeof window !== "undefined" &&
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (prefersReduced) {
      setDisplay(value);
      return undefined;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !started.current) {
            started.current = true;
            const duration = 1400;
            const start = performance.now();
            const tick = (now) => {
              const progress = Math.min((now - start) / duration, 1);
              const eased = 1 - Math.pow(1 - progress, 3);
              setDisplay(Math.round(eased * value));
              if (progress < 1) requestAnimationFrame(tick);
            };
            requestAnimationFrame(tick);
            observer.disconnect();
          }
        });
      },
      { threshold: 0.3 }
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [value, animate]);

  return (
    <span ref={ref} className="stat-block__value">
      {display.toLocaleString()}
      {suffix}
    </span>
  );
}

export default function StatBlock({ section }) {
  const { settings } = useSite();
  const stats = (settings.statistics || []).filter((s) => s && (s.value || s.label));

  if (!stats.length) {
    return (
      <section className={(section && section.settings && section.settings.sectionClass) || "section section--tight"}>
        <div className="container">
          <div className="stat-block reveal">
            <div className="stat-block__item">
              <span className="stat-block__value">1947</span>
              <span className="stat-block__label">Year established</span>
            </div>
          </div>
        </div>
      </section>
    );
  }

  const sectionClass =
    (section && section.settings && section.settings.sectionClass) || "section section--tight";

  return (
    <section className={sectionClass} id={(section && section.settings && section.settings.sectionId) || undefined}>
      <div className="container">
        <div className="stat-block reveal">
          {stats.map((stat, index) => {
            const { number, suffix } = parseValue(stat.value);
            const animate = stat.animate !== false && number !== null;
            return (
              <div className="stat-block__item" key={index}>
                {number !== null ? (
                  <CountUp value={number} suffix={suffix || stat.suffix || ""} animate={animate} />
                ) : (
                  <span className="stat-block__value">{stat.value}</span>
                )}
                <span className="stat-block__label">{stat.label}</span>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

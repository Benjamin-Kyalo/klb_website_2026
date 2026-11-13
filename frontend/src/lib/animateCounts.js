function animateOne(el) {
  if (el.dataset.countAnimated === "1") return;
  el.dataset.countAnimated = "1";
  const target = parseInt(el.getAttribute("data-count"), 10);
  if (Number.isNaN(target)) return;
  const suffix = el.getAttribute("data-suffix") || "";
  const reduced =
    typeof window !== "undefined" &&
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduced) {
    el.textContent = target.toLocaleString() + suffix;
    return;
  }
  const duration = 1400;
  const start = performance.now();
  const tick = (now) => {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(eased * target).toLocaleString() + suffix;
    if (progress < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
  // Safety net for backgrounded tabs / throttled rAF.
  setTimeout(() => {
    el.textContent = target.toLocaleString() + suffix;
  }, duration + 600);
}

function tryAnimate() {
  const nodes = Array.from(document.querySelectorAll("[data-count]:not([data-count-animated])"));
  nodes.forEach((node) => animateOne(node));
}

export function startCountAnimations() {
  if (typeof document === "undefined") return;
  tryAnimate();
  // Watch for CMS HTML injected after the first render.
  const mo = new MutationObserver(() => tryAnimate());
  mo.observe(document.body, { childList: true, subtree: true });
  // Poll for a few seconds in case mutations are batched or delayed.
  let attempts = 0;
  const interval = setInterval(() => {
    tryAnimate();
    attempts += 1;
    if (attempts > 20) clearInterval(interval);
  }, 250);
  // Final safety pass.
  setTimeout(() => tryAnimate(), 3000);
}

export default startCountAnimations;

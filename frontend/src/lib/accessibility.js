/**
 * Accessibility preferences for the public website.
 *
 * Preferences are stored in localStorage so they survive navigation and repeat
 * visits on the same device. They are applied as classes on <html>, which lets
 * the hand-written CSS override the normal design tokens without duplicating
 * component styles.
 */

export const A11Y_STORAGE_KEY = "klb-accessibility-preferences";

export const DEFAULT_A11Y = {
  textScale: 100,
  contrast: false,
  dark: false,
  dyslexia: false,
  spacing: false,
  underline: false,
  grayscale: false,
  reduceMotion: false,
};

const TEXT_SCALE_MIN = 100;
const TEXT_SCALE_MAX = 150;
const TEXT_SCALE_STEP = 10;

function normalise(raw) {
  const output = { ...DEFAULT_A11Y };
  if (!raw || typeof raw !== "object") return output;

  const scale = Number(raw.textScale);
  if (Number.isFinite(scale)) {
    output.textScale = Math.min(
      TEXT_SCALE_MAX,
      Math.max(TEXT_SCALE_MIN, Math.round(scale / TEXT_SCALE_STEP) * TEXT_SCALE_STEP)
    );
  }
  ["contrast", "dark", "dyslexia", "spacing", "underline", "grayscale", "reduceMotion"].forEach(
    (key) => {
      output[key] = Boolean(raw[key]);
    }
  );
  // Older saves could contain both schemes; high contrast takes precedence.
  if (output.dark && output.contrast) output.dark = false;
  return output;
}

export function loadA11yPrefs() {
  if (typeof window === "undefined") return { ...DEFAULT_A11Y };
  try {
    const stored = window.localStorage.getItem(A11Y_STORAGE_KEY);
    return stored ? normalise(JSON.parse(stored)) : { ...DEFAULT_A11Y };
  } catch {
    return { ...DEFAULT_A11Y };
  }
}

export function saveA11yPrefs(prefs) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(A11Y_STORAGE_KEY, JSON.stringify(normalise(prefs)));
  } catch {
    // Storage can be unavailable in private modes. Preferences still apply for
    // the current page, they just will not persist.
  }
}

export function applyA11yPrefs(prefs) {
  if (typeof document === "undefined") return;
  const values = normalise(prefs);
  const root = document.documentElement;
  const classes = {
    "a11y-contrast": values.contrast,
    "a11y-dark": values.dark,
    "a11y-dyslexia": values.dyslexia,
    "a11y-spacing": values.spacing,
    "a11y-underline": values.underline,
    "a11y-grayscale": values.grayscale,
    "a11y-reduced-motion": values.reduceMotion,
  };
  Object.entries(classes).forEach(([name, enabled]) => {
    root.classList.toggle(name, enabled);
  });
  root.style.setProperty("--a11y-text-scale", String(values.textScale / 100));
  root.dataset.a11yTextScale = String(values.textScale);
}

export function stepTextScale(prefs, direction) {
  const next = normalise(prefs).textScale + direction * TEXT_SCALE_STEP;
  return {
    ...prefs,
    textScale: Math.min(TEXT_SCALE_MAX, Math.max(TEXT_SCALE_MIN, next)),
  };
}

export function resetA11yPrefs() {
  return { ...DEFAULT_A11Y };
}

export function a11yActiveCount(prefs) {
  const values = normalise(prefs);
  let count = values.textScale !== DEFAULT_A11Y.textScale ? 1 : 0;
  ["contrast", "dark", "dyslexia", "spacing", "underline", "grayscale", "reduceMotion"].forEach(
    (key) => {
      if (values[key]) count += 1;
    }
  );
  return count;
}

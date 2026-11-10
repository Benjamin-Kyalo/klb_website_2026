# KLB design system notes

This document records the editorial design direction applied to `klb-platform`
after the original refinement pass. It is intentionally not a generic SaaS or
AI-generated aesthetic.

## Direction

KLB is a publishing house established in 1947. The design should feel like an
institutional publisher: confident, book-led, editorial and specific. It should
not feel like a startup landing page.

Avoid by default:
- gradient headlines, glowing backgrounds, glassmorphism, decorative blobs
- three identical feature cards under every heading
- oversized unexplained statistics
- generic marketing phrases and empty introductory labels
- cards inside cards without a functional reason
- coloured vertical stripes on every card

Use instead:
- real KLB photography and book covers
- asymmetric, editorial compositions
- genuine, verifiable statistics
- purposeful colour as wayfinding
- quiet, accessible interaction

## Palette

| Token | Value | Use |
| --- | --- | --- |
| `--ink` | `#062f4e` | primary text, dark surfaces |
| `--blue` / `--blue-deep` | `#0875b9` / `#065f96` | links, focus, active navigation |
| `--red` | `#c92a36` | calls to action, deadlines, destructive actions |
| `--yellow` | `#f3e5ab` | highlights, active states, selected filters |
| `--green` | `#4f9b55` | availability, success, open tenders/careers |
| `--paper` / `--paper-2` | `#f5f9fc` / `#eaf2f8` | page and section backgrounds |

Colour is used for meaning and wayfinding, not decoration.

## Typography

- Display: Fraunces (serif) for headings and key figures.
- Body: Inter for UI, navigation and long-form text.
- Use the existing `--step-*` scale. Prefer `--step-2` to `--step-4` for section
  headings; reserve `--step-5` and `--step-6` for the hero only.
- Keep body text between 15 and 17 pixels with a line height of 1.55 to 1.65.
- Use `font-variant-numeric: tabular-nums` for prices, counts and dates.
- Headings should be concise and specific, not dramatic.

## Spacing rhythm

Use the existing `--space-*` tokens and section padding:

- `.section` = `clamp(3rem, 7vw, 6rem)` vertical padding
- `.section--tight` = `clamp(1.6rem, 4vw, 2.6rem)`
- `.section--loose` = `clamp(4.5rem, 10vw, 8rem)`
- Inner gaps: `--space-3` (1rem) for related items, `--space-5` (2rem) for
  groups, `--space-7` (4.5rem) between major blocks.

## Layout patterns

### Feature spotlight
One large media frame plus one supporting copy block. Use for a single important
title, service or story. Class: `.feature-spotlight`.

### Editorial news list
A bordered list with date/category on the left and title/excerpt on the right.
Not a three-card grid. Class: `.news-list` / `.news-list__item`.

### Resource rows
A bordered list of title, type and description with a right-aligned action.
Class: `.resource-list` / `.resource-row`.

### Numbered process
A bordered list of genuine steps, numbered with CSS counters. Only use when the
steps are real and ordered. Class: `.process-list` / `.process-step`.

### Quiet statistics
Inline figures with tabular numerals and short labels, bordered top and bottom.
No giant decorative numbers. Class: `.stat-block`.

### Media frames
Use `.media-frame` with an aspect-ratio modifier (`--4x3`, `--3x4`, `--16x9`)
instead of ad-hoc image sizing.

## Imagery

- Prefer real KLB photography and book covers.
- Standardise cover aspect ratios and use `loading="lazy"` and `decoding="async"`.
- Always provide meaningful `alt` text; decorative images use empty `alt`.
- Captions should add context, not filler.

## Motion

- Use subtle transitions for hover, focus, dialog open/close and reveal-on-scroll.
- Respect `prefers-reduced-motion`.
- Do not add pulsing, floating, glowing or decorative scroll effects.

## Empty and loading states

- Empty states should be calm and specific: what is missing and how to add it.
- Loading states should be short text, not spinners with marketing copy.

## Components changed in this pass

- `NewsListSection.jsx`: now renders an editorial list (`.news-list`) instead of
  a three-card grid.
- `ResourcesListSection.jsx`: now renders resource rows (`.resource-list`)
  instead of cards.
- `klb.css`: added editorial design system classes, restyled leadership cards
  (quieter, border-top, 3 columns) and added `.value-editorial`.
- `cms-seed.json`: tightened hero copy and converted vision/mission/values to an
  editorial split layout (`.value-editorial`).

## How to extend

When adding a new section, choose a layout from the list above before creating
a new card grid. If none fit, add a new pattern here with a clear purpose and
responsive behaviour, and prefer asymmetry and whitespace over repetition.

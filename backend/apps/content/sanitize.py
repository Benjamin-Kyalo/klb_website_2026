"""HTML sanitising for content saved through the dashboard.

All rich text is cleaned on save (defence in depth) and again in the browser by
React's HTML rendering. Inline event handlers and scripts are always removed.
"""
import re

import bleach
from bleach.css_sanitizer import CSSSanitizer

ALLOWED_TAGS = [
    "a", "abbr", "article", "aside", "b", "blockquote", "br", "button",
    "caption", "cite", "code", "dd", "details", "div", "dl", "dt", "em",
    "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5",
    "h6", "header", "hr", "i", "img", "input", "label", "li", "main", "nav",
    "ol", "option", "p", "picture", "pre", "section", "select", "small",
    "source", "span", "strong", "summary", "table", "tbody", "td", "textarea",
    "tfoot", "th", "thead", "tr", "u", "ul",
    # inline SVG icons used in the KLB design
    "svg", "path", "circle", "rect", "line", "polyline", "polygon", "g",
]

ALLOWED_ATTRIBUTES = {
    "*": [
        "class", "id", "title", "role", "style", "tabindex",
        "aria-label", "aria-hidden", "aria-current", "aria-describedby",
        "aria-expanded", "aria-controls", "aria-live", "aria-labelledby",
        "aria-atomic", "aria-invalid", "aria-required", "aria-selected",
        "aria-pressed", "aria-haspopup", "data-enquiry-form", "data-form-status",
        "data-member", "data-caption", "data-lightbox", "data-team-photo",
    ],
    "a": ["href", "name", "rel", "target", "download"],
    "img": ["src", "alt", "width", "height", "loading", "srcset", "sizes"],
    "source": ["src", "srcset", "type", "media"],
    "form": ["data-enquiry-form", "novalidate", "class", "id", "action", "method", "role"],
    "input": ["type", "name", "id", "value", "placeholder", "required", "autocomplete", "min", "max", "step", "checked", "disabled", "aria-label", "aria-describedby", "aria-invalid", "aria-required", "maxlength", "minlength", "pattern", "readonly", "multiple"],
    "select": ["name", "id", "required", "aria-label"],
    "option": ["value", "selected"],
    "textarea": ["name", "id", "rows", "cols", "placeholder", "required", "aria-label"],
    "button": ["type", "name", "value", "disabled", "aria-label"],
    "label": ["for"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan", "scope"],
    "svg": ["viewbox", "viewBox", "width", "height", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "aria-hidden", "focusable", "xmlns"],
    "path": ["d", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "fill-rule", "clip-rule"],
    "circle": ["cx", "cy", "r", "fill", "stroke", "stroke-width"],
    "rect": ["x", "y", "width", "height", "rx", "fill", "stroke", "stroke-width"],
    "line": ["x1", "y1", "x2", "y2", "stroke", "stroke-width"],
    "polyline": ["points", "fill", "stroke", "stroke-width"],
    "polygon": ["points", "fill", "stroke", "stroke-width"],
    "g": ["fill", "stroke", "transform"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto", "tel", "data"]

CSS_PROPERTIES = [
    "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
    "padding", "padding-top", "padding-right", "padding-bottom", "padding-left",
    "color", "background", "background-color", "background-image",
    "text-align", "font-weight", "font-size", "line-height", "letter-spacing",
    "border", "border-top", "border-bottom", "border-left", "border-right",
    "border-radius", "border-color", "border-width", "border-style",
    "display", "gap", "grid-template-columns", "grid-template-rows",
    "max-width", "min-width", "width", "max-height", "min-height", "height",
    "object-fit", "object-position", "flex", "flex-wrap", "align-items",
    "justify-content", "overflow", "text-decoration", "text-transform",
    "white-space", "box-shadow", "opacity",
]

_SCRIPT_OR_STYLE = re.compile(
    r"<(script|style)\b[^>]*>.*?</\1\s*>",
    flags=re.IGNORECASE | re.DOTALL,
)

_cleaner = bleach.sanitizer.Cleaner(
    tags=ALLOWED_TAGS,
    attributes=ALLOWED_ATTRIBUTES,
    protocols=ALLOWED_PROTOCOLS,
    strip=True,
    strip_comments=True,
    css_sanitizer=CSSSanitizer(allowed_css_properties=CSS_PROPERTIES),
)


def clean_html(value: str) -> str:
    """Return safe HTML for storage and public rendering."""
    if not value:
        return ""
    without_scripts = _SCRIPT_OR_STYLE.sub("", value)
    return _cleaner.clean(without_scripts)

"""Read and decorate the About-page leadership cards.

The leadership section is edited as rich HTML. Each card carries a stable
``data-member`` key (for example ``GO``), which is what a TeamPhoto row stores.
Keeping the parsing here means the public page, the dashboard endpoint and the
tests all agree on how the cards are read.
"""
import re
from html import unescape

from django.utils.html import escape

ARTICLE_RE = re.compile(r"<article\b(?P<attrs>[^>]*)>(?P<body>.*?)</article>", re.S | re.I)
ANY_DIV_RE = re.compile(r"<div\b(?P<attrs>[^>]*)>(?P<body>(?:(?!<div\b).)*?)</div>", re.S | re.I)
ATTR_RE = re.compile(r"([\w:-]+)\s*=\s*\"([^\"]*)\"")
NAME_RE = re.compile(r"<h3\b[^>]*>(.*?)</h3>", re.S | re.I)
ROLE_RE = re.compile(
    r"<p\b[^>]*class=\"[^\"]*(?:team-card__role|person__role)[^\"]*\"[^>]*>(.*?)</p>",
    re.S | re.I,
)
LEGACY_PERSON_RE = re.compile(
    r"<div\b(?P<attrs>[^>]*class=\"[^\"]*\bperson\b[^\"]*\"[^>]*)>"
    r"(?P<body>(?:(?!<div\b).)*?)</div>",
    re.S | re.I,
)

_TITLE_RE = re.compile(r"\b(?:Mr|Mrs|Ms|Miss|Dr|Prof|Ag)\.?\s+", re.I)


def _attributes(raw: str) -> dict:
    return {name.lower(): value for name, value in ATTR_RE.findall(raw or "")}


def _text(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment or "")
    return re.sub(r"\s+", " ", unescape(text)).strip()


def initials_from_name(name: str) -> str:
    cleaned = _TITLE_RE.sub("", name or "")
    words = [word for word in re.split(r"\s+", cleaned) if word]
    if not words:
        return "KLB"
    return "".join(word[0] for word in words[:2]).upper()


def team_members_from_html(html: str) -> list[dict]:
    """Return the cards found in a leadership block, in document order."""
    members = []
    for match in ARTICLE_RE.finditer(html or ""):
        attrs = _attributes(match.group("attrs"))
        classes = (attrs.get("class") or "").split()
        key = attrs.get("data-member") or ""
        if "team-card" not in classes or not key:
            continue
        body = match.group("body")
        name_match = NAME_RE.search(body)
        role_match = ROLE_RE.search(body)
        name = _text(name_match.group(1)) if name_match else ""
        role = _text(role_match.group(1)) if role_match else ""
        members.append(
            {
                "key": key,
                "name": name,
                "role": role,
                "initials": initials_from_name(name) or key,
            }
        )
    if members:
        return members

    # Older installations used plain .person cards without a data-member key.
    # Derive a stable key from the name so photos can still be managed.
    for match in LEGACY_PERSON_RE.finditer(html or ""):
        attrs = _attributes(match.group("attrs"))
        classes = (attrs.get("class") or "").split()
        if "person" not in classes or "team-card__photo" in classes:
            continue
        body = match.group("body")
        name_match = NAME_RE.search(body)
        role_match = ROLE_RE.search(body)
        name = _text(name_match.group(1)) if name_match else ""
        role = _text(role_match.group(1)) if role_match else ""
        members.append(
            {
                "key": initials_from_name(name),
                "name": name,
                "role": role,
                "initials": initials_from_name(name),
            }
        )
    return members


def inject_team_photos(html: str, photos: dict[str, str]) -> str:
    """Replace each card's placeholder with an uploaded photo when present."""
    if not html or not photos:
        return html

    def replace_card(match):
        attrs = _attributes(match.group("attrs"))
        key = attrs.get("data-member") or ""
        photo = (photos.get(key) or "").strip()
        if not photo:
            return match.group(0)

        body = match.group("body")
        name_match = NAME_RE.search(body)
        name = _text(name_match.group(1)) if name_match else ""
        image = (
            '<div class="team-card__photo">'
            f'<img src="{escape(photo)}" alt="{escape(name)}" width="480" height="600" '
            'loading="lazy" decoding="async">'
            "</div>"
        )

        replaced = False

        def replace_photo(div_match):
            nonlocal replaced
            classes = (_attributes(div_match.group("attrs")).get("class") or "").split()
            if "team-card__photo" not in classes or replaced:
                return div_match.group(0)
            replaced = True
            return image

        new_body = ANY_DIV_RE.sub(replace_photo, body)
        if not replaced:
            new_body = image + body
        return f"<article{match.group('attrs')}>{new_body}</article>"

    result = ARTICLE_RE.sub(replace_card, html)

    def replace_legacy(match):
        attrs = _attributes(match.group("attrs"))
        classes = (attrs.get("class") or "").split()
        if "person" not in classes or "team-card__photo" in classes:
            return match.group(0)
        body = match.group("body")
        name_match = NAME_RE.search(body)
        name = _text(name_match.group(1)) if name_match else ""
        key = initials_from_name(name)
        photo = (photos.get(key) or "").strip()
        if not photo:
            return match.group(0)
        image = (
            '<div class="team-card__photo team-card__photo--legacy">'
            f'<img src="{escape(photo)}" alt="{escape(name)}" width="480" height="600" '
            'loading="lazy" decoding="async">'
            "</div>"
        )
        return f"<div{match.group('attrs')}>{image}{body}</div>"

    return LEGACY_PERSON_RE.sub(replace_legacy, result)

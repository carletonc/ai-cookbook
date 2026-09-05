"""Marketplace and preview helpers for picker cards. No Streamlit import."""

from urllib.parse import quote
from urllib.request import Request, urlopen

SCRYFALL_USER_AGENT = "ai-cookbook-mtg-search/1.0"


def scryfall_card_url(card: dict) -> str | None:
    """Canonical Scryfall page for this oracle identity."""
    oracle_id = card.get("scryfall_oracle_id")
    if oracle_id:
        return f"https://scryfall.com/search?q=oracleid%3A{oracle_id}"
    name = (card.get("name") or "").strip()
    if not name:
        return None
    return f'https://scryfall.com/search?q=%21"{quote(name)}"'


def scryfall_image_url(card: dict) -> str | None:
    """
    Default-printing art for this title.

    `/cards/oracle/{id}?format=image` returns a print *list*, not JPEG.
    Named exact is the endpoint that actually redirects to art. Only fetch
    this for the *selected* picker card — a full Jace list on every rerun
    would hammer Scryfall.
    """
    name = (card.get("name") or "").strip()
    if not name:
        return None
    return (
        "https://api.scryfall.com/cards/named?"
        f"exact={quote(name)}&format=image&version=normal"
    )


def fetch_image_bytes(url: str, *, timeout: float = 8) -> bytes | None:
    """GET an image with the User-Agent Scryfall requires. None on failure."""
    request = Request(
        url,
        headers={
            "User-Agent": SCRYFALL_USER_AGENT,
            "Accept": "image/jpeg,image/png,*/*",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            if not content_type.startswith("image/"):
                return None
            return response.read()
    except Exception:
        return None


def tcgplayer_search_url(card: dict) -> str | None:
    """TCGPlayer product search for the printed name. We do not store SKUs."""
    name = (card.get("name") or "").strip()
    if not name:
        return None
    return f"https://www.tcgplayer.com/search/magic/product?productLineName=magic&q={quote(name)}"


def picker_option_label(card: dict) -> str:
    """
    Radio label: printed name, then the full type line.

    Streamlit radios are single-line plain text — a newline is stripped, so
    use a delimiter Streamlit will actually render.
    """
    name = card.get("name") or "(unnamed)"
    face = card.get("face_name")
    if face and face != card.get("name"):
        name = f"{name}  [{face}]"
    type_line = (card.get("type_line") or "").strip()
    if type_line:
        return f"{name}  ·  {type_line}"
    return name


def picker_haystack(card: dict) -> str:
    """Lowercased fields the in-memory picker filter searches."""
    parts = [
        card.get("name"),
        card.get("face_name"),
        card.get("type_line"),
        card.get("oracle_text"),
        card.get("mana_cost"),
    ]
    return " ".join(part for part in parts if part).lower()

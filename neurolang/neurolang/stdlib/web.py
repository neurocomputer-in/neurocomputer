"""Web stdlib neuros — search and scrape."""
from __future__ import annotations

from urllib.parse import quote_plus

from ..neuro import neuro
from ..budget import Budget
from ..effect import Effect


def _require(module_name: str):
    """Soft import — raises a clear error if the optional dep is missing."""
    try:
        return __import__(module_name)
    except ImportError as e:
        raise ImportError(
            f"This neuro needs `{module_name}`. Install with: pip install {module_name}"
        ) from e


@neuro(effect="tool", kind="skill.web", name="neurolang.stdlib.web.search")
def search(query: str, *, n: int = 5) -> list[dict]:
    """Search the web. Returns a list of {url, title, snippet} dicts.

    Phase 1 implementation uses DuckDuckGo's HTML endpoint via `requests`.
    For production use, swap in a real search API (Brave, Tavily, Serper).
    """
    requests = _require("requests")
    bs4 = _require("bs4")

    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; NeuroLang/0.0.1)"}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()

    soup = bs4.BeautifulSoup(resp.text, "html.parser")
    results = []
    for a in soup.select("a.result__a")[:n]:
        href = a.get("href", "")
        title = a.get_text(strip=True)
        snippet = ""
        parent = a.find_parent("div", class_="result")
        if parent is not None:
            snippet_el = parent.select_one(".result__snippet")
            if snippet_el is not None:
                snippet = snippet_el.get_text(strip=True)
        results.append({"url": href, "title": title, "snippet": snippet})
    return results


@neuro(effect="tool", kind="skill.web", name="neurolang.stdlib.web.scrape")
def scrape(url: str, *, max_chars: int = 20000) -> str:
    """Fetch a URL and return its visible text content."""
    requests = _require("requests")
    bs4 = _require("bs4")

    headers = {"User-Agent": "Mozilla/5.0 (compatible; NeuroLang/0.0.1)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()

    soup = bs4.BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    return text

import requests
from langchain_core.tools import tool

from graph.config import NEWS_API_KEY
from graph.logger import get_logger

logger = get_logger("tools.news")

_EVERYTHING_URL = "https://newsapi.org/v2/everything"
_HEADLINES_URL = "https://newsapi.org/v2/top-headlines"


@tool
def search_news(query: str) -> str:
    """Search recent news articles about a specific topic, e.g. 'AI regulation' or
    'Telangana elections'. Use this when the user asks for news on a particular subject."""
    if not NEWS_API_KEY:
        return "News search is not configured (missing NEWS_API_KEY). Ask the admin to set it up."

    try:
        response = requests.get(
            _EVERYTHING_URL,
            params={
                "q": query,
                "apiKey": NEWS_API_KEY,
                "sortBy": "publishedAt",
                "pageSize": 5,
                "language": "en",
            },
            timeout=10,
        )
        response.raise_for_status()
        articles = response.json().get("articles", [])
    except requests.exceptions.Timeout:
        logger.warning(f"News search timed out for query={query!r}")
        return "The news service took too long to respond. Please try again."
    except requests.exceptions.RequestException as e:
        logger.exception("News search request failed")
        return f"Couldn't reach the news service right now: {e}"

    if not articles:
        return f"No recent news found for '{query}'."

    lines = [
        f"- {a.get('title', 'Untitled')} ({a.get('source', {}).get('name', 'unknown source')}) — {a.get('url', '')}"
        for a in articles
    ]
    return "\n".join(lines)


@tool
def get_top_headlines(country: str = "in", category: str = "") -> str:
    """Get today's top news headlines. country is a 2-letter code (default 'in' for India).
    category is optional: business, entertainment, general, health, science, sports, technology."""
    if not NEWS_API_KEY:
        return "News search is not configured (missing NEWS_API_KEY). Ask the admin to set it up."

    params = {"apiKey": NEWS_API_KEY, "country": country, "pageSize": 8}
    if category:
        params["category"] = category

    try:
        response = requests.get(_HEADLINES_URL, params=params, timeout=10)
        response.raise_for_status()
        articles = response.json().get("articles", [])
    except requests.exceptions.Timeout:
        return "The news service took too long to respond. Please try again."
    except requests.exceptions.RequestException as e:
        logger.exception("Top headlines request failed")
        return f"Couldn't reach the news service right now: {e}"

    if not articles:
        return f"No headlines found for country='{country}'" + (f", category='{category}'." if category else ".")

    lines = [f"- {a.get('title', 'Untitled')} ({a.get('source', {}).get('name', 'unknown source')})" for a in articles]
    return "\n".join(lines)

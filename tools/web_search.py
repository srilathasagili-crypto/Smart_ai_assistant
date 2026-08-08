from langchain_core.tools import tool

from graph.config import TAVILY_API_KEY
from graph.logger import get_logger

logger = get_logger("tools.web_search")


def _search_tavily(query: str) -> str:
    from langchain_tavily import TavilySearch

    searcher = TavilySearch(max_results=5, api_key=TAVILY_API_KEY)
    result = searcher.invoke({"query": query})
    items = result.get("results", []) if isinstance(result, dict) else result
    if not items:
        return f"No web results found for '{query}'."
    lines = [f"- {i.get('title', 'Untitled')}: {i.get('content', '')[:200]}... (source: {i.get('url', '')})" for i in items]
    return "\n".join(lines)


def _search_duckduckgo(query: str) -> str:
    from ddgs import DDGS
    from ddgs.exceptions import DDGSException

    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=5)
    except DDGSException as e:
        raise RuntimeError(f"DuckDuckGo search failed: {e}") from e

    if not results:
        return f"No web results found for '{query}'."
    lines = [f"- {r.get('title', 'Untitled')}: {r.get('body', '')[:200]}... (source: {r.get('href', '')})" for r in results]
    return "\n".join(lines)


@tool
def web_search(query: str) -> str:
    """Search the web for general knowledge, current events, or anything not covered
    by the other tools. Returns a short summary of the top results with source links.
    Use this for questions you're not confident answering from memory alone."""
    try:
        if TAVILY_API_KEY:
            return _search_tavily(query)
        return _search_duckduckgo(query)
    except Exception as e:
        logger.exception(f"Web search failed for query={query!r}")
        return f"Web search is temporarily unavailable: {e}"

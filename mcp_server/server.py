from fastmcp import FastMCP

from tools.calculator import calculator
from tools.weather import get_weather
from tools.gmail import send_email
from tools.news import search_news, get_top_headlines
from tools.web_search import web_search
from tools.calendar_tool import add_calendar_event, list_today_events, delete_calendar_event

mcp = FastMCP("Intelligent AI Assistant Tools")

# Note: remember_user_info/recall_user_info, ask_pdf_question/summarize_pdf/extract_pdf_key_info,
# and the reminder tools rely on LangGraph's InjectedState (user_id / pdf_context from the current
# conversation), which doesn't exist in a standalone MCP context. Only the stateless tools —
# ones that work from their explicit arguments alone — are exposed here.
mcp.tool()(calculator.func)
mcp.tool()(get_weather.func)
mcp.tool()(send_email.func)
mcp.tool()(search_news.func)
mcp.tool()(get_top_headlines.func)
mcp.tool()(web_search.func)
mcp.tool()(add_calendar_event.func)
mcp.tool()(list_today_events.func)
mcp.tool()(delete_calendar_event.func)

if __name__ == "__main__":
    mcp.run()

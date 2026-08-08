"""PDF analysis tools.

Design: app.py extracts text from the uploaded PDF (see tools/pdf_extract.py)
and stores it in the graph's state as `pdf_context`. These tools read that
state field via LangGraph's InjectedState — meaning the LLM never has to pass
the PDF text as a tool argument (it can't see it, and doesn't need to); it
just calls the tool with a question, and the actual text is injected
automatically from the current conversation's state.
"""
from typing import Annotated

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from graph.llm import get_llm
from graph.logger import get_logger

logger = get_logger("tools.pdf")

# Keep prompts within a safe token budget for a single LLM call.
_MAX_CHARS = 20000


@tool
def ask_pdf_question(question: str, state: Annotated[dict, InjectedState]) -> str:
    """Answer a question using the content of the PDF the user most recently uploaded.
    Only use this if the user has uploaded a PDF and is asking about its content."""
    pdf_text = (state.get("pdf_context") or "").strip()
    if not pdf_text:
        return "No PDF has been uploaded yet. Please upload a PDF using the sidebar first."

    try:
        llm = get_llm(temperature=0.1)
        prompt = (
            "Answer the question using ONLY the document text below. "
            "If the answer isn't in the document, say so clearly.\n\n"
            f"DOCUMENT:\n{pdf_text[:_MAX_CHARS]}\n\nQUESTION: {question}"
        )
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        logger.exception("Failed to answer PDF question")
        return f"Couldn't analyze the PDF right now: {e}"


@tool
def summarize_pdf(state: Annotated[dict, InjectedState]) -> str:
    """Summarize the PDF the user most recently uploaded."""
    pdf_text = (state.get("pdf_context") or "").strip()
    if not pdf_text:
        return "No PDF has been uploaded yet. Please upload a PDF using the sidebar first."

    try:
        llm = get_llm(temperature=0.2)
        prompt = (
            "Summarize the following document in a clear, well-organized way "
            "(key points as bullets, then a one-line takeaway):\n\n"
            f"{pdf_text[:_MAX_CHARS]}"
        )
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        logger.exception("Failed to summarize PDF")
        return f"Couldn't summarize the PDF right now: {e}"


@tool
def extract_pdf_key_info(state: Annotated[dict, InjectedState]) -> str:
    """Extract key facts, figures, names, and dates from the uploaded PDF."""
    pdf_text = (state.get("pdf_context") or "").strip()
    if not pdf_text:
        return "No PDF has been uploaded yet. Please upload a PDF using the sidebar first."

    try:
        llm = get_llm(temperature=0.1)
        prompt = (
            "Extract the most important information from this document: key facts, "
            "figures/numbers, names, and dates. Present as a short bulleted list.\n\n"
            f"{pdf_text[:_MAX_CHARS]}"
        )
        response = llm.invoke(prompt)
        return response.content
    except Exception as e:
        logger.exception("Failed to extract PDF key info")
        return f"Couldn't extract information from the PDF right now: {e}"

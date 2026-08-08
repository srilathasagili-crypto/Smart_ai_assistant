"""Plain PDF text extraction — used directly by app.py when a file is uploaded.
Not a LangChain @tool, since it operates on an uploaded file object, not on
something the LLM should decide to call with a text argument."""
from pypdf import PdfReader

from graph.logger import get_logger

logger = get_logger("tools.pdf_extract")


def extract_pdf_text(file) -> str:
    """file: a file-like object (e.g. Streamlit's UploadedFile). Returns extracted text,
    or an empty string with a logged error if extraction fails — never raises, so a
    bad PDF upload can't crash the app."""
    try:
        reader = PdfReader(file)
        pages_text = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages_text).strip()
        if not text:
            logger.warning("PDF extraction produced no text (likely a scanned/image-only PDF)")
        return text
    except Exception:
        logger.exception("Failed to extract text from uploaded PDF")
        return ""

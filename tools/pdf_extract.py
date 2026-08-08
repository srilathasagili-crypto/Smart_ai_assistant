from pypdf import PdfReader

from graph.logger import get_logger

logger = get_logger("tools.pdf_extract")


def extract_pdf_text(file) -> str:

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

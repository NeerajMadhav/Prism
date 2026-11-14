"""HTML → PDF rendering for monthly reports."""

from __future__ import annotations

from io import BytesIO

from src.utils.logger import get_logger

logger = get_logger(__name__)


def html_to_pdf(html: str) -> bytes:
    """Render HTML to PDF bytes. Raises RuntimeError if the PDF engine is unavailable."""
    try:
        from xhtml2pdf import pisa
    except ImportError as exc:
        raise RuntimeError(
            "PDF engine not installed. Install xhtml2pdf (pip install xhtml2pdf)."
        ) from exc

    sink = BytesIO()
    result = pisa.CreatePDF(html, dest=sink, encoding="utf-8")
    if result.err:
        logger.error("pdf_render_failed", errors=result.err)
        raise RuntimeError("Failed to render PDF from HTML")
    return sink.getvalue()

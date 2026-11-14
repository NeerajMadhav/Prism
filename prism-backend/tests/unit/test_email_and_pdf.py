"""Unit checks for mail transport selection and PDF rendering."""

from src.services.email_service import EmailService
from src.services.pdf_service import html_to_pdf


def test_html_to_pdf_renders_bytes() -> None:
    pdf = html_to_pdf(
        "<html><body><h1>PRISM</h1><p>Monthly report</p></body></html>"
    )
    assert isinstance(pdf, bytes)
    assert pdf[:4] == b"%PDF"


def test_email_service_graph_flag_default_false() -> None:
    svc = EmailService()
    # Without MS_GRAPH_* env vars, Graph is not configured.
    assert svc.graph_configured is False

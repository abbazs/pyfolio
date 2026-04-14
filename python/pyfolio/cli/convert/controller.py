"""Business logic for HTML-to-PDF conversion."""

import os
from pathlib import Path

from pyfolio._pyfolio import convert_html_to_pdf as _convert

from .models import ConvertResult


def convert(
    input_path: str,
    output_path: str,
    page_size: str,
    margin_top: float,
    margin_bottom: float,
    margin_left: float,
    margin_right: float,
    header_text: str | None,
    footer_text: str | None,
    title: str | None,
) -> ConvertResult:
    """Convert an HTML file to PDF using the folio engine.

    Reads the HTML file, calls the Rust extension, and returns a ConvertResult.
    """
    html = Path(input_path).read_text(encoding="utf-8")
    _convert(
        html,
        output_path,
        page_size=page_size,
        margin_top=margin_top,
        margin_bottom=margin_bottom,
        margin_left=margin_left,
        margin_right=margin_right,
        header_text=header_text,
        footer_text=footer_text,
        title=title,
    )
    size = os.path.getsize(output_path)
    return ConvertResult(
        input_path=input_path,
        output_path=output_path,
        page_size=page_size,
        output_size_bytes=size,
    )

"""Convert command — HTML to PDF via folio."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import cyclopts

from gofolio.utils.decorators import handle_cli_errors

from . import controller, view

cli = cyclopts.App(name="convert", help="Convert an HTML file to PDF.")


@cli.default
@handle_cli_errors
def convert(
    input: Annotated[
        Path,
        cyclopts.Parameter(name=["--input", "-i"], help="Path to the HTML input file."),
    ],
    output: Annotated[
        Path,
        cyclopts.Parameter(name=["--output", "-o"], help="Destination PDF file path."),
    ],
    *,
    page_size: Annotated[
        str,
        cyclopts.Parameter(
            name=["--page-size", "-s"],
            help="Page size: a4 (default), a3, letter, legal.",
        ),
    ] = "a4",
    margin_top: Annotated[
        float, cyclopts.Parameter(name="--margin-top", help="Top margin in mm.")
    ] = 20.0,
    margin_bottom: Annotated[
        float, cyclopts.Parameter(name="--margin-bottom", help="Bottom margin in mm.")
    ] = 20.0,
    margin_left: Annotated[
        float, cyclopts.Parameter(name="--margin-left", help="Left margin in mm.")
    ] = 15.0,
    margin_right: Annotated[
        float, cyclopts.Parameter(name="--margin-right", help="Right margin in mm.")
    ] = 15.0,
    header_text: Annotated[
        str | None,
        cyclopts.Parameter(
            name="--header-text",
            help="Header text. Supports {page} and {total} tokens.",
        ),
    ] = None,
    footer_text: Annotated[
        str | None,
        cyclopts.Parameter(
            name="--footer-text",
            help="Footer text. Supports {page} and {total} tokens.",
        ),
    ] = None,
    title: Annotated[
        str | None,
        cyclopts.Parameter(name="--title", help="PDF document title (metadata)."),
    ] = None,
) -> None:
    """Convert an HTML file to a PDF document."""
    result = controller.convert(
        input_path=str(input),
        output_path=str(output),
        page_size=page_size,
        margin_top=margin_top,
        margin_bottom=margin_bottom,
        margin_left=margin_left,
        margin_right=margin_right,
        header_text=header_text,
        footer_text=footer_text,
        title=title,
    )
    view.show_result(result)

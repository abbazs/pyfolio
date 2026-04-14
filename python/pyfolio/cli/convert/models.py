"""Data models for the convert command."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ConvertResult:
    """Result of an HTML-to-PDF conversion."""

    input_path: str
    output_path: str
    page_size: str
    output_size_bytes: int

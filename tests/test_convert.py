"""Tests for the pyfolio HTML-to-PDF conversion pipeline.

Covers:
- Parameterised fixture-based conversion (1, 5, 10, 50, 100 pages)
- Conversion with custom options (header, footer, title, margins)
- Conversion of real-world asset HTML files from ``tests/assets/``
- Error handling when the output directory does not exist
"""

from pathlib import Path

import pypdf
import pytest

from gofolio.cli.convert.controller import convert
from gofolio.cli.convert.models import ConvertResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_html(html: str, directory: Path, filename: str = "input.html") -> str:
    """Write an HTML string to a temporary file and return its path as str.

    Args:
        html: The HTML content to write.
        directory: Directory in which to create the file.
        filename: Name to give the file (default: ``input.html``).

    Returns:
        Absolute path string to the written file.
    """
    p = directory / filename
    p.write_text(html, encoding="utf-8")
    return str(p)


def _assert_valid_pdf(result: ConvertResult, expected_output_path: str) -> pypdf.PdfReader:
    """Run standard assertions on a ConvertResult and return a PdfReader.

    Asserts:
    - The output file exists.
    - The output file size is greater than zero.
    - ``result.output_path`` matches ``expected_output_path``.
    - pypdf can open the file without raising an exception.

    Args:
        result: The ``ConvertResult`` returned by ``convert()``.
        expected_output_path: The output path string passed to ``convert()``.

    Returns:
        An open ``pypdf.PdfReader`` for further assertions by the caller.
    """
    out = Path(result.output_path)
    assert out.exists(), f"Output PDF does not exist: {out}"
    assert out.stat().st_size > 0, f"Output PDF is empty: {out}"
    assert result.output_path == expected_output_path, (
        f"ConvertResult.output_path mismatch: got {result.output_path!r}, "
        f"expected {expected_output_path!r}"
    )
    # pypdf.PdfReader constructor raises if the file is not a valid PDF
    reader = pypdf.PdfReader(str(out))
    return reader


# ---------------------------------------------------------------------------
# Parameterised fixture-based tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "html_fixture,expected_pages",
    [
        ("html_1page", 1),
        ("html_5page", 5),
        ("html_10page", 10),
        ("html_50page", 50),
        ("html_100page", 100),
    ],
)
def test_convert_fixture(
    request: pytest.FixtureRequest,
    html_fixture: str,
    expected_pages: int,
    tmp_path: Path,
) -> None:
    """Convert a programmatically generated HTML fixture and validate the PDF.

    For each fixture the test asserts:
    1. The output PDF exists and its size is > 0 bytes.
    2. pypdf can open the PDF without error.
    3. ``ConvertResult.output_path`` matches the path passed to ``convert()``.
    4. The page count is at least ``expected_pages // 2`` (generous tolerance
       because pagination is engine-dependent and may vary slightly).

    Args:
        request: Pytest fixture request, used to resolve the named HTML fixture.
        html_fixture: Name of the HTML fixture to retrieve via ``request.getfixturevalue``.
        expected_pages: Expected approximate page count.
        tmp_path: Pytest temporary directory.
    """
    html: str = request.getfixturevalue(html_fixture)
    input_path = _write_html(html, tmp_path)
    output_path = str(tmp_path / "output.pdf")

    result = convert(
        input_path=input_path,
        output_path=output_path,
        page_size="a4",
        margin_top=20.0,
        margin_bottom=20.0,
        margin_left=15.0,
        margin_right=15.0,
        header_text=None,
        footer_text=None,
        title=None,
    )

    reader = _assert_valid_pdf(result, output_path)

    # pypdf >= 6 API (pinned in pyproject.toml)
    num_pages = reader.get_num_pages()

    # Generous tolerance (80 %): CSS page-break rendering is non-deterministic
    # across headless engine versions and platforms; requiring ~80 % of the
    # expected pages catches catastrophic failures without being brittle on
    # minor inter-version rendering differences.
    min_pages = max(1, int(expected_pages * 0.8))
    assert num_pages >= min_pages, (
        f"[{html_fixture}] Expected >= {min_pages} pages, got {num_pages}"
    )


# ---------------------------------------------------------------------------
# Options test
# ---------------------------------------------------------------------------


def test_convert_with_options(html_1page: str, tmp_path: Path) -> None:
    """Verify that optional parameters (header, footer, title, margins) are accepted.

    Uses the ``html_1page`` fixture. Asserts:
    - The output PDF exists and size > 0.
    - pypdf can open the PDF without error.
    - ``ConvertResult.output_path`` is correct.

    The test does not assert on rendered header/footer text content because
    that would require visual inspection; we only verify no error is raised.

    Args:
        html_1page: Single-page HTML fixture string.
        tmp_path: Pytest temporary directory.
    """
    input_path = _write_html(html_1page, tmp_path)
    output_path = str(tmp_path / "with_options.pdf")

    result = convert(
        input_path=input_path,
        output_path=output_path,
        page_size="letter",
        margin_top=10.0,
        margin_bottom=10.0,
        margin_left=8.0,
        margin_right=8.0,
        header_text="Test Header — Page {page} of {total}",
        footer_text="Generated by pyfolio tests",
        title="Test Document Title",
    )

    _assert_valid_pdf(result, output_path)


# ---------------------------------------------------------------------------
# Asset file tests
# ---------------------------------------------------------------------------


# Paths are relative to this file's parent directory (tests/)
_ASSETS_DIR = Path(__file__).parent / "assets"

_ASSET_FILES: list[str] = [
    "01_simple.html",
    "10_tables_flex.html",
    "100_svg_heavy.html",
]


@pytest.mark.parametrize("asset_filename", _ASSET_FILES)
def test_convert_asset_files(asset_filename: str, tmp_path: Path) -> None:
    """Convert each real-world asset HTML file and assert the PDF is valid.

    Asserts:
    - The output PDF exists.
    - The output PDF size is > 0 bytes.
    - pypdf can open the PDF without error.

    Args:
        asset_filename: Filename (relative to ``tests/assets/``) to convert.
        tmp_path: Pytest temporary directory.
    """
    input_path = str(_ASSETS_DIR / asset_filename)
    # Derive a unique output name from the input filename to avoid collisions
    stem = Path(asset_filename).stem
    output_path = str(tmp_path / f"{stem}.pdf")

    result = convert(
        input_path=input_path,
        output_path=output_path,
        page_size="a4",
        margin_top=20.0,
        margin_bottom=20.0,
        margin_left=15.0,
        margin_right=15.0,
        header_text=None,
        footer_text=None,
        title=None,
    )

    _assert_valid_pdf(result, output_path)


# ---------------------------------------------------------------------------
# Error-handling test
# ---------------------------------------------------------------------------


def test_convert_invalid_output_dir(html_1page: str, tmp_path: Path) -> None:
    """Verify that a RuntimeError is raised when the output directory does not exist.

    The Rust extension (and the controller wrapping it) should raise
    ``RuntimeError`` when asked to write to a non-existent directory.

    Args:
        html_1page: Single-page HTML fixture string.
        tmp_path: Pytest temporary directory.
    """
    input_path = _write_html(html_1page, tmp_path)
    # Point to a path whose parent directory does not exist
    missing_dir = tmp_path / "nonexistent_subdir"
    output_path = str(missing_dir / "output.pdf")

    with pytest.raises(RuntimeError):
        convert(
            input_path=input_path,
            output_path=output_path,
            page_size="a4",
            margin_top=20.0,
            margin_bottom=20.0,
            margin_left=15.0,
            margin_right=15.0,
            header_text=None,
            footer_text=None,
            title=None,
        )

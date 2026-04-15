"""Pytest configuration and shared fixtures for gofolio tests.

Provides programmatically generated HTML fixture strings and a temporary PDF
path fixture used across the test suite.
"""

from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# HTML generation helpers
# ---------------------------------------------------------------------------


def _svg_circle(color: str = "#4A90D9", size: int = 40) -> str:
    """Return an inline SVG circle icon string.

    Args:
        color: Fill color as a CSS hex string.
        size: Width/height in pixels.

    Returns:
        An SVG element string suitable for embedding in HTML.
    """
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}"'
        f' viewBox="0 0 {size} {size}">'
        f'<circle cx="{size // 2}" cy="{size // 2}" r="{size // 2 - 2}"'
        f' fill="{color}" /></svg>'
    )


def _svg_bar_chart(page_num: int) -> str:
    """Return a simple inline SVG bar chart for a given page number.

    Args:
        page_num: The page/section number, used to vary bar heights.

    Returns:
        An SVG bar chart element string.
    """
    # Vary bar heights based on page number so each chart looks different
    heights = [20 + (page_num * i * 3) % 60 for i in range(1, 6)]
    bars = "".join(
        f'<rect x="{i * 20}" y="{80 - h}" width="15" height="{h}" fill="#4A90D9" />'
        for i, h in enumerate(heights)
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="80"'
        ' viewBox="0 0 120 80">'
        f"{bars}</svg>"
    )


def _base_style() -> str:
    """Return the base CSS style block used by all fixtures.

    Includes page-break rules so the renderer paginates correctly.

    Returns:
        A ``<style>`` element string.
    """
    return """<style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: Arial, sans-serif; font-size: 12pt; }
        .page-section {
            page-break-after: always;
            width: 100%;
            min-height: 250mm;
            padding: 15mm;
        }
        .page-section:last-child { page-break-after: auto; }
        h1 { font-size: 20pt; margin-bottom: 10pt; }
        h2 { font-size: 16pt; margin-bottom: 8pt; }
        p { line-height: 1.5; margin-bottom: 8pt; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 10pt; }
        th, td { border: 1px solid #ccc; padding: 6pt; text-align: left; }
        th { background: #f0f0f0; }
        .flex-row { display: flex; gap: 20pt; align-items: center; margin-top: 10pt; }
        .grid-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10pt;
            margin-top: 10pt;
        }
    </style>"""


# ---------------------------------------------------------------------------
# Fixtures: programmatically generated HTML strings
# ---------------------------------------------------------------------------


@pytest.fixture
def html_1page() -> str:
    """Return a self-contained single-page HTML string.

    Contains an h1 heading, a paragraph, and one inline SVG circle icon.
    Uses ``page-break-after: always`` on the section div so the renderer
    produces exactly 1 page.

    Returns:
        HTML string for a 1-page document.
    """
    style = _base_style()
    circle = _svg_circle(color="#E74C3C", size=50)
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Single Page Test</title>{style}</head>
<body>
  <div class="page-section">
    <h1>Single Page Document</h1>
    <p>This is a single-page test document used to verify that the HTML-to-PDF
    converter correctly produces a one-page output when the content fits on
    a single A4 page.</p>
    <p>The inline SVG below is an icon embedded directly in the HTML source.</p>
    {circle}
  </div>
</body>
</html>"""


@pytest.fixture
def html_5page() -> str:
    """Return a self-contained 5-page HTML string.

    Each page section contains a table, a flexbox layout row, and one inline
    SVG circle icon. ``page-break-after: always`` separates each section.

    Returns:
        HTML string for a 5-page document.
    """
    style = _base_style()
    sections = []
    for i in range(1, 6):
        circle = _svg_circle(color=f"#{(i * 40):02X}90{(255 - i * 30):02X}", size=40)
        rows = "".join(
            f"<tr><td>Item {j}</td><td>{j * i * 10}</td><td>{'Active' if j % 2 == 0 else 'Inactive'}</td></tr>"
            for j in range(1, 5)
        )
        sections.append(f"""  <div class="page-section">
    <h2>Section {i} — Tables &amp; Flexbox</h2>
    <table>
      <thead><tr><th>Name</th><th>Value</th><th>Status</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <div class="flex-row">
      <p>Icon for section {i}:</p>
      {circle}
    </div>
  </div>""")

    body = "\n".join(sections)
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Five Page Report</title>{style}</head>
<body>
{body}
</body>
</html>"""


@pytest.fixture
def html_10page() -> str:
    """Return a self-contained 10-page HTML string.

    Each page section uses CSS Grid layout and includes an inline SVG bar
    chart. ``page-break-after: always`` separates each section.

    Returns:
        HTML string for a 10-page document.
    """
    style = _base_style()
    sections = []
    for i in range(1, 11):
        chart = _svg_bar_chart(i)
        sections.append(f"""  <div class="page-section">
    <h2>Report Page {i} — CSS Grid Layout</h2>
    <div class="grid-container">
      <div>
        <p>This cell is in column 1 of the grid for page {i}. CSS Grid ensures
        a clean two-column layout across the page content area.</p>
        <p>Additional details for section {i}: metric value is {i * 137}.</p>
      </div>
      <div>
        <p>Column 2 — bar chart visualising data for section {i}:</p>
        {chart}
      </div>
    </div>
  </div>""")

    body = "\n".join(sections)
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Ten Page Grid Report</title>{style}</head>
<body>
{body}
</body>
</html>"""


@pytest.fixture
def html_50page() -> str:
    """Return a self-contained 50-page HTML string.

    Consists of repeated sections each containing multiple SVG diagrams and
    paragraph text. ``page-break-after: always`` separates each section.

    Returns:
        HTML string for a 50-page document.
    """
    style = _base_style()
    sections = []
    for i in range(1, 51):
        # Two diagrams per page to increase SVG density
        circle_a = _svg_circle(color=f"#{(i * 5) % 256:02X}AA{(200 - i) % 256:02X}", size=36)
        circle_b = _svg_circle(color=f"#{(255 - i * 4) % 256:02X}{(i * 7) % 256:02X}CC", size=36)
        sections.append(f"""  <div class="page-section">
    <h2>Section {i:02d} of 50</h2>
    <p>Paragraph A for section {i}: This repeated section tests that the
    converter handles a large number of pages without memory or rendering
    issues. Each section is intentionally similar to stress-test pagination.</p>
    <p>Paragraph B for section {i}: Metric values — alpha: {i * 13},
    beta: {i * 29}, gamma: {i * 7}.</p>
    <div class="flex-row">
      <div>SVG A: {circle_a}</div>
      <div>SVG B: {circle_b}</div>
    </div>
  </div>""")

    body = "\n".join(sections)
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Fifty Page Stress Test</title>{style}</head>
<body>
{body}
</body>
</html>"""


@pytest.fixture
def html_100page() -> str:
    """Return a self-contained 100-page HTML string.

    Each page has a heading, a body paragraph, and an inline SVG element.
    Designed as a stress test for SVG-heavy documents.
    ``page-break-after: always`` separates each section.

    Returns:
        HTML string for a 100-page document.
    """
    style = _base_style()
    sections = []
    for i in range(1, 101):
        # Alternate between circle and bar-chart SVGs
        svg = _svg_circle(size=32) if i % 2 == 0 else _svg_bar_chart(i)
        sections.append(f"""  <div class="page-section">
    <h2>Page {i:03d}</h2>
    <p>Stress-test content for page {i}. This document exercises the renderer
    with 100 individual page sections, each containing an inline SVG element.
    Unique value for this page: {i * 9973 % 99991}.</p>
    {svg}
  </div>""")

    body = "\n".join(sections)
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>100-Page SVG Stress Test</title>{style}</head>
<body>
{body}
</body>
</html>"""

# gofolio

Python wrapper for [folio](https://github.com/carlos7ags/folio) — a Go HTML-to-PDF library — exposed via a PyO3 Rust extension.

## Installation

```bash
pip install gofolio
```

## CLI usage

```bash
gf convert --input report.html --output report.pdf \
    --page-size a4 \
    --margin-top 20 --margin-bottom 20 --margin-left 15 --margin-right 15 \
    --header-text "Confidential" \
    --footer-text "Page {page} of {total}" \
    --title "Q1 Report"
```

## Python API

```python
from gofolio._gofolio import convert_html_to_pdf

convert_html_to_pdf(
    html="<h1>Hello</h1><p>World</p>",
    output_path="output.pdf",
    page_size="a4",           # a4 | a3 | letter | legal
    margin_top=20.0,          # mm
    margin_bottom=20.0,
    margin_left=15.0,
    margin_right=15.0,
    header_text="My Header",
    footer_text="Page {page} of {total}",
    title="My Document",
)
```

## Requirements

- Python 3.12+
- Go 1.21+ *(build-time only)*
- Rust stable *(build-time only)*

## License

Apache-2.0
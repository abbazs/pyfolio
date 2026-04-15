# gofolio

[![PyPI version](https://img.shields.io/pypi/v/gofolio)](https://pypi.org/project/gofolio)
[![Python versions](https://img.shields.io/pypi/pyversions/gofolio)](https://pypi.org/project/gofolio)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://github.com/abbazs/gofolio/blob/main/LICENSE)

Python wrapper for [folio](https://github.com/carlos7ags/folio) — a Go HTML-to-PDF library — exposed via a PyO3 Rust extension.

## Installation

```
pip install gofolio
```

Requires Python 3.12+. No Go or Rust installation needed at runtime — pre-compiled wheels are published for Linux, macOS, and Windows.

## Quick Start

```python
from gofolio import convert_html_to_pdf

convert_html_to_pdf(
    html="<h1>Hello</h1><p>World</p>",
    output_path="output.pdf",
)
```

## Python API

```python
from gofolio import convert_html_to_pdf

convert_html_to_pdf(
    html="<h1>Hello</h1><p>World</p>",
    output_path="output.pdf",
    page_size="a4",                        # a4 | a3 | letter | legal
    margin_top=20.0,                       # mm
    margin_bottom=20.0,
    margin_left=15.0,
    margin_right=15.0,
    header_text="Confidential",
    footer_text="Page {page} of {total}",  # {page} and {total} are substituted
    title="Q1 Report",
)
```

### `convert_html_to_pdf`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `html` | `str` | required | HTML source string to convert |
| `output_path` | `str` | required | Path where the PDF will be written |
| `page_size` | `str` | `"a4"` | Page size: `"a4"`, `"a3"`, `"letter"`, or `"legal"` |
| `margin_top` | `float` | `10.0` | Top margin in millimetres |
| `margin_bottom` | `float` | `10.0` | Bottom margin in millimetres |
| `margin_left` | `float` | `10.0` | Left margin in millimetres |
| `margin_right` | `float` | `10.0` | Right margin in millimetres |
| `header_text` | `str \| None` | `None` | Text printed in the page header |
| `footer_text` | `str \| None` | `None` | Text printed in the page footer — `{page}` and `{total}` are substituted |
| `title` | `str \| None` | `None` | PDF document title metadata |

Raises `RuntimeError` if folio fails to create or render the document.

## CLI Usage

Two entry points are available: `gofolio` and the shorter alias `gf`.

```bash
gf convert --input report.html --output report.pdf \
    --page-size a4 \
    --margin-top 20 --margin-bottom 20 --margin-left 15 --margin-right 15 \
    --header-text "Confidential" \
    --footer-text "Page {page} of {total}" \
    --title "Q1 Report"
```

### CLI options

| Option | Default | Description |
|---|---|---|
| `--input` | required | Path to the input HTML file |
| `--output` | required | Path for the output PDF file |
| `--page-size` | `a4` | Page size: `a4`, `a3`, `letter`, `legal` |
| `--margin-top` | `10.0` | Top margin (mm) |
| `--margin-bottom` | `10.0` | Bottom margin (mm) |
| `--margin-left` | `10.0` | Left margin (mm) |
| `--margin-right` | `10.0` | Right margin (mm) |
| `--header-text` | — | Header text (optional) |
| `--footer-text` | — | Footer text — `{page}` and `{total}` substituted |
| `--title` | — | PDF document title metadata (optional) |

```bash
gf --help
gf convert --help
```

## How It Works

```
HTML string
    │
    ▼
Python  ──── from gofolio import convert_html_to_pdf
    │
    ▼
Rust (PyO3)  ──── gofolio._gofolio (cdylib, built with maturin)
    │
    ▼
Go C-ABI  ──── libfolio (compiled with go build -buildmode=c-shared)
    │
    ▼
PDF file
```

The Go `folio` library does the actual HTML rendering and PDF generation. A thin Rust layer (built with [PyO3](https://pyo3.rs) and [maturin](https://maturin.rs)) provides FFI bindings via `bindgen` and exposes the function to Python. All folio calls are serialised behind a mutex — folio is not thread-safe.

## Build Requirements

Pre-compiled wheels are available on PyPI for Linux, macOS (x86_64 + arm64), and Windows (x86_64). You only need the following if building from source:

- Python 3.12+
- Go 1.21+ (`go build -buildmode=c-shared`)
- Rust stable (`cargo` + `maturin`)

```bash
pip install maturin
maturin develop --release
```

## License

[Apache-2.0](https://github.com/abbazs/gofolio/blob/main/LICENSE)

# pyfolio Design Specification

**Date:** 2026-04-14  
**Project:** pyfolio  
**Status:** Phase 4 — Design Documentation

---

## 1. Overview

**pyfolio** is a Python package that exposes the folio HTML-to-PDF rendering library via PyO3 Rust bindings. It provides a command-line tool and a programmatic Python API for converting HTML documents to PDF with fine-grained control over page layout, margins, headers, and footers.

**Key characteristics:**
- Written in Rust with FFI bindings to Go
- Distributed as pre-built wheels on PyPI
- Requires Python 3.12+
- Single-threaded, thread-safe via a global Mutex lock
- Supports 4 page sizes: A4 (default), A3, letter, legal
- Customizable margins, headers, footers with token substitution

---

## 2. Architecture

pyfolio implements a three-layer stack:

### Layer 1: Go C-ABI Library
- **Component:** folio (carlos7ags/folio@v0.6.2)
- **Delivery:** Compiled as a C-shared library during build
- **Interface:** C function exports (folio_document_new_a4, folio_document_set_margins, etc.)
- **Responsibility:** Core HTML-to-PDF rendering engine

### Layer 2: Rust FFI & PyO3
- **Component:** src/ directory (lib.rs, html.rs, document.rs, error.rs)
- **Bindings:** bindgen-generated from Go C header; included via build.rs
- **PyO3 Module:** _pyfolio (native extension)
- **Responsibility:** 
  - C-string marshalling and validation
  - Thread synchronization via FOLIO_LOCK mutex
  - Error handling and exception conversion
  - RAII document lifecycle management
  - Unit conversions (mm to PDF points)

### Layer 3: Python CLI & SDK
- **Component:** python/pyfolio/ directory
- **CLI Framework:** cyclopts (command parsing)
- **Output Rendering:** Rich (terminal UI)
- **Architecture:** Domain-driven (models, controllers, views)
- **Responsibility:** 
  - Command-line interface with help text
  - HTML file I/O
  - Result formatting and display
  - User-facing error messages

---

## 3. Repository Structure

```
pyfolio/
├── Cargo.toml                 # Rust package manifest
├── Cargo.lock                 # Locked dependency versions
├── build.rs                   # Build script: Go build, bindgen, FFI setup
├── pyproject.toml             # Python package metadata, maturin config
├── uv.lock                    # Python lock file (uv package manager)
├── .github/workflows/
│   ├── ci.yml                 # Test pipeline (push/PR)
│   └── publish.yml            # Wheel build & PyPI publish (tags)
├── src/
│   ├── lib.rs                 # PyO3 module definition, convert_html_to_pdf entry point
│   ├── html.rs                # Conversion logic, FOLIO_LOCK, C-ABI calls
│   ├── document.rs            # RAII Document handle wrapper, Drop impl
│   └── error.rs               # Error message retrieval and code checking
├── python/pyfolio/
│   ├── __init__.py            # Package root
│   ├── cli/
│   │   ├── __init__.py        # Root CLI app (cyclopts)
│   │   └── convert/
│   │       ├── __init__.py    # convert command definition (cyclopts)
│   │       ├── controller.py  # Business logic (file I/O, FFI call)
│   │       ├── models.py      # ConvertResult dataclass
│   │       └── view.py        # Terminal output rendering (Rich)
│   └── utils/
│       ├── __init__.py
│       ├── console.py         # Shared Rich console instance
│       ├── decorators.py      # Error handling decorator
│       └── rp.py              # Relative path utilities
├── tests/
│   ├── conftest.py            # Pytest fixtures: 5 HTML fixture levels
│   ├── test_convert.py        # 8 test cases: fixtures, options, assets, errors
│   └── assets/                # 3 real-world HTML files (simple, tables, SVG-heavy)
│       ├── 01_simple.html
│       ├── 10_tables_flex.html
│       └── 100_svg_heavy.html
└── main.py                    # Development entry point
```

---

## 4. Build Chain

### 4.1 Build Script (build.rs)

The build script executes in this order during `cargo build`:

1. **Locate Go toolchain** — search PATH and common install locations
2. **Create scratch Go module directory** — OUT_DIR/folio_go_module with go.mod
3. **Fetch folio dependency** — run `go get github.com/carlos7ags/folio/export`
4. **Compile to C-shared library** — `go build -buildmode=c-shared -o libfolio.so`
5. **Generate C header** — Go generates libfolio.h automatically
6. **Run bindgen** — parse libfolio.h and output bindings.rs
7. **Link configuration** — set rustc-link-search and rpath for dynamic loading

**Output artifacts:**
- libfolio.so (Linux), libfolio.dylib (macOS), folio.dll (Windows)
- bindings.rs (included in lib.rs via include! macro)

### 4.2 Python Wheel Build (maturin)

Triggered by `maturin build --release`:

1. Calls cargo to build the Rust extension
2. Creates Python wheel for the current platform
3. Embeds libfolio.so in the wheel's _pyfolio.cpython-312-x86_64-linux-gnu.so

**Platform-specific wheels:**
- Windows: x86_64-pc-windows-msvc
- macOS: x86_64-apple-darwin, aarch64-apple-darwin
- Linux: x86_64-unknown-linux-gnu, aarch64-unknown-linux-gnu

---

## 5. Rust Extension API

### 5.1 Exported Function

**Module:** pyfolio._pyfolio

**Function signature:**
```rust
#[pyfunction]
fn convert_html_to_pdf(
    html: &str,
    output_path: &str,
    page_size: &str,
    margin_top: f64,
    margin_bottom: f64,
    margin_left: f64,
    margin_right: f64,
    header_text: Option<&str>,
    footer_text: Option<&str>,
    title: Option<&str>,
) -> PyResult<()>
```

**Parameters:**
- `html` — UTF-8 HTML source (full document)
- `output_path` — path where PDF will be written
- `page_size` — "a4" (default), "a3", "letter", or "legal"
- `margin_top`, `margin_bottom`, `margin_left`, `margin_right` — margins in millimetres
- `header_text` — optional header; `{page}` and `{total}` are replaced at render time
- `footer_text` — optional footer; `{page}` and `{total}` are replaced at render time
- `title` — optional PDF metadata title

**Return value:** None (PyResult<()>)

**Exceptions raised:**
- `RuntimeError` — folio rendering failure (e.g. invalid HTML, missing parent directory)
- `ValueError` — string argument contains null bytes

### 5.2 Thread Safety

All folio C-ABI calls are serialized behind a module-level Mutex:

```rust
static FOLIO_LOCK: Mutex<()> = Mutex::new(());
```

**Rationale:** folio uses global state internally and does not support concurrent calls.

**Pattern:**
```rust
let _lock = FOLIO_LOCK.lock()?;  // Acquire lock; hold for entire conversion
// ... folio calls ...
// Lock released on drop
```

### 5.3 Document Lifecycle (RAII)

```rust
pub struct Document(pub(crate) u64);

impl Document {
    pub fn new(page_size: &str) -> PyResult<Self> { ... }
}

impl Drop for Document {
    fn drop(&mut self) {
        unsafe { bindings::folio_document_free(self.0) }
    }
}
```

**Guarantee:** folio_document_free() is called exactly once, even on error paths, due to Rust's Drop trait.

### 5.4 Error Handling

folio returns i32 codes (≥ 0 = success, < 0 = error) and provides a message via folio_last_error():

```rust
pub fn check(code: i32, guard: &MutexGuard<'_, ()>) -> Result<(), PyErr> {
    if code >= 0 {
        Ok(())
    } else {
        Err(PyRuntimeError::new_err(last_error(guard)))
    }
}
```

**Pattern:** After each folio call, invoke `check(result, &lock)?` to convert error codes to Python exceptions.

### 5.5 Unit Conversion

```rust
fn mm_to_pts(mm: f64) -> f64 {
    mm * 2.834_645_669_291_339  // 72/25.4
}
```

Public API accepts millimetres; folio uses PDF points internally.

---

## 6. Python CLI Interface

### 6.1 Command Structure

**Entry points (from pyproject.toml):**
```
pyfolio → pyfolio.cli:app
pf      → pyfolio.cli:app
```

**Root command:** `pyfolio` (cyclopts.App)
**Subcommand:** `convert` (cyclopts.App)

### 6.2 Convert Command

**Usage:**
```
pf convert --input input.html --output output.pdf [OPTIONS]
pf convert -i input.html -o output.pdf
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| --input | -i | Path | (required) | HTML input file path |
| --output | -o | Path | (required) | PDF output file path |
| --page-size | -s | str | "a4" | a4, a3, letter, legal |
| --margin-top | | float | 20.0 | Top margin (mm) |
| --margin-bottom | | float | 20.0 | Bottom margin (mm) |
| --margin-left | | float | 15.0 | Left margin (mm) |
| --margin-right | | float | 15.0 | Right margin (mm) |
| --header-text | | str | None | Header; supports {page}, {total} |
| --footer-text | | str | None | Footer; supports {page}, {total} |
| --title | | str | None | PDF document title (metadata) |

### 6.3 Domain-Driven Architecture

**Module organization:**

- **Models** (models.py): Pure data structures
  - ConvertResult — immutable dataclass with input_path, output_path, page_size, output_size_bytes

- **Controller** (controller.py): Business logic
  - convert() — reads HTML, calls _pyfolio.convert_html_to_pdf(), returns ConvertResult
  - No terminal I/O; raises exceptions that propagate to decorator

- **View** (view.py): Terminal output
  - show_result() — displays Rich Stepper showing conversion pipeline (4 steps)
  - Formats file size in human-readable units (B, KB, MB)
  - Shows summary panel with input/output paths and page size

- **Decorator** (decorators.py): Cross-cutting error handling
  - @handle_cli_errors — wraps CLI command, catches exceptions, prints error messages to stderr, exits with code 1

### 6.4 Error Handling

1. **Rust extension raises RuntimeError or ValueError**
2. **Controller propagates exception**
3. **Decorator catches exception, formats message, exits**
4. **User sees error in terminal with context**

---

## 7. Test Matrix

### 7.1 Fixture Levels

Programmatically generated HTML fixtures in conftest.py (5 levels):

| Fixture | Pages | Content |
|---------|-------|---------|
| html_1page | 1 | Heading, paragraph, 1 SVG circle |
| html_5page | 5 | Tables, flexbox, 5 SVG circles (one per page) |
| html_10page | 10 | CSS Grid layout, 10 SVG bar charts |
| html_50page | 50 | Repeated sections, 100 SVG circles (2 per page) |
| html_100page | 100 | Single heading + paragraph, 100 SVG alternating circles/charts |

**Design principles:**
- Self-contained, no external resources
- Use page-break-after: always for precise pagination
- CSS (Grid, Flexbox, Tables) for layout complexity
- Inline SVGs with varying colors and patterns

### 7.2 Asset Files

Three real-world HTML files in tests/assets/:

| File | Pages | Purpose |
|------|-------|---------|
| 01_simple.html | ~1 | Minimal HTML: heading, paragraph |
| 10_tables_flex.html | ~10 | Table rendering, flexbox layout |
| 100_svg_heavy.html | ~100 | SVG-intensive document (stress test) |

### 7.3 Test Cases

**conftest.py:** 5 fixtures + 1 helper for style definitions

**test_convert.py:** 8 test cases

1. `test_convert_fixture` (parameterized over 5 fixtures)
   - Converts each fixture level
   - Asserts PDF exists, size > 0, pypdf can parse it
   - Checks page count ≥ 80% of expected (tolerance for rendering variance)

2. `test_convert_with_options`
   - Tests header_text, footer_text, title, custom margins, page_size="letter"
   - Asserts valid PDF generated (no visual inspection of rendered headers/footers)

3. `test_convert_asset_files` (parameterized over 3 assets)
   - Converts each real-world asset
   - Asserts PDF exists and is valid

4. `test_convert_invalid_output_dir`
   - Verifies RuntimeError raised when output directory does not exist
   - Tests error path (missing parent directory)

### 7.4 Assertion Helpers

`_assert_valid_pdf(result, expected_path)` — common assertions:
- Output file exists
- Output file size > 0
- result.output_path == expected_path
- pypdf.PdfReader can open file without exception
- Returns PdfReader for caller assertions

---

## 8. CI/CD Pipelines

### 8.1 CI Pipeline (ci.yml)

**Trigger:** push to any branch, pull requests

**Jobs:** test (ubuntu-latest)

**Steps:**
1. Checkout code
2. Setup Go (stable)
3. Setup Rust (stable via dtolnay toolchain)
4. Setup Python 3.12
5. Install uv
6. Install maturin (via uv tool install)
7. Install patchelf (Linux requirement for wheel building)
8. Build Python extension (maturin develop)
9. Run tests (uv run pytest -v)

**Output:** Pass/fail on each PR and push

### 8.2 Publish Pipeline (publish.yml)

**Trigger:** push tag matching `v*` (e.g., v0.1.0)

**Matrix:**
- OS: ubuntu-latest, macos-latest, windows-latest
- Per-platform wheel building in parallel

**Build job steps (per matrix entry):**
1. Checkout code
2. Setup Go (stable)
3. Setup Rust (stable)
4. Setup Python 3.12
5. Install maturin
6. Build wheels (maturin build --release)
7. Upload wheels artifact

**Publish job steps (after build completes):**
1. Download all wheel artifacts
2. Flatten artifact structure (find *.whl, move to final_dist/)
3. Install twine
4. Publish to PyPI (twine upload final_dist/*)

**Authentication:** PYPI_API_TOKEN secret

---

## 9. Packaging & Distribution

### 9.1 Package Metadata

**From pyproject.toml:**
- Name: pyfolio
- Version: 0.1.0 (bumped per release)
- Python: ≥ 3.12
- License: Apache-2.0
- Keywords: pdf, html, folio, converter

**Entry points:**
- `pyfolio` → pyfolio.cli:app
- `pf` → pyfolio.cli:app

### 9.2 Wheel Structure

Built by maturin; includes:
- _pyfolio.cpython-312-{PLATFORM}.so (Rust extension with embedded libfolio.so)
- Pure Python modules (pyfolio/cli, pyfolio/utils)
- Entry point scripts (pyfolio, pf)

**Platform wheel names (examples):**
- pyfolio-0.1.0-cp312-cp312-win_amd64.whl (Windows x64)
- pyfolio-0.1.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl (Linux x64)
- pyfolio-0.1.0-cp312-cp312-macosx_10_9_x86_64.whl (macOS Intel)
- pyfolio-0.1.0-cp312-cp312-macosx_11_0_arm64.whl (macOS Apple Silicon)

### 9.3 Dependencies

**Runtime:**
- cyclopts ≥ 3.0 (CLI parsing)
- rich ≥ 13.0 (terminal output)
- rich-stepper ≥ 0.2.0 (progress visualization)
- maturin ≥ 1.13.1 (build tool, pinned for reproducibility)

**Dev:**
- mypy ≥ 1.20.1 (static type checking)
- pytest ≥ 9.0.3 (testing framework)
- pypdf ≥ 6.10.0 (PDF validation in tests)
- ruff ≥ 0.15.10 (linting)

### 9.4 Installation

**From PyPI:**
```
pip install pyfolio
uv tool install pyfolio
```

**From source (development):**
```
uv sync
uv run maturin develop
```

---

## 10. Type Safety & Linting

### 10.1 Python Type Checking

**mypy configuration (strict mode):**
- All functions require type hints
- No implicit Any
- PEP 604 syntax: dict[K, V], list[T], str | None (not Dict, List, Optional)

### 10.2 Code Quality

**ruff configuration:**
- Line length: 100
- Target: Python 3.12
- Selected rules: E (errors), F (PyFlakes), I (isort), UP (pyupgrade), SIM (simplify)

---

## 11. Development Workflow

### 11.1 Local Setup

```
git clone https://github.com/abbazs/pyfolio
cd pyfolio
uv sync                      # Install deps and dev tools
uv run maturin develop       # Build Rust extension in-place
uv run pytest -v             # Run tests
uv run pyfolio --help        # Try CLI
```

### 11.2 Making Changes

1. **Python code:** Edit python/pyfolio/*, run tests with `uv run pytest -v`
2. **Rust code:** Edit src/*, run `uv run maturin develop` to rebuild, then test
3. **Build script:** Edit build.rs, run `uv run maturin develop`

### 11.3 Testing

```
uv run pytest -v                 # All tests
uv run pytest tests/test_convert.py::test_convert_with_options -v
uv run pytest -k html_50page     # Fixture-specific
```

### 11.4 Publishing

1. Bump version in Cargo.toml and pyproject.toml
2. Commit and push to main
3. Create and push tag: `git tag v0.1.1 && git push origin v0.1.1`
4. GitHub Actions publish pipeline builds wheels and uploads to PyPI

---

## 12. Design Decisions & Rationale

| Decision | Rationale |
|----------|-----------|
| PyO3 for bindings | Direct Python ↔ Rust interop; no C++ overhead; PyResult exceptions |
| Global FOLIO_LOCK mutex | folio is not thread-safe; lock serializes all calls; RAII guard drops lock automatically |
| Domain-driven CLI (MVC) | Separation of concerns: models, logic, presentation; testable controller; replaceable views |
| Maturin for wheel building | Native support for mixed Rust/Python; handles platform-specific details; single config file |
| 5-level fixture matrix | Tests progressive complexity: 1→5→10→50→100 pages; covers layouts (flexbox, grid, tables); includes SVGs |
| 80% page count tolerance | CSS page-break rendering varies by engine version and platform; 80% threshold catches major failures without brittleness |
| Two CLI entry points (pyfolio, pf) | pyfolio is full name; pf is convenient short alias (like git, npm) |

---

## 13. Future Extensibility

**Potential enhancements:**
- Batch conversion (multiple HTML → multiple PDF in parallel, using thread pool)
- Custom CSS injection (--css-file parameter)
- Templating support (--template-dir with variable substitution)
- Progress reporting for large documents
- Configuration file support (pyfolio.toml)
- Additional output formats (not blocked by folio library)

**Non-goals for Phase 4:**
- Interactive UI
- Web service / API server
- Document signing / encryption
- Async Python API (FOLIO_LOCK forces serialization)

---

## 14. Glossary

| Term | Definition |
|------|-----------|
| folio | Go HTML-to-PDF rendering library (carlos7ags/folio) |
| C-shared library | Binary compiled with -buildmode=c-shared (Linux .so, macOS .dylib, Windows .dll) |
| bindgen | Tool that parses C headers and generates Rust FFI bindings |
| PyO3 | Rust framework for building Python native extensions |
| maturin | Tool for building Python packages with Rust extensions |
| cyclopts | Python CLI framework (modern replacement for Click/Typer) |
| Rich | Python library for rich terminal output (colors, panels, tables) |
| RAII | Resource Acquisition Is Initialization (Rust pattern via Drop trait) |
| FOLIO_LOCK | Module-level Mutex that serializes all folio calls |
| Stepper | Rich component for visualizing multi-step processes |
| PyResult | Rust type that wraps Python exception or success value |

---

**End of Design Specification**

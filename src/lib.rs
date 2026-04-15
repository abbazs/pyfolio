//! PyO3 extension module exposing the folio HTML-to-PDF library to Python.
//!
//! This module is imported as `pyfolio._pyfolio` and exposes a single
//! high-level function: `convert_html_to_pdf`.

use pyo3::prelude::*;

#[allow(
    non_upper_case_globals,
    non_camel_case_types,
    non_snake_case,
    dead_code,
    clippy::all
)]
mod bindings {
    include!(concat!(env!("OUT_DIR"), "/bindings.rs"));
}

mod document;
mod error;
mod html;

/// Convert an HTML string to a PDF file using the folio rendering engine.
///
/// # Arguments
/// - `html` — HTML source (UTF-8)
/// - `output_path` — path where the PDF will be written
/// - `page_size` — "a4" (default), "a3", "letter", or "legal"
/// - `margin_top` — top margin in mm (default 20.0)
/// - `margin_bottom` — bottom margin in mm (default 20.0)
/// - `margin_left` — left margin in mm (default 15.0)
/// - `margin_right` — right margin in mm (default 15.0)
/// - `header_text` — optional header text; `{page}` and `{total}` are replaced at render time
/// - `footer_text` — optional footer text; `{page}` and `{total}` are replaced at render time
/// - `title` — optional title written to PDF document metadata
///
/// Raises `RuntimeError` on folio errors.
/// Raises `ValueError` if a string argument contains null bytes.
#[pyfunction]
#[pyo3(signature = (
    html,
    output_path,
    page_size = "a4",
    margin_top = 20.0,
    margin_bottom = 20.0,
    margin_left = 15.0,
    margin_right = 15.0,
    header_text = None,
    footer_text = None,
    title = None
))]
#[allow(clippy::too_many_arguments)]
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
) -> PyResult<()> {
    html::convert_html_to_pdf(
        html,
        output_path,
        page_size,
        margin_top,
        margin_bottom,
        margin_left,
        margin_right,
        header_text,
        footer_text,
        title,
    )
}

/// gofolio Rust extension — folio HTML-to-PDF bindings.
#[pymodule]
fn _gofolio(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(convert_html_to_pdf, m)?)?;
    Ok(())
}

//! HTML-to-PDF conversion using the folio C-ABI.
//!
//! All folio calls are serialised behind FOLIO_LOCK because folio is not thread-safe.

use std::ffi::CString;
use std::os::raw::c_char;
use std::sync::Mutex;

use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::PyResult;

use crate::bindings;
use crate::document::Document;
use crate::error::check;

/// Global lock protecting all folio calls (folio is single-threaded internally).
static FOLIO_LOCK: Mutex<()> = Mutex::new(());

/// Convert millimetres to PDF points (1 pt = 1/72 inch; 1 mm ≈ 2.83465 pt).
#[inline]
fn mm_to_pts(mm: f64) -> f64 {
    mm * 2.834_645_669_291_339
}

/// Build a null-terminated C string, returning PyValueError on interior null bytes.
fn to_cstring(s: &str, field: &str) -> PyResult<CString> {
    CString::new(s).map_err(|_| {
        PyValueError::new_err(format!("'{field}' contains a null byte"))
    })
}

/// Cast a CString's const pointer to a mutable pointer for folio C-ABI calls.
///
/// folio declares its string parameters as `char*` (mutable) even though it does not
/// mutate the pointed-to data. The cast is safe here because folio only reads the string.
#[inline]
unsafe fn as_mut_char_ptr(s: &CString) -> *mut c_char {
    // SAFETY: folio treats the pointer as read-only despite the `char*` signature.
    s.as_ptr() as *mut c_char
}

/// Convert an HTML document to a PDF file.
///
/// # Arguments
/// - `html` — UTF-8 HTML source
/// - `output_path` — destination PDF file path
/// - `page_size` — "a4" | "a3" | "letter" | "legal"
/// - `margin_top/bottom/left/right` — page margins in millimetres
/// - `header_text` — optional header (supports `{page}` / `{total}`)
/// - `footer_text` — optional footer (supports `{page}` / `{total}`)
/// - `title` — optional PDF metadata title
pub fn convert_html_to_pdf(
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
    let _lock = FOLIO_LOCK
        .lock()
        .map_err(|_| PyRuntimeError::new_err("folio mutex was poisoned"))?;

    let doc = Document::new(page_size)?;

    if let Some(t) = title {
        let c = to_cstring(t, "title")?;
        check(unsafe { bindings::folio_document_set_title(doc.0, as_mut_char_ptr(&c)) }, &_lock)?;
    }

    check(unsafe {
        bindings::folio_document_set_margins(
            doc.0,
            mm_to_pts(margin_top),
            mm_to_pts(margin_right),
            mm_to_pts(margin_bottom),
            mm_to_pts(margin_left),
        )
    }, &_lock)?;

    if let Some(h) = header_text {
        let c = to_cstring(h, "header_text")?;
        // folio_font_helvetica() returns a built-in standard font handle; align 1 = center
        let font_handle = unsafe { bindings::folio_font_helvetica() };
        check(unsafe {
            bindings::folio_document_set_header_text(
                doc.0,
                as_mut_char_ptr(&c),
                font_handle,
                10.0,
                1,
            )
        }, &_lock)?;
    }

    if let Some(f) = footer_text {
        let c = to_cstring(f, "footer_text")?;
        // folio_font_helvetica() returns a built-in standard font handle; align 1 = center
        let font_handle = unsafe { bindings::folio_font_helvetica() };
        check(unsafe {
            bindings::folio_document_set_footer_text(
                doc.0,
                as_mut_char_ptr(&c),
                font_handle,
                10.0,
                1,
            )
        }, &_lock)?;
    }

    let c_html = to_cstring(html, "html")?;
    check(unsafe { bindings::folio_document_add_html(doc.0, as_mut_char_ptr(&c_html)) }, &_lock)?;

    let c_path = to_cstring(output_path, "output_path")?;
    check(unsafe { bindings::folio_document_save(doc.0, as_mut_char_ptr(&c_path)) }, &_lock)?;

    Ok(())
}

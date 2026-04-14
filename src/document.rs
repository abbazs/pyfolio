//! RAII wrapper for the folio document handle.
//!
//! Ensures folio_document_free() is called when the Document goes out of scope,
//! even on error paths.

use pyo3::exceptions::PyRuntimeError;
use pyo3::PyResult;

use crate::bindings;

/// Owned wrapper around a folio document handle (opaque u64).
///
/// The handle is freed via folio_document_free() on drop.
pub struct Document(pub(crate) u64);

impl Document {
    /// Create a new document for the specified page size.
    ///
    /// Supported values: "a4", "a3", "letter", "legal". Defaults to A4.
    /// Returns `Err` if folio returns a null (zero) handle.
    pub(crate) fn new(page_size: &str) -> PyResult<Self> {
        let handle = unsafe {
            match page_size.to_lowercase().as_str() {
                "a4" => bindings::folio_document_new_a4(),
                "letter" => bindings::folio_document_new_letter(),
                "a3" => bindings::folio_document_new(841.890, 1190.551),
                "legal" => bindings::folio_document_new(612.0, 1008.0),
                _ => bindings::folio_document_new_a4(),
            }
        };
        if handle == 0 {
            return Err(PyRuntimeError::new_err(
                "folio failed to create document (null handle returned)",
            ));
        }
        Ok(Document(handle))
    }
}

impl Drop for Document {
    fn drop(&mut self) {
        // Safety: self.0 is a valid non-zero handle created by folio and not yet freed.
        unsafe { bindings::folio_document_free(self.0) }
    }
}

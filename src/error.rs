//! Error handling utilities for the folio C-ABI.
//!
//! folio returns i32 codes (0 = success, negative = error) and stores the
//! last error message accessible via folio_last_error().

use std::sync::MutexGuard;

use crate::bindings;

/// Retrieve the last folio error message.
///
/// # Safety / Locking
/// Must be called while holding `FOLIO_LOCK`. The returned string is only valid
/// for the duration of the lock guard — folio may overwrite the error buffer on
/// the next folio call.
pub(crate) fn last_error(_guard: &MutexGuard<'_, ()>) -> String {
    unsafe {
        let ptr = bindings::folio_last_error();
        if ptr.is_null() {
            "unknown folio error".to_string()
        } else {
            std::ffi::CStr::from_ptr(ptr).to_string_lossy().into_owned()
        }
    }
}

/// Check a folio return code, converting failures to PyRuntimeError.
///
/// Returns Ok(()) if `code >= 0`, otherwise returns Err with the last folio error message.
/// Must be called while holding `FOLIO_LOCK`.
pub(crate) fn check(code: i32, guard: &MutexGuard<'_, ()>) -> Result<(), pyo3::PyErr> {
    if code >= 0 {
        Ok(())
    } else {
        Err(pyo3::exceptions::PyRuntimeError::new_err(last_error(guard)))
    }
}

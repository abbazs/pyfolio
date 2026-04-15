---
name: wrapping-go-with-pyo3
description: Use when building a Python extension that wraps a Go library via PyO3 and Rust FFI, targeting Linux, macOS, and Windows from a single codebase with maturin-built wheels
---

# Wrapping a Go Library with PyO3

## Overview

Build chain: **Go (C-ABI shared lib)** → **bindgen (Rust FFI bindings)** → **PyO3 (Python extension)** → **Python**

The Go library is compiled as a C-shared library. Rust calls it via bindgen-generated FFI, PyO3 exposes the function to Python, and maturin builds the wheel. The hard part is Windows.

## Core Build Chain

### build.rs skeleton

```rust
fn main() {
    let out_dir = PathBuf::from(env::var("OUT_DIR").unwrap());
    let target_os = env::var("CARGO_CFG_TARGET_OS").unwrap();

    // 1. Compile Go → C-shared library
    let lib_name = match target_os.as_str() {
        "windows" => "folio.dll",
        "macos"   => "libfolio.dylib",
        _         => "libfolio.so",
    };
    Command::new("go")
        .args(["build", "-buildmode=c-shared", "-o"])
        .arg(out_dir.join(lib_name))
        .arg("github.com/carlos7ags/folio/export")
        .env("CGO_ENABLED", "1")   // ← NO CC=cl on Windows (see Challenges)
        .status().expect("go build failed");

    // 2. Generate Rust bindings from the cgo-produced header
    bindgen::Builder::default()
        .header(out_dir.join("folio.h").to_str().unwrap())
        .generate().unwrap()
        .write_to_file(out_dir.join("bindings.rs")).unwrap();

    // 3. Emit link directives
    println!("cargo:rustc-link-search=native={}", out_dir.display());
    if target_os == "windows" {
        ensure_import_lib(&out_dir);  // generate folio.lib (see Challenges)
        println!("cargo:rustc-link-arg={}", out_dir.join("folio.lib").display());
    } else {
        println!("cargo:rustc-link-lib=dylib=folio");
        println!("cargo:rustc-link-arg=-Wl,-rpath,$ORIGIN");
    }
}
```

### Thread safety — FOLIO_LOCK

Go C-ABI libraries are typically not thread-safe. Serialise every FFI call:

```rust
// src/html.rs
static FOLIO_LOCK: Mutex<()> = Mutex::new(());

pub fn convert(...) -> PyResult<()> {
    let _lock = FOLIO_LOCK.lock().unwrap();
    let doc = Document::new(page_size)?;        // passes lock implicitly
    check(unsafe { folio_set_margins(...) }, &_lock)?;
    // ...
}
```

### RAII document handle

```rust
// src/document.rs
pub struct Document(pub(crate) u64);

impl Document {
    pub(crate) fn new(page_size: &str) -> PyResult<Self> {
        let handle = unsafe { /* folio_document_new_a4() etc */ };
        if handle == 0 {
            return Err(PyRuntimeError::new_err("folio: null handle"));
        }
        Ok(Document(handle))
    }
}

impl Drop for Document {
    fn drop(&mut self) { unsafe { folio_document_free(self.0); } }
}
```

### Pythonic public API

Never expose `pkg._ext` to users. Re-export from `__init__.py`:

```python
# python/gofolio/__init__.py
from gofolio._gofolio import convert_html_to_pdf  # noqa: E402
__all__ = ["convert_html_to_pdf", "__version__"]
```

Users write `from gofolio import convert_html_to_pdf`, not `from gofolio._gofolio import ...`.

---

## Challenges and Fixes

| Challenge | Root Cause | Fix |
|---|---|---|
| `cl: invalid numeric argument '/Werror'` | CGO passes GCC-style flags; MSVC (`cl.exe`) rejects them | **Remove `CC=cl`** — CGO must use MinGW `gcc`, not MSVC |
| `LNK1181: cannot open input file 'folio.lib'` | MinGW CGO produces `folio.dll` but no MSVC import library | Generate via `llvm-dlltool` → `lib.exe` fallback (see `ensure_import_lib` below); activate `lib.exe` with `ilammy/msvc-dev-cmd@v1` in CI |
| `folio.dll` not found at Python import time | DLL not on Windows DLL search path | Copy DLL to package dir in `build.rs`; call `os.add_dll_directory` in `__init__.py`; run `delvewheel repair` in CI to bundle transitive DLLs |
| Crash / silent wrong results under concurrency | Go library is not thread-safe | `static Mutex<()>` — hold lock across every FFI call sequence |
| Panic on null handle | `folio_document_new_*` returns `0` on failure | Validate in `Document::new()`, return `PyErr` if `handle == 0` |
| `invalid-publisher` OIDC error on PyPI publish | OIDC token's `environment` claim absent | Add `environment: pypi` to the publish job; must exactly match the Environment name in PyPI trusted publisher settings |
| `file-name-reuse` error after partial upload | PyPI permanently rejects re-upload of same filename | Bump version; add `skip-existing: true` to `pypa/gh-action-pypi-publish` |
| `FileSystem::D:\...` error in delvewheel | PowerShell `Split-Path` on `FileInfo` returns provider path | Use `.DirectoryName` property: `$dllDir = $dllFile.DirectoryName` |

---

## Windows Import Library Generation

CGO with MinGW produces `folio.dll` but Rust's linker on Windows needs `folio.lib`. Generate it in `build.rs`:

```rust
#[cfg(target_os = "windows")]
fn ensure_import_lib(out_dir: &Path) {
    let dll = out_dir.join("folio.dll");
    let lib = out_dir.join("folio.lib");

    // Try llvm-dlltool first (available without MSVC)
    if Command::new("llvm-dlltool")
        .args(["-m", "i386:x86-64", "-D", "folio.dll", "-l"])
        .arg(&lib)
        .current_dir(out_dir)
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
    {
        return;
    }

    // Fall back to MSVC lib.exe (requires ilammy/msvc-dev-cmd in CI)
    let def_path = out_dir.join("folio.def");
    write_def_from_header(out_dir, &def_path); // parse folio.h for EXPORT symbols
    Command::new("lib.exe")
        .args(["/DEF:", "/OUT:", "/MACHINE:X64"])
        // ... pass paths
        .status().expect("lib.exe failed");
}
```

CI must activate MSVC before the build step:

```yaml
- name: Set up MSVC developer environment (Windows only)
  if: runner.os == 'Windows'
  uses: ilammy/msvc-dev-cmd@v1
```

---

## Windows DLL Runtime Loading

```python
# python/gofolio/__init__.py
import os, sys

if sys.platform == "win32":
    _pkg_dir = os.path.dirname(os.path.abspath(__file__))
    if hasattr(os, "add_dll_directory"):   # Python 3.8+
        os.add_dll_directory(_pkg_dir)
```

And in CI, repair the wheel so transitive DLLs are bundled:

```yaml
- name: Repair wheel (Windows only)
  if: runner.os == 'Windows'
  shell: pwsh
  run: |
    $wheel  = (Get-ChildItem target\wheels\*.whl | Select-Object -First 1).FullName
    $dllFile = Get-ChildItem -Recurse -Path target\release\build -Filter folio.dll |
               Select-Object -First 1
    $dllDir  = $dllFile.DirectoryName   # ← .DirectoryName, NOT | Split-Path
    delvewheel repair $wheel --wheel-dir target\wheels\ --add-path $dllDir
    Remove-Item $wheel
```

---

## CI Matrix (maturin + PyPI OIDC)

```yaml
jobs:
  build:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
    steps:
      - uses: actions/setup-go@v5
      - uses: dtolnay/rust-toolchain@stable
      - run: pip install maturin
      - if: runner.os == 'Linux'
        run: sudo apt-get install -y patchelf
      - if: runner.os == 'Windows'
        run: pip install delvewheel
      - if: runner.os == 'Windows'
        uses: ilammy/msvc-dev-cmd@v1        # puts lib.exe on PATH
      - run: maturin build --release --out target/wheels/
      # ... delvewheel repair on Windows ...

  publish:
    needs: build
    environment: pypi                       # MUST match PyPI trusted publisher
    permissions:
      id-token: write                       # required for OIDC
    steps:
      - uses: pypa/gh-action-pypi-publish@release/v1
        with:
          packages-dir: dist/
          skip-existing: true
```

---

## Quick Reference

| Goal | Key |
|---|---|
| Compile Go → shared lib | `go build -buildmode=c-shared` |
| Generate FFI bindings | `bindgen` in `build.rs` |
| Build wheel | `maturin build --release` |
| Dev install | `maturin develop` |
| Windows import lib | `llvm-dlltool` or `lib.exe /DEF:` |
| Activate `lib.exe` in CI | `ilammy/msvc-dev-cmd@v1` |
| Bundle DLLs in wheel | `delvewheel repair --add-path <dll_dir>` |
| Runtime DLL loading | `os.add_dll_directory(<pkg_dir>)` |
| Thread safety | `static Mutex<()>` held across FFI call sequence |
| PyPI OIDC auth | `environment: pypi` + `id-token: write` on publish job |

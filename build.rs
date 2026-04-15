use std::env;
use std::path::PathBuf;
use std::process::Command;

/// Locate the `go` binary, extending PATH with common install locations if needed.
fn find_go() -> String {
    // Try standard PATH first
    if Command::new("go").arg("version").output().is_ok() {
        return "go".to_string();
    }
    // Common non-PATH Go install locations (Linux / macOS)
    let candidates = [
        "/usr/local/go/bin/go",
        "/usr/bin/go",
        "/snap/bin/go",
    ];
    for path in candidates {
        if std::path::Path::new(path).exists() {
            return path.to_string();
        }
    }
    panic!("Could not find `go` binary — please install Go and ensure it is on PATH");
}

/// On Windows, Go with MinGW/GCC CGO produces `folio.dll` but not `folio.lib`
/// (the MSVC import library required by `link.exe`). This function generates
/// `folio.lib` from the DLL using `llvm-dlltool`, which ships with every LLVM /
/// Visual Studio installation and is on PATH on GitHub Actions Windows runners.
#[cfg(target_os = "windows")]
fn ensure_import_lib(out_dir: &std::path::Path) {
    let lib_path = out_dir.join("folio.lib");
    if lib_path.exists() {
        // Go already produced it (e.g. when CC=cl / MSVC was used) — nothing to do.
        return;
    }

    let dll_path = out_dir.join("folio.dll");
    assert!(dll_path.exists(), "folio.dll not found in OUT_DIR after go build");

    // llvm-dlltool ships with LLVM and is available on GitHub Actions runners.
    // `-m i386:x86-64` targets 64-bit Windows; `-D` names the DLL; `-l` is the output .lib.
    let status = Command::new("llvm-dlltool")
        .args([
            "-m", "i386:x86-64",
            "-D", dll_path.to_str().unwrap(),
            "-l", lib_path.to_str().unwrap(),
        ])
        .status();

    match status {
        Ok(s) if s.success() => return,
        Ok(_) => eprintln!("cargo:warning=llvm-dlltool exited with non-zero status; trying lib.exe"),
        Err(_) => eprintln!("cargo:warning=llvm-dlltool not found; trying lib.exe"),
    }

    // Fallback: use MSVC lib.exe. We need a .def file with the exported symbols.
    // Generate it by reading the header produced by cgo.
    let def_path = out_dir.join("folio.def");
    let header_path = out_dir.join("folio.h");
    let header = std::fs::read_to_string(&header_path)
        .expect("folio.h not found — go build should have generated it");

    // Extract `extern ... TYPE NAME(` declarations to get export names.
    // This is a best-effort parse of the cgo-generated header.
    let mut exports = vec!["EXPORTS".to_string()];
    for line in header.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with("extern") && trimmed.contains('(') {
            // e.g.: `extern GoUint64 folio_document_new_a4();`
            if let Some(name) = trimmed
                .split_whitespace()
                .nth(2)
                .and_then(|s| s.split('(').next())
            {
                exports.push(name.to_string());
            }
        }
    }
    std::fs::write(&def_path, exports.join("\n"))
        .expect("failed to write folio.def");

    let status = Command::new("lib.exe")
        .args([
            &format!("/DEF:{}", def_path.display()),
            &format!("/OUT:{}", lib_path.display()),
            "/MACHINE:X64",
        ])
        .status()
        .expect("lib.exe not found — install Visual Studio Build Tools");

    assert!(status.success(), "lib.exe failed to generate folio.lib");
}

fn main() {
    println!("cargo:rerun-if-changed=build.rs");

    let out_dir = PathBuf::from(env::var("OUT_DIR").unwrap());
    let target_os = env::var("CARGO_CFG_TARGET_OS").unwrap();

    let lib_name = match target_os.as_str() {
        "windows" => "folio.dll",
        "macos" | "darwin" => "libfolio.dylib",
        _ => "libfolio.so",
    };

    let lib_path = out_dir.join(lib_name);
    let go_bin = find_go();

    // Determine Go binary directory so we can set GOROOT / PATH explicitly
    let go_bin_path = PathBuf::from(&go_bin);
    let go_bin_dir = go_bin_path
        .parent()
        .map(|p| p.to_path_buf())
        .unwrap_or_else(|| PathBuf::from("/usr/local/go/bin"));

    // Build an extended PATH that includes the Go bin directory
    let original_path = env::var("PATH").unwrap_or_default();
    let path_sep = if target_os == "windows" { ";" } else { ":" };
    let extended_path = format!("{}{}{}", go_bin_dir.display(), path_sep, original_path);

    // Create a scratch Go module directory inside OUT_DIR for fetching/building folio.
    let go_mod_dir = out_dir.join("folio_go_module");
    std::fs::create_dir_all(&go_mod_dir).expect("failed to create go module scratch dir");

    let go_mod_content = "module folio_build\n\ngo 1.21\n";
    std::fs::write(go_mod_dir.join("go.mod"), go_mod_content)
        .expect("failed to write go.mod");

    // go get: fetch the folio module (updates go.mod / go.sum in scratch dir)
    let get_status = Command::new(&go_bin)
        .args(["get", "github.com/carlos7ags/folio/export"])
        .current_dir(&go_mod_dir)
        .env("PATH", &extended_path)
        .env("GOPATH", out_dir.join("gopath").to_str().unwrap())
        .status()
        .expect("Failed to run `go get` — is Go installed?");

    if !get_status.success() {
        // Non-fatal: go get may fail if network is unavailable but module is cached
        eprintln!("cargo:warning=`go get` did not succeed (network may be unavailable); trying cached module");
    }

    // On Windows, set CC=cl so CGO uses MSVC and produces folio.lib natively.
    // This is the preferred path; ensure_import_lib() is a fallback for when
    // MSVC is not the active CGO compiler (e.g. MinGW / GCC).
    let mut go_build = Command::new(&go_bin);
    go_build
        .args([
            "build",
            "-buildmode=c-shared",
            "-o",
            lib_path.to_str().unwrap(),
            "github.com/carlos7ags/folio/export",
        ])
        .current_dir(&go_mod_dir)
        .env("PATH", &extended_path)
        .env("GOPATH", out_dir.join("gopath").to_str().unwrap());

    if target_os == "windows" {
        // CGO_ENABLED=1 is required for buildmode=c-shared.
        // Go will use MinGW (gcc) on GitHub Actions Windows runners since cl.exe
        // is not on PATH without the MSVC Developer Command Prompt.
        // ensure_import_lib() below generates folio.lib from the DLL afterward.
        go_build.env("CGO_ENABLED", "1");
    }

    let status = go_build
        .status()
        .expect("Failed to run `go build` — is Go installed?");

    assert!(status.success(), "go build -buildmode=c-shared failed");

    // On Windows: ensure folio.lib exists for the linker, then copy folio.dll into the
    // Python package directory so maturin bundles it in the wheel and it is findable
    // at runtime (via os.add_dll_directory in __init__.py).
    if target_os == "windows" {
        #[cfg(target_os = "windows")]
        ensure_import_lib(&out_dir);

        // Copy folio.dll to python/gofolio/ so maturin includes it in the wheel.
        // __init__.py adds this directory to the DLL search path on import.
        let pkg_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap())
            .join("python")
            .join("gofolio");
        std::fs::create_dir_all(&pkg_dir).ok();
        let dst = pkg_dir.join("folio.dll");
        std::fs::copy(out_dir.join("folio.dll"), &dst)
            .expect("failed to copy folio.dll into python/gofolio/");
        println!("cargo:warning=Copied folio.dll to {}", dst.display());
    }

    // The header is generated by `go build -buildmode=c-shared` alongside the library.
    let lib_stem = lib_name
        .trim_end_matches(".so")
        .trim_end_matches(".dylib")
        .trim_end_matches(".dll");
    let header_path = out_dir.join(format!("{lib_stem}.h"));

    // Generate Rust bindings from the C header produced by cgo
    let bindings = bindgen::Builder::default()
        .header(header_path.to_str().unwrap())
        .parse_callbacks(Box::new(bindgen::CargoCallbacks::new()))
        .generate()
        .expect("Unable to generate bindings from folio.h");

    bindings
        .write_to_file(out_dir.join("bindings.rs"))
        .expect("Couldn't write bindings.rs");

    println!("cargo:rustc-link-search=native={}", out_dir.display());

    if target_os == "windows" {
        // Pass the full path to folio.lib directly — MSVC link.exe does not
        // reliably pick it up through cargo:rustc-link-search alone.
        let lib_file = out_dir.join("folio.lib");
        println!("cargo:rustc-link-arg={}", lib_file.display());
    } else {
        println!("cargo:rustc-link-lib=dylib=folio");
        // Embed OUT_DIR as rpath so the dynamic linker finds libfolio at runtime
        // without requiring LD_LIBRARY_PATH / DYLD_LIBRARY_PATH to be set.
        println!("cargo:rustc-link-arg=-Wl,-rpath,{}", out_dir.display());
    }
}

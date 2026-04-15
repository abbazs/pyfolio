"""gofolio — Python wrapper for the folio HTML-to-PDF library."""

import os
import sys

if sys.platform == "win32":
    # folio.dll is bundled in this package directory.
    # Register it so Windows' DLL loader can find it when _gofolio.pyd is imported.
    # os.add_dll_directory was added in Python 3.8 (PEP 628).
    _pkg_dir = os.path.dirname(os.path.abspath(__file__))
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(_pkg_dir)

__version__ = "0.1.1"

__all__ = ["__version__"]

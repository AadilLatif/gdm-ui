"""Test-time import path bootstrap for workspace packages."""

from pathlib import Path
import sys

CORE_PACKAGE_DIR = Path(__file__).resolve().parent.parent / "fgc_core"
if str(CORE_PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_PACKAGE_DIR))

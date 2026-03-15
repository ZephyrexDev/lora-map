"""Shared pytest configuration and fixtures for all backend tests.

Sets SPLAT_PATH and DB_PATH environment variables before any app modules
are imported, so the real SPLAT! binaries are used (no mocks) and the
database points to a temporary file.
"""

import os
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Environment setup — must happen before any app imports
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Point to the locally-built SPLAT! binaries
_splat_bin_dir = _PROJECT_ROOT / "splat" / "bin"
if _splat_bin_dir.is_dir():
    os.environ.setdefault("SPLAT_PATH", str(_splat_bin_dir))

# Use a temporary database for tests
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db_path = _tmp_db.name
_tmp_db.close()
os.environ["DB_PATH"] = _tmp_db_path

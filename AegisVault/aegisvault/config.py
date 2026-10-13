"""Application paths & constants."""
from __future__ import annotations
import os
import sys
from pathlib import Path

APP_NAME = "AegisVault"


def _app_dir() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    p = base / APP_NAME
    p.mkdir(parents=True, exist_ok=True)
    # Hide on Windows
    if sys.platform.startswith("win"):
        try:
            import ctypes
            FILE_ATTRIBUTE_HIDDEN = 0x02
            ctypes.windll.kernel32.SetFileAttributesW(str(p), FILE_ATTRIBUTE_HIDDEN)
        except Exception:
            pass
    return p


APP_DIR = _app_dir()
BLOB_DIR = APP_DIR / "blobs"
BLOB_DIR.mkdir(exist_ok=True)
DB_PATH = APP_DIR / "vault.db"

# Crypto
PBKDF2_ITERS = 200_000
KEY_LEN = 32           # AES-256
SALT_LEN = 16
GCM_IV_LEN = 12

# Security
MAX_FAILED = 5
LOCKOUT_STEPS_SEC = [30, 60, 300, 900, 3600]
AUTOLOCK_SECONDS = 300  # 5 minutes

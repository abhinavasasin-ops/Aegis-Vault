# AegisVault

A modern, dark-themed desktop cryptographic vault for Windows. Built with Python, CustomTkinter and PyCryptodome.

AegisVault stores your sensitive files and notes locally inside an encrypted vault protected by a master password. All payloads are encrypted with AES-256-GCM using a PBKDF2-derived key. The master password itself is never stored — only a SHA-256 hash with a per-user salt is kept for verification.

## Features

- Master password authentication (SHA-256 + salt, never stored in plaintext)
- AES-256-GCM encryption for files and notes (random 12-byte IV per item)
- PBKDF2-HMAC-SHA256 key derivation (200k iterations, 16-byte salt)
- Drag-and-drop file ingestion (via `tkinterdnd2`)
- Encrypted text notes editor
- Folder / category organization, tagging, favorites
- Search across vault items
- Auto-lock after configurable inactivity (default 5 min)
- File integrity verification using SHA-256 hashes
- Brute-force protection: exponential lockout after 5 failed attempts
- Secure wipe of temporary decrypted files (multi-pass overwrite)
- Vault export / import (encrypted archive)
- Backup recovery system
- Password strength checker
- Audit log of all sensitive actions
- Futuristic dark cybersecurity UI with animated lock screen
- Sidebar navigation, dashboard, metadata display

## Folder Structure

```
AegisVault/
├── main.py                  # Entry point
├── requirements.txt
├── README.md
├── build_windows.md         # PyInstaller build instructions
└── aegisvault/
    ├── __init__.py
    ├── config.py            # Paths & constants
    ├── core/
    │   ├── __init__.py
    │   ├── crypto.py        # AES-256-GCM + PBKDF2 + SHA-256
    │   ├── database.py      # SQLite schema & DAO
    │   ├── vault.py         # High-level vault operations
    │   ├── auth.py          # Master password + brute-force guard
    │   ├── secure_delete.py # Multi-pass file wipe
    │   └── strength.py      # Password strength checker
    └── ui/
        ├── __init__.py
        ├── app.py           # Root CTk application & router
        ├── lock_screen.py   # Animated login/setup screen
        ├── dashboard.py     # Main vault dashboard
        ├── sidebar.py
        ├── files_view.py
        ├── notes_view.py
        ├── settings_view.py
        └── widgets.py       # Shared themed widgets
```

## Database Schema (SQLite)

Stored at `%APPDATA%/AegisVault/vault.db` (hidden on Windows).

```sql
CREATE TABLE users (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    username     TEXT UNIQUE NOT NULL,
    pwd_hash     TEXT NOT NULL,        -- SHA-256(salt || password)
    pwd_salt     TEXT NOT NULL,        -- hex, 16 bytes
    kdf_salt     TEXT NOT NULL,        -- hex, 16 bytes (PBKDF2)
    created_at   TEXT NOT NULL,
    failed_count INTEGER DEFAULT 0,
    locked_until TEXT
);

CREATE TABLE vault_files (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    name          TEXT NOT NULL,
    folder        TEXT DEFAULT 'General',
    tags          TEXT DEFAULT '',
    favorite      INTEGER DEFAULT 0,
    size_bytes    INTEGER NOT NULL,
    sha256        TEXT NOT NULL,       -- of plaintext, integrity check
    iv            TEXT NOT NULL,       -- hex, 12 bytes (GCM nonce)
    storage_path  TEXT NOT NULL,       -- ciphertext blob path
    created_at    TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE encrypted_notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    title       TEXT NOT NULL,
    folder      TEXT DEFAULT 'General',
    tags        TEXT DEFAULT '',
    favorite    INTEGER DEFAULT 0,
    iv          TEXT NOT NULL,
    ciphertext  BLOB NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE audit_logs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER,
    action    TEXT NOT NULL,
    detail    TEXT,
    ts        TEXT NOT NULL
);
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python main.py
```

On first launch you will be prompted to create a master account. **There is no recovery if you forget the master password** — the encryption key is derived from it.

See `build_windows.md` for packaging into a single Windows `.exe`.

## Security Notes

- Cipher: AES-256-GCM (authenticated, prevents tampering)
- KDF: PBKDF2-HMAC-SHA256, 200,000 iterations, 16-byte random salt
- Password storage: SHA-256(salt || password) — verification only, never used as encryption key
- IVs: cryptographically random 12 bytes per item, never reused
- Encrypted blobs live in a hidden app directory; only ciphertext touches disk
- Temporary decrypted exports are multi-pass overwritten before deletion
- Brute-force guard: 5 failures → exponential lockout (30s, 1m, 5m, 15m, 1h)

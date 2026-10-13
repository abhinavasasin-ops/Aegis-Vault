"""High-level vault operations: file/note encryption + storage."""
from __future__ import annotations
import json
import os
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Optional

from . import crypto
from .database import Database
from .secure_delete import secure_wipe
from ..config import BLOB_DIR


class Vault:
    def __init__(self, db: Database, key: bytes, user_id: int):
        self.db = db
        self.key = key
        self.user_id = user_id

    # --- files
    def add_file(self, src_path: str, folder: str = "General", tags: str = "") -> int:
        src = Path(src_path)
        data = src.read_bytes()
        digest = crypto.sha256_bytes(data)
        iv, blob = crypto.encrypt(self.key, data)
        storage = BLOB_DIR / f"{uuid.uuid4().hex}.bin"
        storage.write_bytes(blob)
        fid = self.db.add_file(
            user_id=self.user_id,
            name=src.name,
            folder=folder or "General",
            tags=tags,
            favorite=0,
            size_bytes=len(data),
            sha256=digest,
            iv=iv.hex(),
            storage_path=str(storage),
        )
        self.db.log(self.user_id, "file_add", src.name)
        return fid

    def export_file(self, file_id: int, dest_path: str) -> bool:
        row = self.db.get_file(file_id)
        if not row:
            return False
        blob = Path(row["storage_path"]).read_bytes()
        plaintext = crypto.decrypt(self.key, bytes.fromhex(row["iv"]), blob)
        if crypto.sha256_bytes(plaintext) != row["sha256"]:
            raise ValueError("Integrity check failed")
        Path(dest_path).write_bytes(plaintext)
        self.db.log(self.user_id, "file_export", row["name"])
        return True

    def verify_file(self, file_id: int) -> bool:
        row = self.db.get_file(file_id)
        if not row:
            return False
        blob = Path(row["storage_path"]).read_bytes()
        plaintext = crypto.decrypt(self.key, bytes.fromhex(row["iv"]), blob)
        ok = crypto.sha256_bytes(plaintext) == row["sha256"]
        self.db.log(self.user_id, "file_verify", f"{row['name']}={ok}")
        return ok

    def delete_file(self, file_id: int) -> None:
        row = self.db.get_file(file_id)
        if not row:
            return
        secure_wipe(row["storage_path"])
        self.db.delete_file(file_id)
        self.db.log(self.user_id, "file_delete", row["name"])

    # --- notes
    def save_note(self, title: str, body: str, folder: str = "General",
                  tags: str = "", note_id: Optional[int] = None) -> int:
        iv, blob = crypto.encrypt(self.key, body.encode("utf-8"))
        if note_id:
            self.db.update_note(note_id, title, iv.hex(), blob, tags, folder)
            self.db.log(self.user_id, "note_update", title)
            return note_id
        nid = self.db.add_note(self.user_id, title, folder, tags, iv.hex(), blob)
        self.db.log(self.user_id, "note_add", title)
        return nid

    def open_note(self, note_id: int) -> Optional[str]:
        row = self.db.get_note(note_id)
        if not row:
            return None
        plaintext = crypto.decrypt(self.key, bytes.fromhex(row["iv"]), row["ciphertext"])
        return plaintext.decode("utf-8")

    def delete_note(self, note_id: int) -> None:
        row = self.db.get_note(note_id)
        if not row:
            return
        self.db.delete_note(note_id)
        self.db.log(self.user_id, "note_delete", row["title"])

    # --- backup / export & import
    def export_vault(self, dest_zip: str) -> None:
        """Export the encrypted DB + blobs as-is (still requires master pw to open)."""
        with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(self.db.path, arcname="vault.db")
            for blob in BLOB_DIR.glob("*.bin"):
                z.write(blob, arcname=f"blobs/{blob.name}")
        self.db.log(self.user_id, "vault_export", dest_zip)

    def import_vault(self, src_zip: str, target_dir: Path) -> None:
        with zipfile.ZipFile(src_zip, "r") as z:
            z.extractall(target_dir)
        self.db.log(self.user_id, "vault_import", src_zip)

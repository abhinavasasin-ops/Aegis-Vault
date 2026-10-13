"""SQLite layer for AegisVault."""
from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from ..config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    username     TEXT UNIQUE NOT NULL,
    pwd_hash     TEXT NOT NULL,
    pwd_salt     TEXT NOT NULL,
    kdf_salt     TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    failed_count INTEGER DEFAULT 0,
    locked_until TEXT
);
CREATE TABLE IF NOT EXISTS vault_files (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    name          TEXT NOT NULL,
    folder        TEXT DEFAULT 'General',
    tags          TEXT DEFAULT '',
    favorite      INTEGER DEFAULT 0,
    size_bytes    INTEGER NOT NULL,
    sha256        TEXT NOT NULL,
    iv            TEXT NOT NULL,
    storage_path  TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS vault_folders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    UNIQUE(user_id, name),
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS user_settings (
    user_id INTEGER NOT NULL,
    key     TEXT NOT NULL,
    value   TEXT NOT NULL,
    PRIMARY KEY(user_id, key),
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS encrypted_notes (
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
CREATE TABLE IF NOT EXISTS audit_logs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER,
    action    TEXT NOT NULL,
    detail    TEXT,
    ts        TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path = DB_PATH):
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    @contextmanager
    def cursor(self):
        cur = self.conn.cursor()
        try:
            yield cur
            self.conn.commit()
        finally:
            cur.close()

    # -- users
    def get_user(self, username: str) -> Optional[sqlite3.Row]:
        with self.cursor() as c:
            c.execute("SELECT * FROM users WHERE username=?", (username,))
            return c.fetchone()

    def any_user(self) -> Optional[sqlite3.Row]:
        with self.cursor() as c:
            c.execute("SELECT * FROM users LIMIT 1")
            return c.fetchone()

    def create_user(self, username: str, pwd_hash: str, pwd_salt_hex: str, kdf_salt_hex: str) -> int:
        with self.cursor() as c:
            c.execute(
                "INSERT INTO users(username,pwd_hash,pwd_salt,kdf_salt,created_at) VALUES(?,?,?,?,?)",
                (username, pwd_hash, pwd_salt_hex, kdf_salt_hex, now()),
            )
            return c.lastrowid

    def update_user_lock(self, user_id: int, failed_count: int, locked_until: Optional[str]) -> None:
        with self.cursor() as c:
            c.execute(
                "UPDATE users SET failed_count=?, locked_until=? WHERE id=?",
                (failed_count, locked_until, user_id),
            )

    # -- settings
    def get_user_setting(self, user_id: int, key: str, default: str = "") -> str:
        with self.cursor() as c:
            c.execute(
                "SELECT value FROM user_settings WHERE user_id=? AND key=?",
                (user_id, key),
            )
            row = c.fetchone()
        return row["value"] if row else default

    def set_user_setting(self, user_id: int, key: str, value: str) -> None:
        with self.cursor() as c:
            c.execute(
                """
                INSERT INTO user_settings(user_id,key,value) VALUES(?,?,?)
                ON CONFLICT(user_id, key) DO UPDATE SET value=excluded.value
                """,
                (user_id, key, value),
            )

    # -- audit
    def log(self, user_id: Optional[int], action: str, detail: str = "") -> None:
        with self.cursor() as c:
            c.execute(
                "INSERT INTO audit_logs(user_id,action,detail,ts) VALUES(?,?,?,?)",
                (user_id, action, detail, now()),
            )

    def recent_logs(self, limit: int = 50) -> list[sqlite3.Row]:
        with self.cursor() as c:
            c.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
            return c.fetchall()

    # -- files
    def ensure_folder(self, user_id: int, name: str) -> str:
        folder = (name or "General").strip() or "General"
        with self.cursor() as c:
            c.execute(
                "INSERT OR IGNORE INTO vault_folders(user_id,name,created_at) VALUES(?,?,?)",
                (user_id, folder, now()),
            )
        return folder

    def list_file_folders(self, user_id: int) -> list[str]:
        with self.cursor() as c:
            c.execute(
                """
                SELECT name FROM vault_folders WHERE user_id=?
                UNION
                SELECT COALESCE(NULLIF(TRIM(folder), ''), 'General') AS name
                FROM vault_files WHERE user_id=?
                ORDER BY name COLLATE NOCASE
                """,
                (user_id, user_id),
            )
            folders = [row["name"] for row in c.fetchall()]
        if "General" in folders:
            folders.remove("General")
        folders.insert(0, "General")
        return folders

    def file_folder_counts(self, user_id: int) -> dict[str, int]:
        counts = {folder: 0 for folder in self.list_file_folders(user_id)}
        with self.cursor() as c:
            c.execute(
                """
                SELECT COALESCE(NULLIF(TRIM(folder), ''), 'General') AS folder, COUNT(*) AS count
                FROM vault_files
                WHERE user_id=?
                GROUP BY COALESCE(NULLIF(TRIM(folder), ''), 'General')
                """,
                (user_id,),
            )
            for row in c.fetchall():
                counts[row["folder"]] = row["count"]
        return counts

    def add_file(self, **kw) -> int:
        folder = self.ensure_folder(kw["user_id"], kw.get("folder") or "General")
        with self.cursor() as c:
            c.execute(
                """INSERT INTO vault_files
                (user_id,name,folder,tags,favorite,size_bytes,sha256,iv,storage_path,created_at)
                VALUES(:user_id,:name,:folder,:tags,:favorite,:size_bytes,:sha256,:iv,:storage_path,:created_at)""",
                {**kw, "folder": folder, "created_at": now()},
            )
            return c.lastrowid

    def list_files(self, user_id: int, search: str = "", folder: Optional[str] = None,
                   favorites_only: bool = False) -> list[sqlite3.Row]:
        q = "SELECT * FROM vault_files WHERE user_id=?"
        args: list = [user_id]
        if search:
            q += " AND (name LIKE ? OR tags LIKE ?)"
            args += [f"%{search}%", f"%{search}%"]
        if folder:
            q += " AND folder=?"
            args.append(folder)
        if favorites_only:
            q += " AND favorite=1"
        q += " ORDER BY favorite DESC, created_at DESC"
        with self.cursor() as c:
            c.execute(q, args)
            return c.fetchall()

    def get_file(self, fid: int) -> Optional[sqlite3.Row]:
        with self.cursor() as c:
            c.execute("SELECT * FROM vault_files WHERE id=?", (fid,))
            return c.fetchone()

    def delete_file(self, fid: int) -> None:
        with self.cursor() as c:
            c.execute("DELETE FROM vault_files WHERE id=?", (fid,))

    def move_file_to_folder(self, fid: int, user_id: int, folder: str) -> None:
        target = self.ensure_folder(user_id, folder)
        with self.cursor() as c:
            c.execute(
                "UPDATE vault_files SET folder=? WHERE id=? AND user_id=?",
                (target, fid, user_id),
            )

    def rename_file_folder(self, user_id: int, old_name: str, new_name: str) -> str:
        old = (old_name or "General").strip() or "General"
        new = (new_name or "General").strip() or "General"
        if old == new:
            return new
        self.ensure_folder(user_id, new)
        with self.cursor() as c:
            c.execute(
                "UPDATE vault_files SET folder=? WHERE user_id=? AND folder=?",
                (new, user_id, old),
            )
            c.execute(
                "DELETE FROM vault_folders WHERE user_id=? AND name=?",
                (user_id, old),
            )
        return new

    def delete_file_folder(self, user_id: int, name: str) -> None:
        folder = (name or "General").strip() or "General"
        with self.cursor() as c:
            c.execute(
                "SELECT COUNT(*) AS count FROM vault_files WHERE user_id=? AND folder=?",
                (user_id, folder),
            )
            if c.fetchone()["count"]:
                raise ValueError("Move or delete the files in this folder first.")
            c.execute(
                "DELETE FROM vault_folders WHERE user_id=? AND name=?",
                (user_id, folder),
            )

    def toggle_favorite_file(self, fid: int) -> None:
        with self.cursor() as c:
            c.execute("UPDATE vault_files SET favorite = 1 - favorite WHERE id=?", (fid,))

    # -- notes
    def add_note(self, user_id: int, title: str, folder: str, tags: str, iv: str, ciphertext: bytes) -> int:
        with self.cursor() as c:
            c.execute(
                """INSERT INTO encrypted_notes(user_id,title,folder,tags,iv,ciphertext,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?)""",
                (user_id, title, folder, tags, iv, ciphertext, now(), now()),
            )
            return c.lastrowid

    def update_note(self, nid: int, title: str, iv: str, ciphertext: bytes, tags: str = "", folder: str = "General") -> None:
        with self.cursor() as c:
            c.execute(
                """UPDATE encrypted_notes
                SET title=?, iv=?, ciphertext=?, tags=?, folder=?, updated_at=? WHERE id=?""",
                (title, iv, ciphertext, tags, folder, now(), nid),
            )

    def list_notes(self, user_id: int, search: str = "", favorites_only: bool = False) -> list[sqlite3.Row]:
        q = "SELECT * FROM encrypted_notes WHERE user_id=?"
        args: list = [user_id]
        if search:
            q += " AND (title LIKE ? OR tags LIKE ?)"
            args += [f"%{search}%", f"%{search}%"]
        if favorites_only:
            q += " AND favorite=1"
        q += " ORDER BY favorite DESC, updated_at DESC"
        with self.cursor() as c:
            c.execute(q, args)
            return c.fetchall()

    def get_note(self, nid: int) -> Optional[sqlite3.Row]:
        with self.cursor() as c:
            c.execute("SELECT * FROM encrypted_notes WHERE id=?", (nid,))
            return c.fetchone()

    def delete_note(self, nid: int) -> None:
        with self.cursor() as c:
            c.execute("DELETE FROM encrypted_notes WHERE id=?", (nid,))

    def toggle_favorite_note(self, nid: int) -> None:
        with self.cursor() as c:
            c.execute("UPDATE encrypted_notes SET favorite = 1 - favorite WHERE id=?", (nid,))

"""Authentication, brute-force protection, session key holder."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from . import crypto
from .database import Database
from ..config import MAX_FAILED, LOCKOUT_STEPS_SEC


@dataclass
class Session:
    user_id: int
    username: str
    key: bytes  # AES-256 key derived via PBKDF2


class AuthError(Exception): ...
class LockedOut(AuthError):
    def __init__(self, until: datetime):
        super().__init__(f"Locked until {until.isoformat()}")
        self.until = until


class AuthManager:
    def __init__(self, db: Database):
        self.db = db

    # ---- registration
    def register(self, username: str, password: str) -> Session:
        if self.db.get_user(username):
            raise AuthError("User already exists")
        salt = crypto.new_salt()
        kdf_salt = crypto.new_salt()
        ph = crypto.hash_password(password, salt)
        uid = self.db.create_user(username, ph, salt.hex(), kdf_salt.hex())
        key = crypto.derive_key(password, kdf_salt)
        self.db.log(uid, "register", username)
        return Session(uid, username, key)

    # ---- login
    def login(self, username: str, password: str) -> Session:
        row = self.db.get_user(username)
        if not row:
            raise AuthError("Invalid credentials")

        if row["locked_until"]:
            until = datetime.fromisoformat(row["locked_until"])
            if datetime.utcnow() < until:
                raise LockedOut(until)

        salt = bytes.fromhex(row["pwd_salt"])
        if not crypto.verify_password(password, salt, row["pwd_hash"]):
            failed = (row["failed_count"] or 0) + 1
            locked_until: Optional[str] = None
            if failed >= MAX_FAILED:
                step = min(failed - MAX_FAILED, len(LOCKOUT_STEPS_SEC) - 1)
                seconds = LOCKOUT_STEPS_SEC[step]
                locked_until = (datetime.utcnow() + timedelta(seconds=seconds)).isoformat()
            self.db.update_user_lock(row["id"], failed, locked_until)
            self.db.log(row["id"], "login_failed", f"attempts={failed}")
            raise AuthError("Invalid credentials")

        # success — reset counters
        self.db.update_user_lock(row["id"], 0, None)
        kdf_salt = bytes.fromhex(row["kdf_salt"])
        key = crypto.derive_key(password, kdf_salt)
        self.db.log(row["id"], "login_success", username)
        return Session(row["id"], username, key)

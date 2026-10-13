"""Best-effort multi-pass file wipe."""
from __future__ import annotations
import os
from pathlib import Path
from Crypto.Random import get_random_bytes


def secure_wipe(path: str | os.PathLike, passes: int = 3) -> None:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return
    try:
        size = p.stat().st_size
        with open(p, "r+b", buffering=0) as f:
            for _ in range(passes):
                f.seek(0)
                remaining = size
                while remaining > 0:
                    chunk = min(1 << 20, remaining)
                    f.write(get_random_bytes(chunk))
                    remaining -= chunk
                f.flush()
                os.fsync(f.fileno())
            f.seek(0)
            f.write(b"\x00" * min(size, 1 << 20))
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        pass
    try:
        p.unlink()
    except Exception:
        pass

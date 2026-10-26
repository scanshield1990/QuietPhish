from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import List, Optional

from phishguard.util.text import registrable_domain

REPUTATION_SAFE = "safe"
REPUTATION_BAD = "bad"


class SenderReputationStore:
    """Tracks trusted (safe) and untrusted (bad) senders across scans.

    Trust is keyed by registrable domain (so whitelisting taxact.com covers
    every address at once) and optionally by exact address. Persisted to SQLite
    so it survives restarts. This is the foundation for keeping legitimate bulk
    mail out of the phishing verdict.
    """

    def __init__(self, db_path: str = "./reports/reputation.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            timeout=30
        )

        self._conn.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
         with self._lock:
             self._conn.executescript(
                 """
                 CREATE TABLE IF NOT EXISTS sender_reputation (
                     key TEXT PRIMARY KEY,
                     kind TEXT NOT NULL,
                     reputation TEXT NOT NULL,
                     note TEXT,
                     updated_at TEXT
                 );
                 """
             )
             self._conn.commit()

    def _key(self, email_or_domain: str) -> str:
        email_or_domain = (email_or_domain or "").strip().lower()
        if "@" in email_or_domain:
            return registrable_domain(email_or_domain) or email_or_domain
        return registrable_domain(email_or_domain) or email_or_domain

    def set_reputation(self, email_or_domain: str, reputation: str, note: str = "") -> None:
        if reputation not in (REPUTATION_SAFE, REPUTATION_BAD):
            raise ValueError("reputation must be 'safe' or 'bad'")

        import time
        key = self._key(email_or_domain)

        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO sender_reputation(key, kind, reputation, note, updated_at) VALUES (?, ?, ?, ?, ?)",
                (
                    key,
                    "domain" if "@" not in email_or_domain else "address",
                    reputation,
                    note,
                    time.strftime("%Y-%m-%d %H:%M:%S")
                )
            )
            self._conn.commit()

    def trust(self, email_or_domain: str, note: str = "") -> None:
        self.set_reputation(email_or_domain, REPUTATION_SAFE, note)

    def mark_bad(self, email_or_domain: str, note: str = "") -> None:
        self.set_reputation(email_or_domain, REPUTATION_BAD, note)

    def remove(self, email_or_domain: str) -> None:
        key = self._key(email_or_domain)

        with self._lock:
            self._conn.execute(
                "DELETE FROM sender_reputation WHERE key = ?",
                (key,)
            )
            self._conn.commit()

    def reputation_of(self, email_or_domain: str) -> Optional[str]:
        """Returns 'safe', 'bad', or None (unknown)."""
        email_or_domain = (email_or_domain or "").strip().lower()

        if not email_or_domain:
            return None

        with self._lock:
            if "@" in email_or_domain:
                cur = self._conn.execute(
                    "SELECT reputation FROM sender_reputation WHERE key = ? AND kind = 'address'",
                    (email_or_domain,)
                ).fetchone()

                if cur:
                    return cur["reputation"]

            domain = registrable_domain(email_or_domain) or email_or_domain

            cur = self._conn.execute(
                "SELECT reputation FROM sender_reputation WHERE key = ? AND kind = 'domain'",
                (domain,)
            ).fetchone()

            return cur["reputation"] if cur else None

    def all_safe(self, limit: int = 5000) -> List[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT key FROM sender_reputation WHERE reputation = ? ORDER BY updated_at DESC LIMIT ?",
                (REPUTATION_SAFE, limit)
            ).fetchall()

            return [r["key"] for r in rows]

    def stats(self) -> dict:
        with self._lock:
            safe = self._conn.execute(
                "SELECT COUNT(*) FROM sender_reputation WHERE reputation = ?",
                (REPUTATION_SAFE,)
            ).fetchone()[0]

            bad = self._conn.execute(
                "SELECT COUNT(*) FROM sender_reputation WHERE reputation = ?",
                (REPUTATION_BAD,)
            ).fetchone()[0]

            return {
                "safe": safe,
                "bad": bad,
                "total": safe + bad
            }

    def close(self) -> None:
        with self._lock:
            try:
                self._conn.close()
            except sqlite3.ProgrammingError:
                pass
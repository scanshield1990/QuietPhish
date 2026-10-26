from __future__ import annotations

import imaplib
import ssl
from typing import List, Tuple

from phishguard.config import Config


class MailFetcher:
    def __init__(self, config: Config):
        self.config = config
        self._conn = None

    def connect(self) -> None:
        host = self.config.imap_server
        port = self.config.imap_port or (993 if self.config.imap_use_ssl else 143)
        if not host or not self.config.imap_username or not self.config.imap_password:
            raise ValueError("IMAP server, username, and password must be configured")
        if not self.config.imap_use_ssl:
            raise ValueError("Plaintext IMAP is disabled for security; enable IMAP SSL")
        self._conn = imaplib.IMAP4_SSL(
            host, port, ssl_context=ssl.create_default_context(),
            timeout=self.config.imap_timeout,
        )
        sock = getattr(self._conn, "sock", None)
        if sock is not None:
            sock.settimeout(self.config.imap_timeout)
        # Some providers display app passwords in groups separated by spaces.
        password = self.config.imap_password.replace(" ", "")
        try:
            self._conn.login(self.config.imap_username, password)
            status, _ = self._conn.select(self.config.imap_mailbox or "INBOX")
            if status != "OK":
                raise RuntimeError("Unable to select the configured IMAP mailbox")
        except Exception:
            self.disconnect()
            raise

    def disconnect(self) -> None:
        if self._conn:
            try:
                self._conn.close()
                self._conn.logout()
            except Exception:
                pass
            self._conn = None

    def fetch_unseen(self, limit: int = 50) -> List[Tuple[str, bytes]]:
        return self._fetch("UNSEEN", limit)

    def fetch_recent(self, limit: int = 50) -> List[Tuple[str, bytes]]:
        return self._fetch("RECENT", limit)

    def fetch_all(self, limit: int = 1000) -> List[Tuple[str, bytes]]:
        return self._fetch("ALL", limit)

    def _fetch(self, criterion: str, limit: int) -> List[Tuple[str, bytes]]:
        if not self._conn:
            self.connect()
        typ, data = self._conn.uid("SEARCH", None, criterion)
        if typ != "OK":
            return []
        uids = data[0].split()[-max(0, int(limit)):] if limit > 0 and data and data[0] else []
        out = []
        mark_read = getattr(self.config, "imap_mark_read", False)
        for uid in uids:
            # BODY.PEEK[] preserves unread state unless explicitly configured otherwise.
            typ, msg_data = self._conn.uid("FETCH", uid, "(BODY.PEEK[])")
            if typ != "OK" or not msg_data:
                continue
            raw = next(
                (item[1] for item in msg_data
                 if isinstance(item, tuple) and len(item) > 1 and isinstance(item[1], bytes)),
                None,
            )
            if raw is None:
                continue
            out.append((uid.decode() if isinstance(uid, bytes) else str(uid), raw))
            if mark_read:
                self._conn.uid("STORE", uid, "+FLAGS", "\\Seen")
        return out

    def uidvalidity(self) -> str:
        """Return the current mailbox UIDVALIDITY, or empty string if unavailable."""
        try:
            if not self._conn:
                self.connect()
            typ, data = self._conn.select(self.config.imap_mailbox or "INBOX")
            if typ == "OK" and data:
                return str(data[0].decode() if isinstance(data[0], bytes) else data[0])
        except Exception:
            return ""
        return ""

    def fetch_unseen_uids(self, limit: int = 50) -> List[str]:
        """Return just the UNSEEN UIDs (no body fetch) for dedup filtering."""
        if not self._conn:
            self.connect()
        typ, data = self._conn.uid("SEARCH", None, "UNSEEN")
        if typ != "OK":
            return []
        return [u.decode() if isinstance(u, bytes) else str(u)
                for u in (data[0].split()[-max(0, int(limit)):] if limit > 0 and data and data[0] else [])]

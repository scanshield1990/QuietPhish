import sqlite3
from pathlib import Path


class M365History:
    def __init__(self):
        folder = Path.home() / "AppData" / "Local" / "SSSH" / "PhishGuard"
        folder.mkdir(parents=True, exist_ok=True)

        self.database = folder / "m365_history.db"

        with sqlite3.connect(self.database) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processed_messages (
                    message_id TEXT PRIMARY KEY,
                    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def is_processed(self, message_id):
        with sqlite3.connect(self.database) as conn:
            result = conn.execute(
                "SELECT 1 FROM processed_messages WHERE message_id = ?",
                (message_id,)
            ).fetchone()

        return result is not None

    def mark_processed(self, message_id):
        with sqlite3.connect(self.database) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO processed_messages (message_id)
                VALUES (?)
                """,
                (message_id,)
            )
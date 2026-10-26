import sqlite3
import hashlib
from pathlib import Path

DATABASE = Path(__file__).resolve().parent / "processed_samples.db"


def initialize_database():
    with sqlite3.connect(DATABASE) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS processed_samples (
                sha256 TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                processed_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

    print("[PhishGuard] Sample tracking database initialized.")

def calculate_sha256(file_path):
    """Calculate the SHA-256 fingerprint of an email sample."""
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as email_file:
        for chunk in iter(lambda: email_file.read(65536), b""):
            sha256.update(chunk)

    return sha256.hexdigest()

def is_sample_processed(sha256):
    """Check whether an email sample has already been processed."""
    with sqlite3.connect(DATABASE) as connection:
        result = connection.execute(
            "SELECT 1 FROM processed_samples WHERE sha256 = ?",
            (sha256,)
        ).fetchone()

    return result is not None

def mark_sample_processed(sha256, file_path):
    """Record a successfully processed email sample."""
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO processed_samples
            (sha256, file_path)
            VALUES (?, ?)
            """,
            (sha256, str(file_path))
        )

    print(f"[PhishGuard] Recorded processed sample: {sha256}")

if __name__ == "__main__":
    initialize_database()
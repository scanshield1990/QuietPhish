import sqlite3
from pathlib import Path

from sample_tracker import DATABASE, calculate_sha256

CORPUS_PATH = Path.home() / "Documents" / "email-corpus" / "submissions"


def establish_baseline():
    print("[PhishGuard] Establishing email corpus baseline...")

    files = list(CORPUS_PATH.rglob("*.eml"))

    with sqlite3.connect(DATABASE) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS baseline_samples (
                sha256 TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                baseline_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        for file_path in files:
            sha256 = calculate_sha256(file_path)

            connection.execute(
                """
                INSERT OR IGNORE INTO baseline_samples
                (sha256, file_path)
                VALUES (?, ?)
                """,
                (sha256, str(file_path))
            )

    print(f"[SUCCESS] Baseline established from {len(files)} email files.")


if __name__ == "__main__":
    establish_baseline()
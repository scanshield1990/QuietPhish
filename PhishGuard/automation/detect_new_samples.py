import sqlite3
from pathlib import Path

from sample_tracker import DATABASE, calculate_sha256

CORPUS_PATH = Path.home() / "Documents" / "email-corpus" / "submissions"


def detect_new_samples():
    print("[PhishGuard] Checking for new email samples...")

    new_samples = []

    with sqlite3.connect(DATABASE) as connection:
        for file_path in CORPUS_PATH.rglob("*.eml"):
            sha256 = calculate_sha256(file_path)

            baseline = connection.execute(
                "SELECT 1 FROM baseline_samples WHERE sha256 = ?",
                (sha256,)
            ).fetchone()

            processed = connection.execute(
                "SELECT 1 FROM processed_samples WHERE sha256 = ?",
                (sha256,)
            ).fetchone()

            if not baseline and not processed:
                new_samples.append(file_path)

    print(f"[PhishGuard] New samples detected: {len(new_samples)}")

    for sample in new_samples[:20]:
        print(f"[NEW] {sample.name}")

    return new_samples


if __name__ == "__main__":
    detect_new_samples()
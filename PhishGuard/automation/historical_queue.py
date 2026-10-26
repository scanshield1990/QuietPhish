import sqlite3
from pathlib import Path

from sample_tracker import DATABASE, calculate_sha256

CORPUS_PATH = Path.home() / "Documents" / "email-corpus" / "submissions"

HISTORICAL_BATCH_SIZE = 3
HISTORICAL_INTERVAL = 10800  # 3 hours


def get_historical_samples(limit=HISTORICAL_BATCH_SIZE):
    """
    Retrieve historical email samples that have not
    already been investigated by PhishGuard.
    """

    historical_samples = []

    with sqlite3.connect(DATABASE) as connection:
        rows = connection.execute(
            """
            SELECT b.file_path, b.sha256
            FROM baseline_samples AS b
            LEFT JOIN processed_samples AS p
                ON b.sha256 = p.sha256
            WHERE p.sha256 IS NULL
            ORDER BY b.file_path ASC
            """
        ).fetchall()

    for file_path, expected_sha256 in rows:
        sample = Path(file_path)

        # Skip files that no longer exist.
        if not sample.is_file():
            continue

        # Verify the file still matches its baseline fingerprint.
        if calculate_sha256(sample) != expected_sha256:
            continue

        historical_samples.append(sample)

        if len(historical_samples) >= limit:
            break

    return historical_samples

if __name__ == "__main__":
    samples = get_historical_samples()

    print(f"Historical samples selected: {len(samples)}")

    for sample in samples:
        print(sample.name)

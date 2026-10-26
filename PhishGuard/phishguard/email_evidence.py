from __future__ import annotations

import hashlib
import os
from pathlib import Path
from uuid import UUID


def _evidence_path(report_dir: str, report_id: str) -> Path:
    # Validate the report ID to prevent directory traversal.
    normalized_id = UUID(hex=report_id).hex
    return Path(report_dir) / "original_emails" / f"{normalized_id}.eml"


def save_original_email(
    report_dir: str,
    report_id: str,
    raw_email: bytes,
) -> dict:
    """Preserve original MIME evidence without overwriting existing files."""

    if not isinstance(raw_email, bytes):
        raise TypeError("Original email evidence must be bytes.")

    evidence_path = _evidence_path(report_dir, report_id)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)

    # Exclusive creation prevents overwriting existing evidence.
    with evidence_path.open("xb") as evidence_file:
        evidence_file.write(raw_email)
        evidence_file.flush()
        os.fsync(evidence_file.fileno())

    return {
        "filename": evidence_path.name,
        "sha256": hashlib.sha256(raw_email).hexdigest(),
        "size": len(raw_email),
    }


def load_original_email(report_dir: str, report_id: str) -> bytes:
    """Retrieve preserved original MIME evidence."""

    evidence_path = _evidence_path(report_dir, report_id)
    return evidence_path.read_bytes()
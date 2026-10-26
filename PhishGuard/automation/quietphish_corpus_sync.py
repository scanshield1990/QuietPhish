"""Synchronize an existing local email-corpus Git checkout.

Set QUIETPHISH_CORPUS_PATH to select a different checkout. The checkout is
not included or cloned automatically; review its license and contents before
redistributing any email samples.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


# Layout of a portable QuietPhish workspace:
# QuietPhish/email-corpus and QuietPhish/PhishGuard/automation/corpus_sync.py
_WORKSPACE_CORPUS = Path(__file__).resolve().parents[2] / "email-corpus"
_LEGACY_CORPUS = Path.home() / "Documents" / "email-corpus"


def _corpus_path() -> Path:
    configured = os.environ.get("QUIETPHISH_CORPUS_PATH", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    if (_WORKSPACE_CORPUS / ".git").exists():
        return _WORKSPACE_CORPUS
    return _LEGACY_CORPUS


# Retain the existing module-level name for scripts that import it.
CORPUS_PATH = _corpus_path()


def sync_email_corpus() -> bool:
    """Fast-forward the local checkout; return True only on success."""
    print("[QuietPhish] Checking email-corpus for updates...")

    if not (CORPUS_PATH / ".git").exists():
        print(f"[ERROR] Email corpus Git checkout not found: {CORPUS_PATH}")
        return False

    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    try:
        result = subprocess.run(
            ["git", "pull", "--ff-only"],
            cwd=CORPUS_PATH,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            **kwargs,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"[ERROR] Git synchronization could not complete: {exc}")
        return False

    if result.returncode == 0:
        print("[SUCCESS] Git synchronization completed.")
        if result.stdout.strip():
            print(result.stdout.strip())
        return True

    print("[ERROR] Git synchronization failed.")
    if result.stderr.strip():
        print(result.stderr.strip())
    return False


if __name__ == "__main__":
    sync_email_corpus()
